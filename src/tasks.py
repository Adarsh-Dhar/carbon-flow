from crewai import Task

from src.agents import sensor_ingest_agent

task_fetch_cpcb = Task(
    description="Fetch CPCB air quality data.",
    expected_output="A pandas DataFrame of CPCB data focused on Delhi NCR.",
    agent=sensor_ingest_agent,
)

task_fetch_nasa = Task(
    description="Fetch NASA fire data for Punjab & Haryana farm fires.",
    expected_output="A pandas DataFrame of NASA FIRMS data filtered to Punjab and Haryana.",
    agent=sensor_ingest_agent,
)

task_fetch_dss = Task(
    description="Scrape the DSS pollution source contributions.",
    expected_output="A pandas DataFrame of DSS pollution contribution percentages.",
    agent=sensor_ingest_agent,
)

task_consolidate_and_save = Task(
    description="Normalize, merge, and save all data.",
    expected_output="A final success message with the AWS S3 file path.",
    agent=sensor_ingest_agent,
    context=[task_fetch_cpcb, task_fetch_nasa, task_fetch_dss],  # Pass outputs from previous tasks
)