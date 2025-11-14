"""
Main Orchestrator for CarbonFlow Autonomous Governance Platform

This orchestrator coordinates all four agents into a continuous autonomous workflow:
1. SensorIngestAgent - Runs every 30 minutes
2. ForecastAgent - Triggered after each ingestion
3. GRAP-EnforcementAgent - Triggered when "Severe" AQI is predicted
4. InterState-AccountabilityAgent - Triggered when border station spikes are detected
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add agent directories to path for imports
# Agents use "from src.xxx" imports, so we need to add parent directories to path
project_root = Path(__file__).parent
forecast_agent_dir = project_root / "forecast-agent"
enforcement_agent_dir = project_root / "grap-inforcement-agent"
accountability_agent_dir = project_root / "interstate-accountability-agent"

from crewai import Crew, Process

# Configure LLM BEFORE importing any agents to avoid initialization errors
# Load .env file first
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configure Gemini API key to work with CrewAI's OpenAI-compatible interface
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = gemini_key
    os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
    os.environ["OPENAI_MODEL_NAME"] = "gemini-2.0-flash"
    os.environ.setdefault("OPENAI_API_BASE", os.environ["OPENAI_BASE_URL"])
    os.environ.setdefault("MODEL_NAME", "gemini-2.0-flash")
    os.environ.setdefault("MODEL", "gemini-2.0-flash")

# Import forecast agent functions - need to import from the specific main module
# We'll import the functions directly by executing the module setup
# IMPORTANT: Only add forecast_agent_dir to path when loading forecast_main
import importlib.util

# Store original sys.path
original_sys_path = sys.path.copy()

# Helper function to clean agent directories from sys.path
def remove_agent_dirs_from_path():
    """Remove all agent directories from sys.path to avoid conflicts."""
    agent_dirs = [str(forecast_agent_dir), str(enforcement_agent_dir), str(accountability_agent_dir)]
    sys.path = [p for p in sys.path if p not in agent_dirs]

# Temporarily modify sys.path to only include forecast agent directory
remove_agent_dirs_from_path()
sys.path.insert(0, str(forecast_agent_dir))

# Load forecast agent main module
forecast_main_path = forecast_agent_dir / "src" / "main.py"
forecast_main_spec = importlib.util.spec_from_file_location(
    "forecast_main", forecast_main_path
)
forecast_main = importlib.util.module_from_spec(forecast_main_spec)
sys.modules["forecast_main"] = forecast_main
forecast_main_spec.loader.exec_module(forecast_main)

# Import functions from forecast main
run_cycle = forecast_main.run_cycle
run_forecast_cycle = forecast_main.run_forecast_cycle

# Restore original sys.path
sys.path = original_sys_path.copy()

# Import enforcement agent - use importlib to avoid module cache conflicts
remove_agent_dirs_from_path()
sys.path.insert(0, str(enforcement_agent_dir))

# Clear any cached src modules to avoid conflicts
modules_to_remove = [mod for mod in sys.modules.keys() if mod.startswith('src.')]
for mod in modules_to_remove:
    del sys.modules[mod]

try:
    enforcement_agents_spec = importlib.util.spec_from_file_location(
        "enforcement_agents", enforcement_agent_dir / "src" / "agents.py"
    )
    enforcement_agents = importlib.util.module_from_spec(enforcement_agents_spec)
    sys.modules["enforcement_agents"] = enforcement_agents
    enforcement_agents_spec.loader.exec_module(enforcement_agents)
    enforcement_agent = enforcement_agents.enforcement_agent
    
    enforcement_tasks_spec = importlib.util.spec_from_file_location(
        "enforcement_tasks", enforcement_agent_dir / "src" / "tasks.py"
    )
    enforcement_tasks = importlib.util.module_from_spec(enforcement_tasks_spec)
    sys.modules["enforcement_tasks"] = enforcement_tasks
    enforcement_tasks_spec.loader.exec_module(enforcement_tasks)
    task_execute_grap = enforcement_tasks.task_execute_grap
finally:
    sys.path = original_sys_path.copy()

# Import accountability agent - use importlib to avoid module cache conflicts
remove_agent_dirs_from_path()
sys.path.insert(0, str(accountability_agent_dir))

# Clear any cached src modules to avoid conflicts
modules_to_remove = [mod for mod in list(sys.modules.keys()) if mod.startswith('src.')]
for mod in modules_to_remove:
    del sys.modules[mod]

try:
    # Load config modules first (they don't have dependencies)
    accountability_config_bs_spec = importlib.util.spec_from_file_location(
        "accountability_config_bs", accountability_agent_dir / "src" / "config" / "border_stations.py"
    )
    accountability_config_bs = importlib.util.module_from_spec(accountability_config_bs_spec)
    sys.modules["accountability_config_bs"] = accountability_config_bs
    accountability_config_bs_spec.loader.exec_module(accountability_config_bs)
    DELHI_BORDER_STATIONS = accountability_config_bs.DELHI_BORDER_STATIONS
    is_border_station = accountability_config_bs.is_border_station
    
    accountability_config_thresh_spec = importlib.util.spec_from_file_location(
        "accountability_config_thresh", accountability_agent_dir / "src" / "config" / "thresholds.py"
    )
    accountability_config_thresh = importlib.util.module_from_spec(accountability_config_thresh_spec)
    sys.modules["accountability_config_thresh"] = accountability_config_thresh
    accountability_config_thresh_spec.loader.exec_module(accountability_config_thresh)
    SURGE_AQI_THRESHOLD = accountability_config_thresh.SURGE_AQI_THRESHOLD
    
    # Load tools module first (agents depends on it)
    accountability_tools_spec = importlib.util.spec_from_file_location(
        "accountability_tools", accountability_agent_dir / "src" / "tools" / "accountability_tools.py"
    )
    accountability_tools = importlib.util.module_from_spec(accountability_tools_spec)
    # Register it as src.tools.accountability_tools so imports work
    sys.modules["src.tools.accountability_tools"] = accountability_tools
    sys.modules["accountability_tools"] = accountability_tools
    accountability_tools_spec.loader.exec_module(accountability_tools)
    
    # Also register src.tools so the import path works
    if "src.tools" not in sys.modules:
        tools_module = type(sys)("src.tools")
        sys.modules["src.tools"] = tools_module
    sys.modules["src.tools"].accountability_tools = accountability_tools
    
    # Register src.agents module namespace
    if "src.agents" not in sys.modules:
        agents_module = type(sys)("src.agents")
        sys.modules["src.agents"] = agents_module
    
    # Now load agents (which depends on tools)
    accountability_agents_spec = importlib.util.spec_from_file_location(
        "accountability_agents", accountability_agent_dir / "src" / "agents.py"
    )
    accountability_agents = importlib.util.module_from_spec(accountability_agents_spec)
    sys.modules["accountability_agents"] = accountability_agents
    sys.modules["src.agents"] = accountability_agents  # Register as src.agents for imports
    accountability_agents_spec.loader.exec_module(accountability_agents)
    accountability_agent = accountability_agents.accountability_agent
    
    accountability_tasks_spec = importlib.util.spec_from_file_location(
        "accountability_tasks", accountability_agent_dir / "src" / "tasks.py"
    )
    accountability_tasks = importlib.util.module_from_spec(accountability_tasks_spec)
    sys.modules["accountability_tasks"] = accountability_tasks
    accountability_tasks_spec.loader.exec_module(accountability_tasks)
    task_build_report = accountability_tasks.task_build_report
finally:
    sys.path = original_sys_path.copy()

# Configuration
INGEST_INTERVAL_SECONDS = int(os.getenv("INGEST_INTERVAL_SECONDS", "1800"))  # 30 minutes
FORECAST_OUTPUT_DIR = os.getenv("FORECAST_OUTPUT_DIR", str(project_root / "forecast-agent" / "output"))
ORCHESTRATOR_LOG_DIR = os.getenv("ORCHESTRATOR_LOG_DIR", str(project_root / "orchestrator" / "logs"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE_SECONDS = float(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "1.0"))

# State tracking
last_ingestion_timestamp: str | None = None
last_forecast_timestamp: str | None = None
last_enforcement_trigger: str | None = None
last_accountability_trigger: str | None = None

# Logging setup
log_dir = Path(ORCHESTRATOR_LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)


def get_log_file() -> Path:
    """Get log file path for today."""
    today = datetime.now().strftime("%Y%m%d")
    return log_dir / f"orchestrator_{today}.log"


def log(message: str, level: str = "INFO") -> None:
    """Log message to both console and file."""
    timestamp = datetime.now(tz=timezone.utc).isoformat()
    log_message = f"[{timestamp}] [{level}] {message}"
    
    # Console output
    print(log_message)
    
    # File output
    try:
        with open(get_log_file(), "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: Failed to write to log file: {e}")


def _current_timestamp() -> str:
    """Get current UTC timestamp."""
    return datetime.now(tz=timezone.utc).isoformat()


def run_with_retry(func: callable, func_name: str, max_retries: int = MAX_RETRIES) -> dict[str, Any]:
    """
    Execute a function with retry logic and exponential backoff.
    
    Args:
        func: Function to execute
        func_name: Name of function for logging
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict with success status and result or error details
    """
    backoff_delay = RETRY_BACKOFF_BASE_SECONDS
    
    for attempt in range(max_retries):
        try:
            log(f"Executing {func_name} (attempt {attempt + 1}/{max_retries})")
            result = func()
            log(f"{func_name} completed successfully")
            return {"success": True, "result": result, "attempt": attempt + 1}
        except Exception as e:  # noqa: BLE001
            error_message = str(e)
            log(f"{func_name} failed (attempt {attempt + 1}/{max_retries}): {error_message}", "ERROR")
            
            if attempt < max_retries - 1:
                log(f"Retrying {func_name} in {backoff_delay} seconds...")
                time.sleep(backoff_delay)
                backoff_delay *= 2  # Exponential backoff
            else:
                log(f"{func_name} failed after {max_retries} attempts", "ERROR")
                return {
                    "success": False,
                    "error": error_message,
                    "attempts": max_retries
                }
    
    return {"success": False, "error": "Max retries exceeded"}


def run_sensor_ingest() -> dict[str, Any]:
    """Invoke SensorIngestAgent."""
    global last_ingestion_timestamp
    log("Starting SensorIngestAgent cycle")
    
    result = run_with_retry(run_cycle, "SensorIngestAgent")
    
    if result["success"]:
        last_ingestion_timestamp = _current_timestamp()
        log(f"SensorIngestAgent completed at {last_ingestion_timestamp}")
    else:
        log(f"SensorIngestAgent failed: {result.get('error')}", "ERROR")
    
    return result


def run_forecast() -> dict[str, Any]:
    """Invoke ForecastAgent."""
    global last_forecast_timestamp
    log("Starting ForecastAgent cycle")
    
    # Initialize TOOL_RESULT_CACHE before forecast cycle
    try:
        # Ensure the cache is initialized in the forecast agent module
        if hasattr(forecast_main, 'TOOL_RESULT_CACHE'):
            if forecast_main.TOOL_RESULT_CACHE is None or not isinstance(forecast_main.TOOL_RESULT_CACHE, dict):
                forecast_main.TOOL_RESULT_CACHE = {}
        # Also clear it to start fresh
        if hasattr(forecast_main, 'TOOL_RESULT_CACHE'):
            forecast_main.TOOL_RESULT_CACHE.clear()
    except Exception as e:  # noqa: BLE001
        log(f"Warning: Could not initialize TOOL_RESULT_CACHE: {e}", "WARNING")
    
    result = run_with_retry(run_forecast_cycle, "ForecastAgent")
    
    if result["success"]:
        last_forecast_timestamp = _current_timestamp()
        log(f"ForecastAgent completed at {last_forecast_timestamp}")
    else:
        log(f"ForecastAgent failed: {result.get('error')}", "ERROR")
    
    return result


def get_latest_forecast_file() -> Path | None:
    """
    Get the latest forecast JSON file from the output directory.
    
    Returns:
        Path to latest forecast file or None if no files found
    """
    output_dir = Path(FORECAST_OUTPUT_DIR)
    
    if not output_dir.exists():
        log(f"Forecast output directory does not exist: {output_dir}", "WARNING")
        return None
    
    # Find all forecast JSON files
    forecast_files = list(output_dir.glob("forecast_*.json"))
    
    if not forecast_files:
        log("No forecast files found", "WARNING")
        return None
    
    # Sort by filename (which contains timestamp) to get latest
    forecast_files.sort(key=lambda x: x.name, reverse=True)
    
    return forecast_files[0]


def monitor_forecast_for_severe() -> dict[str, Any] | None:
    """
    Monitor latest forecast output for "Severe" AQI prediction.
    
    Returns:
        Forecast data dict if "Severe" detected, None otherwise
    """
    log("Monitoring forecast for 'Severe' AQI prediction")
    
    forecast_file = get_latest_forecast_file()
    
    if forecast_file is None:
        log("No forecast file available for monitoring", "WARNING")
        return None
    
    try:
        with open(forecast_file, "r", encoding="utf-8") as f:
            forecast_data = json.load(f)
        
        # Check prediction category
        prediction = forecast_data.get("prediction", {})
        aqi_category = prediction.get("aqi_category", "")
        
        log(f"Latest forecast category: {aqi_category}")
        
        if aqi_category == "Severe":
            log("⚠️  SEVERE AQI PREDICTED - Triggering enforcement agent", "WARNING")
            return forecast_data
        else:
            log(f"Forecast category '{aqi_category}' does not require enforcement")
            return None
            
    except json.JSONDecodeError as e:
        log(f"Failed to parse forecast JSON: {e}", "ERROR")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"Error reading forecast file: {e}", "ERROR")
        return None


def trigger_enforcement_agent(forecast_data: dict[str, Any]) -> dict[str, Any]:
    """
    Trigger GRAP-EnforcementAgent with forecast context.
    
    Args:
        forecast_data: Forecast JSON data containing prediction and reasoning
        
    Returns:
        Dict with execution result
    """
    global last_enforcement_trigger
    log("Triggering GRAP-EnforcementAgent")
    
    # Extract forecast information
    prediction = forecast_data.get("prediction", {})
    reasoning = forecast_data.get("reasoning", "Severe AQI forecast detected")
    aqi_category = prediction.get("aqi_category", "Severe")
    
    # Extract hotspots from data_sources if available
    data_sources = forecast_data.get("data_sources", {})
    hotspots = []
    
    # Try to infer hotspots from current AQI data or use default border stations
    # For now, use border stations as hotspots
    hotspots = [station["name"] for station in DELHI_BORDER_STATIONS]
    
    # Create forecast context string
    forecast_context = json.dumps({
        "predicted_aqi_category": aqi_category,
        "confidence_level": forecast_data.get("confidence_level", "High"),
        "reasoning": reasoning,
        "hotspots": hotspots,
        "threshold": prediction.get("threshold", 401),
        "estimated_hours_to_threshold": prediction.get("estimated_hours_to_threshold", 0)
    })
    
    # Update task description with forecast context
    task_execute_grap.description = (
        f"A 'Severe' AQI forecast has been confirmed by the 'ForecastAgent'. "
        f"The forecast data is: {forecast_context}. "
        f"You must now execute the full GRAP Stage III emergency protocol. "
        f"Execute the following 4 steps in order: "
        f"1. Use the 'issue_construction_ban' tool. Pass the forecast reasoning as the 'reasoning_text'. "
        f"2. Use the 'restrict_vehicles' tool. Pass the forecast reasoning as the 'reasoning_text'. "
        f"3. Use the 'notify_public' tool. Pass the forecast reasoning as the 'reasoning_text'. "
        f"4. Use the 'dispatch_enforcement_teams' tool. Extract the list of 'hotspots' from the forecast data and pass it as the 'hotspots' argument."
    )
    
    # Create enforcement crew
    enforcement_crew = Crew(
        agents=[enforcement_agent],
        tasks=[task_execute_grap],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute with retry
    def execute_enforcement():
        return enforcement_crew.kickoff()
    
    result = run_with_retry(execute_enforcement, "GRAP-EnforcementAgent")
    
    if result["success"]:
        last_enforcement_trigger = _current_timestamp()
        log(f"GRAP-EnforcementAgent completed at {last_enforcement_trigger}")
    else:
        log(f"GRAP-EnforcementAgent failed: {result.get('error')}", "ERROR")
    
    return result


def read_latest_sensor_data() -> dict[str, Any] | None:
    """
    Read latest sensor data from S3 or use accountability agent's tool.
    
    Returns:
        Sensor data dict with cpcb_data, nasa_data, dss_data sections, or None if unavailable
    """
    # Try to read from S3 first
    bucket_name = os.getenv("S3_BUCKET_NAME")
    
    if bucket_name:
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client("s3")
            prefix = "data/"
            
            # List objects and get latest
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
                
                # Get object content
                obj_response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                content = obj_response["Body"].read().decode("utf-8")
                data = json.loads(content)
                
                log(f"Read sensor data from S3: {object_key}")
                
                # Parse list data into structured format
                if isinstance(data, list):
                    return _parse_sensor_data_list(data)
                elif isinstance(data, dict):
                    # Already in the correct format
                    return data
                else:
                    log(f"Unexpected data format: {type(data)}", "WARNING")
                    return None
        except Exception as e:  # noqa: BLE001
            log(f"Failed to read from S3: {e}, trying accountability tool", "WARNING")
    
    # Fallback: Use accountability agent's tool to read correlated data
    try:
        # Import the tool function directly
        accountability_tools_path = accountability_agent_dir / "src" / "tools" / "accountability_tools.py"
        accountability_tools_spec = importlib.util.spec_from_file_location(
            "accountability_tools", accountability_tools_path
        )
        accountability_tools = importlib.util.module_from_spec(accountability_tools_spec)
        accountability_tools_spec.loader.exec_module(accountability_tools)
        
        if hasattr(accountability_tools, "read_correlated_data"):
            log("Reading sensor data using accountability agent tool")
            data = accountability_tools.read_correlated_data()
            # Ensure it's in the correct format
            if isinstance(data, list):
                return _parse_sensor_data_list(data)
            return data
    except Exception as e:  # noqa: BLE001
        log(f"Failed to read sensor data: {e}", "ERROR")
        return None


def _parse_sensor_data_list(data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Parse sensor data from JSON array into structured format for border spike detection.
    
    Args:
        data: List of data records from S3
        
    Returns:
        Dict with cpcb_data (list of station records), nasa_data, and dss_data sections
    """
    result: dict[str, Any] = {
        "cpcb_data": [],
        "nasa_data": None,
        "dss_data": None
    }
    
    if not data or not isinstance(data, list):
        return result
    
    # Extract CPCB records and group by station
    # Check both 'data_source' (new) and 'source' (legacy) fields
    cpcb_records = [r for r in data if str(r.get('data_source', '') or r.get('source', '')).upper() == 'CPCB']
    
    if cpcb_records:
        # Group by station
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
            
            # Update pollutant values
            if pollutant == 'PM2.5' and pollutant_avg is not None:
                try:
                    pm25_val = float(pollutant_avg)
                    stations_dict[station]['pm25'] = pm25_val
                    # Use PM2.5 as AQI proxy
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


def detect_border_spike() -> bool:
    """
    Detect if any border station has AQI >= threshold.
    
    Returns:
        True if spike detected, False otherwise
    """
    log(f"Checking border stations for AQI spikes (threshold: {SURGE_AQI_THRESHOLD})")
    
    sensor_data = read_latest_sensor_data()
    
    if sensor_data is None:
        log("No sensor data available for border spike detection", "WARNING")
        return False
    
    # Check CPCB data for border stations
    cpcb_data = sensor_data.get("cpcb_data", [])
    
    if not cpcb_data:
        log("No CPCB data in sensor data", "WARNING")
        return False
    
    # Check each border station
    for station_data in cpcb_data:
        station_name = station_data.get("station", "")
        aqi = station_data.get("aqi", 0)
        
        if is_border_station(station_name) and aqi >= SURGE_AQI_THRESHOLD:
            log(
                f"⚠️  BORDER SPIKE DETECTED: {station_name} AQI = {aqi} "
                f"(threshold: {SURGE_AQI_THRESHOLD})",
                "WARNING"
            )
            return True
    
    log("No border station spikes detected")
    return False


def trigger_accountability_agent() -> dict[str, Any]:
    """
    Trigger InterState-AccountabilityAgent when border spike is detected.
    
    Returns:
        Dict with execution result
    """
    global last_accountability_trigger
    log("Triggering InterState-AccountabilityAgent")
    
    # Create accountability crew
    accountability_crew = Crew(
        agents=[accountability_agent],
        tasks=[task_build_report],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute with retry
    def execute_accountability():
        return accountability_crew.kickoff()
    
    result = run_with_retry(execute_accountability, "InterState-AccountabilityAgent")
    
    if result["success"]:
        last_accountability_trigger = _current_timestamp()
        log(f"InterState-AccountabilityAgent completed at {last_accountability_trigger}")
    else:
        log(f"InterState-AccountabilityAgent failed: {result.get('error')}", "ERROR")
    
    return result


def main_loop() -> None:
    """Main orchestrator loop."""
    log("=" * 80)
    log("CarbonFlow Orchestrator Starting")
    log("=" * 80)
    log(f"Ingest interval: {INGEST_INTERVAL_SECONDS} seconds ({INGEST_INTERVAL_SECONDS / 60:.1f} minutes)")
    log(f"Forecast output directory: {FORECAST_OUTPUT_DIR}")
    log(f"Log directory: {ORCHESTRATOR_LOG_DIR}")
    log("=" * 80)
    
    try:
        while True:
            cycle_start = time.time()
            cycle_timestamp = _current_timestamp()
            
            log("")
            log("=" * 80)
            log(f"Starting orchestrator cycle at {cycle_timestamp}")
            log("=" * 80)
            
            # Step 1: Run SensorIngestAgent
            ingest_result = run_sensor_ingest()
            
            if not ingest_result["success"]:
                log("SensorIngestAgent failed, skipping forecast cycle", "ERROR")
                # Continue loop even if ingestion fails
            else:
                # Step 2: Run ForecastAgent after successful ingestion
                forecast_result = run_forecast()
                
                if forecast_result["success"]:
                    # Step 3: Monitor forecast for "Severe" prediction
                    severe_forecast = monitor_forecast_for_severe()
                    
                    if severe_forecast:
                        # Step 4: Trigger enforcement agent
                        log("Triggering enforcement agent due to Severe forecast")
                        trigger_enforcement_agent(severe_forecast)
                
                # Step 5: Check for border station spikes
                if detect_border_spike():
                    # Step 6: Trigger accountability agent
                    log("Triggering accountability agent due to border spike")
                    trigger_accountability_agent()
            
            # Calculate cycle duration
            cycle_duration = time.time() - cycle_start
            log(f"Cycle completed in {cycle_duration:.1f} seconds")
            
            # Sleep until next cycle
            sleep_for = max(0.0, INGEST_INTERVAL_SECONDS - cycle_duration)
            log(f"Sleeping for {sleep_for:.1f} seconds until next cycle")
            log("=" * 80)
            
            time.sleep(sleep_for)
            
    except KeyboardInterrupt:
        log("")
        log("=" * 80)
        log("Orchestrator interrupted by user. Exiting gracefully.")
        log("=" * 80)
    except Exception as e:  # noqa: BLE001
        log(f"Fatal error in main loop: {e}", "ERROR")
        raise


if __name__ == "__main__":
    # Validate environment
    required_vars = ["GEMINI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        log(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}", "ERROR")
        sys.exit(1)
    
    # LLM is already configured at module level before agent imports
    # Additional configuration from forecast agent's utils (optional, for consistency)
    try:
        forecast_utils_path = forecast_agent_dir / "src" / "utils" / "env_config.py"
        forecast_utils_spec = importlib.util.spec_from_file_location(
            "forecast_utils", forecast_utils_path
        )
        forecast_utils = importlib.util.module_from_spec(forecast_utils_spec)
        forecast_utils_spec.loader.exec_module(forecast_utils)
        if hasattr(forecast_utils, "configure_llm_from_env"):
            forecast_utils.configure_llm_from_env()
            log("Additional LLM configuration applied")
    except Exception as e:  # noqa: BLE001
        log(f"Additional LLM configuration not available: {e}", "WARNING")
    
    # Start main loop
    main_loop()

