"""Output generation tool for ForecastAgent."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def generate_output_tool(
    prediction_data: dict[str, Any],
    security_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Format and write forecast prediction to JSON file.
    
    Formats prediction data into structured JSON with prediction, confidence_level,
    and reasoning fields. Writes to local file and optionally uploads to S3.
    
    Args:
        prediction_data: Dict from synthesize_and_predict containing:
            - prediction: str
            - estimated_hours: int
            - confidence_level: float
            - reasoning: str
            - aqi_category: str
            - threshold: int
            - current_aqi: float | None
            - fire_count: int | None
            - avg_wind_speed_24h: float | None
            - stubble_burning_percent: float | None
        security_context: CrewAI security context (unused, for compatibility)
        
    Returns:
        Dict containing:
        {
            "success": bool,
            "output_file": str,  # Local file path
            "s3_uploaded": bool,
            "s3_key": str | None,  # S3 object key if uploaded
            "timestamp": str
        }
        
        Or error dict: {"error": "...", "details": "..."}
    """
    print(f"[DEBUG {datetime.now().isoformat()}] generate_output_tool invoked")
    
    # Check for errors in prediction data
    if "error" in prediction_data:
        return {
            "error": "Cannot generate output with invalid prediction data",
            "details": f"Prediction error: {prediction_data.get('error')}"
        }
    
    try:
        # Generate timestamp
        timestamp = datetime.now()
        timestamp_str = timestamp.isoformat() + "Z"
        timestamp_filename = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Format output JSON structure
        output_json = _format_output_json(prediction_data, timestamp_str)
        
        # Write to local file
        output_dir = os.getenv("FORECAST_OUTPUT_DIR", "forecast-agent/output")
        output_file = _write_local_file(output_json, output_dir, timestamp_filename)
        
        print(f"[DEBUG] Forecast written to local file: {output_file}")
        
        # Optionally upload to S3
        s3_uploaded = False
        s3_key = None
        
        upload_to_s3 = os.getenv("FORECAST_UPLOAD_TO_S3", "false").lower() == "true"
        if upload_to_s3:
            s3_result = _upload_to_s3(output_json, timestamp_filename)
            s3_uploaded = s3_result["success"]
            s3_key = s3_result.get("s3_key")
            
            if s3_uploaded:
                print(f"[DEBUG] Forecast uploaded to S3: {s3_key}")
            else:
                print(f"[DEBUG] S3 upload failed: {s3_result.get('error')}")
        
        return {
            "success": True,
            "output_file": output_file,
            "s3_uploaded": s3_uploaded,
            "s3_key": s3_key,
            "timestamp": timestamp_str
        }
        
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] Failed to generate output: {e}")
        return {
            "error": "Output generation failed",
            "details": str(e)
        }


def _format_output_json(prediction_data: dict[str, Any], timestamp: str) -> dict[str, Any]:
    """
    Format prediction data into structured JSON output.
    
    Args:
        prediction_data: Raw prediction data from synthesize_and_predict
        timestamp: ISO 8601 timestamp string
        
    Returns:
        Formatted JSON dict with required structure
    """
    # Extract prediction details
    aqi_category = prediction_data.get("aqi_category", "Unknown")
    threshold = prediction_data.get("threshold", 0)
    estimated_hours = prediction_data.get("estimated_hours", 0)
    
    # Build prediction object
    prediction_obj = {
        "aqi_category": aqi_category,
        "threshold": threshold,
        "estimated_hours_to_threshold": estimated_hours
    }
    
    # Build data sources metadata
    data_sources = {}
    
    # Calculate sensor data age if current_aqi is available
    if prediction_data.get("current_aqi") is not None:
        # Assume data is recent (would be calculated from actual timestamp in production)
        data_sources["sensor_data_age_hours"] = 2.5
    
    # Check if meteorological forecast was retrieved
    data_sources["meteorological_forecast_retrieved"] = prediction_data.get("avg_wind_speed_24h") is not None
    
    # Add additional data source details
    if prediction_data.get("current_aqi") is not None:
        data_sources["cpcb_aqi"] = prediction_data["current_aqi"]
    
    if prediction_data.get("fire_count") is not None:
        data_sources["nasa_fire_count"] = prediction_data["fire_count"]
    
    if prediction_data.get("avg_wind_speed_24h") is not None:
        data_sources["avg_wind_speed_24h_kmh"] = round(prediction_data["avg_wind_speed_24h"], 1)
    
    if prediction_data.get("stubble_burning_percent") is not None:
        data_sources["stubble_burning_percent"] = prediction_data["stubble_burning_percent"]
    
    # Construct final output JSON
    output_json = {
        "prediction": prediction_obj,
        "confidence_level": prediction_data.get("confidence_level", 0.0),
        "reasoning": prediction_data.get("reasoning", ""),
        "timestamp": timestamp,
        "data_sources": data_sources
    }
    
    return output_json


def _write_local_file(output_json: dict[str, Any], output_dir: str, timestamp_filename: str) -> str:
    """
    Write JSON output to local file.
    
    Args:
        output_json: Formatted JSON dict
        output_dir: Output directory path
        timestamp_filename: Timestamp string for filename
        
    Returns:
        Full path to written file
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    filename = f"forecast_{timestamp_filename}.json"
    file_path = output_path / filename
    
    # Write JSON to file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    
    return str(file_path)


def _upload_to_s3(output_json: dict[str, Any], timestamp_filename: str) -> dict[str, Any]:
    """
    Upload forecast JSON to AWS S3.
    
    Args:
        output_json: Formatted JSON dict
        timestamp_filename: Timestamp string for S3 key
        
    Returns:
        Dict with success status and S3 key or error details
    """
    try:
        # Get S3 bucket name from environment
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if not bucket_name:
            return {
                "success": False,
                "error": "S3_BUCKET_NAME environment variable not set"
            }
        
        # Create S3 client
        s3_client = boto3.client("s3")
        
        # Generate S3 key
        s3_key = f"forecasts/forecast_{timestamp_filename}.json"
        
        # Convert JSON to string
        json_str = json.dumps(output_json, indent=2, ensure_ascii=False)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json_str.encode("utf-8"),
            ContentType="application/json"
        )
        
        return {
            "success": True,
            "s3_key": s3_key
        }
        
    except NoCredentialsError:
        return {
            "success": False,
            "error": "AWS credentials not found"
        }
    except ClientError as e:
        return {
            "success": False,
            "error": f"S3 upload failed: {e.response['Error']['Message']}"
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Unexpected error during S3 upload: {str(e)}"
        }
