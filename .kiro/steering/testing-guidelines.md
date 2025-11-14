---
inclusion: fileMatch
fileMatchPattern: '**/test_*.py'
---

# Testing Guidelines

This steering file is automatically included when working with test files.

## Test Structure

### File Organization

- Test files should mirror source file structure
- Name test files with `test_` prefix: `test_s3_reader_tools.py`
- Group related tests in classes when appropriate
- Use descriptive test function names: `test_fetch_data_success`, `test_fetch_data_missing_bucket`

### Test Function Naming

Use the pattern: `test_<function_name>_<scenario>`

```python
def test_read_ingested_data_success():
    """Test successful data retrieval from S3."""
    pass

def test_read_ingested_data_missing_bucket():
    """Test error handling when bucket doesn't exist."""
    pass

def test_read_ingested_data_invalid_json():
    """Test error handling when JSON parsing fails."""
    pass
```

## Mocking External Services

### Mocking boto3 S3 Client

```python
from unittest.mock import Mock, patch
import pytest

@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch('boto3.client') as mock_client:
        s3_mock = Mock()
        mock_client.return_value = s3_mock
        yield s3_mock

def test_read_from_s3(mock_s3_client):
    """Test reading data from S3."""
    # Setup mock response
    mock_s3_client.get_object.return_value = {
        'Body': Mock(read=lambda: b'{"data": "test"}')
    }
    
    # Test function
    result = read_ingested_data_tool(bucket_name="test-bucket")
    
    # Assertions
    assert result["data"] == "test"
    mock_s3_client.get_object.assert_called_once()
```

### Mocking HTTP Requests

```python
import responses
import requests

@responses.activate
def test_fetch_meteo_forecast_success():
    """Test successful API call to Open-Meteo."""
    # Mock API response
    responses.add(
        responses.GET,
        'https://api.open-meteo.com/v1/forecast',
        json={
            'hourly': {
                'time': ['2025-11-13T09:00', '2025-11-13T10:00'],
                'wind_speed_10m': [8.5, 7.2]
            }
        },
        status=200
    )
    
    # Test function
    result = get_meteorological_forecast_tool()
    
    # Assertions
    assert len(result['hourly_wind_speed']) == 2
    assert result['hourly_wind_speed'][0]['wind_speed_kmh'] == 8.5
```

### Mocking with pytest-mock

```python
def test_with_mocker(mocker):
    """Test using pytest-mock."""
    mock_func = mocker.patch('src.tools.s3_reader_tools.boto3.client')
    mock_func.return_value.get_object.return_value = {'Body': Mock()}
    
    result = read_ingested_data_tool()
    assert mock_func.called
```

## Test Data Fixtures

### Creating Realistic Test Data

```python
@pytest.fixture
def sample_sensor_data():
    """Sample sensor data matching production format."""
    return {
        "data": [
            {
                "source": "CPCB",
                "aqi": 380,
                "timestamp": "2025-11-13T08:00:00Z",
                "station": "Delhi-Anand Vihar"
            },
            {
                "source": "NASA",
                "fire_count": 450,
                "region": "Punjab-Haryana",
                "timestamp": "2025-11-13T08:00:00Z"
            },
            {
                "source": "DSS",
                "stubble_burning_percent": 22,
                "vehicular_percent": 35,
                "industrial_percent": 18,
                "timestamp": "2025-11-13T08:00:00Z"
            }
        ]
    }

@pytest.fixture
def sample_meteo_response():
    """Sample Open-Meteo API response."""
    return {
        'hourly': {
            'time': [
                '2025-11-13T09:00', '2025-11-13T10:00', '2025-11-13T11:00',
                '2025-11-13T12:00', '2025-11-13T13:00'
            ],
            'wind_speed_10m': [8.5, 7.2, 6.8, 9.1, 10.3]
        }
    }
```

### Using Fixtures in Tests

```python
def test_prediction_logic(sample_sensor_data, sample_meteo_response):
    """Test prediction logic with sample data."""
    result = synthesize_and_predict(sample_sensor_data, sample_meteo_response)
    
    assert result['prediction'] is not None
    assert 0 <= result['confidence_level'] <= 100
    assert 'reasoning' in result
```

## Testing Error Scenarios

### Testing Exception Handling

```python
def test_s3_access_error(mock_s3_client):
    """Test handling of S3 access errors."""
    mock_s3_client.get_object.side_effect = Exception("Access denied")
    
    result = read_ingested_data_tool(bucket_name="test-bucket")
    
    assert 'error' in result
    assert 'Access denied' in result['details']
```

### Testing Retry Logic

```python
@responses.activate
def test_api_retry_on_failure():
    """Test retry logic when API fails."""
    # First two calls fail, third succeeds
    responses.add(responses.GET, 'https://api.example.com', status=500)
    responses.add(responses.GET, 'https://api.example.com', status=500)
    responses.add(responses.GET, 'https://api.example.com', json={'data': 'success'}, status=200)
    
    result = fetch_with_retry('https://api.example.com')
    
    assert result['data'] == 'success'
    assert len(responses.calls) == 3
```

### Testing Missing Data

```python
def test_incomplete_sensor_data():
    """Test handling of incomplete sensor data."""
    incomplete_data = {
        "data": [
            {"source": "CPCB", "aqi": 380}
            # Missing NASA and DSS data
        ]
    }
    
    result = synthesize_and_predict(incomplete_data, {})
    
    assert result['confidence_level'] < 100
    assert 'incomplete' in result['reasoning'].lower()
```

## Integration Testing

### Testing Complete Workflows

```python
@pytest.fixture
def mock_all_external_services(mocker):
    """Mock all external services for integration tests."""
    # Mock S3
    mock_s3 = mocker.patch('boto3.client')
    mock_s3.return_value.get_object.return_value = {
        'Body': Mock(read=lambda: b'{"data": [...]}')
    }
    
    # Mock HTTP requests
    mocker.patch('requests.get', return_value=Mock(
        status_code=200,
        json=lambda: {'hourly': {...}}
    ))
    
    return {'s3': mock_s3}

def test_forecast_workflow_end_to_end(mock_all_external_services):
    """Test complete forecast workflow."""
    result = run_forecast_cycle()
    
    assert 'prediction' in result
    assert 'confidence_level' in result
    assert 'reasoning' in result
```

### Testing Output Format

```python
import json

def test_output_json_structure(tmp_path):
    """Test that output JSON has correct structure."""
    output_file = tmp_path / "forecast.json"
    
    # Generate output
    generate_output_tool(
        prediction_data={...},
        output_path=str(output_file)
    )
    
    # Verify file exists and has correct structure
    assert output_file.exists()
    
    with open(output_file) as f:
        data = json.load(f)
    
    assert 'prediction' in data
    assert 'confidence_level' in data
    assert 'reasoning' in data
    assert 'timestamp' in data
    assert isinstance(data['confidence_level'], (int, float))
    assert 0 <= data['confidence_level'] <= 100
```

## Assertion Best Practices

### Use Specific Assertions

```python
# BAD
assert result

# GOOD
assert result is not None
assert isinstance(result, dict)
assert 'data' in result
```

### Test Multiple Conditions

```python
def test_prediction_output():
    """Test prediction output format."""
    result = generate_prediction()
    
    # Test structure
    assert 'prediction' in result
    assert 'confidence_level' in result
    assert 'reasoning' in result
    
    # Test types
    assert isinstance(result['confidence_level'], float)
    assert isinstance(result['reasoning'], str)
    
    # Test ranges
    assert 0 <= result['confidence_level'] <= 100
    
    # Test content
    assert len(result['reasoning']) > 0
    assert 'AQI' in result['reasoning']
```

### Use pytest.approx for Floats

```python
def test_confidence_calculation():
    """Test confidence level calculation."""
    result = calculate_confidence(completeness=0.9, age_hours=3)
    
    # Use approx for floating point comparison
    assert result == pytest.approx(90.0, rel=1e-2)
```

## Test Coverage Goals

- Aim for 80%+ code coverage
- Focus on critical paths and error handling
- Don't test external libraries (boto3, requests)
- Test business logic thoroughly
- Test edge cases and boundary conditions

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest src/tests/test_s3_reader_tools.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest src/tests/test_s3_reader_tools.py::test_read_ingested_data_success
```

## Test Documentation

Always include docstrings explaining what each test validates:

```python
def test_severe_aqi_prediction():
    """
    Test that severe AQI prediction is triggered when:
    - Fire count exceeds 400
    - Wind speed is below 10 km/h
    - Stubble burning contribution is above 20%
    """
    # Test implementation
```
