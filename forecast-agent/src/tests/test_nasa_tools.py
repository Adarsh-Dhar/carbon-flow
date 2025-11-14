import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch, Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.nasa_tools import fetch_nasa_fire_data


class TestFetchNASAFireData:
    """Tests for fetch_nasa_fire_data function"""
    
    @patch('tools.nasa_tools.os.getenv')
    def test_missing_api_key(self, mock_getenv):
        """Test that function returns empty DataFrame when API key is missing"""
        mock_getenv.return_value = None
        
        result = fetch_nasa_fire_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('tools.nasa_tools.make_api_request')
    @patch('tools.nasa_tools.os.getenv')
    def test_successful_api_call(self, mock_getenv, mock_make_api_request):
        """Test successful API call returns DataFrame with data"""
        mock_getenv.return_value = 'test_api_key'
        
        csv_data = "latitude,longitude,brightness,confidence\n12.34,56.78,320.5,high\n23.45,67.89,315.2,nominal"
        mock_response = Mock()
        mock_response.text = csv_data
        mock_make_api_request.return_value = mock_response
        
        result = fetch_nasa_fire_data()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'latitude' in result.columns
        assert 'longitude' in result.columns
        mock_make_api_request.assert_called_once()
    
    @patch('tools.nasa_tools.make_api_request')
    @patch('tools.nasa_tools.os.getenv')
    def test_api_error_status(self, mock_getenv, mock_make_api_request):
        """Test that function handles failed helper responses"""
        mock_getenv.return_value = 'test_api_key'
        mock_make_api_request.return_value = None
        
        result = fetch_nasa_fire_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('tools.nasa_tools.make_api_request')
    @patch('tools.nasa_tools.os.getenv')
    def test_helper_failure(self, mock_getenv, mock_make_api_request):
        """Test that function handles helper exceptions by returning empty DataFrame"""
        mock_getenv.return_value = 'test_api_key'
        mock_make_api_request.return_value = None
        
        result = fetch_nasa_fire_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
