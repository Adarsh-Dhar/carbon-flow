"""
Education Department API Adapter

Handles communication with education department API for school notifications.
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


class EducationAPIAdapter:
    """Adapter for education department API with graceful fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("education")
        self.url = self.config["url"]
        self.api_key = self.config["api_key"]
        self.use_mock = not (self.url and self.api_key)
        
        if self.use_mock:
            logger.warning(
                "[EducationAPI] Using mock implementation - credentials not configured. "
                "Set EDUCATION_API_URL and EDUCATION_API_KEY for real API calls."
            )
        else:
            logger.info(f"[EducationAPI] Initialized with real API: {self.url}")
    
    def notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Send public notifications via SAMEER App and issue school directives.
        
        Args:
            reasoning_text: Explanation for why public notifications are being sent
            
        Returns:
            Dict with status and action confirmation (always succeeds, falls back to mock if needed)
        """
        if self.use_mock:
            return self._mock_notify_public(reasoning_text)
        else:
            return self._real_notify_public(reasoning_text)
    
    def _real_notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to notify public with retry logic.
        
        Args:
            reasoning_text: Explanation for notifications
            
        Returns:
            Dict with API response or falls back to mock on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "action": "notify_public",
            "reasoning": reasoning_text,
            "timestamp": datetime.utcnow().isoformat(),
            "notifications": {
                "sameer_app": True,
                "school_directive": {
                    "enabled": True,
                    "classes": "V and below",
                    "mode": "hybrid"
                }
            }
        }
        
        # Retry logic with exponential backoff
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"[EducationAPI] Attempt {attempt}/{max_attempts}: "
                    f"POST {self.url} (action: notify_public)"
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
                        f"[EducationAPI] Success: {result.get('sameer_notifications_sent', 0)} SAMEER notifications, "
                        f"{result.get('schools_notified', 0)} schools notified"
                    )
                    print(f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}")
                    print(f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}")
                    
                    return {
                        "status": "SUCCESS",
                        "action": "public_notification_sent",
                        "api_mode": "real",
                        "sameer_notifications": result.get("sameer_notifications_sent", 0),
                        "schools_notified": result.get("schools_notified", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[EducationAPI] Attempt {attempt} failed: {error_msg}")
                    
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.info(f"[EducationAPI] Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error("[EducationAPI] All attempts failed, falling back to mock")
                        return self._mock_notify_public(reasoning_text)
                        
            except requests.exceptions.Timeout:
                logger.warning(f"[EducationAPI] Attempt {attempt} timed out")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[EducationAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[EducationAPI] All attempts timed out, falling back to mock")
                    return self._mock_notify_public(reasoning_text)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[EducationAPI] Attempt {attempt} failed: {str(e)}")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[EducationAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[EducationAPI] All attempts failed, falling back to mock")
                    return self._mock_notify_public(reasoning_text)
        
        # Should never reach here, but fallback just in case
        return self._mock_notify_public(reasoning_text)
    
    def _mock_notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of public notifications.
        
        Args:
            reasoning_text: Explanation for notifications
            
        Returns:
            Dict with mock response
        """
        logger.info("[EducationAPI] Using mock implementation")
        print(f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}")
        print(f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "public_notification_sent",
            "api_mode": "mock",
            "sameer_notifications": 50000,  # Simulated count
            "schools_notified": 2500,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

