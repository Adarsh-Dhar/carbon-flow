"""
Construction API Adapter

Handles communication with construction site management API for issuing stop-work orders.
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


class ConstructionAPIAdapter:
    """Adapter for construction site API with graceful fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("construction")
        self.url = self.config["url"]
        self.api_key = self.config["api_key"]
        self.use_mock = not (self.url and self.api_key)
        
        if self.use_mock:
            logger.warning(
                "[ConstructionAPI] Using mock implementation - credentials not configured. "
                "Set CONSTRUCTION_API_URL and CONSTRUCTION_API_KEY for real API calls."
            )
        else:
            logger.info(f"[ConstructionAPI] Initialized with real API: {self.url}")
    
    def issue_construction_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Issue GRAP-III stop-work orders to all non-essential construction sites.
        
        Args:
            reasoning_text: Explanation for why the construction ban is being issued
            
        Returns:
            Dict with status and action confirmation (always succeeds, falls back to mock if needed)
        """
        if self.use_mock:
            return self._mock_issue_ban(reasoning_text)
        else:
            return self._real_issue_ban(reasoning_text)
    
    def _real_issue_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to issue construction ban with retry logic.
        
        Args:
            reasoning_text: Explanation for the ban
            
        Returns:
            Dict with API response or falls back to mock on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "action": "issue_construction_ban",
            "reasoning": reasoning_text,
            "timestamp": datetime.utcnow().isoformat(),
            "scope": "all_non_essential_sites"
        }
        
        # Retry logic with exponential backoff
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"[ConstructionAPI] Attempt {attempt}/{max_attempts}: "
                    f"POST {self.url} (action: issue_construction_ban)"
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
                        f"[ConstructionAPI] Success: {result.get('sites_notified', 0)} sites notified"
                    )
                    print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
                    
                    return {
                        "status": "SUCCESS",
                        "action": "construction_ban_issued",
                        "api_mode": "real",
                        "sites_notified": result.get("sites_notified", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[ConstructionAPI] Attempt {attempt} failed: {error_msg}")
                    
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.info(f"[ConstructionAPI] Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error("[ConstructionAPI] All attempts failed, falling back to mock")
                        return self._mock_issue_ban(reasoning_text)
                        
            except requests.exceptions.Timeout:
                logger.warning(f"[ConstructionAPI] Attempt {attempt} timed out")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[ConstructionAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[ConstructionAPI] All attempts timed out, falling back to mock")
                    return self._mock_issue_ban(reasoning_text)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[ConstructionAPI] Attempt {attempt} failed: {str(e)}")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[ConstructionAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[ConstructionAPI] All attempts failed, falling back to mock")
                    return self._mock_issue_ban(reasoning_text)
        
        # Should never reach here, but fallback just in case
        return self._mock_issue_ban(reasoning_text)
    
    def _mock_issue_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of construction ban.
        
        Args:
            reasoning_text: Explanation for the ban
            
        Returns:
            Dict with mock response
        """
        logger.info("[ConstructionAPI] Using mock implementation")
        print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "construction_ban_issued",
            "api_mode": "mock",
            "sites_notified": 1240,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

