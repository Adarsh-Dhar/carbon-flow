# Design Document: ForecastAgent

## Overview

The ForecastAgent is an autonomous AI system that predicts 24-hour air quality forecasts for Delhi by synthesizing historical sensor data, real-time meteorological forecasts, and pollution source attribution. Built on the CrewAI framework, the agent orchestrates data retrieval, analysis, and prediction generation through specialized agents and tools.

The system reads ingested data from AWS S3 (produced by the SensorIngestAgent), fetches meteorological forecasts from Open-Meteo API, applies reasoning logic to predict AQI levels, and outputs structured JSON predictions with confidence levels and explanations.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ForecastAgent                          │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ Data Retrieval   │         │ Forecast Analysis│        │
│  │     Agent        │────────▶│      Agent       │        │
│  └──────────────────┘         └──────────────────┘        │
│         │                              │                   │
│         │                              │                   │
│         ▼                              ▼                   │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  Read Ingested   │         │  Synthesize &    │        │
│  │   Data Tool      │         │  Predict Tool    │        │
│  │                  │         │                  │        │
│  │  Get Meteo       │         │  Generate Output │        │
│  │  Forecast Tool   │         │      Tool        │        │
│  └──────────────────┘         └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│   AWS S3        │           │  Output JSON    │
│  (Ingested Data)│           │   (Prediction)  │
└─────────────────┘           └─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│  Open-Meteo API │
│ (Weather Data)  │
└─────────────────┘
```

### Component Interaction Flow

1. **Data Retrieval Agent** executes tasks to gather input data:
   - Reads latest ingested sensor data from S3 (CPCB AQI, NASA fires, DSS sources)
   - Fetches 48-hour wind speed forecast from Open-Meteo API

2. **Forecast Analysis Agent** processes the data:
   - Applies reasoning logic to synthesize inputs
   - Generates AQI prediction with timeframe
   - Calculates confidence level based on data quality
   - Produces natural language reasoning explanation

3. **Output Generation** creates structured JSON:
   - Formats prediction, confidence_level, and reasoning
   - Writes to specified output location

## Components and Interfaces

### Agents

#### 1. DataRetrievalAgent

**Role:** Data Collector and Validator

**Goal:** Retrieve all necessary input data from S3 and meteorological APIs with validation

**Backstory:** You are the data acquisition specialist who ensures the ForecastAgent has complete, accurate, and timely input data. You validate data completeness and flag any missing or stale data sources.

**Tools:**
- `read_ingested_data_tool`
- `get_meteorological_forecast_tool`

**Responsibilities:**
- Read latest JSON files from S3 bucket
- Parse and validate sensor data structure
- Fetch wind speed forecasts from Open-Meteo
- Report data quality metrics (completeness, recency)

#### 2. ForecastAnalysisAgent

**Role:** Air Quality Forecaster and Reasoner

**Goal:** Generate accurate 24-hour AQI predictions with confidence levels and clear reasoning

**Backstory:** You are an expert air quality analyst who understands the complex relationships between fire events, meteorological conditions, pollution sources, and AQI levels. You synthesize multiple data streams to predict air quality trends and explain your reasoning clearly for policy makers.

**Tools:**
- `synthesize_and_predict_tool` (internal reasoning)
- `generate_output_tool`

**Responsibilities:**
- Apply prediction logic based on thresholds
- Calculate confidence levels
- Generate reasoning statements
- Format output JSON

### Tools

#### 1. read_ingested_data_tool

**Purpose:** Read sensor data JSON files from AWS S3

**Input Parameters:**
- `bucket_name` (str): S3 bucket name (from environment: S3_BUCKET_NAME)
- `object_key` (str, optional): Specific S3 object key. If not provided, reads the latest file

**Output:**
```python
{
    "cpcb_data": {
        "aqi": float,
        "timestamp": str,
        "station": str
    },
    "nasa_data": {
        "fire_count": int,
        "region": str,
        "timestamp": str
    },
    "dss_data": {
        "stubble_burning_percent": float,
        "vehicular_percent": float,
        "industrial_percent": float,
        "timestamp": str
    },
    "data_quality": {
        "completeness": float,  # 0-1
        "age_hours": float
    }
}
```

**Error Handling:**
- Returns error dict with `error` key if S3 access fails
- Returns partial data with warnings if JSON parsing fails
- Logs AWS credential issues

**Implementation Details:**
- Uses boto3 S3 client
- Authenticates via AWS credentials from environment or IAM role
- Lists objects with prefix `data/aqi_data_` and sorts by timestamp to get latest
- Parses JSON and validates expected fields

#### 2. get_meteorological_forecast_tool

**Purpose:** Fetch 48-hour wind speed forecast for Delhi from Open-Meteo API

**Input Parameters:**
- `latitude` (float, default=28.6139): Delhi latitude
- `longitude` (float, default=77.2090): Delhi longitude
- `hours` (int, default=48): Forecast hours to retrieve

**Output:**
```python
{
    "hourly_wind_speed": [
        {
            "timestamp": str,  # ISO 8601
            "wind_speed_kmh": float
        },
        ...
    ],
    "location": {
        "latitude": float,
        "longitude": float,
        "city": "Delhi"
    }
}
```

**API Endpoint:**
```
GET https://api.open-meteo.com/v1/forecast
?latitude=28.6139
&longitude=77.2090
&hourly=wind_speed_10m
&forecast_days=2
&wind_speed_unit=kmh
```

**Error Handling:**
- Returns error dict if API request fails
- Retries up to 3 times with exponential backoff
- Logs HTTP errors with status codes

**Implementation Details:**
- Uses requests library for HTTP calls
- No authentication required (free API)
- Converts wind speed to km/h if needed
- Parses hourly forecast array

#### 3. synthesize_and_predict_tool (Internal)

**Purpose:** Apply reasoning logic to generate AQI prediction

**Input:** Combined data from read_ingested_data_tool and get_meteorological_forecast_tool

**Logic:**

```python
# Prediction thresholds
SEVERE_AQI_THRESHOLD = 401
HIGH_FIRE_COUNT = 400
LOW_WIND_SPEED_KMH = 10
HIGH_STUBBLE_PERCENT = 20

# Reasoning logic
if (fire_count > HIGH_FIRE_COUNT and 
    avg_wind_speed_24h < LOW_WIND_SPEED_KMH and 
    stubble_burning_percent >= HIGH_STUBBLE_PERCENT):
    
    prediction = "AQI will cross Severe threshold (401)"
    estimated_hours = calculate_time_to_threshold(current_aqi, fire_count, wind_speed)
    
# Additional logic for other scenarios...
```

**Confidence Calculation:**
```python
confidence = 100.0
if data_quality['completeness'] < 1.0:
    confidence *= data_quality['completeness']
if data_quality['age_hours'] > 6:
    confidence *= max(0.5, 1.0 - (data_quality['age_hours'] - 6) / 24)
if any_api_errors:
    confidence *= 0.8
```

**Output:**
```python
{
    "prediction": str,
    "estimated_hours": int,
    "confidence_level": float,
    "reasoning": str
}
```

#### 4. generate_output_tool

**Purpose:** Format and write final prediction JSON

**Input:** Prediction data from synthesize_and_predict_tool

**Output File Format:**
```json
{
    "prediction": {
        "aqi_category": "Severe",
        "threshold": 401,
        "estimated_hours_to_threshold": 18
    },
    "confidence_level": 85.5,
    "reasoning": "IF SensorIngestAgent reports 450 new fires, AND meteorological data shows low wind speed (8 km/h average over next 24h), AND DSS forecasts stubble burning's contribution will rise to 22%, THEN I predict the AQI will cross the 'Severe' threshold (401) in 18 hours.",
    "timestamp": "2025-11-13T10:30:00Z",
    "data_sources": {
        "sensor_data_age_hours": 2.5,
        "meteorological_forecast_retrieved": true
    }
}
```

**Output Location:**
- Local file: `forecast-agent/output/forecast_{timestamp}.json`
- Optional S3 upload: `s3://{bucket}/forecasts/forecast_{timestamp}.json`

## Data Models

### SensorData

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CPCBData:
    aqi: float
    timestamp: datetime
    station: str
    pm25: float | None = None
    pm10: float | None = None

@dataclass
class NASAFireData:
    fire_count: int
    region: str
    timestamp: datetime
    confidence_high: int | None = None

@dataclass
class DSSData:
    stubble_burning_percent: float
    vehicular_percent: float
    industrial_percent: float
    dust_percent: float | None = None
    timestamp: datetime

@dataclass
class SensorData:
    cpcb: CPCBData
    nasa: NASAFireData
    dss: DSSData
    data_quality: dict[str, float]
```

### MeteorologicalForecast

```python
@dataclass
class HourlyWindSpeed:
    timestamp: datetime
    wind_speed_kmh: float

@dataclass
class MeteorologicalForecast:
    hourly_wind_speed: list[HourlyWindSpeed]
    location: dict[str, float | str]
    forecast_retrieved_at: datetime
```

### Prediction

```python
@dataclass
class AQIPrediction:
    aqi_category: str
    threshold: int
    estimated_hours_to_threshold: int

@dataclass
class ForecastOutput:
    prediction: AQIPrediction
    confidence_level: float
    reasoning: str
    timestamp: datetime
    data_sources: dict[str, any]
```

## Error Handling

### S3 Access Errors

**Scenario:** AWS credentials missing or S3 bucket inaccessible

**Handling:**
- Tool returns error dict: `{"error": "S3 access failed", "details": "..."}`
- DataRetrievalAgent logs error and reports to ForecastAnalysisAgent
- ForecastAnalysisAgent reduces confidence to 0 and outputs prediction with caveat

### API Failures

**Scenario:** Open-Meteo API timeout or rate limit

**Handling:**
- Retry with exponential backoff (3 attempts)
- If all retries fail, return error dict
- ForecastAnalysisAgent proceeds with historical wind data if available
- Confidence level reduced by 30%

### Incomplete Data

**Scenario:** Missing fields in S3 JSON or partial API response

**Handling:**
- Parse available fields and flag missing data
- Calculate data_quality['completeness'] metric
- Adjust confidence level proportionally
- Include data quality warnings in reasoning

### Prediction Edge Cases

**Scenario:** Input data doesn't match any prediction threshold patterns

**Handling:**
- Generate conservative prediction based on current AQI trend
- Provide reasoning explaining uncertainty
- Set confidence level to 50% or lower
- Suggest data sources needed for better prediction

## Testing Strategy

### Unit Tests

**Tool Testing:**
- `test_read_ingested_data_tool_success`: Mock boto3 S3 client, verify JSON parsing
- `test_read_ingested_data_tool_missing_bucket`: Test error handling for missing bucket
- `test_get_meteorological_forecast_tool_success`: Mock Open-Meteo API response
- `test_get_meteorological_forecast_tool_retry`: Test retry logic on API failure
- `test_synthesize_prediction_severe_threshold`: Verify prediction logic for severe conditions
- `test_confidence_calculation`: Test confidence adjustments for various data quality scenarios

**Agent Testing:**
- `test_data_retrieval_agent_execution`: Verify agent calls correct tools in sequence
- `test_forecast_analysis_agent_reasoning`: Validate reasoning statement generation

### Integration Tests

**End-to-End Workflow:**
- `test_forecast_crew_complete_workflow`: Run full crew with mocked S3 and API
- `test_forecast_output_json_format`: Verify output JSON structure and required fields
- `test_forecast_with_missing_data`: Test graceful degradation with incomplete inputs

**External Service Integration:**
- `test_s3_read_real_bucket`: Integration test with actual S3 bucket (optional, requires AWS credentials)
- `test_open_meteo_api_real_call`: Integration test with real API (rate-limited)

### Test Data

**Mock S3 JSON:**
```json
{
    "data": [
        {
            "source": "CPCB",
            "aqi": 380,
            "timestamp": "2025-11-13T08:00:00Z",
            "station": "Delhi-Anand Vihar"
        },
        {
            "source": "NASA",
            "fire_count": 450,
            "region": "Punjab-Haryana",
            "timestamp": "2025-11-13T08:00:00Z"
        },
        {
            "source": "DSS",
            "stubble_burning_percent": 22,
            "vehicular_percent": 35,
            "industrial_percent": 18,
            "timestamp": "2025-11-13T08:00:00Z"
        }
    ]
}
```

**Mock Open-Meteo Response:**
```json
{
    "hourly": {
        "time": ["2025-11-13T09:00", "2025-11-13T10:00", ...],
        "wind_speed_10m": [8.5, 7.2, 6.8, ...]
    }
}
```

## Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=<aws_key>
AWS_SECRET_ACCESS_KEY=<aws_secret>
AWS_DEFAULT_REGION=ap-south-1
S3_BUCKET_NAME=<bucket_name>

# LLM Configuration (for CrewAI agents)
GEMINI_API_KEY=<gemini_key>

# Forecast Configuration
FORECAST_OUTPUT_DIR=forecast-agent/output
FORECAST_UPLOAD_TO_S3=true  # Optional: upload predictions to S3
```

### Prediction Thresholds (Configurable)

```python
# forecast-agent/src/config/thresholds.py
SEVERE_AQI_THRESHOLD = 401
VERY_POOR_AQI_THRESHOLD = 301
HIGH_FIRE_COUNT = 400
LOW_WIND_SPEED_KMH = 10
HIGH_STUBBLE_PERCENT = 20
```

## Deployment Considerations

### Execution Schedule

- Run ForecastAgent every 6 hours to generate updated predictions
- Coordinate with SensorIngestAgent schedule (runs every 30 minutes)
- Ensure latest sensor data is available before forecast execution

### Resource Requirements

- Python 3.9+
- Dependencies: crewai, boto3, requests, pandas
- AWS IAM role with S3 read permissions
- Network access to Open-Meteo API

### Monitoring

- Log all tool executions with timestamps
- Track prediction accuracy over time (compare predictions to actual AQI)
- Alert on consecutive API failures or S3 access issues
- Monitor confidence levels (alert if consistently below 60%)
