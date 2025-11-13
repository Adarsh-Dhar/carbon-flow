from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from crewai import Crew, Process

from src.agents import (
    normalize_and_merge_from_cache,
    save_latest_to_s3_from_cache,
    sensor_ingest_agent,
)
from src.tasks import (
    task_consolidate_and_save,
    task_fetch_cpcb,
    task_fetch_dss,
    task_fetch_nasa,
)

# Define the crew with a sequential process for reliability
sensor_crew = Crew(
    agents=[sensor_ingest_agent],
    tasks=[task_fetch_cpcb, task_fetch_nasa, task_fetch_dss, task_consolidate_and_save],
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


def _current_timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


if __name__ == "__main__":
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
