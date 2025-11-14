"""Unit tests for prediction tools."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.prediction_tools import (
    synthesize_and_predict,
    SEVERE_AQI_THRESHOLD,
    HIGH_FIRE_COUNT,
    LOW_WIND_SPEED_KMH,
    HIGH_STUBBLE_PERCENT
)


def test_synthesize_and_predict_severe_conditions():
    """Test prediction logic for severe AQI conditions."""
    # Mock sensor data with high fire count and stubble burning
    sensor_data = {
        "cpcb_data": {
            "aqi": 380.0,
            "timestamp": "2025-11-13T08:00:00Z",
            "station": "Delhi-Anand Vihar",
            "pm25": 250.0,
            "pm10": 400.0
        },
        "nasa_data": {
            "fire_count": 450,
            "region": "Punjab-Haryana",
            "timestamp": "2025-11-13T08:00:00Z",
            "confidence_high": 350
        },
        "dss_data": {
            "stubble_burning_percent": 22.0,
            "vehicular_percent": 35.0,
            "industrial_percent": 18.0,
            "dust_percent": 10.0,
            "timestamp": "2025-11-13T08:00:00Z"
        },
        "data_quality": {
            "completeness": 1.0,
            "age_hours": 2.5
        }
    }
    
    # Mock meteorological data with low wind speed
    meteo_data = {
        "hourly_wind_speed": [
            {"timestamp": f"2025-11-13T{h:02d}:00", "wind_speed_kmh": 8.0}
            for h in range(24)
        ],
        "location": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "city": "Delhi"
        }
    }
    
    # Call synthesize_and_predict
    result = synthesize_and_predict(sensor_data, meteo_data)
    
    # Verify result structure
    assert "prediction" in result
    assert "estimated_hours" in result
    assert "confidence_level" in result
    assert "reasoning" in result
    assert "aqi_category" in result
    assert "threshold" in result
    
    # Verify prediction logic
    assert result["aqi_category"] == "Severe"
    assert result["threshold"] == SEVERE_AQI_THRESHOLD
    assert result["estimated_hours"] > 0
    assert result["confidence_level"] > 0
    
    # Verify reasoning contains key information
    assert "450" in result["reasoning"]  # fire count
    assert "8.0" in result["reasoning"]  # wind speed
    assert "22" in result["reasoning"]  # stubble burning percent
    
    print(f"Test passed: {result['prediction']}")
    print(f"Confidence: {result['confidence_level']}%")
    print(f"Reasoning: {result['reasoning']}")


def test_synthesize_and_predict_missing_sensor_data():
    """Test prediction with missing sensor data."""
    sensor_data = {
        "error": "S3 access failed",
        "details": "Bucket not found"
    }
    
    meteo_data = {
        "hourly_wind_speed": [
            {"timestamp": f"2025-11-13T{h:02d}:00", "wind_speed_kmh": 12.0}
            for h in range(24)
        ]
    }
    
    result = synthesize_and_predict(sensor_data, meteo_data)
    
    # Should return error
    assert "error" in result
    print(f"Test passed: Error handling works - {result['error']}")


def test_synthesize_and_predict_incomplete_data():
    """Test prediction with incomplete but valid data."""
    sensor_data = {
        "cpcb_data": {
            "aqi": 250.0,
            "timestamp": "2025-11-13T08:00:00Z",
            "station": "Delhi-Anand Vihar"
        },
        "nasa_data": None,
        "dss_data": None,
        "data_quality": {
            "completeness": 0.33,
            "age_hours": 1.0
        }
    }
    
    meteo_data = {
        "hourly_wind_speed": [
            {"timestamp": f"2025-11-13T{h:02d}:00", "wind_speed_kmh": 15.0}
            for h in range(24)
        ]
    }
    
    result = synthesize_and_predict(sensor_data, meteo_data)
    
    # Should still generate prediction but with lower confidence
    assert "prediction" in result
    assert result["confidence_level"] < 50.0  # Low confidence due to missing data
    print(f"Test passed: Incomplete data handled - Confidence: {result['confidence_level']}%")


if __name__ == "__main__":
    test_synthesize_and_predict_severe_conditions()
    test_synthesize_and_predict_missing_sensor_data()
    test_synthesize_and_predict_incomplete_data()
    print("\nAll tests passed!")
