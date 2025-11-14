import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch, Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.dss_tools import fetch_dss_data


class TestFetchDSSData:
    """Tests for fetch_dss_data function"""
    
    @patch('tools.dss_tools.make_api_request')
    def test_successful_scrape(self, mock_api_request):
        """Test successful web scraping returns DataFrame with data"""
        # Mock HTML response
        html_content = """
        <html>
            <body>
                <div class="data-item" title="Item 1">Data Point 1</div>
                <div class="data-item" title="Item 2">Data Point 2</div>
            </body>
        </html>
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_api_request.return_value = mock_response
        
        result = fetch_dss_data()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'text' in result.columns
        assert 'title' in result.columns
        mock_api_request.assert_called_once()
    
    @patch('tools.dss_tools.make_api_request')
    def test_http_error_status(self, mock_api_request):
        """Test that function handles non-200 status codes"""
        mock_api_request.return_value = None
        
        result = fetch_dss_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('tools.dss_tools.make_api_request')
    def test_request_exception(self, mock_api_request):
        """Test that function handles request exceptions"""
        mock_api_request.return_value = None
        
        result = fetch_dss_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('tools.dss_tools.make_api_request')
    def test_empty_html_response(self, mock_api_request):
        """Test handling of HTML with no matching elements"""
        html_content = "<html><body><p>No data items here</p></body></html>"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_api_request.return_value = mock_response
        
        result = fetch_dss_data()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
