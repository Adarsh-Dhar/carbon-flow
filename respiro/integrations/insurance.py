"""Insurance integration for premium adjustments and wellness programs."""
from typing import Dict, Any, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class InsuranceClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.api.insurance_api_base_url
        self.api_key = settings.api.insurance_api_key
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def request_premium_adjustment(self, patient_id: str, adherence_score: float) -> bool:
        """Request premium adjustment based on adherence."""
        if not self.base_url or not self.api_key:
            return False
        try:
            response = requests.post(
                f"{self.base_url}/premium/adjustment",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"patient_id": patient_id, "adherence_score": adherence_score},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Insurance API failed: {e}")
            return False
