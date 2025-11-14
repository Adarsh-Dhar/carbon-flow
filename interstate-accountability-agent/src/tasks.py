"""
Task definitions for the InterState-AccountabilityAgent.
"""

from crewai import Task

from src.agents import accountability_agent

# This task would have 'context' from the SensorIngestAgent's tasks
task_build_report = Task(
    description=(
        "A severe pollution surge has been detected at Delhi's borders. "
        "Your mission is to build an official accountability report for the CAQM. "
        "Follow these steps EXACTLY:"
        "\n\n"
        "1.  Use the 'read_correlated_data' tool to get the complete evidence package."
        "\n\n"
        "2.  Analyze the data. Look for a CPCB spike (e.g., at Alipur) and correlate it "
        "    with a high NASA fire count (e.g., in Jind or Fatehabad) from the "
        "    previous hours."
        "\n\n"
        "3.  Use the DSS stubble burning percentage to confirm the link."
        "\n\n"
        "4.  Once correlated, you MUST draft a formal, evidence-based report. "
        "    The report MUST start with 'To: CAQM.' "
        "    It MUST cite the specific data (e.g., '121 fire events in Jind, Haryana', '140% spike at Alipur')."
        "    It MUST state 'This confirms non-compliance with CAQM Direction No. 95.'"
        "    It MUST conclude by 'Requesting immediate enforcement action as per Section 12 of the CAQM Act.'"
        "\n\n"
        "5.  Finally, pass the complete, formatted report text to the 'send_caqm_report' tool."
    ),
    expected_output=(
        "A JSON string confirming the report was sent, e.g., "
        "{'status': 'SUCCESS', 'action': 'Report sent to CAQM.'}"
    ),
    agent=accountability_agent,
    # context=[task_from_sensor_agent]  # This links it to the previous agent
)
