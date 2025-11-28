"""Pharmacy integration for discount codes and medication management."""
from typing import Dict, Any, List, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class PharmacyClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.api.pharmacy_api_base_url
        self.api_key = settings.api.pharmacy_api_key
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_discount_code(self, patient_id: str, medication: str) -> Optional[str]:
        """Generate discount code for medication."""
        if not self.base_url or not self.api_key:
            return None
        try:
            response = requests.post(
                f"{self.base_url}/discounts/generate",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"patient_id": patient_id, "medication": medication},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("discount_code")
        except Exception as e:
            logger.error(f"Pharmacy API failed: {e}")
            return None
