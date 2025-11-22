"""Meteorological forecast tools for ForecastAgent."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests


def get_meteorological_forecast_tool(
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    hours: int = 48,
    security_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Fetch 48-hour wind speed forecast for Delhi from Open-Meteo API.
    
    Retrieves hourly wind speed forecasts from the Open-Meteo API for the specified
    location. Implements retry logic with exponential backoff for reliability.
    
    Args:
        latitude: Location latitude (default: 28.6139 for Delhi)
        longitude: Location longitude (default: 77.2090 for Delhi)
        hours: Number of forecast hours to retrieve (default: 48)
        security_context: CrewAI security context (unused, for compatibility)
        
    Returns:
        Dict containing meteorological forecast data:
        {
            "hourly_wind_speed": [
                {
                    "timestamp": str,  # ISO 8601 format
                    "wind_speed_kmh": float,
                    "wind_direction_deg": float  # Wind direction in degrees (0-360)
                },
                ...
            ],
            "location": {
                "latitude": float,
                "longitude": float,
                "city": "Delhi"
            }
        }
        
        Or error dict: {"error": "...", "details": "..."}
        
    Raises:
        None - returns error dict instead of raising exceptions
    """
    # Calculate forecast days (Open-Meteo API uses days, not hours)
    forecast_days = max(1, (hours + 23) // 24)  # Round up to nearest day
    
    # Open-Meteo API endpoint
    url = "https://api.open-meteo.com/v1/forecast"
    
    # Request parameters
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "forecast_days": forecast_days,
        "wind_speed_unit": "kmh"
    }
    
    print(f"[DEBUG {datetime.now().isoformat()}] Fetching meteorological forecast from Open-Meteo API")
    print(f"[DEBUG] Parameters: lat={latitude}, lon={longitude}, forecast_days={forecast_days}")
    
    # Retry logic with exponential backoff
    max_attempts = 3
    base_delay = 1.0  # seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Check for successful response
            if response.status_code == 200:
                data = response.json()
                print(f"[DEBUG] Successfully retrieved meteorological forecast on attempt {attempt}")
                
                # Parse and format the response
                parsed_data = _parse_meteo_response(data, latitude, longitude, hours)
                return parsed_data
            
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_detail = response.json().get('reason', response.text)
                except Exception:  # noqa: BLE001
                    error_detail = response.text
                
                print(f"[DEBUG] Attempt {attempt}/{max_attempts} failed: {error_msg}")
                
                # If this is the last attempt, return error
                if attempt == max_attempts:
                    return {
                        "error": "Open-Meteo API request failed",
                        "details": f"{error_msg}: {error_detail}"
                    }
                
                # Wait before retrying (exponential backoff)
                delay = base_delay * (2 ** (attempt - 1))
                print(f"[DEBUG] Retrying in {delay} seconds...")
                time.sleep(delay)
        
        except requests.exceptions.Timeout:
            print(f"[DEBUG] Attempt {attempt}/{max_attempts} timed out")
            
            if attempt == max_attempts:
                return {
                    "error": "Open-Meteo API request timed out",
                    "details": f"Request timed out after {max_attempts} attempts"
                }
            
            # Wait before retrying
            delay = base_delay * (2 ** (attempt - 1))
            print(f"[DEBUG] Retrying in {delay} seconds...")
            time.sleep(delay)
        
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Attempt {attempt}/{max_attempts} failed with RequestException: {e}")
            
            if attempt == max_attempts:
                return {
                    "error": "Open-Meteo API request failed",
                    "details": f"RequestException: {str(e)}"
                }
            
            # Wait before retrying
            delay = base_delay * (2 ** (attempt - 1))
            print(f"[DEBUG] Retrying in {delay} seconds...")
            time.sleep(delay)
        
        except Exception as e:  # noqa: BLE001
            # Unexpected error - don't retry
            return {
                "error": "Unexpected error fetching meteorological forecast",
                "details": f"{type(e).__name__}: {str(e)}"
            }
    
    # Should not reach here, but just in case
    return {
        "error": "Failed to fetch meteorological forecast",
        "details": "Maximum retry attempts exceeded"
    }


def _parse_meteo_response(
    data: dict[str, Any],
    latitude: float,
    longitude: float,
    max_hours: int
) -> dict[str, Any]:
    """
    Parse Open-Meteo API response into structured format.
    
    Args:
        data: Raw API response JSON
        latitude: Location latitude
        longitude: Location longitude
        max_hours: Maximum number of hours to include
        
    Returns:
        Dict with hourly_wind_speed list (including wind direction) and location info
    """
    hourly_data = data.get('hourly', {})
    timestamps = hourly_data.get('time', [])
    wind_speeds = hourly_data.get('wind_speed_10m', [])
    wind_directions = hourly_data.get('wind_direction_10m', [])
    
    # Combine timestamps, wind speeds, and wind directions, limiting to max_hours
    hourly_wind_speed = []
    for i, (timestamp, wind_speed) in enumerate(zip(timestamps, wind_speeds)):
        if i >= max_hours:
            break
        
        # Get wind direction if available (same index as wind speed)
        wind_direction = wind_directions[i] if i < len(wind_directions) else None
        
        hourly_wind_speed.append({
            "timestamp": timestamp,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": wind_direction
        })
    
    return {
        "hourly_wind_speed": hourly_wind_speed,
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "city": "Delhi"
        }
    }

