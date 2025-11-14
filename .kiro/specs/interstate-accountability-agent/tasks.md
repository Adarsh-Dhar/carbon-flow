# Implementation Plan

- [x] 1. Set up project structure and configuration
  - Create directory structure: `interstate-accountability-agent/src/` with subdirectories for tools, tests, config, models, and utils
  - Create `interstate-accountability-agent/output/` directory for generated reports
  - Define border stations configuration in `config/border_stations.py`
  - Define thresholds and constants in `config/thresholds.py`
  - _Requirements: 7.3_

- [ ] 2. Implement data models
  - Create `models/data_models.py` with BorderStation, FireEvent, CorrelationResult, LegalCitations, and CAQMReport dataclasses
  - Add type hints and validation methods for each model
  - Implement model serialization to/from dict for JSON compatibility
  - Include legal_citations field in CAQMReport with CAQM Direction No. 95 and Section 12 references
  - _Requirements: 1.3, 2.3, 4.2, 4.5, 4.6_

- [ ] 3. Implement read_correlated_data_tool
  - Create `tools/s3_reader_tools.py` with ReadCorrelatedDataInput Pydantic schema
  - Implement S3 client initialization using boto3 with environment variables
  - Write function to list S3 objects with prefix and sort by LastModified
  - Implement JSON parsing and validation of required fields (cpcb_data, timestamp)
  - Add exponential backoff retry logic (3 attempts: 1s, 2s, 4s delays)
  - Implement error handling with structured error dict returns
  - Add debug logging with timestamps for tool invocation and completion
  - Cache successful results in TOOL_RESULT_CACHE dict
  - _Requirements: 1.1, 1.5, 6.1_

- [ ] 3.1 Write unit tests for read_correlated_data_tool
  - Create `tests/test_s3_reader_tools.py` with pytest fixtures
  - Mock boto3 S3 client using unittest.mock
  - Test successful data read with valid JSON
  - Test S3 access errors with retry logic verification
  - Test invalid JSON parsing error handling
  - Test missing required fields validation
  - _Requirements: 1.1, 1.5_

- [ ] 4. Implement surge detection logic
  - Create `tools/surge_detection_tools.py` with surge detection function
  - Filter CPCB data for border stations using DELHI_BORDER_STATIONS config
  - Identify stations with AQI exceeding SURGE_AQI_THRESHOLD (300)
  - Extract station metadata: name, location, AQI, PM2.5, PM10, timestamp
  - Return list of BorderStation objects with is_surge flag set to True
  - Add logging for detected surges with station names and AQI values
  - _Requirements: 1.2, 1.3, 1.4_

- [ ] 4.1 Write unit tests for surge detection
  - Create `tests/test_surge_detection_tools.py`
  - Test surge detection with AQI values above and below threshold
  - Test filtering for border stations only
  - Test with empty CPCB data
  - Test with missing AQI fields
  - _Requirements: 1.2, 1.3_

- [ ] 5. Implement fire correlation logic
  - Create `tools/correlation_tools.py` with fire correlation functions
  - Implement haversine distance calculation for fire-to-station distance
  - Filter NASA FIRMS data for fires within FIRE_CORRELATION_RADIUS_KM (200km)
  - Filter fires within CORRELATION_WINDOW_HOURS (48 hours) before surge timestamp
  - Group fire events by state and district
  - Calculate fire count per state and flag states with count > HIGH_CONTRIBUTION_FIRE_COUNT (100)
  - Return list of CorrelationResult objects with state, fire_count, districts, avg_distance_km
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 5.1 Write unit tests for fire correlation
  - Create `tests/test_correlation_tools.py`
  - Test haversine distance calculation with known coordinates
  - Test fire filtering by distance (within and outside radius)
  - Test fire filtering by time window
  - Test state grouping and counting
  - Test high-contribution state flagging
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 6. Implement confidence score calculation
  - Add confidence calculation function to `tools/correlation_tools.py`
  - Start with base confidence of 100.0
  - Apply NASA_DATA_MISSING_PENALTY (40.0) if NASA data unavailable
  - Apply DSS_DATA_MISSING_PENALTY (20.0) if DSS data unavailable
  - Apply LOW_FIRE_COUNT_PENALTY (10.0) if fire count < 50
  - Apply HIGH_DISTANCE_PENALTY (10.0) if average distance > 150km
  - Enforce minimum confidence of MIN_CONFIDENCE_SCORE (30.0)
  - Return confidence score as float between 30.0 and 100.0
  - _Requirements: 4.4, 6.2, 6.3, 6.4, 6.5_

- [ ] 6.1 Write unit tests for confidence calculation
  - Test confidence with all data available (should be 100.0)
  - Test confidence with missing NASA data (should reduce by 40)
  - Test confidence with missing DSS data (should reduce by 20)
  - Test confidence with low fire count penalty
  - Test confidence with high distance penalty
  - Test minimum confidence threshold enforcement
  - _Requirements: 4.4, 6.2, 6.3, 6.4, 6.5_

- [ ] 7. Implement report generation logic
  - Create `tools/report_generation_tools.py` with report generation function
  - Generate unique report ID with format "CAQM-YYYY-MM-DD-NNN"
  - Create executive summary with surge station, AQI, and top contributing states
  - Build surge_details section with station metadata and pollutant concentrations
  - Build fire_correlation section with CorrelationResult list
  - Extract stubble_burning_contribution from DSS data if available
  - Generate IF-AND-THEN reasoning statement correlating fires, weather, and surge
  - Calculate confidence score using confidence calculation function
  - Build data_quality section listing available and missing data sources
  - Build legal_citations section with CAQM Direction No. 95 and Section 12 of the CAQM Act references
  - Generate recommendations list based on fire counts and stubble burning percentage
  - Include formal enforcement request citing Section 12 authority
  - Return CAQMReport object serialized to dict
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7.1 Write unit tests for report generation
  - Create `tests/test_report_generation_tools.py`
  - Test report generation with complete data
  - Test report generation with missing NASA data
  - Test report generation with missing DSS data
  - Test report ID format and uniqueness
  - Test reasoning statement format
  - Test recommendations generation
  - Verify JSON serialization of report
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 8. Implement send_caqm_report_tool
  - Create `tools/caqm_submission_tools.py` with SendCAQMReportInput Pydantic schema
  - Implement local file save to `interstate-accountability-agent/output/` with timestamped filename
  - Implement S3 upload to `reports/` prefix using boto3
  - Implement mock CAQM submission with simulated HTTP POST
  - Add retry logic for CAQM submission (2 attempts)
  - Return submission status dict with report_id, local_path, s3_path, timestamp
  - Handle partial success (local save works but submission fails)
  - Add debug logging for all submission steps
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8.1 Write unit tests for send_caqm_report_tool
  - Create `tests/test_caqm_submission_tools.py`
  - Mock file system operations using unittest.mock
  - Mock boto3 S3 upload
  - Mock HTTP POST for CAQM submission
  - Test successful submission with all steps
  - Test local save success with S3 upload failure
  - Test local save success with CAQM submission failure
  - Test retry logic for CAQM submission
  - Verify status dict structure
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 9. Implement report deduplication logic
  - Create `utils/report_log.py` with report log management functions
  - Implement function to load report log from `interstate-accountability-agent/report_log.json`
  - Implement function to check if surge event already has a report (match by station and timestamp within 1 hour)
  - Implement function to add new report entry to log
  - Implement function to save updated log to file
  - Handle missing log file gracefully (create new log)
  - _Requirements: 7.3, 7.4_

- [ ] 9.1 Write unit tests for report deduplication
  - Create `tests/test_report_log.py`
  - Test loading existing report log
  - Test creating new report log when file missing
  - Test duplicate detection for same surge event
  - Test adding new report entry
  - Test saving updated log
  - _Requirements: 7.3, 7.4_

- [ ] 10. Define CrewAI agent
  - Create `src/agents.py` with InterState-AccountabilityAgent definition
  - Set role to "Legal Analyst and Evidence Correlator"
  - Set goal to "Generate evidence-based legal reports correlating pollution surges with cross-border fire events"
  - Write backstory explaining expertise in environmental law and data analysis
  - Assign tools: read_correlated_data_tool, send_caqm_report_tool
  - Set verbose=True for debugging
  - Use Google Gemini LLM via GEMINI_API_KEY environment variable
  - _Requirements: 1.1, 5.1_

- [ ] 11. Define CrewAI tasks
  - Create `src/tasks.py` with task definitions
  - Define Task 1: Read and validate sensor data (uses read_correlated_data_tool)
  - Define Task 2: Detect pollution surge (uses surge detection logic)
  - Define Task 3: Correlate fire events (uses correlation logic)
  - Define Task 4: Generate legal report (uses report generation logic)
  - Define Task 5: Submit report to CAQM (uses send_caqm_report_tool)
  - Set task context dependencies (each task uses output from previous)
  - Write clear descriptions and expected outputs for each task
  - _Requirements: 1.1, 1.2, 2.1, 4.1, 5.1_

- [ ] 12. Implement crew orchestration and main execution loop
  - Create `src/main.py` with crew setup and execution logic
  - Initialize InterState-AccountabilityAgent with tools
  - Create Crew with agent, tasks, and Process.sequential
  - Implement run_cycle() function to execute crew and return result dict
  - Add error handling for LLM rate limits (Gemini RESOURCE_EXHAUSTED)
  - Implement fallback logic using TOOL_RESULT_CACHE
  - Add logging for cycle start, completion, and elapsed time
  - Handle KeyboardInterrupt for graceful shutdown
  - Check report log for duplicates before starting cycle
  - _Requirements: 7.1, 7.2, 7.4, 7.5_

- [ ] 12.1 Write integration tests
  - Create `tests/test_accountability_integration.py`
  - Mock S3 with realistic sensor data fixtures
  - Test complete workflow from data read to report submission
  - Test workflow with missing NASA data (reduced confidence)
  - Test workflow with missing DSS data (reduced confidence)
  - Test workflow with no pollution surge detected (no report generated)
  - Verify report JSON structure and required fields
  - Verify confidence score ranges (30-100)
  - Test duplicate report prevention
  - _Requirements: 1.1, 1.2, 2.1, 4.1, 5.1, 6.1, 6.2, 6.3, 6.4, 6.5, 7.4_

- [ ] 13. Create environment configuration
  - Create `.env.example` file with required environment variables
  - Document GEMINI_API_KEY for Google Gemini LLM
  - Document AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY for S3 access
  - Document S3_BUCKET_NAME for data storage
  - Document optional CAQM_API_ENDPOINT for real CAQM integration
  - Add comments explaining each variable's purpose
  - _Requirements: 5.1, 5.3_

- [ ] 14. Create execution script
  - Create `interstate-accountability-agent/run_accountability.py` as entry point
  - Load environment variables from .env file
  - Import and call run_cycle() from main.py
  - Print execution summary with report ID and status
  - Handle errors and print user-friendly error messages
  - Add command-line argument for bucket name override
  - _Requirements: 7.1, 7.2, 7.5_
