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
    Determine if mock APIs should be used globally.
    
    This function checks for an explicit global flag. Individual APIs
    can still work independently based on their own credentials.
    
    Returns:
        True if mock APIs should be used globally, False otherwise
    """
    # Check for explicit flag
    use_mock = os.getenv("USE_MOCK_APIS", "").lower()
    if use_mock in ("true", "1", "yes"):
        return True
    
    # If no explicit flag, allow individual APIs to work independently
    return False


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
    # Check global flag first, then check if this specific API has credentials
    global_use_mock = should_use_mock_apis()
    has_credentials = bool(config["url"] and config["api_key"])
    
    # Use mock if global flag is set OR if this specific API lacks credentials
    use_mock = global_use_mock or not has_credentials
    
    return {
        "url": config["url"],
        "api_key": config["api_key"],
        "use_mock": use_mock,
    }

