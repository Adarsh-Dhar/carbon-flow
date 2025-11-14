# Technical Steering - Tech Stack & Standards

## Language

- **Python 3.11+**: Primary development language for all agents and tools

## Framework

- **crewai**: Core multi-agent orchestration framework
- **crewai[tools]**: CrewAI tools extension for custom tool integration

## Libraries

### Core Dependencies
- **python-dotenv**: Environment variable management and configuration
- **boto3**: AWS SDK for Python (S3 access, IAM integration)
- **requests**: HTTP client for external API calls
- **pandas**: Data processing and time series analysis
- **openmeteo-requests**: Open-Meteo API client for meteorological data

### Development Dependencies
- **pytest**: Unit and integration testing framework
- **unittest.mock**: Mocking external dependencies in tests

## Code Standards

- Use type hints for all function parameters and return values
- Follow PEP 8 style guidelines
- Prefer dataclasses or Pydantic models for data structures
- Use descriptive variable names
- Document all public functions with docstrings

## Testing Requirements

- Write unit tests using pytest
- Use unittest.mock for mocking external services (S3, APIs)
- Test both success and error scenarios
- Verify error handling and retry logic
- Mock boto3 S3 client and HTTP requests in tests

## Error Handling

- Use specific exception types
- Implement retry logic with exponential backoff for external calls
- Return error dicts with `{"error": "...", "details": "..."}` structure
- Log errors with context before raising or returning

## Environment Configuration

- All API keys and credentials must be in `.env` file
- Never hardcode credentials in source code
- Use `os.getenv()` with sensible defaults where appropriate
