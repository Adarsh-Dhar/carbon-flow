"""
Tools for reading correlated sensor data and submitting CAQM reports.
Supports both AWS S3 and local mock JSON files for demo purposes.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from crewai.tools import tool
from pydantic import BaseModel, Field

# Tool result cache for fallback execution
TOOL_RESULT_CACHE: dict[str, Any] = {}


class ReadCorrelatedDataInput(BaseModel):
    """Input schema for read_correlated_data_tool."""

    bucket_name: str = Field(
        default="",
        description="S3 bucket name (leave empty to use mock data for demo)",
    )
    prefix: str = Field(
        default="data/",
        description="S3 object prefix for sensor data",
    )
    use_mock_data: bool = Field(
        default=True,
        description="Use mock JSON files instead of S3 for demo",
    )
    security_context: dict | None = Field(
        default=None,
        description="Security context for CrewAI compatibility",
    )


def debug_log(tool_name: str, message: str) -> None:
    """Log debug messages with timestamp."""
    timestamp = datetime.utcnow().isoformat()
    print(f"[DEBUG {timestamp}] Tool '{tool_name}': {message}")


def read_correlated_data() -> dict:
    """
    Read correlated sensor data from three mock JSON files.
    
    Reads from:
    - data/cpcb_latest.json (CPCB AQI data)
    - data/nasa_latest.json (NASA FIRMS fire events)
    - data/dss_latest.json (DSS stubble burning contribution)
    
    Returns:
        Dict containing combined correlated_evidence with all three data sources
    """
    debug_log("read_correlated_data", "Reading correlated data from local JSON files")
    
    correlated_evidence = {}
    
    # Define file paths relative to project root
    base_path = Path("interstate-accountability-agent/data")
    cpcb_file = base_path / "cpcb_latest.json"
    nasa_file = base_path / "nasa_latest.json"
    dss_file = base_path / "dss_latest.json"
    
    # Read CPCB data
    try:
        with open(cpcb_file, "r") as f:
            cpcb_data = json.load(f)
            correlated_evidence["cpcb_data"] = cpcb_data.get("stations", [])
            debug_log("read_correlated_data", f"Loaded CPCB data: {len(correlated_evidence['cpcb_data'])} stations")
    except FileNotFoundError:
        debug_log("read_correlated_data", f"CPCB file not found: {cpcb_file}")
        correlated_evidence["cpcb_data"] = []
        correlated_evidence["cpcb_error"] = "File not found"
    except json.JSONDecodeError as e:
        debug_log("read_correlated_data", f"CPCB JSON parse error: {str(e)}")
        correlated_evidence["cpcb_data"] = []
        correlated_evidence["cpcb_error"] = f"JSON parse error: {str(e)}"
    
    # Read NASA FIRMS data
    try:
        with open(nasa_file, "r") as f:
            nasa_data = json.load(f)
            correlated_evidence["nasa_data"] = nasa_data.get("fire_events", [])
            debug_log("read_correlated_data", f"Loaded NASA data: {len(correlated_evidence['nasa_data'])} fire events")
    except FileNotFoundError:
        debug_log("read_correlated_data", f"NASA file not found: {nasa_file}")
        correlated_evidence["nasa_data"] = []
        correlated_evidence["nasa_error"] = "File not found"
    except json.JSONDecodeError as e:
        debug_log("read_correlated_data", f"NASA JSON parse error: {str(e)}")
        correlated_evidence["nasa_data"] = []
        correlated_evidence["nasa_error"] = f"JSON parse error: {str(e)}"
    
    # Read DSS data
    try:
        with open(dss_file, "r") as f:
            dss_data = json.load(f)
            correlated_evidence["dss_data"] = {
                "stubble_burning_percent": dss_data.get("stubble_burning_contribution", {}).get("percent", 0),
                "timestamp": dss_data.get("data_timestamp", ""),
                "source": dss_data.get("source", "DSS"),
                "regional_breakdown": dss_data.get("regional_breakdown", {}),
            }
            debug_log("read_correlated_data", f"Loaded DSS data: {correlated_evidence['dss_data']['stubble_burning_percent']}% stubble burning")
    except FileNotFoundError:
        debug_log("read_correlated_data", f"DSS file not found: {dss_file}")
        correlated_evidence["dss_data"] = None
        correlated_evidence["dss_error"] = "File not found"
    except json.JSONDecodeError as e:
        debug_log("read_correlated_data", f"DSS JSON parse error: {str(e)}")
        correlated_evidence["dss_data"] = None
        correlated_evidence["dss_error"] = f"JSON parse error: {str(e)}"
    
    # Add timestamp
    correlated_evidence["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    debug_log("read_correlated_data", "Successfully combined all data sources into correlated_evidence")
    return correlated_evidence


def read_from_s3(bucket_name: str, prefix: str, retries: int = 3) -> dict:
    """
    Read the latest sensor data from AWS S3.
    
    Args:
        bucket_name: S3 bucket name
        prefix: Object prefix (e.g., 'data/')
        retries: Number of retry attempts
        
    Returns:
        Dict containing parsed sensor data
        
    Raises:
        Exception: If S3 read fails after all retries
    """
    debug_log("read_correlated_data", f"Reading from S3: s3://{bucket_name}/{prefix}")
    
    s3_client = boto3.client("s3")
    backoff_delay = 1  # Start with 1 second
    
    for attempt in range(retries):
        try:
            # List objects with prefix and sort by LastModified
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
            )
            
            if "Contents" not in response or len(response["Contents"]) == 0:
                return {
                    "error": "No data found",
                    "details": f"No objects found in s3://{bucket_name}/{prefix}",
                }
            
            # Sort by LastModified to get the latest file
            objects = sorted(
                response["Contents"],
                key=lambda x: x["LastModified"],
                reverse=True,
            )
            latest_object = objects[0]
            object_key = latest_object["Key"]
            
            debug_log("read_correlated_data", f"Reading latest object: {object_key}")
            
            # Get object content
            obj_response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = obj_response["Body"].read().decode("utf-8")
            
            # Parse JSON
            data = json.loads(content)
            
            # Validate required fields
            if "cpcb_data" not in data:
                return {
                    "error": "Invalid data format",
                    "details": "Missing required field: cpcb_data",
                }
            
            if "timestamp" not in data:
                data["timestamp"] = datetime.utcnow().isoformat() + "Z"
            
            debug_log("read_correlated_data", f"Successfully read data from S3 (attempt {attempt + 1})")
            
            # Cache result
            TOOL_RESULT_CACHE["read_correlated_data"] = data
            
            return data
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            debug_log("read_correlated_data", f"S3 error on attempt {attempt + 1}: {error_code} - {str(e)}")
            
            if attempt < retries - 1:
                debug_log("read_correlated_data", f"Retrying in {backoff_delay} seconds...")
                time.sleep(backoff_delay)
                backoff_delay *= 2  # Exponential backoff
            else:
                return {
                    "error": "S3 read failed",
                    "details": f"Failed after {retries} attempts: {str(e)}",
                }
                
        except json.JSONDecodeError as e:
            debug_log("read_correlated_data", f"JSON parse error: {str(e)}")
            return {
                "error": "Invalid JSON",
                "details": f"Failed to parse JSON content: {str(e)}",
            }
        except Exception as e:  # noqa: BLE001
            debug_log("read_correlated_data", f"Unexpected error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < retries - 1:
                time.sleep(backoff_delay)
                backoff_delay *= 2
            else:
                return {
                    "error": "Unexpected error",
                    "details": f"Failed after {retries} attempts: {str(e)}",
                }
    
    return {
        "error": "S3 read failed",
        "details": "Exhausted all retry attempts",
    }


@tool("Read correlated sensor data")
def read_correlated_data_tool(
    bucket_name: str = "",
    prefix: str = "data/",
    use_mock_data: bool = True,
    security_context: dict | None = None,
) -> dict:
    """
    Read and parse the latest sensor data from AWS S3 or mock files.
    
    This tool reads harmonized sensor data containing CPCB AQI measurements,
    NASA FIRMS fire events, and DSS stubble burning contributions.
    
    For demo purposes, reads from three local JSON files:
    - data/cpcb_latest.json
    - data/nasa_latest.json
    - data/dss_latest.json
    
    Args:
        bucket_name: S3 bucket name (leave empty to use mock data)
        prefix: S3 object prefix for sensor data
        use_mock_data: Use mock JSON files instead of S3 for demo
        security_context: Security context for CrewAI compatibility
        
    Returns:
        Dict containing correlated_evidence with cpcb_data, nasa_data, dss_data, and timestamp
    """
    debug_log("read_correlated_data_tool", f"Invoked with args: bucket_name={bucket_name}, use_mock_data={use_mock_data}")
    
    try:
        # Use mock data for demo if requested or if no bucket specified
        if use_mock_data or not bucket_name:
            result = read_correlated_data()
        else:
            result = read_from_s3(bucket_name, prefix)
        
        # Cache result
        TOOL_RESULT_CACHE["read_correlated_data_tool"] = result
        
        debug_log("read_correlated_data_tool", f"Tool completed with result type: {type(result).__name__}")
        return result
        
    except Exception as e:  # noqa: BLE001
        error_result = {
            "error": "Tool execution failed",
            "details": str(e),
        }
        debug_log("read_correlated_data_tool", f"Tool failed: {str(e)}")
        return error_result


class SendCAQMReportInput(BaseModel):
    """Input schema for send_caqm_report tool."""

    report_text: str = Field(
        description="The report text to send to CAQM",
    )
    security_context: dict | None = Field(
        default=None,
        description="Security context for CrewAI compatibility",
    )


@tool("Send report to CAQM")
def send_caqm_report(
    report_text: str,
    security_context: dict | None = None,
) -> str:
    """
    Send a legal report to the Commission for Air Quality Management (CAQM).
    
    This tool submits the generated accountability report to CAQM for official review
    and enforcement action. For demo purposes, it prints the report to console.
    
    Args:
        report_text: The report text to send to CAQM
        security_context: Security context for CrewAI compatibility
        
    Returns:
        JSON string with status and action confirmation
    """
    debug_log("send_caqm_report", "Invoked to send report to CAQM")
    
    # Print official communique
    print("--- OFFICIAL COMMUNIQUE ---")
    print(report_text)
    print("--- END OF COMMUNIQUE ---")
    
    # Return success status
    result = '{"status": "SUCCESS", "action": "Report sent to CAQM."}'
    
    debug_log("send_caqm_report", "Report successfully sent to CAQM")
    
    return result
