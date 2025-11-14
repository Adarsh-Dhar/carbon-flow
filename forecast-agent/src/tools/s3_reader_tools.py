"""S3 data reading tools for ForecastAgent."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
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
    
    if not data or not isinstance(data, list):
        return result
    
    # Aggregate CPCB data - calculate average AQI from PM2.5 values
    # Check both 'source' (legacy) and 'data_source' (new) fields
    cpcb_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'CPCB']
    if cpcb_records:
        # Calculate average AQI from pollutant_avg values (PM2.5 is primary indicator)
        pm25_values = []
        pm10_values = []
        stations = []
        timestamps = []
        
        for record in cpcb_records:
            pollutant = record.get('pollutant_id', '')
            if pollutant == 'PM2.5':
                pm25_val = record.get('pollutant_avg')
                if pm25_val is not None:
                    try:
                        val = float(pm25_val)
                        if not (isinstance(pm25_val, float) and pd.isna(pm25_val)):
                            pm25_values.append(val)
                    except (ValueError, TypeError):
                        pass
            elif pollutant == 'PM10':
                pm10_val = record.get('pollutant_avg')
                if pm10_val is not None:
                    try:
                        val = float(pm10_val)
                        if not (isinstance(pm10_val, float) and pd.isna(pm10_val)):
                            pm10_values.append(val)
                    except (ValueError, TypeError):
                        pass
            
            station = record.get('station', 'Unknown')
            if station and station not in stations:
                stations.append(station)
            
            timestamp = record.get('last_update') or record.get('date') or record.get('timestamp')
            if timestamp and timestamp not in timestamps:
                timestamps.append(timestamp)
        
        # Calculate AQI from PM2.5 (simplified: PM2.5 value approximates AQI for high values)
        avg_pm25 = sum(pm25_values) / len(pm25_values) if pm25_values else None
        avg_pm10 = sum(pm10_values) / len(pm10_values) if pm10_values else None
        
        result["cpcb_data"] = {
            "aqi": avg_pm25,  # Use PM2.5 as AQI proxy
            "timestamp": timestamps[0] if timestamps else None,
            "station": stations[0] if stations else 'Unknown',
            "pm25": avg_pm25,
            "pm10": avg_pm10
        }
    
    # Aggregate NASA data - count fires
    # Check both 'source' (legacy) and 'data_source' (new) fields
    nasa_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'NASA']
    if nasa_records:
        fire_count = len(nasa_records)
        timestamps = [r.get('acq_date') or r.get('date') or r.get('timestamp') for r in nasa_records if r.get('acq_date') or r.get('date') or r.get('timestamp')]
        
        result["nasa_data"] = {
            "fire_count": fire_count,
            "region": "Punjab/Haryana",
            "timestamp": timestamps[0] if timestamps else None,
            "confidence_high": sum(1 for r in nasa_records if r.get('confidence', 0) > 70)
        }
    
    # Aggregate DSS data - extract percentages
    # DSS records have data_source='DSS' and the actual pollution source name is in the 'source' field
    # Check both 'data_source' (new) and 'source' (legacy) fields
    dss_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'DSS']
    if dss_records:
        stubble_pct = None
        vehicular_pct = None
        industrial_pct = None
        dust_pct = None
        
        for record in dss_records:
            # DSS records now have 'source' field with pollution source names (Stubble burning, Transport, etc.)
            # and 'percentage' field with the percentage value
            source_name = str(record.get('source', '')).lower()
            percentage = record.get('percentage')
            
            if percentage is not None:
                try:
                    pct_val = float(percentage)
                    
                    # Match based on source name
                    if 'stubble' in source_name or 'burning' in source_name:
                        stubble_pct = pct_val
                    elif 'transport' in source_name or 'vehicle' in source_name or 'vehicular' in source_name:
                        vehicular_pct = pct_val
                    elif 'industr' in source_name:
                        industrial_pct = pct_val
                    elif 'dust' in source_name:
                        dust_pct = pct_val
                except (ValueError, TypeError):
                    pass
        
        # Fallback: If we still don't have values, try to extract from raw_text field
        if stubble_pct is None or vehicular_pct is None:
            for record in dss_records:
                raw_text = str(record.get('raw_text', '')).lower()
                percentage = record.get('percentage')
                if percentage is not None:
                    try:
                        pct_val = float(percentage)
                        if 'stubble' in raw_text or 'burning' in raw_text:
                            if stubble_pct is None:
                                stubble_pct = pct_val
                        elif 'transport' in raw_text or 'vehicle' in raw_text or 'vehicular' in raw_text:
                            if vehicular_pct is None:
                                vehicular_pct = pct_val
                        elif 'industr' in raw_text:
                            if industrial_pct is None:
                                industrial_pct = pct_val
                        elif 'dust' in raw_text:
                            if dust_pct is None:
                                dust_pct = pct_val
                    except (ValueError, TypeError):
                        pass
        
        timestamps = [r.get('date') or r.get('timestamp') or r.get('last_update') for r in dss_records if r.get('date') or r.get('timestamp') or r.get('last_update')]
        
        result["dss_data"] = {
            "stubble_burning_percent": stubble_pct,
            "vehicular_percent": vehicular_pct,
            "industrial_percent": industrial_pct,
            "dust_percent": dust_pct,
            "timestamp": timestamps[0] if timestamps else None
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
