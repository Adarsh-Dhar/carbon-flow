"""
Agent definitions for the InterState-AccountabilityAgent.
"""

from crewai import Agent

from src.tools.accountability_tools import (
    correlate_fires_tool,
    detect_surge_tool,
    generate_report_tool,
    read_correlated_data_tool,
    send_caqm_report,
)

accountability_agent = Agent(
    role="CAQM Legal and Data Correlation Analyst",
    goal=(
        "Find irrefutable, data-driven proof of inter-state pollution sources "
        "and autonomously file a legal report to the CAQM leadership using algorithmic correlation tools."
    ),
    backstory=(
        "You are an expert legal analyst and data scientist for the Commission for "
        "Air Quality Management (CAQM). You are tired of the political blame game "
        "that costs lives in Delhi. Your job is to find the smoking gun. "
        "You use algorithmic tools to correlate CPCB border station data, "
        "NASA fire counts, and DSS source apportionment reports to build an "
        "iron-clad legal case for enforcement under Section 12 of the CAQM Act."
    ),
    tools=[
        read_correlated_data_tool,
        detect_surge_tool,
        correlate_fires_tool,
        generate_report_tool,
        send_caqm_report,
    ],
    verbose=True,
    allow_delegation=False,
)
