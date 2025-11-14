# Design Document: GRAP-EnforcementAgent

## Overview

The GRAP-EnforcementAgent is an autonomous AI system that executes Delhi's Graded Response Action Plan (GRAP) Stage III enforcement protocol when triggered by severe air quality forecasts. Built on the CrewAI framework, the agent monitors ForecastAgent outputs and automatically initiates four sequential enforcement actions: construction bans, vehicle restrictions, enforcement team deployment, and public notifications.

The system reads forecast JSON files (from local filesystem or AWS S3), validates the severity classification, and executes enforcement tools in a predefined sequence. Each tool simulates real-world enforcement actions and returns structured results for audit and compliance tracking.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  GRAP-EnforcementAgent                      │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ Forecast Monitor │         │ Enforcement      │        │
│  │     Agent        │────────▶│ Execution Agent  │        │
│  └──────────────────┘         └──────────────────┘        │
│         │                              │                   │
│         │                              │                   │
│         ▼                              ▼                   │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ Read Forecast    │         │ Execute GRAP     │        │
│  │     Tool         │         │ Stage III Tools  │        │
│  │                  │         │                  │        │
│  │ Validate Trigger │         │ 1. Construction  │        │
│  │     Tool         │         │ 2. Vehicles      │        │
│  │                  │         │ 3. Teams         │        │
│  │                  │         │ 4. Public        │        │
│  └──────────────────┘         └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│ ForecastAgent   │           │ Enforcement Log │
│   Output JSON   │           │      JSON       │
│  (S3 or Local)  │           │  (S3 or Local)  │
└─────────────────┘           └─────────────────┘
```

### Component Interaction Flow

1. **Forecast Monitor Agent** checks for new forecasts:
   - Reads latest forecast JSON from S3 or local filesystem
   - Parses prediction field to extract severity classification
   - Validates if trigger condition is met (prediction == "Severe")

2. **Enforcement Execution Agent** executes Stage III protocol:
   - Sequentially invokes four enforcement tools
   - Logs each tool execution with timestamp and result
   - Continues execution even if individual tools fail
   - Generates comprehensive enforcement report

3. **Output Generation** creates audit trail:
   - Formats enforcement actions and results as JSON
   - Writes to local filesystem with timestamped filename
   - Optionally uploads to S3 for centralized logging

## Components and Interfaces

### Agents

#### 1. ForecastMonitorAgent

**Role:** Forecast Trigger Validator

**Goal:** Monitor ForecastAgent outputs and determine if GRAP Stage III enforcement should be activated

**Backstory:** You are the automated monitoring system that continuously watches air quality forecasts and triggers enforcement protocols when severe pollution events are predicted. You ensure that enforcement actions are initiated promptly and only when necessary, based on validated forecast data.

**Tools:**
- `read_forecast_tool`
- `validate_trigger_tool`

**Responsibilities:**
- Read latest forecast JSON from configured location
- Parse and validate forecast structure
- Extract prediction severity classification
- Determine if Stage III trigger condition is met
- Report trigger decision to Enforcement Execution Agent

#### 2. EnforcementExecutionAgent

**Role:** GRAP Stage III Protocol Executor

**Goal:** Execute all four GRAP Stage III enforcement actions sequentially and generate comprehensive audit logs

**Backstory:** You are the enforcement coordinator responsible for implementing Delhi's GRAP Stage III protocol. When activated by a severe air quality forecast, you systematically execute construction bans, vehicle restrictions, enforcement team deployments, and public notifications. You ensure all actions are logged for compliance and continue execution even if individual actions encounter issues.

**Tools:**
- `issue_construction_ban_tool`
- `restrict_vehicles_tool`
- `dispatch_enforcement_teams_tool`
- `notify_public_tool`
- `generate_enforcement_report_tool`

**Responsibilities:**
- Execute enforcement tools in defined sequence
- Log each tool invocation and result
- Handle tool failures gracefully
- Generate comprehensive enforcement report
- Write output JSON to filesystem and S3

### Tools

#### 1. read_forecast_tool

**Purpose:** Read forecast JSON from ForecastAgent output location

**Input Parameters:**
- `source_location` (str): Path to forecast JSON (local file path or S3 URI)
- `bucket_name` (str, optional): S3 bucket name if reading from S3
- `object_key` (str, optional): Specific S3 object key, or None to read latest

**Output:**
```python
{
    "prediction": {
        "aqi_category": str,  # "Severe", "Very Poor", etc.
        "threshold": int,
        "estimated_hours_to_threshold": int
    },
    "confidence_level": float,
    "reasoning": str,
    "timestamp": str,  # ISO 8601
    "data_sources": dict
}
```

**Error Handling:**
- Returns error dict if file not found or S3 access fails
- Returns error dict if JSON parsing fails
- Logs missing or malformed fields

**Implementation Details:**
- Supports both local filesystem and S3 sources
- Uses boto3 for S3 access (if S3 URI provided)
- Lists objects with prefix `forecasts/forecast_` and sorts by timestamp to get latest
- Validates required fields: prediction, confidence_level, timestamp

#### 2. validate_trigger_tool

**Purpose:** Determine if forecast meets GRAP Stage III trigger criteria

**Input Parameters:**
- `forecast_data` (dict): Parsed forecast JSON from read_forecast_tool

**Output:**
```python
{
    "trigger_activated": bool,
    "trigger_reason": str,
    "forecast_timestamp": str,
    "aqi_category": str,
    "confidence_level": float
}
```

**Trigger Logic:**
```python
def validate_trigger(forecast_data: dict) -> dict:
    aqi_category = forecast_data.get("prediction", {}).get("aqi_category", "")
    
    # Stage III triggers on "Severe" classification (AQI 401+)
    trigger_activated = aqi_category.lower() == "severe"
    
    if trigger_activated:
        trigger_reason = (
            f"Forecast predicts {aqi_category} AQI category "
            f"(threshold 401+) with {forecast_data['confidence_level']}% confidence"
        )
    else:
        trigger_reason = f"Forecast predicts {aqi_category} AQI category (below Stage III threshold)"
    
    return {
        "trigger_activated": trigger_activated,
        "trigger_reason": trigger_reason,
        "forecast_timestamp": forecast_data["timestamp"],
        "aqi_category": aqi_category,
        "confidence_level": forecast_data["confidence_level"]
    }
```

**Error Handling:**
- Returns trigger_activated=False if forecast data is invalid
- Logs validation errors with details

#### 3. issue_construction_ban_tool

**Purpose:** Simulate issuing stop-work orders to registered construction sites

**Input Parameters:**
- `region` (str, default="Delhi NCR"): Geographic scope of ban
- `security_context` (dict | None): CrewAI security context

**Output:**
```python
{
    "action": "construction_ban",
    "status": "executed",
    "sites_notified": int,
    "region": str,
    "ban_effective_time": str,  # ISO 8601
    "execution_timestamp": str,  # ISO 8601
    "details": str
}
```

**Simulation Logic:**
```python
def issue_construction_ban(region: str = "Delhi NCR") -> dict:
    # Simulate database query for registered construction sites
    sites_count = simulate_construction_site_count(region)
    
    # Simulate notification dispatch
    timestamp = datetime.utcnow().isoformat()
    
    return {
        "action": "construction_ban",
        "status": "executed",
        "sites_notified": sites_count,
        "region": region,
        "ban_effective_time": timestamp,
        "execution_timestamp": timestamp,
        "details": f"Stop-work orders issued to {sites_count} registered construction sites in {region}"
    }
```

**Error Handling:**
- Returns status="failed" if simulation encounters errors
- Includes error details in output dict
- Implements retry logic (3 attempts with exponential backoff)

**Implementation Details:**
- Simulates notification to construction site registry
- Logs action to enforcement audit trail
- Execution time: < 30 seconds

#### 4. restrict_vehicles_tool

**Purpose:** Simulate notifying traffic police to ban BS-III petrol and BS-IV diesel vehicles

**Input Parameters:**
- `vehicle_categories` (list[str], default=["BS-III petrol", "BS-IV diesel"]): Vehicle types to restrict
- `zones` (list[str], default=["All Delhi NCR"]): Geographic zones for restrictions
- `security_context` (dict | None): CrewAI security context

**Output:**
```python
{
    "action": "vehicle_restrictions",
    "status": "executed",
    "vehicle_categories": list[str],
    "zones": list[str],
    "traffic_posts_notified": int,
    "restriction_effective_time": str,  # ISO 8601
    "execution_timestamp": str,  # ISO 8601
    "details": str
}
```

**Simulation Logic:**
```python
def restrict_vehicles(
    vehicle_categories: list[str] = None,
    zones: list[str] = None
) -> dict:
    if vehicle_categories is None:
        vehicle_categories = ["BS-III petrol", "BS-IV diesel"]
    if zones is None:
        zones = ["All Delhi NCR"]
    
    # Simulate traffic police notification
    traffic_posts_count = simulate_traffic_post_count(zones)
    timestamp = datetime.utcnow().isoformat()
    
    return {
        "action": "vehicle_restrictions",
        "status": "executed",
        "vehicle_categories": vehicle_categories,
        "zones": zones,
        "traffic_posts_notified": traffic_posts_count,
        "restriction_effective_time": timestamp,
        "execution_timestamp": timestamp,
        "details": (
            f"Notified {traffic_posts_count} traffic posts to ban "
            f"{', '.join(vehicle_categories)} in {', '.join(zones)}"
        )
    }
```

**Error Handling:**
- Returns status="failed" if simulation encounters errors
- Validates vehicle_categories and zones parameters
- Implements retry logic (3 attempts)

#### 5. dispatch_enforcement_teams_tool

**Purpose:** Simulate dispatching enforcement teams to pollution hotspots

**Input Parameters:**
- `hotspots` (list[str], optional): Specific hotspot locations. If None, uses predefined list
- `teams_per_hotspot` (int, default=2): Number of teams to assign per location
- `security_context` (dict | None): CrewAI security context

**Output:**
```python
{
    "action": "enforcement_team_dispatch",
    "status": "executed",
    "hotspots": list[str],
    "teams_dispatched": int,
    "assignments": list[dict],  # [{hotspot: str, teams: int, team_ids: list[str]}]
    "dispatch_timestamp": str,  # ISO 8601
    "details": str
}
```

**Predefined Hotspots:**
```python
DEFAULT_HOTSPOTS = [
    "Anand Vihar",
    "Punjabi Bagh",
    "RK Puram",
    "Dwarka",
    "Rohini",
    "Najafgarh",
    "Mundka",
    "Wazirpur"
]
```

**Simulation Logic:**
```python
def dispatch_enforcement_teams(
    hotspots: list[str] = None,
    teams_per_hotspot: int = 2
) -> dict:
    if hotspots is None:
        hotspots = DEFAULT_HOTSPOTS
    
    # Simulate team assignment
    assignments = []
    total_teams = 0
    
    for hotspot in hotspots:
        team_ids = [f"TEAM-{hotspot[:3].upper()}-{i+1}" for i in range(teams_per_hotspot)]
        assignments.append({
            "hotspot": hotspot,
            "teams": teams_per_hotspot,
            "team_ids": team_ids
        })
        total_teams += teams_per_hotspot
    
    timestamp = datetime.utcnow().isoformat()
    
    return {
        "action": "enforcement_team_dispatch",
        "status": "executed",
        "hotspots": hotspots,
        "teams_dispatched": total_teams,
        "assignments": assignments,
        "dispatch_timestamp": timestamp,
        "details": f"Dispatched {total_teams} enforcement teams to {len(hotspots)} pollution hotspots"
    }
```

**Error Handling:**
- Returns status="failed" if simulation encounters errors
- Validates hotspots parameter (non-empty list)
- Implements retry logic (3 attempts)

#### 6. notify_public_tool

**Purpose:** Simulate sending alerts via SAMEER app and directing schools to hybrid mode

**Input Parameters:**
- `alert_message` (str): Custom alert message for SAMEER app
- `school_directive` (str, default="Class 5 and below to transition to hybrid mode"): School instruction
- `security_context` (dict | None): CrewAI security context

**Output:**
```python
{
    "action": "public_notification",
    "status": "executed",
    "sameer_app_notifications": int,
    "schools_notified": int,
    "alert_message": str,
    "school_directive": str,
    "notification_timestamp": str,  # ISO 8601
    "details": str
}
```

**Simulation Logic:**
```python
def notify_public(
    alert_message: str = None,
    school_directive: str = "Class 5 and below to transition to hybrid mode"
) -> dict:
    if alert_message is None:
        alert_message = (
            "SEVERE AIR QUALITY ALERT: GRAP Stage III activated. "
            "Avoid outdoor activities. Use N95 masks if going outside."
        )
    
    # Simulate SAMEER app push notifications
    sameer_users = simulate_sameer_app_user_count()
    
    # Simulate school notifications
    schools_count = simulate_school_count_class_5_below()
    
    timestamp = datetime.utcnow().isoformat()
    
    return {
        "action": "public_notification",
        "status": "executed",
        "sameer_app_notifications": sameer_users,
        "schools_notified": schools_count,
        "alert_message": alert_message,
        "school_directive": school_directive,
        "notification_timestamp": timestamp,
        "details": (
            f"Sent alerts to {sameer_users} SAMEER app users and "
            f"notified {schools_count} schools: {school_directive}"
        )
    }
```

**Error Handling:**
- Returns status="failed" if simulation encounters errors
- Validates alert_message is non-empty
- Implements retry logic (3 attempts)

#### 7. generate_enforcement_report_tool

**Purpose:** Generate comprehensive enforcement report JSON

**Input Parameters:**
- `trigger_data` (dict): Trigger validation results
- `enforcement_results` (list[dict]): Results from all four enforcement tools

**Output File Format:**
```json
{
    "enforcement_cycle_id": "ENF-20251113-103045",
    "trigger": {
        "forecast_timestamp": "2025-11-13T08:30:00Z",
        "aqi_category": "Severe",
        "confidence_level": 85.5,
        "trigger_reason": "Forecast predicts Severe AQI category (threshold 401+) with 85.5% confidence"
    },
    "enforcement_actions": [
        {
            "sequence": 1,
            "action": "construction_ban",
            "status": "executed",
            "execution_timestamp": "2025-11-13T10:30:45Z",
            "result": {
                "sites_notified": 1247,
                "region": "Delhi NCR"
            }
        },
        {
            "sequence": 2,
            "action": "vehicle_restrictions",
            "status": "executed",
            "execution_timestamp": "2025-11-13T10:31:12Z",
            "result": {
                "vehicle_categories": ["BS-III petrol", "BS-IV diesel"],
                "traffic_posts_notified": 156
            }
        },
        {
            "sequence": 3,
            "action": "enforcement_team_dispatch",
            "status": "executed",
            "execution_timestamp": "2025-11-13T10:31:38Z",
            "result": {
                "teams_dispatched": 16,
                "hotspots": 8
            }
        },
        {
            "sequence": 4,
            "action": "public_notification",
            "status": "executed",
            "execution_timestamp": "2025-11-13T10:32:05Z",
            "result": {
                "sameer_app_notifications": 450000,
                "schools_notified": 2834
            }
        }
    ],
    "summary": {
        "total_actions": 4,
        "successful_actions": 4,
        "failed_actions": 0,
        "execution_start": "2025-11-13T10:30:45Z",
        "execution_end": "2025-11-13T10:32:05Z",
        "total_duration_seconds": 80
    },
    "compliance_status": "COMPLETE"
}
```

**Output Location:**
- Local file: `grap-enforcement-agent/output/enforcement_{timestamp}.json`
- Optional S3 upload: `s3://{bucket}/enforcement/enforcement_{timestamp}.json`

## Data Models

### ForecastData

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AQIPrediction:
    aqi_category: str
    threshold: int
    estimated_hours_to_threshold: int

@dataclass
class ForecastData:
    prediction: AQIPrediction
    confidence_level: float
    reasoning: str
    timestamp: datetime
    data_sources: dict
```

### TriggerValidation

```python
@dataclass
class TriggerValidation:
    trigger_activated: bool
    trigger_reason: str
    forecast_timestamp: datetime
    aqi_category: str
    confidence_level: float
```

### EnforcementAction

```python
@dataclass
class EnforcementAction:
    sequence: int
    action: str
    status: str  # "executed", "failed", "skipped"
    execution_timestamp: datetime
    result: dict
    error: str | None = None
```

### EnforcementReport

```python
@dataclass
class EnforcementSummary:
    total_actions: int
    successful_actions: int
    failed_actions: int
    execution_start: datetime
    execution_end: datetime
    total_duration_seconds: float

@dataclass
class EnforcementReport:
    enforcement_cycle_id: str
    trigger: TriggerValidation
    enforcement_actions: list[EnforcementAction]
    summary: EnforcementSummary
    compliance_status: str  # "COMPLETE", "PARTIAL", "FAILED"
```

## Error Handling

### Forecast Read Errors

**Scenario:** Forecast JSON file not found or S3 access fails

**Handling:**
- ForecastMonitorAgent logs error and retries (3 attempts with 30s delay)
- If all retries fail, agent terminates without triggering enforcement
- Error logged to enforcement audit trail with reason

### Invalid Forecast Data

**Scenario:** Forecast JSON missing required fields or malformed

**Handling:**
- validate_trigger_tool returns trigger_activated=False
- Agent logs validation error with details
- No enforcement actions executed
- Error report generated for monitoring

### Tool Execution Failures

**Scenario:** Individual enforcement tool raises exception or returns error

**Handling:**
- EnforcementExecutionAgent catches exception and logs error
- Agent continues with remaining enforcement tools (graceful degradation)
- Failed action marked with status="failed" in enforcement report
- Retry logic applied (3 attempts with exponential backoff)
- Final compliance_status set to "PARTIAL" if any tools fail

### Complete Enforcement Failure

**Scenario:** All four enforcement tools fail

**Handling:**
- Agent generates enforcement report with all failures documented
- compliance_status set to "FAILED"
- Alert sent to monitoring system (if configured)
- Manual intervention required

## Testing Strategy

### Unit Tests

**Tool Testing:**
- `test_read_forecast_tool_local_file`: Test reading forecast from local filesystem
- `test_read_forecast_tool_s3`: Mock boto3 S3 client, verify S3 read
- `test_validate_trigger_tool_severe`: Test trigger activation for "Severe" forecast
- `test_validate_trigger_tool_non_severe`: Test no trigger for non-severe forecasts
- `test_issue_construction_ban_tool`: Verify construction ban simulation
- `test_restrict_vehicles_tool`: Verify vehicle restriction simulation
- `test_dispatch_enforcement_teams_tool`: Verify team dispatch simulation
- `test_notify_public_tool`: Verify public notification simulation
- `test_generate_enforcement_report_tool`: Verify report JSON structure

**Agent Testing:**
- `test_forecast_monitor_agent_trigger_detection`: Verify agent detects severe forecasts
- `test_enforcement_execution_agent_sequential_execution`: Verify tools execute in order
- `test_enforcement_execution_agent_error_handling`: Test graceful degradation on tool failures

### Integration Tests

**End-to-End Workflow:**
- `test_enforcement_crew_complete_workflow`: Run full crew with mocked forecast
- `test_enforcement_output_json_format`: Verify enforcement report structure
- `test_enforcement_with_tool_failures`: Test partial execution with simulated failures
- `test_enforcement_no_trigger`: Test agent behavior when forecast is not severe

**External Service Integration:**
- `test_s3_read_real_forecast`: Integration test with actual S3 bucket (optional)
- `test_s3_write_enforcement_report`: Integration test for S3 upload (optional)

### Test Data

**Mock Forecast JSON (Severe):**
```json
{
    "prediction": {
        "aqi_category": "Severe",
        "threshold": 401,
        "estimated_hours_to_threshold": 18
    },
    "confidence_level": 85.5,
    "reasoning": "IF SensorIngestAgent reports 450 new fires...",
    "timestamp": "2025-11-13T08:30:00Z",
    "data_sources": {
        "sensor_data_age_hours": 2.5,
        "meteorological_forecast_retrieved": true
    }
}
```

**Mock Forecast JSON (Non-Severe):**
```json
{
    "prediction": {
        "aqi_category": "Very Poor",
        "threshold": 301,
        "estimated_hours_to_threshold": 24
    },
    "confidence_level": 78.0,
    "reasoning": "Moderate fire activity detected...",
    "timestamp": "2025-11-13T08:30:00Z",
    "data_sources": {}
}
```

## Configuration

### Environment Variables

```bash
# AWS Configuration (for S3 access)
AWS_ACCESS_KEY_ID=<aws_key>
AWS_SECRET_ACCESS_KEY=<aws_secret>
AWS_DEFAULT_REGION=ap-south-1
S3_BUCKET_NAME=<bucket_name>

# LLM Configuration (for CrewAI agents)
GEMINI_API_KEY=<gemini_key>

# Enforcement Configuration
FORECAST_SOURCE_LOCATION=forecast-agent/output  # Local path or S3 URI
ENFORCEMENT_OUTPUT_DIR=grap-enforcement-agent/output
ENFORCEMENT_UPLOAD_TO_S3=true  # Optional: upload reports to S3
ENFORCEMENT_RETRY_ATTEMPTS=3
ENFORCEMENT_RETRY_DELAY_SECONDS=5
```

### Simulation Parameters (Configurable)

```python
# grap-enforcement-agent/src/config/simulation_params.py

# Construction sites
CONSTRUCTION_SITES_DELHI_NCR = 1247

# Traffic posts
TRAFFIC_POSTS_DELHI_NCR = 156

# Pollution hotspots
DEFAULT_HOTSPOTS = [
    "Anand Vihar",
    "Punjabi Bagh",
    "RK Puram",
    "Dwarka",
    "Rohini",
    "Najafgarh",
    "Mundka",
    "Wazirpur"
]

# Public notification
SAMEER_APP_USERS = 450000
SCHOOLS_CLASS_5_BELOW = 2834
```

## Deployment Considerations

### Execution Trigger

- Monitor ForecastAgent output directory for new forecast files
- Run GRAP-EnforcementAgent immediately when new "Severe" forecast detected
- Implement file watcher or scheduled polling (every 5 minutes)
- Ensure only one enforcement cycle runs at a time (use lock file)

### Resource Requirements

- Python 3.11+
- Dependencies: crewai, boto3, python-dotenv
- AWS IAM role with S3 read/write permissions (if using S3)
- Execution time: < 5 minutes per enforcement cycle

### Monitoring

- Log all enforcement cycles with timestamps and results
- Track enforcement action success rates
- Alert on complete enforcement failures
- Monitor forecast-to-enforcement latency
- Generate daily compliance reports

### Integration with ForecastAgent

- Ensure ForecastAgent writes forecasts to configured location
- Validate forecast JSON schema compatibility
- Coordinate execution schedules (ForecastAgent runs every 6 hours)
- Test end-to-end workflow from forecast generation to enforcement execution
