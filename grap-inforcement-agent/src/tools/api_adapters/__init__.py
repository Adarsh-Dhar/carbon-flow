"""
API Adapters for GRAP Enforcement Actions

This module provides adapters for real government APIs with mock fallback support.
"""

from .config import get_api_config, should_use_mock_apis
from .construction_api import ConstructionAPIAdapter
from .traffic_api import TrafficAPIAdapter
from .education_api import EducationAPIAdapter
from .enforcement_api import EnforcementAPIAdapter

__all__ = [
    "get_api_config",
    "should_use_mock_apis",
    "ConstructionAPIAdapter",
    "TrafficAPIAdapter",
    "EducationAPIAdapter",
    "EnforcementAPIAdapter",
]

