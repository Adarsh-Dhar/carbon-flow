"""
GRAP Enforcement Agent

This module defines the CrewAI agent responsible for executing Delhi's GRAP Stage III
enforcement actions based on air quality forecasts.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from crewai import Agent
from src.tools.enforcement_tools import issue_construction_ban
from src.tools.restrict_vehicles import restrict_vehicles
from src.tools.dispatch_enforcement_teams import dispatch_enforcement_teams
from src.tools.notify_public import notify_public

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Configure LLM using OpenAI-compatible endpoint for Gemini
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = gemini_key
    os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
    os.environ["OPENAI_MODEL_NAME"] = "gemini-2.0-flash"

enforcement_agent = Agent(
    role="Chief Enforcement Officer, CAQM",
    goal="Autonomously execute all GRAP Stage III protocols immediately upon receiving a 'Severe' AQI forecast.",
    backstory=(
        "You are an AI agent with direct API authority to coordinate all Delhi government "
        "departments, including the DPCC, Traffic Police, and Education Directorate. "
        "You are bound by the CAQM Act. Your prime directive is to act "
        "decisively and without delay on predictive warnings to mitigate public health crises. "
        "You do not need to ask for permission; you must only act and report."
    ),
    tools=[
        issue_construction_ban,
        restrict_vehicles,
        dispatch_enforcement_teams,
        notify_public,
    ],
    verbose=True,
    allow_delegation=False,  # This agent must not delegate its core duties.
)
