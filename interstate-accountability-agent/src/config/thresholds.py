"""
Thresholds and constants for InterState-AccountabilityAgent.
All configurable parameters for surge detection, correlation, and confidence scoring.
"""

# Pollution surge detection
SURGE_AQI_THRESHOLD = 300  # AQI level that triggers report generation

# Fire correlation parameters
FIRE_CORRELATION_RADIUS_KM = 200  # Maximum distance for fire-to-station correlation
HIGH_CONTRIBUTION_FIRE_COUNT = 100  # Fire count threshold for high-contribution classification

# Confidence scoring penalties
MIN_CONFIDENCE_SCORE = 30.0  # Minimum confidence score for report generation
NASA_DATA_MISSING_PENALTY = 40.0  # Penalty when NASA FIRMS data is unavailable
DSS_DATA_MISSING_PENALTY = 20.0  # Penalty when DSS data is unavailable
LOW_FIRE_COUNT_PENALTY = 10.0  # Penalty when fire count < 50
HIGH_DISTANCE_PENALTY = 10.0  # Penalty when average distance > 150km

# Timing parameters
CORRELATION_WINDOW_HOURS = 48  # Time window for correlating fires with pollution surge
MAX_DATA_AGE_HOURS = 24  # Maximum acceptable age for sensor data
EXECUTION_TIMEOUT_MINUTES = 10  # Maximum execution time for agent

# Retry configuration
S3_READ_RETRIES = 3  # Number of retry attempts for S3 read operations
CAQM_SUBMISSION_RETRIES = 2  # Number of retry attempts for CAQM submission
RETRY_BACKOFF_BASE_SECONDS = 1  # Base delay for exponential backoff (1s, 2s, 4s)

# Fire count thresholds for recommendations
LOW_FIRE_COUNT_THRESHOLD = 50  # Below this is considered low fire activity
MEDIUM_FIRE_COUNT_THRESHOLD = 100  # Between low and high
HIGH_FIRE_COUNT_THRESHOLD = 200  # Above this is considered severe fire activity

# Distance thresholds for correlation strength
CLOSE_DISTANCE_KM = 100  # Fires within this distance have strong correlation
MEDIUM_DISTANCE_KM = 150  # Fires within this distance have moderate correlation
FAR_DISTANCE_KM = 200  # Maximum distance for any correlation
