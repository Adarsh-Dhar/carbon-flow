"""
Surge detection tools for InterState-AccountabilityAgent.

Detects pollution surges at Delhi border stations by filtering CPCB data
and identifying stations with AQI exceeding the threshold.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.config.border_stations import DELHI_BORDER_STATIONS, is_border_station
from src.config.thresholds import SURGE_AQI_THRESHOLD
from src.models.data_models import BorderStation


def debug_log(tool_name: str, message: str) -> None:
    """Log debug messages with timestamp."""
    timestamp = datetime.utcnow().isoformat()
    print(f"[DEBUG {timestamp}] Tool '{tool_name}': {message}")


def detect_surge(
    cpcb_data: list[dict[str, Any]],
    surge_threshold: float = SURGE_AQI_THRESHOLD,
) -> list[BorderStation]:
    """
    Detect pollution surges at Delhi border stations.
    
    Args:
        cpcb_data: List of CPCB station data records
        surge_threshold: AQI threshold for surge detection (default: 300)
        
    Returns:
        List of BorderStation objects with is_surge=True for stations exceeding threshold
    """
    debug_log("detect_surge", f"Analyzing {len(cpcb_data)} CPCB records for surges")
    
    surge_stations: list[BorderStation] = []
    
    # Group CPCB data by station name
    stations_dict: dict[str, dict[str, Any]] = {}
    
    for record in cpcb_data:
        station_name = record.get("station", record.get("name", "Unknown"))
        
        # Only process border stations
        if not is_border_station(station_name):
            continue
        
        # Get border station config
        from src.config.border_stations import get_border_station
        border_config = get_border_station(station_name)
        if not border_config:
            continue
        
        # Initialize station data if not exists
        if station_name not in stations_dict:
            stations_dict[station_name] = {
                "name": station_name,
                "latitude": border_config["latitude"],
                "longitude": border_config["longitude"],
                "border": border_config["border"],
                "district": border_config["district"],
                "aqi": None,
                "pm25": None,
                "pm10": None,
                "timestamp": record.get("timestamp") or record.get("last_update") or record.get("date"),
            }
        
        # Extract pollutant values
        pollutant = record.get("pollutant_id", "")
        pollutant_avg = record.get("pollutant_avg")
        
        if pollutant_avg is not None:
            try:
                value = float(pollutant_avg)
                
                if pollutant == "PM2.5":
                    stations_dict[station_name]["pm25"] = value
                    # Use PM2.5 as AQI proxy if AQI not available
                    if stations_dict[station_name]["aqi"] is None:
                        stations_dict[station_name]["aqi"] = value
                elif pollutant == "PM10":
                    stations_dict[station_name]["pm10"] = value
                elif pollutant in ["AQI", "aqi"]:
                    stations_dict[station_name]["aqi"] = value
            except (ValueError, TypeError):
                pass
    
    # Check each station for surge
    for station_name, station_data in stations_dict.items():
        aqi = station_data.get("aqi")
        
        if aqi is not None and aqi >= surge_threshold:
            debug_log(
                "detect_surge",
                f"Surge detected at {station_name}: AQI={aqi} (threshold={surge_threshold})"
            )
            
            surge_station = BorderStation(
                name=station_data["name"],
                latitude=station_data["latitude"],
                longitude=station_data["longitude"],
                border=station_data["border"],
                district=station_data["district"],
                aqi=aqi,
                pm25=station_data.get("pm25"),
                pm10=station_data.get("pm10"),
                timestamp=station_data.get("timestamp"),
                is_surge=True,
            )
            surge_stations.append(surge_station)
    
    debug_log("detect_surge", f"Detected {len(surge_stations)} surge(s) at border stations")
    
    return surge_stations

