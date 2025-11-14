"""
FastAPI Server for CarbonFlow Orchestrator
Exposes orchestrator state, forecast data, sensor data, and logs to the frontend.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configuration
FORECAST_OUTPUT_DIR = os.getenv("FORECAST_OUTPUT_DIR", str(project_root / "forecast-agent" / "output"))
ORCHESTRATOR_LOG_DIR = os.getenv("ORCHESTRATOR_LOG_DIR", str(project_root / "orchestrator" / "logs"))
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", "8000"))
API_SERVER_HOST = os.getenv("API_SERVER_HOST", "localhost")

# Initialize FastAPI app
app = FastAPI(title="CarbonFlow API Server", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_latest_forecast_file() -> Path | None:
    """Get the latest forecast JSON file from the output directory."""
    output_dir = Path(FORECAST_OUTPUT_DIR)
    
    if not output_dir.exists():
        return None
    
    forecast_files = list(output_dir.glob("forecast_*.json"))
    
    if not forecast_files:
        return None
    
    # Sort by filename (which contains timestamp) to get latest
    forecast_files.sort(key=lambda x: x.name, reverse=True)
    
    return forecast_files[0]


def read_forecast_data() -> dict[str, Any] | None:
    """Read the latest forecast data from JSON file."""
    forecast_file = get_latest_forecast_file()
    
    if forecast_file is None:
        return None
    
    try:
        with open(forecast_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_recent_logs(limit: int = 50) -> list[dict[str, Any]]:
    """
    Read recent log entries from orchestrator log file.
    
    Args:
        limit: Maximum number of log entries to return
        
    Returns:
        List of log entries with timestamp, level, and message
    """
    log_dir = Path(ORCHESTRATOR_LOG_DIR)
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"orchestrator_{today}.log"
    
    if not log_file.exists():
        return []
    
    logs = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Read last N lines
            for line in lines[-limit:]:
                line = line.strip()
                if not line:
                    continue
                
                # Parse log format: [timestamp] [LEVEL] message
                try:
                    if line.startswith("[") and "]" in line:
                        # Extract timestamp
                        timestamp_end = line.find("]", 1)
                        if timestamp_end > 0:
                            timestamp_str = line[1:timestamp_end]
                            
                            # Extract level
                            level_start = line.find("[", timestamp_end + 1)
                            level_end = line.find("]", level_start + 1) if level_start > 0 else -1
                            level = "INFO"
                            message = line[level_end + 1:].strip() if level_end > 0 else line[timestamp_end + 1:].strip()
                            
                            if level_start > 0 and level_end > 0:
                                level = line[level_start + 1:level_end]
                                message = line[level_end + 1:].strip()
                            
                            logs.append({
                                "timestamp": timestamp_str,
                                "level": level,
                                "message": message
                            })
                except Exception:
                    # If parsing fails, include raw line
                    logs.append({
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                        "level": "INFO",
                        "message": line
                    })
    except IOError:
        pass
    
    return logs[-limit:]


def get_orchestrator_state() -> dict[str, Any]:
    """
    Get current orchestrator state from log files.
    
    Returns:
        Dict with orchestrator state information
    """
    logs = get_recent_logs(limit=100)
    
    state = {
        "status": "unknown",
        "last_ingestion_timestamp": None,
        "last_forecast_timestamp": None,
        "last_enforcement_trigger": None,
        "last_accountability_trigger": None,
        "last_cycle_timestamp": None,
        "cycle_duration_seconds": None,
    }
    
    # Parse logs to extract state
    for log_entry in reversed(logs):  # Start from most recent
        message = log_entry.get("message", "")
        
        if "SensorIngestAgent completed at" in message:
            # Extract timestamp from message
            if "at" in message:
                try:
                    timestamp_str = message.split("at")[-1].strip()
                    state["last_ingestion_timestamp"] = timestamp_str
                except Exception:
                    pass
        
        elif "ForecastAgent completed at" in message:
            try:
                timestamp_str = message.split("at")[-1].strip()
                state["last_forecast_timestamp"] = timestamp_str
            except Exception:
                pass
        
        elif "GRAP-EnforcementAgent completed at" in message:
            try:
                timestamp_str = message.split("at")[-1].strip()
                state["last_enforcement_trigger"] = timestamp_str
            except Exception:
                pass
        
        elif "InterState-AccountabilityAgent completed at" in message:
            try:
                timestamp_str = message.split("at")[-1].strip()
                state["last_accountability_trigger"] = timestamp_str
            except Exception:
                pass
        
        elif "Starting orchestrator cycle at" in message:
            try:
                timestamp_str = message.split("at")[-1].strip()
                state["last_cycle_timestamp"] = timestamp_str
            except Exception:
                pass
        
        elif "Cycle completed in" in message:
            try:
                # Extract duration: "Cycle completed in X.X seconds"
                duration_str = message.split("in")[-1].split("seconds")[0].strip()
                state["cycle_duration_seconds"] = float(duration_str)
            except Exception:
                pass
    
    # Determine overall status
    if state["last_cycle_timestamp"]:
        # Check if cycle was recent (within last hour)
        try:
            last_cycle = datetime.fromisoformat(state["last_cycle_timestamp"].replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            hours_since_cycle = (now - last_cycle).total_seconds() / 3600
            
            if hours_since_cycle < 1:
                state["status"] = "operational"
            elif hours_since_cycle < 24:
                state["status"] = "idle"
            else:
                state["status"] = "inactive"
        except Exception:
            state["status"] = "unknown"
    
    return state


def read_sensor_data() -> dict[str, Any] | None:
    """
    Read latest sensor data using orchestrator's function.
    This is a simplified version that reads from S3 or uses file-based approach.
    """
    # Try to read from S3 first
    bucket_name = os.getenv("S3_BUCKET_NAME")
    
    if bucket_name:
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client("s3")
            prefix = "data/"
            
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
            )
            
            if "Contents" in response and len(response["Contents"]) > 0:
                objects = sorted(
                    response["Contents"],
                    key=lambda x: x["LastModified"],
                    reverse=True,
                )
                latest_object = objects[0]
                object_key = latest_object["Key"]
                
                obj_response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                content = obj_response["Body"].read().decode("utf-8")
                data = json.loads(content)
                
                # Parse list data into structured format
                if isinstance(data, list):
                    return _parse_sensor_data_list(data)
                elif isinstance(data, dict):
                    return data
        except Exception:
            pass
    
    # Fallback: return None (frontend can handle this)
    return None


def _parse_sensor_data_list(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse sensor data from JSON array into structured format."""
    result: dict[str, Any] = {
        "cpcb_data": [],
        "nasa_data": None,
        "dss_data": None
    }
    
    if not data or not isinstance(data, list):
        return result
    
    # Extract CPCB records
    cpcb_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'CPCB']
    
    if cpcb_records:
        stations_dict: dict[str, dict[str, Any]] = {}
        
        for record in cpcb_records:
            station = record.get('station', 'Unknown')
            pollutant = record.get('pollutant_id', '')
            pollutant_avg = record.get('pollutant_avg')
            
            if station not in stations_dict:
                stations_dict[station] = {
                    'station': station,
                    'aqi': 0,
                    'pm25': None,
                    'pm10': None,
                    'timestamp': record.get('last_update') or record.get('date') or record.get('timestamp'),
                    'latitude': record.get('latitude'),
                    'longitude': record.get('longitude')
                }
            
            if pollutant == 'PM2.5' and pollutant_avg is not None:
                try:
                    pm25_val = float(pollutant_avg)
                    stations_dict[station]['pm25'] = pm25_val
                    stations_dict[station]['aqi'] = pm25_val
                except (ValueError, TypeError):
                    pass
            elif pollutant == 'PM10' and pollutant_avg is not None:
                try:
                    pm10_val = float(pollutant_avg)
                    stations_dict[station]['pm10'] = pm10_val
                except (ValueError, TypeError):
                    pass
        
        result["cpcb_data"] = list(stations_dict.values())
    
    # Extract NASA data
    nasa_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'NASA']
    if nasa_records:
        result["nasa_data"] = {
            "fire_count": len(nasa_records),
            "region": "Punjab/Haryana",
            "timestamp": nasa_records[0].get('acq_date') if nasa_records else None,
            "confidence_high": sum(1 for r in nasa_records if r.get('confidence', 0) > 70)
        }
    
    # Extract DSS data
    dss_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'DSS']
    if dss_records:
        stubble_pct = None
        vehicular_pct = None
        industrial_pct = None
        dust_pct = None
        
        for record in dss_records:
            source_name = str(record.get('source', '')).lower()
            percentage = record.get('percentage')
            
            if percentage is not None:
                try:
                    pct_val = float(percentage)
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
        
        result["dss_data"] = {
            "stubble_burning_percent": stubble_pct,
            "vehicular_percent": vehicular_pct,
            "industrial_percent": industrial_pct,
            "dust_percent": dust_pct,
            "timestamp": dss_records[0].get('date') if dss_records else None
        }
    
    return result


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CarbonFlow API Server",
        "version": "1.0.0",
        "endpoints": {
            "status": "/api/status",
            "forecast": "/api/forecast/latest",
            "sensors": "/api/sensors/latest",
            "logs": "/api/logs/recent"
        }
    }


@app.get("/api/status")
async def get_status():
    """Get orchestrator status and state."""
    try:
        state = get_orchestrator_state()
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/forecast/latest")
async def get_latest_forecast():
    """Get the latest forecast data."""
    try:
        forecast_data = read_forecast_data()
        if forecast_data is None:
            raise HTTPException(status_code=404, detail="No forecast data available")
        return forecast_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read forecast: {str(e)}")


@app.get("/api/sensors/latest")
async def get_latest_sensors():
    """Get the latest sensor data."""
    try:
        sensor_data = read_sensor_data()
        if sensor_data is None:
            raise HTTPException(status_code=404, detail="No sensor data available")
        return sensor_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read sensor data: {str(e)}")


@app.get("/api/logs/recent")
async def get_recent_logs_endpoint(limit: int = 50):
    """Get recent log entries."""
    try:
        logs = get_recent_logs(limit=min(limit, 200))  # Cap at 200
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@app.get("/api/agents/history")
async def get_agents_history():
    """Get agent execution history from logs."""
    try:
        logs = get_recent_logs(limit=100)
        
        history = {
            "sensor_ingest": [],
            "forecast": [],
            "enforcement": [],
            "accountability": []
        }
        
        for log_entry in logs:
            message = log_entry.get("message", "")
            timestamp = log_entry.get("timestamp", "")
            level = log_entry.get("level", "INFO")
            
            if "SensorIngestAgent" in message:
                if "completed" in message.lower() or "failed" in message.lower():
                    history["sensor_ingest"].append({
                        "timestamp": timestamp,
                        "status": "success" if "completed" in message.lower() else "failed",
                        "message": message
                    })
            
            elif "ForecastAgent" in message:
                if "completed" in message.lower() or "failed" in message.lower():
                    history["forecast"].append({
                        "timestamp": timestamp,
                        "status": "success" if "completed" in message.lower() else "failed",
                        "message": message
                    })
            
            elif "GRAP-EnforcementAgent" in message or "enforcement" in message.lower():
                if "completed" in message.lower() or "failed" in message.lower() or "triggered" in message.lower():
                    history["enforcement"].append({
                        "timestamp": timestamp,
                        "status": "triggered" if "triggered" in message.lower() else ("success" if "completed" in message.lower() else "failed"),
                        "message": message
                    })
            
            elif "InterState-AccountabilityAgent" in message or "accountability" in message.lower():
                if "completed" in message.lower() or "failed" in message.lower() or "triggered" in message.lower():
                    history["accountability"].append({
                        "timestamp": timestamp,
                        "status": "triggered" if "triggered" in message.lower() else ("success" if "completed" in message.lower() else "failed"),
                        "message": message
                    })
        
        # Reverse to show most recent first
        for key in history:
            history[key] = list(reversed(history[key][-10:]))  # Last 10 entries
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent history: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_SERVER_HOST, port=API_SERVER_PORT)

