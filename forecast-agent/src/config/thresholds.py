"""
Prediction threshold constants for ForecastAgent.

These thresholds define the conditions under which the ForecastAgent predicts
severe air quality events in Delhi.
"""

# AQI Thresholds
SEVERE_AQI_THRESHOLD = 401  # AQI level indicating hazardous air quality
VERY_POOR_AQI_THRESHOLD = 301  # AQI level indicating very poor air quality
POOR_AQI_THRESHOLD = 201  # AQI level indicating poor air quality

# Fire Event Thresholds
HIGH_FIRE_COUNT = 400  # Number of fires indicating significant biomass burning
MODERATE_FIRE_COUNT = 200  # Number of fires indicating moderate biomass burning

# Meteorological Thresholds
LOW_WIND_SPEED_KMH = 10  # Wind speed below which pollutants accumulate (km/h)
MODERATE_WIND_SPEED_KMH = 15  # Wind speed indicating moderate dispersion (km/h)

# Pollution Source Thresholds
HIGH_STUBBLE_PERCENT = 20  # Stubble burning contribution indicating high impact (%)
MODERATE_STUBBLE_PERCENT = 10  # Stubble burning contribution indicating moderate impact (%)

# Data Quality Thresholds
MAX_DATA_AGE_HOURS = 6  # Maximum acceptable age of sensor data (hours)
MIN_CONFIDENCE_THRESHOLD = 50  # Minimum confidence level for actionable predictions (%)

# Time Estimation Constants
BASE_HOURS_TO_THRESHOLD = 24  # Base timeframe for predictions (hours)
RAPID_DETERIORATION_HOURS = 12  # Timeframe for rapid AQI increase (hours)
