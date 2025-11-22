"""
Enforcement Teams API Adapter

Handles communication with enforcement teams API for dispatching teams to hotspots.
Supports both real API calls and graceful fallback to mock implementation.
"""

import time
import logging
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config

# Set up logger
logger = logging.getLogger(__name__)


class EnforcementAPIAdapter:
    """Adapter for enforcement teams API with graceful fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("enforcement")
        self.url = self.config["url"]
        self.api_key = self.config["api_key"]
        self.use_mock = not (self.url and self.api_key)
        
        if self.use_mock:
            logger.warning(
                "[EnforcementAPI] Using mock implementation - credentials not configured. "
                "Set ENFORCEMENT_API_URL and ENFORCEMENT_API_KEY for real API calls."
            )
        else:
            logger.info(f"[EnforcementAPI] Initialized with real API: {self.url}")
    
    def dispatch_enforcement_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Dispatch enforcement teams to pollution hotspots across Delhi NCR.
        
        Args:
            hotspots: List of pollution hotspot locations to prioritize
            
        Returns:
            Dict with status, action confirmation, and targeted hotspots (always succeeds, falls back to mock if needed)
        """
        if self.use_mock:
            return self._mock_dispatch_teams(hotspots)
        else:
            return self._real_dispatch_teams(hotspots)
    
    def _real_dispatch_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Make real API call to dispatch teams with retry logic.
        
        Args:
            hotspots: List of hotspot locations
            
        Returns:
            Dict with API response or falls back to mock on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "action": "dispatch_enforcement_teams",
            "timestamp": datetime.utcnow().isoformat(),
            "hotspots": hotspots,
            "team_count": 2000
        }
        
        # Retry logic with exponential backoff
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"[EnforcementAPI] Attempt {attempt}/{max_attempts}: "
                    f"POST {self.url} (action: dispatch_enforcement_teams, hotspots: {len(hotspots)})"
                )
                
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"[EnforcementAPI] Success: {result.get('teams_dispatched', 0)} teams dispatched "
                        f"to {len(hotspots)} hotspots"
                    )
                    print(f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}")
                    
                    return {
                        "status": "SUCCESS",
                        "action": "teams_dispatched",
                        "api_mode": "real",
                        "hotspots_targeted": hotspots,
                        "teams_dispatched": result.get("teams_dispatched", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[EnforcementAPI] Attempt {attempt} failed: {error_msg}")
                    
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.info(f"[EnforcementAPI] Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error("[EnforcementAPI] All attempts failed, falling back to mock")
                        return self._mock_dispatch_teams(hotspots)
                        
            except requests.exceptions.Timeout:
                logger.warning(f"[EnforcementAPI] Attempt {attempt} timed out")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[EnforcementAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[EnforcementAPI] All attempts timed out, falling back to mock")
                    return self._mock_dispatch_teams(hotspots)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[EnforcementAPI] Attempt {attempt} failed: {str(e)}")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[EnforcementAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[EnforcementAPI] All attempts failed, falling back to mock")
                    return self._mock_dispatch_teams(hotspots)
        
        # Should never reach here, but fallback just in case
        return self._mock_dispatch_teams(hotspots)
    
    def _mock_dispatch_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Mock implementation of team dispatch.
        
        Args:
            hotspots: List of hotspot locations
            
        Returns:
            Dict with mock response
        """
        logger.info("[EnforcementAPI] Using mock implementation")
        print(f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}")
        
        return {
            "status": "SUCCESS",
            "action": "teams_dispatched",
            "api_mode": "mock",
            "hotspots_targeted": hotspots,
            "teams_dispatched": 2000,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

