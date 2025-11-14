# Design Document - InterState-AccountabilityAgent

## Overview

The InterState-AccountabilityAgent is a CrewAI-based autonomous agent that generates evidence-based legal reports for the Commission for Air Quality Management (CAQM). It correlates pollution surges at Delhi border stations with fire events in neighboring states and stubble burning contributions to provide objective accountability evidence.

The agent operates in a trigger-based or scheduled mode, reading harmonized sensor data from AWS S3 (produced by SensorIngestAgent), performing correlation analysis, and generating structured legal reports in JSON format for CAQM submission.

## Architecture

### System Context

```
┌─────────────────────┐
│ SensorIngestAgent   │
│ (Upstream)          │
└──────────┬──────────┘
           │ Writes sensor data
           ▼
    ┌──────────────┐
    │   AWS S3     │
    │ (Data Lake)  │
    └──────┬───────┘
           │ Reads sensor data
           ▼
┌──────────────────────────────┐
│ InterState-                  │
│ AccountabilityAgent          │
│                              │
│ ┌────────────────────────┐  │
│ │ Surge Detection        │  │
│ └────────────────────────┘  │
│ ┌────────────────────────┐  │
│ │ Correlation Analysis   │  │
│ └────────────────────────┘  │
│ ┌────────────────────────┐  │
│ │ Report Generation      │  │
│ └────────────────────────┘  │
└──────────┬───────────────────┘
           │ Submits report
           ▼
    ┌──────────────┐
    │ CAQM System  │
    │ (Mock)       │
    └──────────────┘
```

### Component Architecture

The agent follows the CrewAI pattern with:
- **Agent**: InterState-AccountabilityAgent with legal analyst role
- **Tasks**: Sequential tasks for data reading, correlation, and report generation
- **Tools**: Custom tools for S3 data access and CAQM submission
- **Crew**: Orchestrates the agent and tasks with sequential processing

## Components and Interfaces

### 1. Agent Definition

**InterState-AccountabilityAgent**
- **Role**: Legal Analyst and Evidence Correlator
- **Goal**: Generate evidence-based legal reports correlating pollution surges with cross-border fire events
- **Backstory**: Expert in environmental law and data analysis, specializing in cross-border pollution accountability
- **Tools**: 
  - `read_correlated_data_tool`
  - `send_caqm_report_tool`
- **Verbose**: True (for debugging)

### 2. Tools

#### 2.1 read_correlated_data_tool

**Purpose**: Read and parse the latest sensor data from AWS S3

**Input Schema** (Pydantic BaseModel):
```python
class ReadCorrelatedDataInput(BaseModel):
    bucket_name: str
    prefix: str = "data/"
    security_context: dict | None = None
```

**Output**:
```python
{
    "cpcb_data": [
        {
            "station": "Alipur",
            "aqi": 450,
            "timestamp": "2025-11-14T08:00:00Z",
            "pm25": 350.5,
            "pm10": 420.2,
            "latitude": 28.8,
            "longitude": 77.1
        }
    ],
    "nasa_data": [
        {
            "latitude": 29.2,
            "longitude": 76.5,
            "brightness": 320.5,
            "confidence": 85,
            "acq_date": "2025-11-13",
            "state": "Haryana",
            "district": "Jind"
        }
    ],
    "dss_data": {
        "stubble_burning_percent": 22.5,
        "timestamp": "2025-11-14T06:00:00Z"
    },
    "timestamp": "2025-11-14T08:30:00Z"
}
```

**Example Report Output with Legal Citations**:
```json
{
    "report_id": "CAQM-2025-11-14-001",
    "timestamp": "2025-11-14T08:30:00Z",
    "executive_summary": "Severe pollution surge detected at Alipur border station (AQI: 450) correlating with 450 fire events in Haryana (Jind district) and 22.5% stubble burning contribution.",
    "surge_details": {
        "station": "Alipur",
        "aqi": 450,
        "pm25": 350.5,
        "pm10": 420.2,
        "timestamp": "2025-11-14T08:00:00Z"
    },
    "fire_correlation": [
        {
            "state": "Haryana",
            "fire_count": 450,
            "districts": ["Jind", "Karnal"],
            "avg_distance_km": 85.3,
            "is_high_contribution": true
        }
    ],
    "stubble_burning_contribution": 22.5,
    "reasoning": "IF Haryana reports 450 fire events within 200km, AND DSS shows 22.5% stubble burning contribution, AND Alipur station records AQI of 450, THEN cross-border agricultural fires are the primary pollution source.",
    "confidence_score": 95.0,
    "data_quality": {
        "cpcb_available": true,
        "nasa_available": true,
        "dss_available": true
    },
    "legal_citations": {
        "caqm_direction": "CAQM Direction No. 95",
        "enforcement_authority": "Section 12 of the CAQM Act, 2021",
        "enforcement_request": "Requesting immediate enforcement action under Section 12 of the CAQM Act against identified pollution sources in Haryana"
    },
    "recommendations": [
        "Immediate enforcement action in Jind and Karnal districts",
        "Deploy monitoring teams to high fire-count areas",
        "Issue notices to state authorities under CAQM Direction No. 95"
    ]
}
```

**Error Handling**:
- Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- Return error dict: `{"error": "S3 read failed", "details": "..."}`
- Log all errors with context

**Implementation Details**:
- Use boto3 S3 client to list objects with prefix
- Sort by LastModified to get latest file
- Parse JSON content
- Validate required fields (cpcb_data, timestamp)
- Cache result in TOOL_RESULT_CACHE for fallback

#### 2.2 send_caqm_report_tool

**Purpose**: Submit the generated legal report to CAQM system (mock implementation)

**Input Schema**:
```python
class SendCAQMReportInput(BaseModel):
    report: dict
    save_local: bool = True
    upload_s3: bool = True
    security_context: dict | None = None
```

**Output**:
```python
{
    "status": "success",
    "report_id": "CAQM-2025-11-14-001",
    "local_path": "interstate-accountability-agent/output/caqm_report_20251114_083000.json",
    "s3_path": "s3://bucket/reports/caqm_report_20251114_083000.json",
    "timestamp": "2025-11-14T08:30:00Z"
}
```

**Error Handling**:
- Retry CAQM submission up to 2 times
- Always save local copy even if submission fails
- Return partial success if local save works but submission fails
- Log submission attempts and results

**Implementation Details**:
- Save report to `interstate-accountability-agent/output/` directory
- Upload to S3 under `reports/` prefix
- Mock CAQM submission with HTTP POST simulation
- Generate unique report ID with timestamp
- Return comprehensive status

### 3. Tasks

#### Task 1: Read and Validate Sensor Data

**Description**: Read the latest sensor data from S3 and validate completeness

**Expected Output**: Parsed sensor data dict with CPCB, NASA, and DSS sections

**Agent**: InterState-AccountabilityAgent

**Tools**: read_correlated_data_tool

**Success Criteria**:
- CPCB data is present (critical)
- Timestamp is within last 24 hours
- Data structure is valid

#### Task 2: Detect Pollution Surge

**Description**: Analyze CPCB data to identify pollution surges at border stations

**Expected Output**: List of border stations with AQI > 300 and surge details

**Agent**: InterState-AccountabilityAgent

**Context**: Output from Task 1

**Success Criteria**:
- Identify stations with AQI exceeding 300 threshold
- Extract station metadata (name, location, pollutants)
- Flag as surge event if threshold exceeded

#### Task 3: Correlate Fire Events

**Description**: Correlate NASA FIRMS fire data with pollution surge timing and location

**Expected Output**: Fire event analysis grouped by state with counts and distances

**Agent**: InterState-AccountabilityAgent

**Context**: Output from Task 1 and Task 2

**Success Criteria**:
- Filter fires within 200km of affected station
- Group by state and district
- Calculate fire counts per state
- Identify high-contribution states (>100 fires)

#### Task 4: Generate Legal Report

**Description**: Create structured legal report with evidence, correlation analysis, and recommendations

**Expected Output**: Complete JSON report with all required sections

**Agent**: InterState-AccountabilityAgent

**Context**: Output from Task 1, 2, and 3

**Success Criteria**:
- Include executive summary
- Document all evidence with timestamps
- Provide IF-AND-THEN reasoning
- Calculate confidence score (30-100%)
- Format as valid JSON

#### Task 5: Submit Report to CAQM

**Description**: Submit the generated report to CAQM system and archive

**Expected Output**: Submission status with report ID and storage paths

**Agent**: InterState-AccountabilityAgent

**Tools**: send_caqm_report_tool

**Context**: Output from Task 4

**Success Criteria**:
- Save local copy
- Upload to S3
- Submit to CAQM (mock)
- Return status with report ID

## Data Models

### Border Station Model

```python
@dataclass
class BorderStation:
    name: str
    latitude: float
    longitude: float
    aqi: float
    pm25: float
    pm10: float
    timestamp: str
    is_surge: bool
```

### Fire Event Model

```python
@dataclass
class FireEvent:
    latitude: float
    longitude: float
    brightness: float
    confidence: int
    acq_date: str
    state: str
    district: str
    distance_km: float  # Distance from border station
```

### Correlation Result Model

```python
@dataclass
class CorrelationResult:
    state: str
    fire_count: int
    districts: list[str]
    avg_distance_km: float
    is_high_contribution: bool  # >100 fires
```

### CAQM Report Model

```python
@dataclass
class CAQMReport:
    report_id: str
    timestamp: str
    executive_summary: str
    surge_details: dict
    fire_correlation: list[CorrelationResult]
    stubble_burning_contribution: float | None
    reasoning: str
    confidence_score: float
    data_quality: dict
    legal_citations: dict
    recommendations: list[str]
```

### Legal Citations Model

```python
@dataclass
class LegalCitations:
    caqm_direction: str = "CAQM Direction No. 95"
    enforcement_authority: str = "Section 12 of the CAQM Act, 2021"
    applicable_sections: list[str] = None
    enforcement_request: str = "Requesting immediate enforcement action under Section 12 of the CAQM Act"
```

## Error Handling

### Data Availability Errors

**CPCB Data Missing**:
- Abort report generation
- Log critical error
- Return error status to caller
- Rationale: CPCB data is essential for surge detection

**NASA FIRMS Data Missing**:
- Continue with report generation
- Note missing fire data in report
- Reduce confidence by 40%
- Include data gap in data_quality section

**DSS Data Missing**:
- Continue with report generation
- Omit stubble burning analysis
- Reduce confidence by 20%
- Note in data_quality section

### S3 Access Errors

- Implement exponential backoff retry (3 attempts)
- Log each retry attempt with error details
- Return error dict after exhausting retries
- Cache successful reads for fallback

### CAQM Submission Errors

- Retry up to 2 times
- Always save local copy regardless of submission status
- Log submission failures
- Return partial success status

### Confidence Score Calculation

```python
base_confidence = 100.0

# Data completeness penalties
if nasa_data_missing:
    base_confidence -= 40.0
if dss_data_missing:
    base_confidence -= 20.0

# Correlation strength adjustments
if fire_count < 50:
    base_confidence -= 10.0
if distance_avg > 150km:
    base_confidence -= 10.0

# Minimum threshold
final_confidence = max(30.0, base_confidence)
```

## Testing Strategy

### Unit Tests

**test_read_correlated_data_tool.py**:
- Mock boto3 S3 client
- Test successful data read
- Test S3 access errors with retry logic
- Test invalid JSON parsing
- Test missing required fields

**test_send_caqm_report_tool.py**:
- Mock file system operations
- Mock S3 upload
- Mock CAQM HTTP submission
- Test local save success
- Test S3 upload failure handling
- Test CAQM submission retry logic

**test_correlation_logic.py**:
- Test surge detection with various AQI values
- Test fire event filtering by distance
- Test state grouping and counting
- Test confidence score calculation
- Test data quality assessment

### Integration Tests

**test_accountability_integration.py**:
- Mock S3 with realistic sensor data
- Test complete workflow from data read to report submission
- Test with missing NASA data
- Test with missing DSS data
- Test with no pollution surge detected
- Verify report JSON structure
- Verify confidence score ranges

### Test Data

Create fixtures with:
- Border station data (Alipur, Anand Vihar, Dwarka)
- Fire events in Haryana, Punjab, UP
- Various AQI levels (200, 350, 450)
- Stubble burning percentages (15%, 25%, 35%)
- Timestamps for correlation windows

## Configuration

### Thresholds (config/thresholds.py)

```python
# Pollution surge detection
SURGE_AQI_THRESHOLD = 300

# Fire correlation
FIRE_CORRELATION_RADIUS_KM = 200
HIGH_CONTRIBUTION_FIRE_COUNT = 100

# Confidence scoring
MIN_CONFIDENCE_SCORE = 30.0
NASA_DATA_MISSING_PENALTY = 40.0
DSS_DATA_MISSING_PENALTY = 20.0
LOW_FIRE_COUNT_PENALTY = 10.0  # <50 fires
HIGH_DISTANCE_PENALTY = 10.0  # >150km avg

# Timing
CORRELATION_WINDOW_HOURS = 48
MAX_DATA_AGE_HOURS = 24
EXECUTION_TIMEOUT_MINUTES = 10

# Retry configuration
S3_READ_RETRIES = 3
CAQM_SUBMISSION_RETRIES = 2
RETRY_BACKOFF_BASE_SECONDS = 1
```

### Border Stations Configuration

```python
DELHI_BORDER_STATIONS = [
    {"name": "Alipur", "latitude": 28.8, "longitude": 77.1, "border": "Haryana"},
    {"name": "Anand Vihar", "latitude": 28.65, "longitude": 77.32, "border": "UP"},
    {"name": "Dwarka", "latitude": 28.59, "longitude": 77.05, "border": "Haryana"},
    {"name": "Rohini", "latitude": 28.74, "longitude": 77.12, "border": "Haryana"},
]
```

## Deployment Considerations

### Execution Modes

**Trigger-Based**:
- Invoked by SensorIngestAgent after data upload
- Checks for pollution surges in latest data
- Generates report only if surge detected

**Scheduled**:
- Runs every 6 hours via cron or AWS EventBridge
- Checks for unreported surges
- Prevents duplicate reports using report log

### Report Deduplication

Maintain a log file `interstate-accountability-agent/report_log.json`:
```json
{
    "reports": [
        {
            "report_id": "CAQM-2025-11-14-001",
            "station": "Alipur",
            "aqi": 450,
            "timestamp": "2025-11-14T08:00:00Z",
            "generated_at": "2025-11-14T08:30:00Z"
        }
    ]
}
```

Check log before generating new report to avoid duplicates for same surge event.

### Performance Targets

- Data read from S3: < 30 seconds
- Correlation analysis: < 2 minutes
- Report generation: < 3 minutes
- Total execution: < 10 minutes
- Memory usage: < 512 MB

## Security Considerations

- Use IAM roles for S3 access (no hardcoded credentials)
- Validate all input data before processing
- Sanitize file paths to prevent directory traversal
- Log all CAQM submissions for audit trail
- Encrypt reports at rest in S3 (SSE-S3)

## Future Enhancements

- Real CAQM API integration (replace mock)
- Wind direction analysis for pollution transport modeling
- Historical trend analysis for recurring patterns
- Multi-pollutant correlation (PM2.5, PM10, NO2, SO2)
- Automated email notifications to state governments
- Interactive dashboard for report visualization
