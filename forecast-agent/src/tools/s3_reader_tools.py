"""S3 data reading tools for ForecastAgent."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def read_ingested_data_tool(
    bucket_name: str | None = None,
    object_key: str | None = None,
    security_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Read sensor data JSON files from AWS S3.
    
    Retrieves the latest ingested sensor data from S3 bucket containing CPCB AQI levels,
    NASA fire counts, and DSS source percentages. If no object_key is provided, fetches
    the most recent file based on timestamp.
    
    Args:
        bucket_name: S3 bucket name. If None, reads from S3_BUCKET_NAME environment variable
        object_key: Specific S3 object key. If None, fetches the latest file with prefix 'data/aqi_data_'
        security_context: CrewAI security context (unused, for compatibility)
        
    Returns:
        Dict containing parsed sensor data with the following structure:
        {
            "cpcb_data": {
                "aqi": float,
                "timestamp": str,
                "station": str,
                "pm25": float | None,
                "pm10": float | None
            },
            "nasa_data": {
                "fire_count": int,
                "region": str,
                "timestamp": str,
                "confidence_high": int | None
            },
            "dss_data": {
                "stubble_burning_percent": float,
                "vehicular_percent": float,
                "industrial_percent": float,
                "dust_percent": float | None,
                "timestamp": str
            },
            "data_quality": {
                "completeness": float,  # 0-1 scale
                "age_hours": float
            }
        }
        
        Or error dict: {"error": "...", "details": "..."}
        
    Raises:
        None - returns error dict instead of raising exceptions
    """
    # Get bucket name from parameter or environment
    if bucket_name is None:
        bucket_name = os.getenv('S3_BUCKET_NAME')
    
    if not bucket_name:
        return {
            "error": "S3 bucket name not provided",
            "details": "bucket_name parameter is None and S3_BUCKET_NAME environment variable is not set"
        }
    
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # If no object key provided, find the latest file
        if object_key is None:
            try:
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix='data/aqi_data_'
                )
                
                if 'Contents' not in response or len(response['Contents']) == 0:
                    return {
                        "error": "No data files found in S3",
                        "details": f"No objects found with prefix 'data/aqi_data_' in bucket {bucket_name}"
                    }
                
                # Sort by LastModified to get the latest file
                objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
                object_key = objects[0]['Key']
                
                print(f"[DEBUG] Found latest S3 object: {object_key}")
                
            except ClientError as e:
                return {
                    "error": "Failed to list S3 objects",
                    "details": f"ClientError: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
                }
        
        # Retrieve the object from S3
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            json_content = response['Body'].read().decode('utf-8')
            data = json.loads(json_content)
            
            print(f"[DEBUG] Successfully retrieved and parsed S3 object: {object_key}")
            
        except ClientError as e:
            return {
                "error": "Failed to retrieve S3 object",
                "details": f"ClientError: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            }
        except json.JSONDecodeError as e:
            return {
                "error": "Failed to parse JSON from S3 object",
                "details": f"JSONDecodeError: {str(e)}"
            }
        
        # Parse and extract data sections
        parsed_data = _parse_sensor_data(data)
        
        # Calculate data quality metrics
        data_quality = _calculate_data_quality(parsed_data)
        parsed_data["data_quality"] = data_quality
        
        return parsed_data
        
    except NoCredentialsError:
        return {
            "error": "AWS credentials not found",
            "details": "No AWS credentials available. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or configure IAM role"
        }
    except Exception as e:  # noqa: BLE001
        return {
            "error": "Unexpected error reading from S3",
            "details": f"{type(e).__name__}: {str(e)}"
        }


def _parse_sensor_data(data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Parse sensor data from JSON array into structured sections.
    
    Args:
        data: List of data records with 'source' field indicating CPCB, NASA, or DSS
        
    Returns:
        Dict with cpcb_data, nasa_data, and dss_data sections
    """
    result: dict[str, Any] = {
        "cpcb_data": None,
        "nasa_data": None,
        "dss_data": None
    }
    
    for record in data:
        source = record.get('source', '').upper()
        
        if source == 'CPCB':
            result["cpcb_data"] = {
                "aqi": record.get('aqi'),
                "timestamp": record.get('date') or record.get('timestamp'),
                "station": record.get('station', 'Unknown'),
                "pm25": record.get('pm25'),
                "pm10": record.get('pm10')
            }
        
        elif source == 'NASA':
            result["nasa_data"] = {
                "fire_count": record.get('fire_count', 0),
                "region": record.get('region', 'Unknown'),
                "timestamp": record.get('date') or record.get('timestamp'),
                "confidence_high": record.get('confidence_high')
            }
        
        elif source == 'DSS':
            result["dss_data"] = {
                "stubble_burning_percent": record.get('stubble_burning_percent', 0.0),
                "vehicular_percent": record.get('vehicular_percent', 0.0),
                "industrial_percent": record.get('industrial_percent', 0.0),
                "dust_percent": record.get('dust_percent'),
                "timestamp": record.get('date') or record.get('timestamp')
            }
    
    return result


def _calculate_data_quality(parsed_data: dict[str, Any]) -> dict[str, float]:
    """
    Calculate data quality metrics based on completeness and age.
    
    Args:
        parsed_data: Parsed sensor data with cpcb_data, nasa_data, dss_data sections
        
    Returns:
        Dict with completeness (0-1) and age_hours metrics
    """
    # Calculate completeness (how many data sources are present)
    sources_present = sum([
        parsed_data["cpcb_data"] is not None,
        parsed_data["nasa_data"] is not None,
        parsed_data["dss_data"] is not None
    ])
    completeness = sources_present / 3.0
    
    # Calculate age in hours (use most recent timestamp)
    timestamps = []
    for key in ["cpcb_data", "nasa_data", "dss_data"]:
        if parsed_data[key] and parsed_data[key].get("timestamp"):
            timestamps.append(parsed_data[key]["timestamp"])
    
    age_hours = 0.0
    if timestamps:
        try:
            # Parse the most recent timestamp
            most_recent = max(timestamps)
            data_time = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            age_hours = (current_time - data_time).total_seconds() / 3600.0
        except (ValueError, TypeError) as e:
            print(f"[DEBUG] Failed to calculate data age: {e}")
            age_hours = 0.0
    
    return {
        "completeness": completeness,
        "age_hours": age_hours
    }
