from crewai import Task

from src.agents import sensor_ingest_agent, data_retrieval_agent, forecast_analysis_agent

# SensorIngestAgent Tasks
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

# ForecastAgent Tasks
task_retrieve_sensor_data = Task(
    description=(
        "Retrieve the latest ingested sensor data from AWS S3. "
        "The data should contain CPCB AQI levels, NASA fire counts, and DSS source percentages. "
        "Validate the data completeness and calculate data quality metrics including completeness "
        "ratio and age in hours. Report any missing or stale data sources."
    ),
    expected_output=(
        "A dictionary containing parsed sensor data with cpcb_data, nasa_data, dss_data sections, "
        "and data_quality metrics (completeness: 0-1, age_hours: float). "
        "Example: {'cpcb_data': {'aqi': 380, 'timestamp': '2025-11-13T08:00:00Z', 'station': 'Delhi-Anand Vihar'}, "
        "'nasa_data': {'fire_count': 450, 'region': 'Punjab-Haryana', 'timestamp': '2025-11-13T08:00:00Z'}, "
        "'dss_data': {'stubble_burning_percent': 22, 'vehicular_percent': 35, 'industrial_percent': 18}, "
        "'data_quality': {'completeness': 1.0, 'age_hours': 2.5}}"
    ),
    agent=data_retrieval_agent,
)

task_retrieve_meteo_forecast = Task(
    description=(
        "Fetch 48-hour wind speed forecast for Delhi from the Open-Meteo API. "
        "Use Delhi coordinates (latitude: 28.6139, longitude: 77.2090). "
        "Retrieve hourly wind speed data in km/h to understand how weather conditions will affect air quality. "
        "Implement retry logic if the API request fails."
    ),
    expected_output=(
        "A dictionary containing hourly wind speed forecasts with timestamps and location information. "
        "Example: {'hourly_wind_speed': [{'timestamp': '2025-11-13T09:00', 'wind_speed_kmh': 8.5}, "
        "{'timestamp': '2025-11-13T10:00', 'wind_speed_kmh': 7.2}, ...], "
        "'location': {'latitude': 28.6139, 'longitude': 77.2090, 'city': 'Delhi'}}"
    ),
    agent=data_retrieval_agent,
)

task_generate_prediction = Task(
    description=(
        "Synthesize sensor data and meteorological forecasts to generate a 24-hour AQI prediction for Delhi. "
        "Analyze fire count data, wind speed forecasts, and DSS source attribution percentages to predict "
        "whether AQI will cross severity thresholds (Severe: 401, Very Poor: 301, Poor: 201). "
        "Apply reasoning logic: IF fire counts exceed 400 AND wind speed falls below 10 km/h AND stubble burning "
        "reaches 20%, THEN predict AQI will cross Severe threshold. "
        "Calculate confidence level (0-100) based on data completeness, recency, and consistency. "
        "Generate a clear IF-AND-THEN reasoning statement explaining the prediction with specific numerical values."
    ),
    expected_output=(
        "A dictionary containing the AQI prediction with confidence level and reasoning. "
        "Example: {'prediction': 'AQI will cross Severe threshold (401)', 'estimated_hours': 18, "
        "'confidence_level': 85.5, 'reasoning': 'IF SensorIngestAgent reports 450 new fires, AND meteorological "
        "data shows low wind speed (8 km/h average over next 24h), AND DSS forecasts stubble burning at 22%, "
        "THEN I predict AQI will cross Severe threshold (401) in 18 hours.', 'aqi_category': 'Severe', "
        "'threshold': 401, 'current_aqi': 380, 'fire_count': 450, 'avg_wind_speed_24h': 8.0, "
        "'stubble_burning_percent': 22.0}"
    ),
    agent=forecast_analysis_agent,
    context=[task_retrieve_sensor_data, task_retrieve_meteo_forecast],
)

task_output_forecast = Task(
    description=(
        "Format the prediction data into a structured JSON output and save it to the specified location. "
        "The JSON must contain prediction (with aqi_category, threshold, estimated_hours_to_threshold), "
        "confidence_level, reasoning, timestamp, and data_sources metadata. "
        "Write the JSON to a local file in the forecast-agent/output/ directory with timestamp-based filename. "
        "If FORECAST_UPLOAD_TO_S3 environment variable is true, also upload the JSON to AWS S3 in the forecasts/ prefix."
    ),
    expected_output=(
        "A dictionary confirming successful output generation with file paths. "
        "Example: {'success': True, 'output_file': 'forecast-agent/output/forecast_20251113_103000.json', "
        "'s3_uploaded': True, 's3_key': 'forecasts/forecast_20251113_103000.json', "
        "'timestamp': '2025-11-13T10:30:00Z'}"
    ),
    agent=forecast_analysis_agent,
    context=[task_generate_prediction],
)