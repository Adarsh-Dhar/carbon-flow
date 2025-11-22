"""
Task definitions for the InterState-AccountabilityAgent.
"""

from crewai import Task

from src.agents import accountability_agent

# This task would have 'context' from the SensorIngestAgent's tasks
task_build_report = Task(
    description=(
        "A severe pollution surge has been detected at Delhi's borders. "
        "Your mission is to build an official accountability report for the CAQM using algorithmic tools. "
        "Follow these steps EXACTLY in order:"
        "\n\n"
        "1. Use the 'read_correlated_data' tool to get the complete evidence package containing "
        "   CPCB data, NASA fire data, and DSS stubble burning data."
        "\n\n"
        "2. Extract the CPCB data from the result and use the 'detect_surge' tool to identify "
        "   border stations with AQI >= 300. This tool will return a list of surge stations."
        "\n\n"
        "3. If surge stations are detected, extract the NASA fire data and use the 'correlate_fires' tool "
        "   with the surge stations and NASA data. This will correlate fires within 200km and 48 hours "
        "   of the surge, grouped by state."
        "\n\n"
        "4. Use the 'generate_report' tool with the first surge station, correlation results, "
        "   and DSS data availability flags. This will generate a complete structured CAQM report "
        "   with executive summary, reasoning, confidence score, legal citations, and recommendations."
        "\n\n"
        "5. Extract the report from the result and format it as a formal report text starting with 'To: CAQM.' "
        "   Include the executive summary, reasoning statement, and recommendations. "
        "   The report MUST state 'This confirms non-compliance with CAQM Direction No. 95.' "
        "   and MUST conclude with 'Requesting immediate enforcement action as per Section 12 of the CAQM Act.'"
        "\n\n"
        "6. Finally, pass the complete, formatted report text to the 'send_caqm_report' tool."
        "\n\n"
        "If no surge is detected in step 2, return a message indicating no action is required."
    ),
    expected_output=(
        "A JSON string confirming the report was sent, e.g., "
        "{'status': 'SUCCESS', 'action': 'Report sent to CAQM.'} "
        "OR a message indicating no surge was detected."
    ),
    agent=accountability_agent,
    # context=[task_from_sensor_agent]  # This links it to the previous agent
)
