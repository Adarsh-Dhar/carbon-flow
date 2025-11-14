"""Tests for meteorological forecast tools."""

import json
import sys
import os
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.meteo_tools import get_meteorological_forecast_tool


class TestGetMeteorologicalForecastTool:
    """Tests for get_meteorological_forecast_tool function"""
    
    @patch('tools.meteo_tools.requests.get')
    def test_successful_forecast_retrieval(self, mock_get):
        """Test successful retrieval and parsing of meteorological forecast"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hourly": {
                "time": [
                    "2025-11-13T09:00",
                    "2025-11-13T10:00",
                    "2025-11-13T11:00"
                ],
                "wind_speed_10m": [8.5, 7.2, 6.8]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_meteorological_forecast_tool(hours=3)
        
        assert "error" not in result
        assert "hourly_wind_speed" in result
        assert "location" in result
        
        # Verify hourly wind speed data
        assert len(result["hourly_wind_speed"]) == 3
        assert result["hourly_wind_speed"][0]["timestamp"] == "2025-11-13T09:00"
        assert result["hourly_wind_speed"][0]["wind_speed_kmh"] == 8.5
        
        # Verify location data
        assert result["location"]["latitude"] == 28.6139
        assert result["location"]["longitude"] == 77.2090
        assert result["location"]["city"] == "Delhi"
    
    @patch('tools.meteo_tools.requests.get')
    def test_api_http_error(self, mock_get):
        """Test handling of HTTP error from API"""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"reason": "Server error"}
        mock_get.return_value = mock_response
        
        result = get_meteorological_forecast_tool()
        
        assert "error" in result
        assert "Open-Meteo API request failed" in result["error"]
        assert "HTTP 500" in result["details"]
    
    @patch('tools.meteo_tools.requests.get')
    @patch('tools.meteo_tools.time.sleep')
    def test_retry_logic_with_timeout(self, mock_sleep, mock_get):
        """Test retry logic with exponential backoff on timeout"""
        # Mock timeout exception
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = get_meteorological_forecast_tool()
        
        assert "error" in result
        assert "timed out" in result["error"]
        
        # Verify that 3 attempts were made
        assert mock_get.call_count == 3
        
        # Verify exponential backoff (sleep called 2 times: after 1st and 2nd attempt)
        assert mock_sleep.call_count == 2
    
    @patch('tools.meteo_tools.requests.get')
    @patch('tools.meteo_tools.time.sleep')
    def test_retry_success_on_second_attempt(self, mock_sleep, mock_get):
        """Test successful retrieval after retry"""
        # First attempt fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.text = "Service Unavailable"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "hourly": {
                "time": ["2025-11-13T09:00"],
                "wind_speed_10m": [10.0]
            }
        }
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]
        
        result = get_meteorological_forecast_tool(hours=1)
        
        assert "error" not in result
        assert len(result["hourly_wind_speed"]) == 1
        assert result["hourly_wind_speed"][0]["wind_speed_kmh"] == 10.0
        
        # Verify retry was attempted
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1
    
    @patch('tools.meteo_tools.requests.get')
    def test_request_exception(self, mock_get):
        """Test handling of general request exception"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = get_meteorological_forecast_tool()
        
        assert "error" in result
        assert "Open-Meteo API request failed" in result["error"]
    
    @patch('tools.meteo_tools.requests.get')
    def test_custom_coordinates(self, mock_get):
        """Test with custom latitude and longitude"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2025-11-13T09:00"],
                "wind_speed_10m": [12.0]
            }
        }
        mock_get.return_value = mock_response
        
        custom_lat = 30.0
        custom_lon = 75.0
        result = get_meteorological_forecast_tool(
            latitude=custom_lat,
            longitude=custom_lon,
            hours=1
        )
        
        assert "error" not in result
        assert result["location"]["latitude"] == custom_lat
        assert result["location"]["longitude"] == custom_lon
        
        # Verify API was called with correct parameters
        call_args = mock_get.call_args
        assert call_args[1]["params"]["latitude"] == custom_lat
        assert call_args[1]["params"]["longitude"] == custom_lon
    
    @patch('tools.meteo_tools.requests.get')
    def test_hours_limit(self, mock_get):
        """Test that hours parameter limits the returned data"""
        # Mock API response with more hours than requested
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hourly": {
                "time": [f"2025-11-13T{i:02d}:00" for i in range(24)],
                "wind_speed_10m": [float(i) for i in range(24)]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_meteorological_forecast_tool(hours=5)
        
        assert "error" not in result
        # Should only return 5 hours even though API returned 24
        assert len(result["hourly_wind_speed"]) == 5

