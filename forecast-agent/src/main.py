from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from crewai import Crew, Process

from src.agents import (
    normalize_and_merge_from_cache,
    save_latest_to_s3_from_cache,
    sensor_ingest_agent,
    data_retrieval_agent,
    forecast_analysis_agent,
    TOOL_RESULT_CACHE,
)
from src.tasks import (
    task_consolidate_and_save,
    task_fetch_cpcb,
    task_fetch_dss,
    task_fetch_nasa,
    task_retrieve_sensor_data,
    task_retrieve_meteo_forecast,
    task_generate_prediction,
    task_output_forecast,
)
from src.utils.env_config import configure_llm_from_env, validate_required_env_vars

# Define the sensor crew with a sequential process for reliability
sensor_crew = Crew(
    agents=[sensor_ingest_agent],
    tasks=[task_fetch_cpcb, task_fetch_nasa, task_fetch_dss, task_consolidate_and_save],
    process=Process.sequential,
    verbose=True,
)

# Define the forecast crew with a sequential process for reliability
forecast_crew = Crew(
    agents=[data_retrieval_agent, forecast_analysis_agent],
    tasks=[
        task_retrieve_sensor_data,
        task_retrieve_meteo_forecast,
        task_generate_prediction,
        task_output_forecast,
    ],
    process=Process.sequential,
    verbose=True,
)


def run_cycle() -> dict:
    """Execute a single ingestion cycle."""
    print("Kicking off the SensorIngestAgent Crew...")
    try:
        result = sensor_crew.kickoff()
    except Exception as exc:  # noqa: BLE001 - bubble non-rate-limit errors
        message = str(exc)
        if "RESOURCE_EXHAUSTED" not in message:
            raise

        print(
            "\nGemini rate limit encountered while generating the final response. "
            "Falling back to deterministic tool execution."
        )
        consolidated_df = normalize_and_merge_from_cache()
        s3_message = save_latest_to_s3_from_cache()
        result = {
            "fallback_ran": True,
            "rows_consolidated": len(consolidated_df),
            "s3_message": s3_message,
        }

    print("\nCrew run completed. Final result:")
    print(result)
    return result


def run_forecast_cycle() -> dict:
    """Execute a single forecast generation cycle."""
    print("Kicking off the ForecastAgent Crew...")
    start_ts = _current_timestamp()
    print(f"=== Forecast cycle started at {start_ts} ===")
    
    # Clear the tool result cache before starting a new forecast cycle
    TOOL_RESULT_CACHE.clear()
    
    try:
        result = forecast_crew.kickoff()
        print(f"\n=== Forecast cycle completed at {_current_timestamp()} ===")
        print("\nForecast crew run completed. Final result:")
        print(result)
        return {"success": True, "result": result, "start_timestamp": start_ts}
    except Exception as exc:  # noqa: BLE001 - handle crew execution failures
        error_message = str(exc)
        print(f"\nERROR: Forecast crew execution failed - {error_message}")
        print(f"=== Forecast cycle failed at {_current_timestamp()} ===")
        
        # Check if it's a rate limit error
        if "RESOURCE_EXHAUSTED" in error_message:
            print(
                "\nGemini rate limit encountered. "
                "The forecast cycle will be retried in the next scheduled run."
            )
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "details": error_message,
                "start_timestamp": start_ts,
            }
        
        # For other errors, return error details
        return {
            "success": False,
            "error": "Crew execution failed",
            "details": error_message,
            "start_timestamp": start_ts,
        }


def _current_timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


if __name__ == "__main__":
    # Validate required environment variables on startup
    try:
        validate_required_env_vars()
        print("✓ Environment variables validated successfully")
    except ValueError as e:
        print(f"ERROR: Environment validation failed:\n{e}")
        exit(1)
    
    # Configure LLM from environment
    configure_llm_from_env()
    
    interval_seconds = int(os.getenv("INGEST_INTERVAL_SECONDS", "1800"))
    run_continuously = interval_seconds > 0

    try:
        while True:
            start_ts = _current_timestamp()
            print(f"\n=== Sensor ingestion cycle started at {start_ts} ===")
            cycle_started = time.time()

            try:
                run_cycle()
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: Sensor ingestion cycle failed - {exc}")

            elapsed = time.time() - cycle_started

            if not run_continuously:
                break

            sleep_for = max(0.0, interval_seconds - elapsed)
            print(
                f"Sensor ingestion cycle finished in {elapsed:.1f}s. "
                f"Sleeping for {sleep_for:.1f}s before next run."
            )
            time.sleep(sleep_for)
    except KeyboardInterrupt:  # pragma: no cover - operator controlled shutdown
        print("\nSensor ingestion loop interrupted by user. Exiting gracefully.")
