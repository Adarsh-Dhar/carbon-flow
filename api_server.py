"""
FastAPI Server for CarbonFlow Orchestrator
Exposes orchestrator state, forecast data, sensor data, and logs to the frontend.
"""

from __future__ import annotations

import json
import os
import sys
import importlib.util
import io
import contextlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from crewai import Crew, Process

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

# Agent directories
forecast_agent_dir = project_root / "forecast-agent"

# Configure Gemini API key to work with CrewAI's OpenAI-compatible interface
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = gemini_key
    os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
    os.environ["OPENAI_MODEL_NAME"] = "gemini-2.0-flash"
    os.environ.setdefault("OPENAI_API_BASE", os.environ["OPENAI_BASE_URL"])
    os.environ.setdefault("MODEL_NAME", "gemini-2.0-flash")
    os.environ.setdefault("MODEL", "gemini-2.0-flash")

# Store original sys.path for agent imports
original_sys_path = sys.path.copy()

def remove_agent_dirs_from_path():
    """Remove all agent directories from sys.path to avoid conflicts."""
    agent_dirs = [str(forecast_agent_dir)]
    sys.path = [p for p in sys.path if p not in agent_dirs]

# Lazy load agent modules (will be loaded when needed)
run_forecast_cycle = None

def load_forecast_agent():
    """Load forecast agent module."""
    global run_forecast_cycle
    if run_forecast_cycle is not None:
        return
    
    remove_agent_dirs_from_path()
    sys.path.insert(0, str(forecast_agent_dir))
    
    try:
        forecast_main_path = forecast_agent_dir / "src" / "main.py"
        forecast_main_spec = importlib.util.spec_from_file_location(
            "forecast_main", forecast_main_path
        )
        forecast_main = importlib.util.module_from_spec(forecast_main_spec)
        sys.modules["forecast_main"] = forecast_main
        forecast_main_spec.loader.exec_module(forecast_main)
        run_forecast_cycle = forecast_main.run_forecast_cycle
    finally:
        sys.path = original_sys_path.copy()

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
                            
                            # Map log levels to frontend types
                            level_mapping = {
                                "INFO": "info",
                                "WARNING": "warning",
                                "ERROR": "error",
                                "SUCCESS": "success"
                            }
                            mapped_level = level_mapping.get(level.upper(), "info")
                            
                            logs.append({
                                "timestamp": timestamp_str,
                                "level": mapped_level,
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


def _normalize_timestamp(timestamp: Any) -> str | None:
    """Normalize various timestamp formats into ISO 8601 string."""
    if timestamp is None:
        return None

    if isinstance(timestamp, (int, float)):
        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except (ValueError, OSError, OverflowError):
            return None

    ts_str = str(timestamp).strip()
    if not ts_str:
        return None

    # Already ISO formatted?
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    # Known CPCB formats (e.g., "14-11-2025 08:00:00")
    known_formats = (
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for fmt in known_formats:
        try:
            dt = datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue

    return None


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
        "nasa_data": [],
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
                    'timestamp': _normalize_timestamp(
                        record.get('last_update') or record.get('date') or record.get('timestamp')
                    ),
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
        
        # Add category to each station
        for station_data in stations_dict.values():
            aqi = station_data.get('aqi', 0)
            if aqi <= 50:
                station_data['category'] = 'Good'
            elif aqi <= 100:
                station_data['category'] = 'Satisfactory'
            elif aqi <= 200:
                station_data['category'] = 'Moderate'
            elif aqi <= 300:
                station_data['category'] = 'Poor'
            elif aqi <= 400:
                station_data['category'] = 'Very Poor'
            else:
                station_data['category'] = 'Severe'
            # Ensure lat/lon are floats
            if station_data.get('latitude'):
                station_data['lat'] = float(station_data['latitude'])
            if station_data.get('longitude'):
                station_data['lon'] = float(station_data['longitude'])
        
        result["cpcb_data"] = list(stations_dict.values())
    
    # Extract NASA data - return full array of fire hotspots
    nasa_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'NASA']
    if nasa_records:
        nasa_fire_data = []
        for record in nasa_records:
            try:
                fire_data = {
                    'lat': float(record.get('latitude', 0)),
                    'lon': float(record.get('longitude', 0)),
                    'brightness': float(record.get('brightness', 0)),
                    'confidence': float(record.get('confidence', 0)),
                    'timestamp': _normalize_timestamp(
                        record.get('timestamp')
                        or f"{record.get('acq_date', '')} {record.get('acq_time', '')}".strip()
                        or record.get('acq_date')
                    )
                    or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
                }
                nasa_fire_data.append(fire_data)
            except (ValueError, TypeError):
                continue
        result["nasa_data"] = nasa_fire_data
    
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
            "stubble_burning_percent": stubble_pct or 0,
            "affected_area_km2": 0,  # Default if not available
            "timestamp": _normalize_timestamp(
                dss_records[0].get('date') or dss_records[0].get('timestamp')
            ) or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        }
    
    return result


def transform_orchestrator_status(state: dict[str, Any]) -> dict[str, Any]:
    """Transform orchestrator state to match OrchestratorStatus type."""
    # Determine agent statuses
    def get_agent_status(last_timestamp: str | None) -> dict[str, Any]:
        if last_timestamp:
            try:
                # Check if timestamp is recent (within last hour)
                ts = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
                now = datetime.now(tz=timezone.utc)
                hours_since = (now - ts).total_seconds() / 3600
                if hours_since < 24:
                    return {
                        "last_run": last_timestamp,
                        "status": "available"
                    }
            except Exception:
                pass
        return {
            "last_run": last_timestamp,
            "status": "unavailable"
        }
    
    return {
        "status": state.get("status", "unknown"),
        "last_run": state.get("last_cycle_timestamp") or datetime.now(tz=timezone.utc).isoformat(),
        "cycle_duration_seconds": state.get("cycle_duration_seconds", 0),
        "agents": {
            "sensor_ingest": get_agent_status(state.get("last_ingestion_timestamp")),
            "forecast": get_agent_status(state.get("last_forecast_timestamp"))
        }
    }


def transform_forecast_data(forecast_data: dict[str, Any], forecast_file: Path | None = None) -> dict[str, Any]:
    """Transform raw forecast data to match ForecastLatest type."""
    prediction_data = forecast_data.get("prediction", {})
    data_sources = forecast_data.get("data_sources", {})
    
    # Extract AQI category
    aqi_category = prediction_data.get("aqi_category", "Moderate")
    if isinstance(aqi_category, str):
        # Ensure it matches TypeScript enum
        valid_categories = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
        if aqi_category not in valid_categories:
            # Try to infer from threshold
            threshold = prediction_data.get("threshold", 0)
            if threshold >= 401:
                aqi_category = "Severe"
            elif threshold >= 301:
                aqi_category = "Very Poor"
            elif threshold >= 201:
                aqi_category = "Poor"
            elif threshold >= 101:
                aqi_category = "Moderate"
            elif threshold >= 51:
                aqi_category = "Satisfactory"
            else:
                aqi_category = "Good"
    
    # Calculate predicted_aqi from current AQI or threshold
    predicted_aqi = data_sources.get("cpcb_aqi", 0)
    if predicted_aqi == 0:
        predicted_aqi = prediction_data.get("threshold", 0)
    
    # Get ETA hours
    eta_hours = prediction_data.get("estimated_hours_to_threshold", 0)
    
    # Build prediction object
    prediction = {
        "aqi_category": aqi_category,
        "confidence_level": forecast_data.get("confidence_level", 0),
        "reasoning": forecast_data.get("reasoning", ""),
        "data_sources": {
            "cpcb_aqi": data_sources.get("cpcb_aqi", 0),
            "nasa_fire_count": data_sources.get("nasa_fire_count", 0),
            "stubble_burning_percent": data_sources.get("stubble_burning_percent", 0),
            "avg_wind_direction_24h_deg": data_sources.get("avg_wind_direction_24h_deg", 0),
            "avg_wind_speed_24h_kmh": data_sources.get("avg_wind_speed_24h_kmh", 0)
        },
        "timestamp": forecast_data.get("timestamp", datetime.now(tz=timezone.utc).isoformat()),
        "predicted_aqi": predicted_aqi,
        "eta_hours": eta_hours
    }
    
    # Generate artifacts list
    artifacts = []
    if forecast_file:
        artifacts.append(forecast_file.name)
    
    return {
        "prediction": prediction,
        "artifacts": artifacts
    }


def get_forecast_history(days: int = 7) -> list[dict[str, Any]]:
    """Get forecast history for the last N days."""
    output_dir = Path(FORECAST_OUTPUT_DIR)
    
    if not output_dir.exists():
        return []
    
    forecast_files = list(output_dir.glob("forecast_*.json"))
    if not forecast_files:
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    history = []
    
    for forecast_file in forecast_files:
        try:
            # Parse timestamp from filename
            filename = forecast_file.stem
            if not filename.startswith("forecast_"):
                continue
            
            timestamp_str = filename.replace("forecast_", "")
            file_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if file_timestamp >= cutoff_date:
                with open(forecast_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    data_sources = data.get("data_sources", {})
                    history.append({
                        "timestamp": file_timestamp.isoformat(),
                        "aqi": data_sources.get("cpcb_aqi", 0),
                        "fire_count": data_sources.get("nasa_fire_count", 0),
                        "stubble_percent": data_sources.get("stubble_burning_percent", 0)
                    })
        except (ValueError, json.JSONDecodeError, Exception):
            continue
    
    # Sort by timestamp (oldest first)
    history.sort(key=lambda x: x.get("timestamp", ""))
    
    return history


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
        return transform_orchestrator_status(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/forecast/latest")
async def get_latest_forecast():
    """Get the latest forecast data."""
    try:
        forecast_file = get_latest_forecast_file()
        forecast_data = read_forecast_data()
        if forecast_data is None:
            raise HTTPException(status_code=404, detail="No forecast data available")
        return transform_forecast_data(forecast_data, forecast_file)
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
            "forecast": []
        }
        
        for log_entry in logs:
            message = log_entry.get("message", "")
            timestamp = log_entry.get("timestamp", "")
            level = log_entry.get("level", "INFO")
            
            if "SensorIngestAgent" in message:
                if "completed" in message.lower() or "failed" in message.lower():
                    history["sensor_ingest"].append({
                        "timestamp": timestamp,
                        "status": "success" if "completed" in message.lower() else "failure",
                        "message": message
                    })
            
            elif "ForecastAgent" in message:
                if "completed" in message.lower() or "failed" in message.lower():
                    history["forecast"].append({
                        "timestamp": timestamp,
                        "status": "success" if "completed" in message.lower() else "failure",
                        "message": message
                    })
            
        # Reverse to show most recent first
        for key in history:
            history[key] = list(reversed(history[key][-10:]))  # Last 10 entries
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent history: {str(e)}")


@app.get("/api/forecast/history")
async def get_forecast_history_endpoint(days: int = 7):
    """Get forecast history for the last N days."""
    try:
        history = get_forecast_history(days=min(days, 30))  # Cap at 30 days
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get forecast history: {str(e)}")


@app.post("/api/agents/forecast/run")
async def run_forecast_agent():
    """Run forecast cycle agent."""
    try:
        load_forecast_agent()
        if run_forecast_cycle is None:
            raise HTTPException(status_code=503, detail="Forecast agent not available")
        
        result = run_forecast_cycle()
        
        # Check if result indicates success
        if isinstance(result, dict):
            success = result.get("success", True)
            message = result.get("message", "Forecast cycle completed")
        else:
            success = True
            message = "Forecast cycle completed"
        
        return {
            "success": success,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run forecast cycle: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_SERVER_HOST, port=API_SERVER_PORT)

