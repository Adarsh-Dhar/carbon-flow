"""Integration tests for complete forecast workflow.

This module tests the end-to-end forecast generation process with mocked
external services (S3, Open-Meteo API) to verify the complete workflow
from data retrieval to output generation.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents import TOOL_RESULT_CACHE
from src.tools.s3_reader_tools import read_ingested_data_tool
from src.tools.meteo_tools import get_meteorological_forecast_tool
from src.tools.prediction_tools import synthesize_and_predict
from src.tools.output_tools import generate_output_tool


@pytest.fixture
def mock_s3_data():
    """Mock S3 sensor data response."""
    return [
        {
            "source": "CPCB",
            "aqi": 380.0,
            "station": "Delhi-Anand Vihar",
            "date": "2025-11-13T08:00:00Z",
            "pm25": 250.0,
            "pm10": 400.0
        },
        {
            "source": "NASA",
            "fire_count": 450,
            "region": "Punjab-Haryana",
            "date": "2025-11-13T08:00:00Z"
        },
        {
            "source": "DSS",
            "stubble_burning_percent": 22.0,
            "vehicular_percent": 35.0,
            "industrial_percent": 18.0,
            "date": "2025-11-13T08:00:00Z"
        }
    ]


@pytest.fixture
def mock_meteo_data():
    """Mock Open-Meteo API response."""
    return {
        "hourly": {
            "time": [f"2025-11-13T{h:02d}:00" for h in range(24)],
            "wind_speed_10m": [8.0 + (h * 0.1) for h in range(24)]
        }
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture(autouse=True)
def clear_tool_cache():
    """Clear tool result cache before each test."""
    TOOL_RESULT_CACHE.clear()
    yield
    TOOL_RESULT_CACHE.clear()


class TestForecastIntegration:
    """Integration tests for complete forecast workflow."""
    
    @patch('src.tools.meteo_tools.requests.get')
    @patch('src.tools.s3_reader_tools.boto3.client')
    @patch('src.tools.s3_reader_tools.os.getenv')
    def test_complete_forecast_workflow(
        self,
        mock_getenv,
        mock_boto_client,
        mock_requests_get,
        mock_s3_data,
        mock_meteo_data,
        temp_output_dir
    ):
        """Test complete forecast workflow from data retrieval to output generation."""
        # Setup environment
        mock_getenv.return_value = 'test-bucket'
        
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'data/aqi_data_20251113_080000.json', 'LastModified': datetime.now(timezone.utc)}
            ]
        }
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(mock_s3_data).encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        # Mock Open-Meteo API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_meteo_data
        mock_requests_get.return_value = mock_response
        
        # Step 1: Read ingested data from S3
        sensor_data = read_ingested_data_tool()
        assert "error" not in sensor_data
        assert "cpcb_data" in sensor_data
        assert "nasa_data" in sensor_data
        assert "dss_data" in sensor_data
        assert sensor_data["cpcb_data"]["aqi"] == 380.0
        assert sensor_data["nasa_data"]["fire_count"] == 450
        
        # Step 2: Get meteorological forecast
        meteo_forecast = get_meteorological_forecast_tool(hours=24)
        assert "error" not in meteo_forecast
        assert "hourly_wind_speed" in meteo_forecast
        assert len(meteo_forecast["hourly_wind_speed"]) == 24
        
        # Step 3: Generate prediction
        prediction = synthesize_and_predict(sensor_data, meteo_forecast)
        assert "error" not in prediction
        assert "prediction" in prediction
        assert "confidence_level" in prediction
        assert "reasoning" in prediction
        assert "aqi_category" in prediction
        assert prediction["confidence_level"] > 0
        
        # Step 4: Generate output
        with patch.dict(os.environ, {
            "FORECAST_OUTPUT_DIR": temp_output_dir,
            "FORECAST_UPLOAD_TO_S3": "false"
        }):
            output_result = generate_output_tool(prediction)
        
        assert output_result["success"] is True
        assert "output_file" in output_result
        
        # Verify output file exists and has correct structure
        output_file = Path(output_result["output_file"])
        assert output_file.exists()
        
        with open(output_file, "r", encoding="utf-8") as f:
            output_json = json.load(f)
        
        # Verify required fields in output JSON
        assert "prediction" in output_json
        assert "confidence_level" in output_json
        assert "reasoning" in output_json
        assert "timestamp" in output_json
        assert "data_sources" in output_json
        
        # Verify prediction structure
        assert "aqi_category" in output_json["prediction"]
        assert "threshold" in output_json["prediction"]
        assert "estimated_hours_to_threshold" in output_json["prediction"]
    
    @patch('src.tools.meteo_tools.requests.get')
    @patch('src.tools.s3_reader_tools.boto3.client')
    @patch('src.tools.s3_reader_tools.os.getenv')
    def test_workflow_with_incomplete_data(
        self,
        mock_getenv,
        mock_boto_client,
        mock_requests_get,
        temp_output_dir
    ):
        """Test graceful degradation with incomplete sensor data."""
        # Setup environment
        mock_getenv.return_value = 'test-bucket'
        
        # Mock S3 with incomplete data (missing NASA and DSS)
        incomplete_data = [
            {
                "source": "CPCB",
                "aqi": 250.0,
                "station": "Delhi-Anand Vihar",
                "date": "2025-11-13T08:00:00Z"
            }
        ]
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'data/aqi_data_20251113_080000.json', 'LastModified': datetime.now(timezone.utc)}
            ]
        }
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(incomplete_data).encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        # Mock Open-Meteo API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hourly": {
                "time": [f"2025-11-13T{h:02d}:00" for h in range(24)],
                "wind_speed_10m": [15.0 for _ in range(24)]
            }
        }
        mock_requests_get.return_value = mock_response
        
        # Read incomplete sensor data
        sensor_data = read_ingested_data_tool()
        assert "cpcb_data" in sensor_data
        assert sensor_data["data_quality"]["completeness"] < 1.0
        
        # Get meteorological forecast
        meteo_forecast = get_meteorological_forecast_tool(hours=24)
        assert "error" not in meteo_forecast
        
        # Generate prediction with incomplete data
        prediction = synthesize_and_predict(sensor_data, meteo_forecast)
        
        # Should still generate prediction but with lower confidence
        assert "prediction" in prediction
        assert "confidence_level" in prediction
        assert prediction["confidence_level"] < 60.0  # Lower confidence due to missing data
        
        # Generate output
        with patch.dict(os.environ, {
            "FORECAST_OUTPUT_DIR": temp_output_dir,
            "FORECAST_UPLOAD_TO_S3": "false"
        }):
            output_result = generate_output_tool(prediction)
        
        assert output_result["success"] is True

    
    @patch('src.tools.meteo_tools.requests.get')
    @patch('src.tools.s3_reader_tools.boto3.client')
    @patch('src.tools.s3_reader_tools.os.getenv')
    def test_workflow_with_s3_failure(
        self,
        mock_getenv,
        mock_boto_client,
        mock_requests_get,
        mock_meteo_data,
        temp_output_dir
    ):
        """Test workflow when S3 access fails."""
        # Setup environment
        mock_getenv.return_value = 'test-bucket'
        
        # Mock S3 client error
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}
        mock_s3.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        
        # Mock Open-Meteo API (still works)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_meteo_data
        mock_requests_get.return_value = mock_response
        
        # Read sensor data - should return error
        sensor_data = read_ingested_data_tool()
        assert "error" in sensor_data
        
        # Get meteorological forecast - should succeed
        meteo_forecast = get_meteorological_forecast_tool(hours=24)
        assert "error" not in meteo_forecast
        
        # Try to generate prediction with error in sensor data
        prediction = synthesize_and_predict(sensor_data, meteo_forecast)
        
        # Should return error since sensor data is required
        assert "error" in prediction
    
    @patch('src.tools.meteo_tools.requests.get')
    @patch('src.tools.s3_reader_tools.boto3.client')
    @patch('src.tools.s3_reader_tools.os.getenv')
    def test_workflow_with_api_failure(
        self,
        mock_getenv,
        mock_boto_client,
        mock_requests_get,
        mock_s3_data,
        temp_output_dir
    ):
        """Test workflow when Open-Meteo API fails."""
        # Setup environment
        mock_getenv.return_value = 'test-bucket'
        
        # Mock S3 client (works)
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'data/aqi_data_20251113_080000.json', 'LastModified': datetime.now(timezone.utc)}
            ]
        }
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(mock_s3_data).encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        # Mock Open-Meteo API failure
        import requests
        mock_requests_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        # Read sensor data - should succeed
        sensor_data = read_ingested_data_tool()
        assert "error" not in sensor_data
        
        # Get meteorological forecast - should fail after retries
        meteo_forecast = get_meteorological_forecast_tool(hours=24)
        assert "error" in meteo_forecast
        
        # Generate prediction without meteorological data
        prediction = synthesize_and_predict(sensor_data, meteo_forecast)
        
        # Should still generate prediction but with reduced confidence
        assert "prediction" in prediction
        assert "confidence_level" in prediction
        # Confidence should be reduced due to missing meteo data
        assert prediction["confidence_level"] < 80.0
        
        # Generate output
        with patch.dict(os.environ, {
            "FORECAST_OUTPUT_DIR": temp_output_dir,
            "FORECAST_UPLOAD_TO_S3": "false"
        }):
            output_result = generate_output_tool(prediction)
        
        assert output_result["success"] is True
        
        # Verify output reflects missing meteorological data
        with open(output_result["output_file"], "r", encoding="utf-8") as f:
            output_json = json.load(f)
        
        assert output_json["data_sources"]["meteorological_forecast_retrieved"] is False
    

    @patch('src.tools.meteo_tools.requests.get')
    @patch('src.tools.s3_reader_tools.boto3.client')
    @patch('src.tools.s3_reader_tools.os.getenv')
    def test_output_json_structure_compliance(
        self,
        mock_getenv,
        mock_boto_client,
        mock_requests_get,
        mock_s3_data,
        mock_meteo_data,
        temp_output_dir
    ):
        """Test that output JSON complies with required structure (Requirements 5.1-5.4)."""
        # Setup mocks
        mock_getenv.return_value = 'test-bucket'
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'data/aqi_data_20251113_080000.json', 'LastModified': datetime.now(timezone.utc)}
            ]
        }
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(mock_s3_data).encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_meteo_data
        mock_requests_get.return_value = mock_response
        
        # Execute workflow
        sensor_data = read_ingested_data_tool()
        meteo_forecast = get_meteorological_forecast_tool(hours=24)
        prediction = synthesize_and_predict(sensor_data, meteo_forecast)
        
        with patch.dict(os.environ, {
            "FORECAST_OUTPUT_DIR": temp_output_dir,
            "FORECAST_UPLOAD_TO_S3": "false"
        }):
            output_result = generate_output_tool(prediction)
        
        # Read and validate output JSON structure
        with open(output_result["output_file"], "r", encoding="utf-8") as f:
            output_json = json.load(f)
        
        # Requirement 5.1: JSON object with required fields
        required_top_level_fields = ["prediction", "confidence_level", "reasoning", "timestamp", "data_sources"]
        for field in required_top_level_fields:
            assert field in output_json, f"Missing required field: {field}"
        
        # Requirement 5.2: prediction field structure
        prediction_obj = output_json["prediction"]
        assert "aqi_category" in prediction_obj
        assert "threshold" in prediction_obj
        assert "estimated_hours_to_threshold" in prediction_obj
        assert isinstance(prediction_obj["estimated_hours_to_threshold"], int)
        
        # Requirement 5.3: confidence_level is numerical 0-100
        confidence = output_json["confidence_level"]
        assert isinstance(confidence, (int, float))
        assert 0 <= confidence <= 100
        
        # Requirement 5.4: reasoning is complete natural language explanation
        reasoning = output_json["reasoning"]
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
        assert any(keyword in reasoning for keyword in ["fire", "wind", "AQI", "predict"])
        
        # Verify timestamp format
        timestamp = output_json["timestamp"]
        assert isinstance(timestamp, str)
        # Should be ISO 8601 format
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Verify data_sources metadata
        data_sources = output_json["data_sources"]
        assert isinstance(data_sources, dict)
        assert "meteorological_forecast_retrieved" in data_sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
