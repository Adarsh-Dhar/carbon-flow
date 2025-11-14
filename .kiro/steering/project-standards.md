---
inclusion: always
---

# Project Standards for AWS Global Vibe Hackathon - Agentic AI Systems

## Project Overview

This is an autonomous AI agent system for the AWS Global Vibe Hackathon's 'Agentic AI Systems' track. The project consists of two main agents:

1. **SensorIngestAgent**: Continuously ingests and harmonizes Delhi NCR pollution data from CPCB, NASA FIRMS, and DSS sources
2. **ForecastAgent**: Predicts 24-hour air quality forecasts for Delhi by synthesizing sensor data and meteorological forecasts

## Technology Stack

- **Framework**: CrewAI (Python)
- **LLM**: Google Gemini (via GEMINI_API_KEY)
- **Cloud**: AWS S3 for data storage
- **APIs**: CPCB data.gov.in, NASA FIRMS, DSS, Open-Meteo
- **Data Processing**: pandas, boto3
- **Python Version**: 3.9+

## Code Style and Standards

### Python Conventions

- Use type hints for all function parameters and return values
- Follow PEP 8 style guidelines
- Use `from __future__ import annotations` for forward references
- Prefer dataclasses for data models
- Use descriptive variable names (e.g., `fire_count`, `wind_speed_kmh`)

### Error Handling

- Use specific exception types, not bare `except:`
- Add `# noqa: BLE001` comment when catching broad exceptions intentionally
- Always log errors with context before raising or returning error dicts
- Implement graceful degradation when external services fail
- Return error dicts with `{"error": "...", "details": "..."}` structure for tool failures

### Logging and Debugging

- Use print statements for debug logging (CrewAI captures stdout)
- Format debug logs as: `[DEBUG {timestamp}] Tool '{tool_name}' invoked with args={args}`
- Log tool completion with result type
- Include timestamps in ISO 8601 format (UTC)

### Environment Configuration

- All API keys and credentials must be in `.env` file
- Never hardcode credentials in source code
- Use `os.getenv()` with sensible defaults where appropriate
- Required environment variables:
  - `GEMINI_API_KEY`: Google Gemini API key
  - `CPCB_API_KEY`: CPCB data.gov.in API key
  - `NASA_MAP_KEY`: NASA FIRMS API key
  - `S3_BUCKET_NAME`: AWS S3 bucket for data storage
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials
  - `INGEST_INTERVAL_SECONDS`: Sensor ingestion interval (default: 1800)

## CrewAI Agent Patterns

### Agent Definition

- Define agents with clear role, goal, and backstory
- Backstory should explain the agent's purpose and reliability requirements
- Set `verbose=True` for debugging during development
- Assign specific tools to each agent based on their responsibilities

### Tool Implementation

- Wrap tool functions with debug logging decorator
- Use Pydantic `BaseModel` for tool argument schemas
- Include `security_context` parameter for CrewAI compatibility
- Cache tool results in `TOOL_RESULT_CACHE` for fallback execution
- Tool names should be descriptive action phrases (e.g., "Fetch CPCB data")

### Task Definition

- Each task must have clear `description` and `expected_output`
- Use `context` parameter to pass outputs from previous tasks
- Tasks should be atomic and focused on single objectives
- Expected outputs should specify data format (e.g., "pandas DataFrame")

### Crew Orchestration

- Use `Process.sequential` for reliability and predictable execution order
- Implement fallback logic for LLM rate limits (especially Gemini RESOURCE_EXHAUSTED)
- Return structured dicts from `run_cycle()` functions
- Handle `KeyboardInterrupt` gracefully for operator-controlled shutdown

## AWS S3 Integration

### Data Storage Patterns

- Store ingested data as JSON in `data/` prefix
- Use timestamped filenames: `aqi_data_{YYYYMMDD_HHMMSS}.json`
- Store forecasts in `forecasts/` prefix
- Set `ContentType='application/json'` for all JSON uploads

### S3 Access

- Use boto3 S3 client for all operations
- Authenticate via environment variables or IAM roles
- List objects with prefix and sort by timestamp to get latest
- Handle S3 access errors with informative error messages

## Data Processing

### DataFrame Standards

- Use pandas for all tabular data processing
- Add `source` column to identify data origin (CPCB, NASA, DSS)
- Convert date columns to `pd.to_datetime()` for consistency
- Use `pd.concat()` with `ignore_index=True` for merging
- Preserve original data with `.copy()` before transformations

### Data Quality

- Calculate completeness metrics (0-1 scale)
- Track data age in hours from timestamp
- Flag missing or stale data sources
- Adjust confidence levels based on data quality

## Testing Requirements

### Unit Tests

- Mock external services (boto3, HTTP APIs) using pytest fixtures
- Test both success and error scenarios
- Verify error handling and retry logic
- Test data validation and parsing

### Integration Tests

- Test complete workflows with mocked external dependencies
- Verify output JSON structure and required fields
- Test graceful degradation with incomplete data
- Use realistic test data matching production formats

### Test Data

- Store mock API responses in test fixtures
- Use realistic timestamps and values
- Include edge cases (empty results, missing fields, API errors)

## Prediction Logic Standards

### Thresholds and Constants

- Define all thresholds as named constants in `config/thresholds.py`
- Document the rationale for each threshold value
- Make thresholds configurable via environment variables if needed
- Example thresholds:
  - `SEVERE_AQI_THRESHOLD = 401`
  - `HIGH_FIRE_COUNT = 400`
  - `LOW_WIND_SPEED_KMH = 10`
  - `HIGH_STUBBLE_PERCENT = 20`

### Reasoning Statements

- Use IF-AND-THEN format for clarity
- Include specific numerical values and thresholds
- Specify timeframes (e.g., "in 18 hours")
- Reference data sources explicitly
- Example: "IF SensorIngestAgent reports 450 new fires, AND meteorological data shows low wind speed (8 km/h), AND DSS forecasts stubble burning at 22%, THEN I predict AQI will cross Severe threshold (401) in 18 hours."

### Confidence Levels

- Calculate confidence as percentage (0-100)
- Start at 100% and reduce based on:
  - Data completeness: multiply by completeness ratio
  - Data age: reduce if older than 6 hours
  - API failures: reduce by 20-30%
- Never return confidence below 0% or above 100%

## File Organization

### Directory Structure

```
forecast-agent/
├── src/
│   ├── agents.py          # Agent definitions
│   ├── tasks.py           # Task definitions
│   ├── main.py            # Crew orchestration and main loop
│   ├── config/
│   │   └── thresholds.py  # Prediction thresholds
│   ├── models/
│   │   └── data_models.py # Data classes and schemas
│   ├── tools/
│   │   ├── s3_reader_tools.py
│   │   ├── meteo_tools.py
│   │   ├── prediction_tools.py
│   │   └── output_tools.py
│   ├── utils/
│   │   └── env_config.py  # Environment configuration
│   └── tests/
│       ├── test_s3_reader_tools.py
│       ├── test_meteo_tools.py
│       ├── test_prediction_tools.py
│       └── test_forecast_integration.py
└── output/                # Generated forecast JSON files
```

### Import Conventions

- Use relative imports within the same package: `from src.tools import s3_reader_tools`
- Import specific functions/classes rather than entire modules when possible
- Group imports: standard library, third-party, local modules

## Documentation

### Docstrings

- Use docstrings for all public functions and classes
- Include parameter descriptions and return value types
- Document exceptions that may be raised
- Example:
```python
def fetch_data(bucket_name: str, object_key: str | None = None) -> dict:
    """
    Fetch sensor data from AWS S3.
    
    Args:
        bucket_name: S3 bucket name
        object_key: Specific object key, or None to fetch latest
        
    Returns:
        Dict containing parsed sensor data with CPCB, NASA, and DSS sections
        
    Raises:
        ValueError: If bucket_name is empty or invalid
    """
```

### Comments

- Explain "why" not "what" in comments
- Document non-obvious logic or workarounds
- Add TODO comments for future improvements
- Use `# pragma: no cover` for code excluded from test coverage

## Performance Considerations

### API Rate Limits

- Implement exponential backoff for retries (3 attempts)
- Cache API responses when appropriate
- Handle rate limit errors gracefully (especially Gemini RESOURCE_EXHAUSTED)
- Log rate limit encounters for monitoring

### Execution Timing

- Log cycle start and completion timestamps
- Calculate and log elapsed time for each cycle
- Implement sleep intervals to respect API rate limits
- Use `time.time()` for performance measurements

## Security Best Practices

- Never commit `.env` file to version control
- Use IAM roles instead of access keys when running on AWS
- Validate and sanitize all external API responses
- Log security-relevant events (authentication failures, access errors)
- Use HTTPS for all external API calls

## Hackathon-Specific Guidelines

### Demo Readiness

- Ensure agents can run continuously without manual intervention
- Implement clear console output for demo visibility
- Generate human-readable reasoning statements for judges
- Store all predictions with timestamps for demo playback

### AWS Integration

- Highlight AWS S3 usage in architecture diagrams
- Document AWS services used (S3, IAM)
- Ensure demo can run on AWS infrastructure (EC2, Lambda)
- Consider AWS-specific optimizations (S3 Select, CloudWatch)

### Presentation Focus

- Emphasize autonomous agent capabilities
- Showcase reasoning and decision-making logic
- Demonstrate proactive vs reactive policy shift
- Highlight real-time data integration from multiple sources
