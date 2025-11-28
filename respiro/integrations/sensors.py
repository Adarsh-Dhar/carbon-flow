"""
Sensor Integration Tools for Respiro

Provides API clients for Google AQI, Ambee pollen, and HealthKit/Fitbit biometrics
with comprehensive error handling and retries.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class GoogleAQIClient:
    """Client for Google Air Quality Index API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.api.google_aqi_api_key
        if not self.api_key:
            logger.warning("Google AQI API key not configured")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def get_aqi(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get current AQI for a location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            AQI data or None if unavailable
        """
        if not self.api_key:
            logger.warning("Google AQI API key not available")
            return None
        
        try:
            # Google AQI API endpoint (example - adjust based on actual API)
            url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
            params = {
                "key": self.api_key,
                "location.latitude": latitude,
                "location.longitude": longitude
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract AQI and pollutants
            aqi_value = data.get("indexes", [{}])[0].get("aqi", 0)
            category = data.get("indexes", [{}])[0].get("category", "Unknown")
            pollutants = {}
            
            for pollutant in data.get("pollutants", []):
                code = pollutant.get("code", "")
                concentration = pollutant.get("concentration", {})
                pollutants[code] = {
                    "value": concentration.get("value", 0),
                    "units": concentration.get("units", "")
                }
            
            return {
                "aqi": aqi_value,
                "category": category,
                "pollutants": pollutants,
                "location": {"latitude": latitude, "longitude": longitude},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Google AQI API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Google AQI client: {e}")
            return None


class AmbeeClient:
    """Client for Ambee Pollen API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.api.ambee_api_key
        if not self.api_key:
            logger.warning("Ambee API key not configured")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def get_pollen_data(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get pollen data for a location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Pollen data or None if unavailable
        """
        if not self.api_key:
            logger.warning("Ambee API key not available")
            return None
        
        try:
            url = "https://api.ambeedata.com/latest/pollen"
            headers = {
                "x-api-key": self.api_key,
                "Content-type": "application/json"
            }
            params = {
                "lat": latitude,
                "lng": longitude
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract pollen data
            pollen_data = data.get("data", [{}])[0] if data.get("data") else {}
            risk = pollen_data.get("Risk", {})
            
            return {
                "overall_risk": risk.get("predominant_pollen", "Unknown"),
                "tree_pollen": pollen_data.get("Tree", {}).get("value", 0),
                "grass_pollen": pollen_data.get("Grass", {}).get("value", 0),
                "weed_pollen": pollen_data.get("Weed", {}).get("value", 0),
                "location": {"latitude": latitude, "longitude": longitude},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Ambee API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Ambee client: {e}")
            return None


class HealthKitClient:
    """Client for Apple HealthKit API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.healthkit.healthkit_api_key
        if not self.api_key:
            logger.warning("HealthKit API key not configured")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def get_biometrics(
        self,
        user_id: str,
        hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get recent biometric data from HealthKit.
        
        Args:
            user_id: User identifier
            hours: Number of hours of data to retrieve
            
        Returns:
            Biometric data or None if unavailable
        """
        if not self.api_key:
            logger.warning("HealthKit API key not available")
            return None
        
        try:
            # HealthKit API endpoint (example - adjust based on actual API)
            url = f"https://api.healthkit.app/v1/users/{user_id}/biometrics"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            params = {
                "hours": hours
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant biometrics for asthma
            return {
                "heart_rate": data.get("heart_rate", {}).get("latest", 0),
                "respiratory_rate": data.get("respiratory_rate", {}).get("latest", 0),
                "oxygen_saturation": data.get("oxygen_saturation", {}).get("latest", 0),
                "peak_flow": data.get("peak_flow", {}).get("latest", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"HealthKit API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in HealthKit client: {e}")
            return None


class FitbitClient:
    """Client for Fitbit API."""
    
    def __init__(self):
        settings = get_settings()
        self.client_id = settings.healthkit.fitbit_client_id
        self.client_secret = settings.healthkit.fitbit_client_secret
        self.access_token = settings.healthkit.fitbit_access_token
        self.refresh_token = settings.healthkit.fitbit_refresh_token
    
    def _refresh_access_token(self) -> bool:
        """Refresh Fitbit access token."""
        if not self.refresh_token:
            return False
        
        try:
            url = "https://api.fitbit.com/oauth2/token"
            auth = (self.client_id, self.client_secret)
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(url, auth=auth, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh Fitbit token: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def get_biometrics(
        self,
        user_id: str = "-",
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get biometric data from Fitbit.
        
        Args:
            user_id: Fitbit user ID (default: "-" for current user)
            date: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Biometric data or None if unavailable
        """
        if not self.access_token:
            if not self._refresh_access_token():
                logger.warning("Fitbit access token not available")
                return None
        
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        try:
            # Get heart rate data
            hr_url = f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{date}/1d.json"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            hr_response = requests.get(hr_url, headers=headers, timeout=10)
            
            # Handle token expiration
            if hr_response.status_code == 401:
                if self._refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    hr_response = requests.get(hr_url, headers=headers, timeout=10)
                else:
                    return None
            
            hr_response.raise_for_status()
            hr_data = hr_response.json()
            
            # Get SpO2 data
            spo2_url = f"https://api.fitbit.com/1/user/{user_id}/spo2/date/{date}.json"
            spo2_response = requests.get(spo2_url, headers=headers, timeout=10)
            
            if spo2_response.status_code == 401:
                if self._refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    spo2_response = requests.get(spo2_url, headers=headers, timeout=10)
            
            spo2_data = spo2_response.json() if spo2_response.status_code == 200 else {}
            
            # Extract relevant data
            heart_rate_zones = hr_data.get("activities-heart", [{}])[0].get("value", {}).get("heartRateZones", [])
            resting_hr = hr_data.get("activities-heart", [{}])[0].get("value", {}).get("restingHeartRate", 0)
            
            return {
                "heart_rate": resting_hr,
                "heart_rate_zones": heart_rate_zones,
                "oxygen_saturation": spo2_data.get("value", [{}])[0].get("avg", 0) if spo2_data.get("value") else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Fitbit API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Fitbit client: {e}")
            return None


def fuse_sensor_data(
    aqi_data: Optional[Dict[str, Any]],
    pollen_data: Optional[Dict[str, Any]],
    biometric_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Fuse data from multiple sensors into unified context.
    
    Args:
        aqi_data: Google AQI data
        pollen_data: Ambee pollen data
        biometric_data: HealthKit/Fitbit biometric data
        
    Returns:
        Fused sensor data
    """
    fused = {
        "air_quality": aqi_data or {},
        "pollen": pollen_data or {},
        "biometrics": biometric_data or {},
        "timestamp": datetime.utcnow().isoformat(),
        "data_completeness": {
            "aqi": aqi_data is not None,
            "pollen": pollen_data is not None,
            "biometrics": biometric_data is not None
        }
    }
    
    return fused
