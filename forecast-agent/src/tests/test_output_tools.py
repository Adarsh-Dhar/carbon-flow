"""Unit tests for output generation tools."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.output_tools import generate_output_tool


@pytest.fixture
def sample_prediction_data():
    """Sample prediction data for testing."""
    return {
        "prediction": "AQI will cross Severe threshold (401)",
        "estimated_hours": 18,
        "confidence_level": 85.5,
        "reasoning": "IF SensorIngestAgent reports 450 new fires, AND meteorological data shows low wind speed (8 km/h), THEN I predict AQI will cross Severe threshold (401) in 18 hours.",
        "aqi_category": "Severe",
        "threshold": 401,
        "current_aqi": 380.0,
        "fire_count": 450,
        "avg_wind_speed_24h": 8.0,
        "stubble_burning_percent": 22.0
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


def test_generate_output_tool_success(sample_prediction_data, temp_output_dir):
    """Test successful output generation to local file."""
    # Set environment variable for output directory
    with patch.dict(os.environ, {"FORECAST_OUTPUT_DIR": temp_output_dir, "FORECAST_UPLOAD_TO_S3": "false"}):
        result = generate_output_tool(sample_prediction_data)
    
    # Verify result structure
    assert result["success"] is True
    assert "output_file" in result
    assert result["s3_uploaded"] is False
    assert result["s3_key"] is None
    assert "timestamp" in result
    
    # Verify file was created
    output_file = Path(result["output_file"])
    assert output_file.exists()
    
    # Verify JSON content
    with open(output_file, "r", encoding="utf-8") as f:
        output_json = json.load(f)
    
    assert "prediction" in output_json
    assert output_json["prediction"]["aqi_category"] == "Severe"
    assert output_json["prediction"]["threshold"] == 401
    assert output_json["prediction"]["estimated_hours_to_threshold"] == 18
    assert output_json["confidence_level"] == 85.5
    assert "reasoning" in output_json
    assert "timestamp" in output_json
    assert "data_sources" in output_json


def test_generate_output_tool_with_error_prediction():
    """Test output generation with error in prediction data."""
    error_prediction = {
        "error": "Cannot generate prediction",
        "details": "Missing sensor data"
    }
    
    result = generate_output_tool(error_prediction)
    
    # Verify error is returned
    assert "error" in result
    assert "Cannot generate output with invalid prediction data" in result["error"]


def test_generate_output_tool_json_format(sample_prediction_data, temp_output_dir):
    """Test that output JSON has correct format."""
    with patch.dict(os.environ, {"FORECAST_OUTPUT_DIR": temp_output_dir, "FORECAST_UPLOAD_TO_S3": "false"}):
        result = generate_output_tool(sample_prediction_data)
    
    # Read generated JSON
    with open(result["output_file"], "r", encoding="utf-8") as f:
        output_json = json.load(f)
    
    # Verify required fields
    assert "prediction" in output_json
    assert "confidence_level" in output_json
    assert "reasoning" in output_json
    assert "timestamp" in output_json
    assert "data_sources" in output_json
    
    # Verify prediction structure
    prediction = output_json["prediction"]
    assert "aqi_category" in prediction
    assert "threshold" in prediction
    assert "estimated_hours_to_threshold" in prediction
    
    # Verify data sources structure
    data_sources = output_json["data_sources"]
    assert "meteorological_forecast_retrieved" in data_sources
    assert data_sources["meteorological_forecast_retrieved"] is True


@patch("src.tools.output_tools.boto3.client")
def test_generate_output_tool_with_s3_upload(mock_boto_client, sample_prediction_data, temp_output_dir):
    """Test output generation with S3 upload enabled."""
    # Mock S3 client
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    
    # Set environment variables
    with patch.dict(os.environ, {
        "FORECAST_OUTPUT_DIR": temp_output_dir,
        "FORECAST_UPLOAD_TO_S3": "true",
        "S3_BUCKET_NAME": "test-bucket"
    }):
        result = generate_output_tool(sample_prediction_data)
    
    # Verify result
    assert result["success"] is True
    assert result["s3_uploaded"] is True
    assert result["s3_key"] is not None
    assert result["s3_key"].startswith("forecasts/forecast_")
    
    # Verify S3 put_object was called
    mock_s3.put_object.assert_called_once()
    call_args = mock_s3.put_object.call_args
    assert call_args[1]["Bucket"] == "test-bucket"
    assert call_args[1]["ContentType"] == "application/json"


def test_generate_output_tool_creates_directory(sample_prediction_data, tmp_path):
    """Test that output directory is created if it doesn't exist."""
    nonexistent_dir = str(tmp_path / "nonexistent" / "output")
    
    with patch.dict(os.environ, {"FORECAST_OUTPUT_DIR": nonexistent_dir, "FORECAST_UPLOAD_TO_S3": "false"}):
        result = generate_output_tool(sample_prediction_data)
    
    # Verify directory was created
    assert Path(nonexistent_dir).exists()
    assert result["success"] is True


def test_generate_output_tool_minimal_data(temp_output_dir):
    """Test output generation with minimal prediction data."""
    minimal_data = {
        "prediction": "AQI expected to remain stable",
        "estimated_hours": 24,
        "confidence_level": 50.0,
        "reasoning": "Based on available data, I predict AQI will remain stable.",
        "aqi_category": "Stable",
        "threshold": 0,
        "current_aqi": None,
        "fire_count": None,
        "avg_wind_speed_24h": None,
        "stubble_burning_percent": None
    }
    
    with patch.dict(os.environ, {"FORECAST_OUTPUT_DIR": temp_output_dir, "FORECAST_UPLOAD_TO_S3": "false"}):
        result = generate_output_tool(minimal_data)
    
    # Verify success
    assert result["success"] is True
    
    # Verify JSON content
    with open(result["output_file"], "r", encoding="utf-8") as f:
        output_json = json.load(f)
    
    # Verify data sources reflects missing data
    data_sources = output_json["data_sources"]
    assert data_sources["meteorological_forecast_retrieved"] is False
