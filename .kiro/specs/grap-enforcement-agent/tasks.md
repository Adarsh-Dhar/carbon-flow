# Implementation Plan

- [ ] 1. Set up project structure and configuration
  - Create directory structure: `grap-enforcement-agent/src/{agents,tasks,tools,config,models,tests,utils}`
  - Create `grap-enforcement-agent/output/` directory for enforcement reports
  - Add simulation parameters configuration file at `src/config/simulation_params.py`
  - Create environment configuration utility at `src/utils/env_config.py`
  - _Requirements: 1.5, 8.5_

- [ ] 2. Implement data models
  - Create `src/models/data_models.py` with dataclasses for ForecastData, AQIPrediction, TriggerValidation, EnforcementAction, EnforcementReport, EnforcementSummary
  - Add type hints and docstrings for all model classes
  - Implement JSON serialization methods for models
  - _Requirements: 7.2, 7.3_

- [ ] 3. Implement forecast reading tool
- [ ] 3.1 Create read_forecast_tool for local filesystem
  - Write `src/tools/forecast_reader_tools.py` with `read_forecast_from_file()` function
  - Implement JSON parsing and validation for required fields (prediction, confidence_level, timestamp)
  - Add error handling for file not found and malformed JSON
  - Wrap tool with debug logging decorator following CrewAI patterns
  - Define `ReadForecastArgs` schema with `source_location` parameter and `security_context`
  - _Requirements: 1.2, 1.3_

- [ ] 3.2 Add S3 support to read_forecast_tool
  - Extend `read_forecast_from_file()` to support S3 URIs (s3://bucket/key format)
  - Use boto3 S3 client to list and read latest forecast from S3
  - Add S3-specific error handling (access denied, bucket not found)
  - _Requirements: 1.2, 7.4_

- [ ] 3.3 Write unit tests for forecast reading tool
  - Test local file reading with valid forecast JSON
  - Test S3 reading with mocked boto3 client
  - Test error handling for missing files and invalid JSON
  - _Requirements: 1.2, 8.1_

- [ ] 4. Implement trigger validation tool
  - Create `validate_trigger_tool()` in `src/tools/forecast_reader_tools.py`
  - Implement logic to check if `aqi_category` equals "Severe"
  - Generate trigger_reason string with forecast details
  - Return TriggerValidation dict with trigger_activated boolean
  - Define `ValidateTriggerArgs` schema with `forecast_data` parameter
  - _Requirements: 1.1, 1.4_

- [ ] 4.1 Write unit tests for trigger validation
  - Test trigger activation for "Severe" forecast
  - Test no trigger for "Very Poor", "Moderate" forecasts
  - Test handling of invalid forecast data
  - _Requirements: 1.4_

- [ ] 5. Implement construction ban enforcement tool
  - Create `src/tools/enforcement_tools.py` with `issue_construction_ban()` function
  - Implement simulation logic to generate sites_notified count (use CONSTRUCTION_SITES_DELHI_NCR from config)
  - Return structured dict with action, status, sites_notified, region, timestamps
  - Add retry logic with exponential backoff (3 attempts)
  - Wrap tool with debug logging decorator
  - Define `ConstructionBanArgs` schema with `region` parameter and `security_context`
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [ ] 5.1 Write unit tests for construction ban tool
  - Test successful execution with default parameters
  - Test custom region parameter
  - Test error handling and retry logic
  - _Requirements: 2.4_

- [ ] 6. Implement vehicle restriction enforcement tool
  - Create `restrict_vehicles()` function in `src/tools/enforcement_tools.py`
  - Implement simulation logic for traffic post notifications (use TRAFFIC_POSTS_DELHI_NCR from config)
  - Support vehicle_categories and zones parameters with defaults
  - Return structured dict with action, status, vehicle_categories, zones, traffic_posts_notified, timestamps
  - Add retry logic with exponential backoff (3 attempts)
  - Define `RestrictVehiclesArgs` schema with `vehicle_categories`, `zones`, and `security_context`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 6.1 Write unit tests for vehicle restriction tool
  - Test successful execution with default vehicle categories
  - Test custom zones parameter
  - Test error handling and retry logic
  - _Requirements: 3.5_

- [ ] 7. Implement enforcement team dispatch tool
  - Create `dispatch_enforcement_teams()` function in `src/tools/enforcement_tools.py`
  - Use DEFAULT_HOTSPOTS from config if hotspots parameter is None
  - Generate team assignments with team IDs for each hotspot
  - Return structured dict with action, status, hotspots, teams_dispatched, assignments, timestamp
  - Add retry logic with exponential backoff (3 attempts)
  - Define `DispatchTeamsArgs` schema with `hotspots`, `teams_per_hotspot`, and `security_context`
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7.1 Write unit tests for enforcement team dispatch tool
  - Test successful execution with default hotspots
  - Test custom hotspots list
  - Test teams_per_hotspot parameter
  - Test error handling and retry logic
  - _Requirements: 4.5_

- [ ] 8. Implement public notification tool
  - Create `notify_public()` function in `src/tools/enforcement_tools.py`
  - Implement simulation logic for SAMEER app notifications (use SAMEER_APP_USERS from config)
  - Implement simulation logic for school notifications (use SCHOOLS_CLASS_5_BELOW from config)
  - Support custom alert_message and school_directive parameters
  - Return structured dict with action, status, sameer_app_notifications, schools_notified, alert_message, school_directive, timestamp
  - Add retry logic with exponential backoff (3 attempts)
  - Define `NotifyPublicArgs` schema with `alert_message`, `school_directive`, and `security_context`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8.1 Write unit tests for public notification tool
  - Test successful execution with default alert message
  - Test custom alert_message and school_directive
  - Test error handling and retry logic
  - _Requirements: 5.5_

- [ ] 9. Implement enforcement report generation tool
  - Create `src/tools/output_tools.py` with `generate_enforcement_report()` function
  - Generate enforcement_cycle_id with timestamp format "ENF-YYYYMMDD-HHMMSS"
  - Compile enforcement_actions list from tool results with sequence numbers
  - Calculate summary statistics (total_actions, successful_actions, failed_actions, duration)
  - Determine compliance_status ("COMPLETE", "PARTIAL", "FAILED")
  - Write JSON to local file: `grap-enforcement-agent/output/enforcement_{timestamp}.json`
  - Optionally upload to S3 if ENFORCEMENT_UPLOAD_TO_S3 is true
  - Define `GenerateReportArgs` schema with `trigger_data`, `enforcement_results`, and `security_context`
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 9.1 Write unit tests for enforcement report generation
  - Test report generation with all successful actions
  - Test report generation with partial failures
  - Test JSON file writing
  - Test S3 upload with mocked boto3 client
  - _Requirements: 7.3, 7.4_

- [ ] 10. Implement ForecastMonitorAgent
  - Create `src/agents.py` with ForecastMonitorAgent definition
  - Set role="Forecast Trigger Validator"
  - Set goal to monitor forecasts and determine Stage III activation
  - Write comprehensive backstory explaining monitoring responsibilities
  - Assign tools: read_forecast_tool, validate_trigger_tool
  - Set verbose=True for debugging
  - Register tools using CrewAI Tool class with debug logging wrappers
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 11. Implement EnforcementExecutionAgent
  - Create EnforcementExecutionAgent in `src/agents.py`
  - Set role="GRAP Stage III Protocol Executor"
  - Set goal to execute all four enforcement actions sequentially
  - Write comprehensive backstory explaining enforcement coordination responsibilities
  - Assign tools: issue_construction_ban_tool, restrict_vehicles_tool, dispatch_enforcement_teams_tool, notify_public_tool, generate_enforcement_report_tool
  - Set verbose=True for debugging
  - Register all tools using CrewAI Tool class with debug logging wrappers
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 12. Implement CrewAI tasks
  - Create `src/tasks.py` with task definitions
  - Define `read_forecast_task` for ForecastMonitorAgent to read and validate forecast
  - Define `validate_trigger_task` for ForecastMonitorAgent to check trigger condition
  - Define `execute_construction_ban_task` for EnforcementExecutionAgent
  - Define `execute_vehicle_restrictions_task` for EnforcementExecutionAgent
  - Define `execute_team_dispatch_task` for EnforcementExecutionAgent
  - Define `execute_public_notification_task` for EnforcementExecutionAgent
  - Define `generate_report_task` for EnforcementExecutionAgent with context from all enforcement tasks
  - Set clear descriptions and expected_outputs for each task
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 13. Implement Crew orchestration and main execution loop
  - Create `src/main.py` with Crew definition
  - Configure Crew with Process.sequential for reliable execution order
  - Implement `run_enforcement_cycle()` function to execute crew
  - Add TOOL_RESULT_CACHE global dict for fallback execution
  - Implement fallback execution logic for RESOURCE_EXHAUSTED errors
  - Add error handling for tool failures with graceful degradation
  - Log execution start, end, and duration
  - Call `configure_llm_from_env()` at module level
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 14. Implement configuration and utilities
  - Create `src/config/simulation_params.py` with constants: CONSTRUCTION_SITES_DELHI_NCR, TRAFFIC_POSTS_DELHI_NCR, DEFAULT_HOTSPOTS, SAMEER_APP_USERS, SCHOOLS_CLASS_5_BELOW
  - Create `src/utils/env_config.py` with `configure_llm_from_env()` function to set GEMINI_API_KEY
  - Add helper functions for simulation: `simulate_construction_site_count()`, `simulate_traffic_post_count()`, `simulate_sameer_app_user_count()`, `simulate_school_count_class_5_below()`
  - _Requirements: 1.5, 8.5_

- [ ] 15. Implement retry logic utility
  - Create `src/utils/retry_logic.py` with `retry_with_exponential_backoff()` decorator
  - Support configurable max_attempts (default 3) and initial_delay (default 5 seconds)
  - Implement exponential backoff: delay = initial_delay * (2 ** attempt)
  - Log retry attempts with timestamps
  - Apply decorator to all enforcement tools
  - _Requirements: 8.2, 8.3_

- [ ] 16. Write integration tests
  - Create `src/tests/test_enforcement_integration.py`
  - Test complete enforcement workflow with mocked forecast (Severe)
  - Test no enforcement execution with non-severe forecast
  - Test partial execution with simulated tool failures
  - Verify enforcement report JSON structure and required fields
  - Test S3 integration with mocked boto3 client
  - _Requirements: 1.1, 6.1, 6.2, 6.3, 7.2, 8.3_

- [ ] 17. Create main entry point and CLI
  - Add `if __name__ == "__main__":` block to `src/main.py`
  - Support command-line argument for forecast source location
  - Add `--forecast-path` argument to specify forecast JSON file or S3 URI
  - Print enforcement cycle summary to console
  - Handle KeyboardInterrupt gracefully
  - _Requirements: 1.2, 1.5_

- [ ] 18. Add project dependencies and documentation
  - Create `grap-enforcement-agent/requirements.txt` with: crewai, crewai[tools], boto3, python-dotenv, pytest
  - Create `grap-enforcement-agent/README.md` with setup instructions, usage examples, and configuration guide
  - Document environment variables required: AWS credentials, GEMINI_API_KEY, FORECAST_SOURCE_LOCATION, ENFORCEMENT_OUTPUT_DIR
  - Add example `.env.example` file
  - _Requirements: 1.5, 8.5_
