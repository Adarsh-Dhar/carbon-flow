from crewai import Task
from src.agents import cpcb_agent, nasa_agent, dss_agent, consolidator_agent

task_fetch_cpcb = Task(
    description='Fetch CPCB air quality data.',
    expected_output='A pandas DataFrame of CPCB data.',
    agent=cpcb_agent
)

task_fetch_nasa = Task(
    description='Fetch NASA fire data.',
    expected_output='A pandas DataFrame of NASA FIRMS data.',
    agent=nasa_agent
)

task_fetch_dss = Task(
    description='Scrape the DSS pollution source website.',
    expected_output='A pandas DataFrame of DSS data.',
    agent=dss_agent
)

task_consolidate_and_save = Task(
    description='Normalize, merge, and save all data.',
    expected_output='A final success message with the AWS S3 file path.',
    agent=consolidator_agent,
    context=[task_fetch_cpcb, task_fetch_nasa, task_fetch_dss] # This passes outputs from previous tasks
)