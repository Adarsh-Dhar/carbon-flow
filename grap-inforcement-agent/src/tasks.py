"""
GRAP Enforcement Agent Tasks

This module defines the CrewAI tasks for executing GRAP Stage III enforcement actions
based on air quality forecasts from the ForecastAgent.
"""

from crewai import Task
from src.agents import enforcement_agent

# Assuming task_generate_forecast is imported from where it's defined
# from forecast_tasks import task_generate_forecast

task_execute_grap = Task(
    description=(
        "A 'Severe' AQI forecast has been confirmed by the 'ForecastAgent'. "
        "You must now execute the full GRAP Stage III emergency protocol. "
        "The 'ForecastAgent' has provided its reasoning and a list of current pollution hotspots in its output. "
        "You must use this context to perform your actions. "
        "Execute the following 4 steps in order:"
        "1. Use the 'issue_construction_ban' tool. Pass the forecast reasoning as the 'reasoning_text'."
        "2. Use the 'restrict_vehicles' tool. Pass the forecast reasoning as the 'reasoning_text'."
        "3. Use the 'notify_public' tool. Pass the forecast reasoning as the 'reasoning_text'."
        "4. Use the 'dispatch_enforcement_teams' tool. Extract the list of 'hotspots' from the context provided by the previous agent's task and pass it as the 'hotspots' argument."
    ),
    expected_output=(
        "A final JSON report summarizing the success status of all four triggered actions."
    ),
    agent=enforcement_agent,
    context=[],  # This will be set to [task_generate_forecast] when integrated
)
