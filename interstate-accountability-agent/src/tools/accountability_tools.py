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

# Import new tools
from src.tools.surge_detection_tools import detect_surge
from src.tools.correlation_tools import correlate_fires, calculate_confidence_score
from src.tools.report_generation_tools import generate_report

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


class DetectSurgeInput(BaseModel):
    """Input schema for detect_surge_tool."""
    
    cpcb_data: list[dict[str, Any]] = Field(
        description="List of CPCB station data records"
    )
    security_context: dict | None = Field(
        default=None,
        description="Security context for CrewAI compatibility",
    )


@tool("Detect pollution surge at border stations")
def detect_surge_tool(
    cpcb_data: list[dict[str, Any]],
    security_context: dict | None = None,
) -> dict[str, Any]:
    """
    Detect pollution surges at Delhi border stations.
    
    Filters CPCB data for border stations and identifies stations with AQI
    exceeding the threshold (300).
    
    Args:
        cpcb_data: List of CPCB station data records
        security_context: Security context for CrewAI compatibility
        
    Returns:
        Dict with surge_stations list (serialized BorderStation objects)
    """
    debug_log("detect_surge_tool", f"Detecting surges in {len(cpcb_data)} CPCB records")
    
    try:
        surge_stations = detect_surge(cpcb_data)
        
        # Serialize to dict
        result = {
            "surge_stations": [station.to_dict() for station in surge_stations],
            "surge_count": len(surge_stations),
        }
        
        # Cache result
        TOOL_RESULT_CACHE["detect_surge_tool"] = result
        
        debug_log("detect_surge_tool", f"Detected {len(surge_stations)} surge(s)")
        return result
        
    except Exception as e:  # noqa: BLE001
        error_result = {
            "error": "Surge detection failed",
            "details": str(e),
            "surge_stations": [],
            "surge_count": 0,
        }
        debug_log("detect_surge_tool", f"Tool failed: {str(e)}")
        return error_result


class CorrelateFiresInput(BaseModel):
    """Input schema for correlate_fires_tool."""
    
    surge_stations: list[dict[str, Any]] = Field(
        description="List of surge station data (BorderStation objects as dicts)"
    )
    nasa_data: list[dict[str, Any]] = Field(
        description="List of NASA FIRMS fire event dictionaries"
    )
    security_context: dict | None = Field(
        default=None,
        description="Security context for CrewAI compatibility",
    )


@tool("Correlate fire events with pollution surges")
def correlate_fires_tool(
    surge_stations: list[dict[str, Any]],
    nasa_data: list[dict[str, Any]],
    security_context: dict | None = None,
) -> dict[str, Any]:
    """
    Correlate NASA FIRMS fire events with pollution surges at border stations.
    
    Uses haversine distance calculation to find fires within 200km of surge stations
    and within 48 hours of the surge timestamp.
    
    Args:
        surge_stations: List of surge station data (BorderStation objects as dicts)
        nasa_data: List of NASA FIRMS fire event dictionaries
        security_context: Security context for CrewAI compatibility
        
    Returns:
        Dict with correlation_results list (serialized CorrelationResult objects)
    """
    debug_log("correlate_fires_tool", f"Correlating {len(nasa_data)} fires with {len(surge_stations)} surge stations")
    
    try:
        # Convert dicts to BorderStation objects
        from src.models.data_models import BorderStation
        
        border_stations = [BorderStation.from_dict(st) for st in surge_stations]
        
        # Correlate fires
        correlation_results = correlate_fires(border_stations, nasa_data)
        
        # Serialize to dict
        result = {
            "correlation_results": [cr.to_dict() for cr in correlation_results],
            "total_fires": sum(cr.fire_count for cr in correlation_results),
        }
        
        # Cache result
        TOOL_RESULT_CACHE["correlate_fires_tool"] = result
        
        debug_log("correlate_fires_tool", f"Correlated {result['total_fires']} fires")
        return result
        
    except Exception as e:  # noqa: BLE001
        error_result = {
            "error": "Fire correlation failed",
            "details": str(e),
            "correlation_results": [],
            "total_fires": 0,
        }
        debug_log("correlate_fires_tool", f"Tool failed: {str(e)}")
        return error_result


class GenerateReportInput(BaseModel):
    """Input schema for generate_report_tool."""
    
    surge_station: dict[str, Any] = Field(
        description="Surge station data dictionary"
    )
    correlation_results: list[dict[str, Any]] = Field(
        description="List of correlation results (CorrelationResult objects as dicts)"
    )
    nasa_data_available: bool = Field(
        default=True,
        description="Whether NASA data is available"
    )
    dss_data_available: bool = Field(
        default=True,
        description="Whether DSS data is available"
    )
    dss_data: dict[str, Any] | None = Field(
        default=None,
        description="DSS data dictionary (optional)"
    )
    security_context: dict | None = Field(
        default=None,
        description="Security context for CrewAI compatibility",
    )


@tool("Generate CAQM accountability report")
def generate_report_tool(
    surge_station: dict[str, Any],
    correlation_results: list[dict[str, Any]],
    nasa_data_available: bool = True,
    dss_data_available: bool = True,
    dss_data: dict[str, Any] | None = None,
    security_context: dict | None = None,
) -> dict[str, Any]:
    """
    Generate complete CAQM accountability report.
    
    Creates a structured report with executive summary, surge details,
    fire correlation analysis, reasoning statement, confidence score,
    legal citations, and recommendations.
    
    Args:
        surge_station: Surge station data dictionary
        correlation_results: List of correlation results (CorrelationResult objects as dicts)
        nasa_data_available: Whether NASA data is available
        dss_data_available: Whether DSS data is available
        dss_data: DSS data dictionary (optional)
        security_context: Security context for CrewAI compatibility
        
    Returns:
        Dict with complete CAQM report (CAQMReport object as dict)
    """
    debug_log("generate_report_tool", "Generating CAQM accountability report")
    
    try:
        # Convert dicts to CorrelationResult objects
        from src.models.data_models import CorrelationResult
        
        correlation_objs = [CorrelationResult.from_dict(cr) for cr in correlation_results]
        
        # Generate report
        report = generate_report(
            surge_station,
            correlation_objs,
            nasa_data_available,
            dss_data_available,
            dss_data,
        )
        
        # Serialize to dict
        result = report.to_dict()
        
        # Cache result
        TOOL_RESULT_CACHE["generate_report_tool"] = result
        
        debug_log("generate_report_tool", f"Report generated with ID: {result.get('report_id')}")
        return result
        
    except Exception as e:  # noqa: BLE001
        error_result = {
            "error": "Report generation failed",
            "details": str(e),
        }
        debug_log("generate_report_tool", f"Tool failed: {str(e)}")
        return error_result
