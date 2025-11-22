"""
API Configuration and Fallback Logic

This module handles API configuration and determines whether to use real APIs or mock implementations.
"""

import os
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
project_root = Path(__file__).parent.parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


def should_use_mock_apis() -> bool:
    """
    Determine if mock APIs should be used.
    
    Returns:
        True if mock APIs should be used, False if real APIs should be used
    """
    # Check for explicit flag
    use_mock = os.getenv("USE_MOCK_APIS", "").lower()
    if use_mock in ("true", "1", "yes"):
        return True
    
    # Check if real API credentials are available
    # If any required credential is missing, use mock
    construction_url = os.getenv("CONSTRUCTION_API_URL")
    construction_key = os.getenv("CONSTRUCTION_API_KEY")
    
    traffic_url = os.getenv("TRAFFIC_API_URL")
    traffic_key = os.getenv("TRAFFIC_API_KEY")
    
    education_url = os.getenv("EDUCATION_API_URL")
    education_key = os.getenv("EDUCATION_API_KEY")
    
    enforcement_url = os.getenv("ENFORCEMENT_API_URL")
    enforcement_key = os.getenv("ENFORCEMENT_API_KEY")
    
    # If all APIs have credentials, use real APIs
    # Otherwise, use mock
    has_all_credentials = all([
        construction_url and construction_key,
        traffic_url and traffic_key,
        education_url and education_key,
        enforcement_url and enforcement_key,
    ])
    
    return not has_all_credentials


def get_api_config(api_name: str) -> dict[str, Any]:
    """
    Get API configuration for a specific API.
    
    Args:
        api_name: Name of the API (construction, traffic, education, enforcement)
        
    Returns:
        Dict with API configuration (url, api_key, use_mock)
    """
    api_name_lower = api_name.lower()
    
    config_map = {
        "construction": {
            "url": os.getenv("CONSTRUCTION_API_URL"),
            "api_key": os.getenv("CONSTRUCTION_API_KEY"),
        },
        "traffic": {
            "url": os.getenv("TRAFFIC_API_URL"),
            "api_key": os.getenv("TRAFFIC_API_KEY"),
        },
        "education": {
            "url": os.getenv("EDUCATION_API_URL"),
            "api_key": os.getenv("EDUCATION_API_KEY"),
        },
        "enforcement": {
            "url": os.getenv("ENFORCEMENT_API_URL"),
            "api_key": os.getenv("ENFORCEMENT_API_KEY"),
        },
    }
    
    config = config_map.get(api_name_lower, {"url": None, "api_key": None})
    
    # Determine if mock should be used for this specific API
    use_mock = should_use_mock_apis() or not (config["url"] and config["api_key"])
    
    return {
        "url": config["url"],
        "api_key": config["api_key"],
        "use_mock": use_mock,
    }

