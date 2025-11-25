"""
Fire correlation tools for InterState-AccountabilityAgent.

Correlates NASA FIRMS fire events with pollution surges at border stations
using haversine distance calculations and time window filtering.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Any

try:
    from haversine import haversine as _haversine_impl
except ImportError:
    def _haversine_impl(point1: tuple[float, float], point2: tuple[float, float]) -> float:
        """
        Lightweight fallback haversine implementation if dependency is unavailable.
        """
        lat1, lon1 = point1
        lat2, lon2 = point2
        rlat1 = radians(lat1)
        rlon1 = radians(lon1)
        rlat2 = radians(lat2)
        rlon2 = radians(lon2)
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = (
            sin(dlat / 2) ** 2
            + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        earth_radius_km = 6371.0
        return earth_radius_km * c

from src.config.thresholds import (
    CORRELATION_WINDOW_HOURS,
    FIRE_CORRELATION_RADIUS_KM,
    HIGH_CONTRIBUTION_FIRE_COUNT,
    HIGH_DISTANCE_PENALTY,
    LOW_FIRE_COUNT_PENALTY,
    LOW_FIRE_COUNT_THRESHOLD,
    MAX_DATA_AGE_HOURS,
    MEDIUM_DISTANCE_KM,
    MIN_CONFIDENCE_SCORE,
    NASA_DATA_MISSING_PENALTY,
    DSS_DATA_MISSING_PENALTY,
)
from src.models.data_models import BorderStation, CorrelationResult, FireEvent


def debug_log(tool_name: str, message: str) -> None:
    """Log debug messages with timestamp."""
    timestamp = datetime.utcnow().isoformat()
    print(f"[DEBUG {timestamp}] Tool '{tool_name}': {message}")


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate haversine distance between two coordinates in kilometers.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in kilometers
    """
    return _haversine_impl((lat1, lon1), (lat2, lon2))


def parse_fire_timestamp(fire_data: dict[str, Any]) -> datetime | None:
    """
    Parse timestamp from fire event data.
    
    Args:
        fire_data: Fire event dictionary
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    try:
        # Try acq_date and acq_time combination
        acq_date = fire_data.get("acq_date")
        acq_time = fire_data.get("acq_time")
        
        if acq_date and acq_time:
            # Format: YYYY-MM-DD and HHMM
            date_str = f"{acq_date} {acq_time[:2]}:{acq_time[2:]}"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        
        # Try timestamp field
        timestamp = fire_data.get("timestamp")
        if timestamp:
            if isinstance(timestamp, str):
                # Try ISO format
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp)
        
        # Try date field
        date_str = fire_data.get("date")
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError, AttributeError):
        pass
    
    return None


def correlate_fires(
    surge_stations: list[BorderStation],
    nasa_data: list[dict[str, Any]],
    correlation_radius_km: float = FIRE_CORRELATION_RADIUS_KM,
    correlation_window_hours: int = CORRELATION_WINDOW_HOURS,
) -> list[CorrelationResult]:
    """
    Correlate NASA FIRMS fire events with pollution surges at border stations.
    
    Args:
        surge_stations: List of BorderStation objects with is_surge=True
        nasa_data: List of NASA FIRMS fire event dictionaries
        correlation_radius_km: Maximum distance for correlation (default: 200km)
        correlation_window_hours: Time window for correlation (default: 48 hours)
        
    Returns:
        List of CorrelationResult objects grouped by state
    """
    debug_log("correlate_fires", f"Correlating {len(nasa_data)} fires with {len(surge_stations)} surge stations")
    
    if not surge_stations:
        debug_log("correlate_fires", "No surge stations provided, returning empty correlation")
        return []
    
    if not nasa_data:
        debug_log("correlate_fires", "No NASA fire data provided, returning empty correlation")
        return []
    
    # Get the earliest surge timestamp to establish time window
    surge_timestamps = [
        datetime.fromisoformat(st.timestamp.replace("Z", "+00:00"))
        for st in surge_stations
        if st.timestamp
    ]
    
    if not surge_timestamps:
        # Use current time if no timestamps available
        surge_time = datetime.utcnow()
    else:
        surge_time = min(surge_timestamps)
    
    # Calculate time window start
    window_start = surge_time - timedelta(hours=correlation_window_hours)
    
    # Filter and correlate fires
    correlated_fires: list[FireEvent] = []
    
    for fire_data in nasa_data:
        fire_lat = fire_data.get("latitude")
        fire_lon = fire_data.get("longitude")
        
        if fire_lat is None or fire_lon is None:
            continue
        
        # Check if fire is within correlation radius of any surge station
        min_distance = float("inf")
        closest_station = None
        
        for station in surge_stations:
            distance = haversine_distance_km(
                station.latitude,
                station.longitude,
                fire_lat,
                fire_lon,
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_station = station
        
        # Check if within correlation radius
        if min_distance > correlation_radius_km:
            continue
        
        # Check if within time window
        fire_timestamp = parse_fire_timestamp(fire_data)
        if fire_timestamp and fire_timestamp < window_start:
            continue
        
        # Create FireEvent object
        fire_event = FireEvent(
            latitude=fire_lat,
            longitude=fire_lon,
            brightness=fire_data.get("brightness"),
            confidence=fire_data.get("confidence"),
            acq_date=fire_data.get("acq_date"),
            acq_time=fire_data.get("acq_time"),
            state=fire_data.get("state"),
            district=fire_data.get("district"),
            distance_km=min_distance,
        )
        correlated_fires.append(fire_event)
    
    debug_log("correlate_fires", f"Found {len(correlated_fires)} fires within correlation parameters")
    
    # Group fires by state
    state_fires: dict[str, list[FireEvent]] = {}
    
    for fire in correlated_fires:
        state = fire.state or "Unknown"
        if state not in state_fires:
            state_fires[state] = []
        state_fires[state].append(fire)
    
    # Create CorrelationResult objects
    correlation_results: list[CorrelationResult] = []
    
    for state, fires in state_fires.items():
        fire_count = len(fires)
        districts = list(set(f.district for f in fires if f.district))
        avg_distance = sum(f.distance_km or 0 for f in fires) / fire_count if fires else 0.0
        
        is_high_contribution = fire_count >= HIGH_CONTRIBUTION_FIRE_COUNT
        
        correlation_result = CorrelationResult(
            state=state,
            fire_count=fire_count,
            districts=districts,
            avg_distance_km=avg_distance,
            is_high_contribution=is_high_contribution,
            fire_events=fires,
        )
        correlation_results.append(correlation_result)
        
        debug_log(
            "correlate_fires",
            f"State {state}: {fire_count} fires, avg distance {avg_distance:.1f}km, "
            f"high contribution={is_high_contribution}"
        )
    
    return correlation_results


def calculate_confidence_score(
    correlation_results: list[CorrelationResult],
    nasa_data_available: bool = True,
    dss_data_available: bool = True,
) -> float:
    """
    Calculate confidence score for accountability report.
    
    Args:
        correlation_results: List of CorrelationResult objects
        nasa_data_available: Whether NASA FIRMS data is available
        dss_data_available: Whether DSS data is available
        
    Returns:
        Confidence score between MIN_CONFIDENCE_SCORE and 100.0
    """
    debug_log("calculate_confidence_score", "Calculating confidence score")
    
    # Start with base confidence
    confidence = 100.0
    
    # Apply penalties
    if not nasa_data_available:
        confidence -= NASA_DATA_MISSING_PENALTY
        debug_log("calculate_confidence_score", f"Applied NASA data missing penalty: -{NASA_DATA_MISSING_PENALTY}")
    
    if not dss_data_available:
        confidence -= DSS_DATA_MISSING_PENALTY
        debug_log("calculate_confidence_score", f"Applied DSS data missing penalty: -{DSS_DATA_MISSING_PENALTY}")
    
    # Calculate total fire count
    total_fires = sum(cr.fire_count for cr in correlation_results)
    
    if total_fires < LOW_FIRE_COUNT_THRESHOLD:
        confidence -= LOW_FIRE_COUNT_PENALTY
        debug_log("calculate_confidence_score", f"Applied low fire count penalty: -{LOW_FIRE_COUNT_PENALTY}")
    
    # Check average distance
    if correlation_results:
        avg_distance = sum(cr.avg_distance_km for cr in correlation_results) / len(correlation_results)
        if avg_distance > MEDIUM_DISTANCE_KM:
            confidence -= HIGH_DISTANCE_PENALTY
            debug_log("calculate_confidence_score", f"Applied high distance penalty: -{HIGH_DISTANCE_PENALTY}")
    
    # Enforce minimum
    confidence = max(confidence, MIN_CONFIDENCE_SCORE)
    
    debug_log("calculate_confidence_score", f"Final confidence score: {confidence:.1f}")
    
    return confidence

