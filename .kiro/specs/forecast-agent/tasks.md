# Implementation Plan

- [x] 1. Create S3 data reading tool
  - Implement `read_ingested_data_tool` in `forecast-agent/src/tools/s3_reader_tools.py`
  - Use boto3 to list and retrieve latest JSON file from S3 bucket
  - Parse JSON and extract CPCB, NASA, and DSS data sections
  - Calculate data quality metrics (completeness, age in hours)
  - Handle S3 access errors and missing credentials gracefully
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Create meteorological forecast tool
  - Implement `get_meteorological_forecast_tool` in `forecast-agent/src/tools/meteo_tools.py`
  - Make HTTP GET request to Open-Meteo API with Delhi coordinates
  - Parse hourly wind speed data from API response
  - Implement retry logic with exponential backoff (3 attempts)
  - Handle API failures and timeouts with error dict responses
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Create prediction logic and reasoning engine
  - Implement `synthesize_and_predict` function in `forecast-agent/src/tools/prediction_tools.py`
  - Define prediction thresholds as constants (SEVERE_AQI_THRESHOLD=401, HIGH_FIRE_COUNT=400, etc.)
  - Write conditional logic to match fire count, wind speed, and stubble burning patterns
  - Calculate estimated hours to threshold based on current AQI and trend factors
  - Generate natural language reasoning statement with specific values and thresholds
  - Implement confidence level calculation based on data quality metrics
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3_

- [x] 4. Create output generation tool
  - Implement `generate_output_tool` in `forecast-agent/src/tools/output_tools.py`
  - Format prediction data into JSON structure with prediction, confidence_level, and reasoning fields
  - Add timestamp and data source metadata to output
  - Write JSON to local file in `forecast-agent/output/` directory
  - Optionally upload to S3 if FORECAST_UPLOAD_TO_S3 environment variable is true
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5. Define data models and schemas
  - Create `forecast-agent/src/models/data_models.py` with dataclasses
  - Define CPCBData, NASAFireData, DSSData, SensorData classes
  - Define HourlyWindSpeed, MeteorologicalForecast classes
  - Define AQIPrediction, ForecastOutput classes
  - Add validation methods for required fields
  - _Requirements: 1.2, 2.3, 5.1_

- [x] 6. Create ForecastAgent agents
  - Implement DataRetrievalAgent in `forecast-agent/src/agents.py`
  - Configure agent with role, goal, backstory, and tools (read_ingested_data_tool, get_meteorological_forecast_tool)
  - Implement ForecastAnalysisAgent in `forecast-agent/src/agents.py`
  - Configure agent with role, goal, backstory, and prediction/output tools
  - Add debug logging wrapper for tool invocations
  - _Requirements: 6.1, 6.2_

- [x] 7. Define CrewAI tasks
  - Create `task_retrieve_sensor_data` in `forecast-agent/src/tasks.py`
  - Create `task_retrieve_meteo_forecast` in `forecast-agent/src/tasks.py`
  - Create `task_generate_prediction` in `forecast-agent/src/tasks.py` with context from previous tasks
  - Create `task_output_forecast` in `forecast-agent/src/tasks.py`
  - Specify expected outputs for each task
  - _Requirements: 6.3_

- [x] 8. Implement main forecast crew orchestration
  - Update `forecast-agent/src/main.py` to define forecast_crew with agents and tasks
  - Configure crew with sequential process
  - Implement `run_forecast_cycle()` function to execute crew.kickoff()
  - Add error handling for crew execution failures
  - Add timestamp logging for forecast cycle start/completion
  - _Requirements: 6.4_

- [x] 9. Add configuration management
  - Create `forecast-agent/src/config/thresholds.py` with prediction threshold constants
  - Update `forecast-agent/src/utils/env_config.py` to load forecast-specific environment variables
  - Add S3_BUCKET_NAME, FORECAST_OUTPUT_DIR, FORECAST_UPLOAD_TO_S3 to environment configuration
  - Validate required environment variables on startup
  - _Requirements: 1.4, 2.4, 5.5_

- [x] 10. Create output directory structure
  - Create `forecast-agent/output/` directory for storing forecast JSON files
  - Add `.gitkeep` file to preserve directory in version control
  - Update `.gitignore` to exclude forecast JSON files but keep directory
  - _Requirements: 5.5_

- [x] 11. Write unit tests for tools
  - Create `forecast-agent/src/tests/test_s3_reader_tools.py` with mocked boto3 client
  - Create `forecast-agent/src/tests/test_meteo_tools.py` with mocked HTTP requests
  - Create `forecast-agent/src/tests/test_prediction_tools.py` for reasoning logic
  - Create `forecast-agent/src/tests/test_output_tools.py` for JSON formatting
  - Test error handling scenarios for each tool
  - _Requirements: 1.3, 2.4, 3.1, 3.2, 3.3, 4.1, 4.2, 5.1_

- [x] 12. Write integration tests
  - Create `forecast-agent/src/tests/test_forecast_integration.py`
  - Test complete forecast workflow with mocked external services
  - Verify output JSON structure and required fields
  - Test graceful degradation with incomplete data
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
