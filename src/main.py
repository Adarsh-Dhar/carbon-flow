from crewai import Crew, Process
from src.agents import cpcb_agent, nasa_agent, dss_agent, consolidator_agent
from src.tasks import task_fetch_cpcb, task_fetch_nasa, task_fetch_dss, task_consolidate_and_save

# Define the crew with a sequential process for reliability
sensor_crew = Crew(
    agents=[cpcb_agent, nasa_agent, dss_agent, consolidator_agent],
    tasks=[task_fetch_cpcb, task_fetch_nasa, task_fetch_dss, task_consolidate_and_save],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("Kicking off the SensorIngestAgent Crew...")
    result = sensor_crew.kickoff()
    print("\n\nCrew run completed. Final result:")
    print(result)