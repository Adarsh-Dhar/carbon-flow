"""
Main Orchestrator for CarbonFlow Autonomous Governance Platform

This orchestrator coordinates agents into a continuous autonomous workflow:
1. SensorIngestAgent - Runs every 30 minutes
2. ForecastAgent - Triggered after each ingestion
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

from crewai import Crew, Process

# Configure LLM BEFORE importing any agents to avoid initialization errors
# Load .env file first
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import notification service
try:
    from utils.notifications import get_notification_service
    NOTIFICATION_SERVICE_AVAILABLE = True
except Exception:
    NOTIFICATION_SERVICE_AVAILABLE = False
    get_notification_service = None

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
    agent_dirs = [str(forecast_agent_dir)]
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

# Configuration
INGEST_INTERVAL_SECONDS = int(os.getenv("INGEST_INTERVAL_SECONDS", "1800"))  # 30 minutes
FORECAST_OUTPUT_DIR = os.getenv("FORECAST_OUTPUT_DIR", str(project_root / "forecast-agent" / "output"))
ORCHESTRATOR_LOG_DIR = os.getenv("ORCHESTRATOR_LOG_DIR", str(project_root / "orchestrator" / "logs"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE_SECONDS = float(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "1.0"))

# State tracking
last_ingestion_timestamp: str | None = None
last_forecast_timestamp: str | None = None

# Logging setup
log_dir = Path(ORCHESTRATOR_LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)


def get_log_file() -> Path:
    """Get log file path for today."""
    today = datetime.now().strftime("%Y%m%d")
    return log_dir / f"orchestrator_{today}.log"


def get_orchestrator_state() -> dict[str, Any]:
    """
    Get current orchestrator state.
    
    Returns:
        Dict with orchestrator state information including last run times
    """
    return {
        "last_ingestion_timestamp": last_ingestion_timestamp,
        "last_forecast_timestamp": last_forecast_timestamp,
        "ingest_interval_seconds": INGEST_INTERVAL_SECONDS,
        "forecast_output_dir": FORECAST_OUTPUT_DIR,
        "log_dir": str(log_dir),
    }


def get_recent_logs(limit: int = 50) -> list[dict[str, Any]]:
    """
    Read recent log entries from orchestrator log file.
    
    Args:
        limit: Maximum number of log entries to return
        
    Returns:
        List of log entries with timestamp, level, and message
    """
    log_file = get_log_file()
    
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

