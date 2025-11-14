"""
Enforcement Agent Test Runner

This script demonstrates the GRAP Enforcement Agent working autonomously
by mocking the output from the ForecastAgent and triggering enforcement actions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Process
from crewai.tasks import TaskOutput
from src.agents import enforcement_agent
from src.tasks import task_execute_grap

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 1. Mock the output from the ForecastAgent
# This simulates Agent 2 "handing off" its result
mock_forecast_data = '{"predicted_aqi_category": "Severe", "confidence_level": "High", "reasoning": "High stubble burning + low wind speed detected", "hotspots": ["Anand Vihar", "Punjabi Bagh", "RK Puram", "Dwarka"]}'

# Update the task description to include the forecast context directly
task_execute_grap.description = (
    f"A 'Severe' AQI forecast has been confirmed by the 'ForecastAgent'. "
    f"The forecast data is: {mock_forecast_data}. "
    f"You must now execute the full GRAP Stage III emergency protocol. "
    f"Execute the following 4 steps in order: "
    f"1. Use the 'issue_construction_ban' tool. Pass the forecast reasoning as the 'reasoning_text'. "
    f"2. Use the 'restrict_vehicles' tool. Pass the forecast reasoning as the 'reasoning_text'. "
    f"3. Use the 'notify_public' tool. Pass the forecast reasoning as the 'reasoning_text'. "
    f"4. Use the 'dispatch_enforcement_teams' tool. Extract the list of 'hotspots' from the forecast data and pass it as the 'hotspots' argument."
)

# 3. Create and run a crew with ONLY this agent and task
enforcement_crew = Crew(
    agents=[enforcement_agent],
    tasks=[task_execute_grap],
    process=Process.sequential,
    verbose=True
)

print("=" * 80)
print("--- STARTING ENFORCEMENT AGENT TEST ---")
print("=" * 80)
print("\nMocked Forecast Input:")
print(mock_forecast_data)
print("\n" + "=" * 80)

result = enforcement_crew.kickoff()

print("\n" + "=" * 80)
print("--- TEST COMPLETE ---")
print("=" * 80)
print("\nFinal Output:")
print(result)
print("\n" + "=" * 80)
