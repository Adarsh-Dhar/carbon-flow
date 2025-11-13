from crewai import Agent
from crewai.tools.base_tool import Tool
from src.tools import cpcb_tools, nasa_tools, dss_tools, storage_tools


cpcb_fetch_tool = Tool(
    name="Fetch CPCB data",
    description="Fetches real-time air quality data from the CPCB data.gov.in API and returns a pandas DataFrame.",
    func=cpcb_tools.fetch_cpcb_data
)

nasa_fetch_tool = Tool(
    name="Fetch NASA fire data",
    description="Retrieves active fire data from the NASA FIRMS API and returns a pandas DataFrame.",
    func=nasa_tools.fetch_nasa_fire_data
)

dss_fetch_tool = Tool(
    name="Fetch DSS pollution data",
    description="Scrapes the DSS pollution source website and returns a pandas DataFrame of extracted items.",
    func=dss_tools.fetch_dss_data
)

normalize_tool = Tool(
    name="Normalize and merge data",
    description="Normalizes CPCB, NASA, and DSS DataFrames and merges them into a consolidated dataset.",
    func=storage_tools.normalize_and_merge
)

save_to_s3_tool = Tool(
    name="Save DataFrame to S3",
    description="Uploads a pandas DataFrame to the configured AWS S3 bucket in JSON format.",
    func=storage_tools.save_to_s3
)

cpcb_agent = Agent(
    role='CPCB Data Fetcher',
    goal='Fetch real-time air quality data from the CPCB data.gov.in API',
    backstory='You are a specialist in government API endpoints.',
    tools=[cpcb_fetch_tool],
    verbose=True
)

nasa_agent = Agent(
    role='NASA Fire Data Fetcher',
    goal='Fetch real-time active fire data from the NASA FIRMS API',
    backstory='You are a specialist in geospatial and satellite data APIs.',
    tools=[nasa_fetch_tool],
    verbose=True
)

dss_agent = Agent(
    role='DSS Data Scraper',
    goal='Scrape the DSS website for pollution source apportionment data',
    backstory='You are a specialist in web scraping with Python and BeautifulSoup.',
    tools=[dss_fetch_tool],
    verbose=True
)

consolidator_agent = Agent(
    role='Data Consolidator and Storage Manager',
    goal='Normalize data from all sources, merge it, and upload the final JSON to AWS S3',
    backstory='You are an expert data engineer and AWS specialist.',
    tools=[normalize_tool, save_to_s3_tool],
    verbose=True
)