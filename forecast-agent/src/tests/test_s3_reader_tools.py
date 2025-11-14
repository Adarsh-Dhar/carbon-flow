"""Tests for S3 reader tools."""

import json
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.s3_reader_tools import read_ingested_data_tool


class TestReadIngestedDataTool:
    """Tests for read_ingested_data_tool function"""
    
    @patch('tools.s3_reader_tools.os.getenv')
    def test_missing_bucket_name(self, mock_getenv):
        """Test that function returns error when bucket name is not provided"""
        mock_getenv.return_value = None
        
        result = read_ingested_data_tool()
        
        assert "error" in result
        assert "S3 bucket name not provided" in result["error"]
    
    @patch('tools.s3_reader_tools.boto3.client')
    @patch('tools.s3_reader_tools.os.getenv')
    def test_successful_data_retrieval(self, mock_getenv, mock_boto_client):
        """Test successful retrieval and parsing of S3 data"""
        mock_getenv.return_value = 'test-bucket'
        
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock list_objects_v2 response
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'data/aqi_data_20251113_100000.json', 'LastModified': datetime.now(timezone.utc)}
            ]
        }
        
        # Mock get_object response with sample data
        sample_data = [
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
        
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(sample_data).encode('utf-8')
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        result = read_ingested_data_tool()
        
        assert "error" not in result
        assert "cpcb_data" in result
        assert "nasa_data" in result
        assert "dss_data" in result
        assert "data_quality" in result
        
        # Verify CPCB data
        assert result["cpcb_data"]["aqi"] == 380.0
        assert result["cpcb_data"]["station"] == "Delhi-Anand Vihar"
        
        # Verify NASA data
        assert result["nasa_data"]["fire_count"] == 450
        
        # Verify DSS data
        assert result["dss_data"]["stubble_burning_percent"] == 22.0
        
        # Verify data quality
        assert result["data_quality"]["completeness"] == 1.0  # All 3 sources present
    
    @patch('tools.s3_reader_tools.boto3.client')
    @patch('tools.s3_reader_tools.os.getenv')
    def test_no_files_in_bucket(self, mock_getenv, mock_boto_client):
        """Test handling when no data files exist in S3"""
        mock_getenv.return_value = 'test-bucket'
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock empty list response
        mock_s3.list_objects_v2.return_value = {'Contents': []}
        
        result = read_ingested_data_tool()
        
        assert "error" in result
        assert "No data files found" in result["error"]
    
    @patch('tools.s3_reader_tools.boto3.client')
    @patch('tools.s3_reader_tools.os.getenv')
    def test_s3_client_error(self, mock_getenv, mock_boto_client):
        """Test handling of S3 ClientError"""
        mock_getenv.return_value = 'test-bucket'
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock ClientError
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}}
        mock_s3.list_objects_v2.side_effect = ClientError(error_response, 'ListObjectsV2')
        
        result = read_ingested_data_tool()
        
        assert "error" in result
        assert "Failed to list S3 objects" in result["error"]
