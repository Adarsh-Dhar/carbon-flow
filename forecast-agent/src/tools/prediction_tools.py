"""Prediction logic and reasoning engine for ForecastAgent."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any


# Prediction thresholds (configurable constants)
SEVERE_AQI_THRESHOLD = 401
VERY_POOR_AQI_THRESHOLD = 301
POOR_AQI_THRESHOLD = 201
MODERATE_AQI_THRESHOLD = 101

HIGH_FIRE_COUNT = 400
MODERATE_FIRE_COUNT = 200
LOW_WIND_SPEED_KMH = 10
MODERATE_WIND_SPEED_KMH = 15
HIGH_STUBBLE_PERCENT = 20
MODERATE_STUBBLE_PERCENT = 10


def synthesize_and_predict(
    sensor_data: dict[str, Any],
    meteo_data: dict[str, Any],
    security_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Synthesize sensor and meteorological data to generate AQI prediction.
    
    Applies reasoning logic to predict air quality based on fire counts, wind speed,
    stubble burning patterns, and current AQI levels. Generates confidence levels
    based on data quality metrics.
    
    Args:
        sensor_data: Dict from read_ingested_data_tool containing cpcb_data, nasa_data,
                     dss_data, and data_quality sections
        meteo_data: Dict from get_meteorological_forecast_tool containing hourly_wind_speed
        security_context: CrewAI security context (unused, for compatibility)
        
    Returns:
        Dict containing prediction results:
        {
            "prediction": str,  # e.g., "AQI will cross Severe threshold (401)"
            "estimated_hours": int,  # Hours until threshold is reached
            "confidence_level": float,  # 0-100
            "reasoning": str,  # Natural language explanation
            "aqi_category": str,  # e.g., "Severe", "Very Poor"
            "threshold": int,  # AQI threshold value
            "current_aqi": float | None,  # Current AQI level
            "fire_count": int | None,  # Fire count from NASA data
            "avg_wind_speed_24h": float | None,  # Average wind speed over 24h
            "stubble_burning_percent": float | None  # Stubble burning contribution
        }
        
        Or error dict: {"error": "...", "details": "..."}
    """
    print(f"[DEBUG {datetime.now().isoformat()}] synthesize_and_predict invoked")
    
    # Check for None or invalid input data
    if sensor_data is None or not isinstance(sensor_data, dict):
        return {
            "error": "Cannot generate prediction with invalid sensor data",
            "details": "Sensor data is None or not a dictionary"
        }
    
    # Check for errors in input data
    if "error" in sensor_data:
        return {
            "error": "Cannot generate prediction with invalid sensor data",
            "details": f"Sensor data error: {sensor_data.get('error')}"
        }
    
    # Handle meteo_data safely
    if meteo_data is not None and isinstance(meteo_data, dict) and "error" in meteo_data:
        # We can still make predictions without meteo data, but with reduced confidence
        print("[DEBUG] Meteorological data unavailable, proceeding with reduced confidence")
        meteo_data = None
    
    # Extract data from sensor_data with safe None handling
    cpcb_data = sensor_data.get("cpcb_data") if sensor_data else None
    nasa_data = sensor_data.get("nasa_data") if sensor_data else None
    dss_data = sensor_data.get("dss_data") if sensor_data else None
    data_quality = sensor_data.get("data_quality", {}) if sensor_data else {}
    
    # Ensure data_quality is always a dict
    if not isinstance(data_quality, dict):
        data_quality = {}
    
    # Ensure data_quality is always a dict
    if not isinstance(data_quality, dict):
        data_quality = {}
    
    # Extract key metrics with safe None handling
    current_aqi = None
    if cpcb_data and isinstance(cpcb_data, dict):
        aqi_val = cpcb_data.get("aqi")
        if aqi_val is not None:
            try:
                current_aqi = float(aqi_val)
            except (ValueError, TypeError):
                current_aqi = None
    
    fire_count = None
    if nasa_data and isinstance(nasa_data, dict):
        fire_val = nasa_data.get("fire_count")
        if fire_val is not None:
            try:
                fire_count = int(fire_val)
            except (ValueError, TypeError):
                fire_count = None
    
    stubble_burning_percent = None
    if dss_data and isinstance(dss_data, dict):
        stubble_val = dss_data.get("stubble_burning_percent")
        if stubble_val is not None:
            try:
                stubble_burning_percent = float(stubble_val)
            except (ValueError, TypeError):
                stubble_burning_percent = None
    
    # Calculate average wind speed and direction over next 24 hours with safe None handling
    avg_wind_speed_24h = None
    avg_wind_direction_24h = None
    if meteo_data and isinstance(meteo_data, dict) and "hourly_wind_speed" in meteo_data:
        hourly_wind = meteo_data.get("hourly_wind_speed")
        if hourly_wind and isinstance(hourly_wind, list):
            # Take first 24 hours
            wind_speeds_24h = []
            wind_directions_24h = []
            for h in hourly_wind[:24]:
                if isinstance(h, dict):
                    wind_val = h.get("wind_speed_kmh")
                    if wind_val is not None:
                        try:
                            wind_speeds_24h.append(float(wind_val))
                        except (ValueError, TypeError):
                            pass
                    
                    wind_dir_val = h.get("wind_direction_deg")
                    if wind_dir_val is not None:
                        try:
                            wind_directions_24h.append(float(wind_dir_val))
                        except (ValueError, TypeError):
                            pass
            
            if wind_speeds_24h:
                avg_wind_speed_24h = sum(wind_speeds_24h) / len(wind_speeds_24h)
            
            if wind_directions_24h:
                # Calculate average wind direction using circular mean
                # Convert to radians, calculate mean, convert back to degrees
                radians = [math.radians(d) for d in wind_directions_24h]
                sin_sum = sum(math.sin(r) for r in radians)
                cos_sum = sum(math.cos(r) for r in radians)
                avg_rad = math.atan2(sin_sum / len(radians), cos_sum / len(radians))
                avg_wind_direction_24h = math.degrees(avg_rad)
                # Normalize to 0-360
                if avg_wind_direction_24h < 0:
                    avg_wind_direction_24h += 360
    
    print(f"[DEBUG] Extracted metrics: AQI={current_aqi}, fires={fire_count}, "
          f"wind={avg_wind_speed_24h} km/h @ {avg_wind_direction_24h}°, stubble={stubble_burning_percent}%")
    
    # Apply prediction logic
    prediction_result = _apply_prediction_logic(
        current_aqi=current_aqi,
        fire_count=fire_count,
        avg_wind_speed_24h=avg_wind_speed_24h,
        stubble_burning_percent=stubble_burning_percent
    )
    
    # Calculate confidence level
    confidence_level = _calculate_confidence_level(
        data_quality=data_quality,
        has_meteo_data=meteo_data is not None and "error" not in meteo_data,
        has_cpcb_data=cpcb_data is not None,
        has_nasa_data=nasa_data is not None,
        has_dss_data=dss_data is not None
    )
    
    # Generate reasoning statement
    reasoning = _generate_reasoning(
        prediction_result=prediction_result,
        current_aqi=current_aqi,
        fire_count=fire_count,
        avg_wind_speed_24h=avg_wind_speed_24h,
        stubble_burning_percent=stubble_burning_percent
    )
    
    # Combine results
    result = {
        "prediction": prediction_result["prediction"],
        "estimated_hours": prediction_result["estimated_hours"],
        "confidence_level": confidence_level,
        "reasoning": reasoning,
        "aqi_category": prediction_result["aqi_category"],
        "threshold": prediction_result["threshold"],
        "current_aqi": current_aqi,
        "fire_count": fire_count,
        "avg_wind_speed_24h": avg_wind_speed_24h,
        "avg_wind_direction_24h": avg_wind_direction_24h,
        "stubble_burning_percent": stubble_burning_percent
    }
    
    print(f"[DEBUG] Prediction generated: {prediction_result['prediction']} "
          f"(confidence: {confidence_level:.1f}%)")
    
    return result


def _apply_prediction_logic(
    current_aqi: float | None,
    fire_count: int | None,
    avg_wind_speed_24h: float | None,
    stubble_burning_percent: float | None
) -> dict[str, Any]:
    """
    Apply conditional logic to generate AQI prediction.
    
    Args:
        current_aqi: Current AQI level from CPCB
        fire_count: Fire count from NASA data
        avg_wind_speed_24h: Average wind speed over next 24 hours (km/h)
        stubble_burning_percent: Stubble burning contribution percentage
        
    Returns:
        Dict with prediction, estimated_hours, aqi_category, and threshold
    """
    # Default prediction if insufficient data
    if current_aqi is None:
        return {
            "prediction": "Insufficient data to generate AQI prediction",
            "estimated_hours": 0,
            "aqi_category": "Unknown",
            "threshold": 0
        }
    
    # Scenario 1: High fire count + low wind speed + high stubble burning = Severe AQI
    if (fire_count is not None and fire_count > HIGH_FIRE_COUNT and
        avg_wind_speed_24h is not None and avg_wind_speed_24h < LOW_WIND_SPEED_KMH and
        stubble_burning_percent is not None and stubble_burning_percent >= HIGH_STUBBLE_PERCENT):
        
        # Calculate estimated hours to reach severe threshold
        estimated_hours = _calculate_hours_to_threshold(
            current_aqi=current_aqi,
            target_threshold=SEVERE_AQI_THRESHOLD,
            fire_count=fire_count,
            wind_speed=avg_wind_speed_24h,
            stubble_percent=stubble_burning_percent
        )
        
        return {
            "prediction": f"AQI will cross Severe threshold ({SEVERE_AQI_THRESHOLD})",
            "estimated_hours": estimated_hours,
            "aqi_category": "Severe",
            "threshold": SEVERE_AQI_THRESHOLD
        }
    
    # Scenario 2: Moderate fire count + low wind speed = Very Poor AQI
    if (fire_count is not None and fire_count > MODERATE_FIRE_COUNT and
        avg_wind_speed_24h is not None and avg_wind_speed_24h < MODERATE_WIND_SPEED_KMH):
        
        estimated_hours = _calculate_hours_to_threshold(
            current_aqi=current_aqi,
            target_threshold=VERY_POOR_AQI_THRESHOLD,
            fire_count=fire_count,
            wind_speed=avg_wind_speed_24h,
            stubble_percent=stubble_burning_percent or 0
        )
        
        return {
            "prediction": f"AQI will cross Very Poor threshold ({VERY_POOR_AQI_THRESHOLD})",
            "estimated_hours": estimated_hours,
            "aqi_category": "Very Poor",
            "threshold": VERY_POOR_AQI_THRESHOLD
        }
    
    # Scenario 3: High stubble burning + low wind = Poor AQI
    if (stubble_burning_percent is not None and stubble_burning_percent >= MODERATE_STUBBLE_PERCENT and
        avg_wind_speed_24h is not None and avg_wind_speed_24h < MODERATE_WIND_SPEED_KMH):
        
        estimated_hours = _calculate_hours_to_threshold(
            current_aqi=current_aqi,
            target_threshold=POOR_AQI_THRESHOLD,
            fire_count=fire_count or 0,
            wind_speed=avg_wind_speed_24h,
            stubble_percent=stubble_burning_percent
        )
        
        return {
            "prediction": f"AQI will cross Poor threshold ({POOR_AQI_THRESHOLD})",
            "estimated_hours": estimated_hours,
            "aqi_category": "Poor",
            "threshold": POOR_AQI_THRESHOLD
        }
    
    # Scenario 4: Good conditions (high wind speed) = AQI improvement or stable
    if avg_wind_speed_24h is not None and avg_wind_speed_24h >= MODERATE_WIND_SPEED_KMH:
        if current_aqi >= VERY_POOR_AQI_THRESHOLD:
            return {
                "prediction": "AQI expected to improve due to favorable wind conditions",
                "estimated_hours": 12,
                "aqi_category": "Improving",
                "threshold": 0
            }
        else:
            return {
                "prediction": "AQI expected to remain stable with current conditions",
                "estimated_hours": 24,
                "aqi_category": "Stable",
                "threshold": 0
            }
    
    # Default: Trend-based prediction
    if current_aqi >= SEVERE_AQI_THRESHOLD:
        category = "Severe"
        threshold = SEVERE_AQI_THRESHOLD
    elif current_aqi >= VERY_POOR_AQI_THRESHOLD:
        category = "Very Poor"
        threshold = VERY_POOR_AQI_THRESHOLD
    elif current_aqi >= POOR_AQI_THRESHOLD:
        category = "Poor"
        threshold = POOR_AQI_THRESHOLD
    elif current_aqi >= MODERATE_AQI_THRESHOLD:
        category = "Moderate"
        threshold = MODERATE_AQI_THRESHOLD
    else:
        category = "Good"
        threshold = 0
    
    return {
        "prediction": f"AQI expected to remain in {category} category",
        "estimated_hours": 24,
        "aqi_category": category,
        "threshold": threshold
    }


def _calculate_hours_to_threshold(
    current_aqi: float,
    target_threshold: int,
    fire_count: int,
    wind_speed: float,
    stubble_percent: float
) -> int:
    """
    Calculate estimated hours until AQI reaches target threshold.
    
    Uses a simplified model based on current AQI, fire intensity, wind dispersion,
    and pollution source contribution.
    
    Args:
        current_aqi: Current AQI level
        target_threshold: Target AQI threshold
        fire_count: Number of fires detected
        wind_speed: Average wind speed (km/h)
        stubble_percent: Stubble burning contribution percentage
        
    Returns:
        Estimated hours until threshold is reached (minimum 1, maximum 24)
    """
    # If already above threshold, return immediate
    if current_aqi >= target_threshold:
        return 1
    
    # Calculate AQI gap
    aqi_gap = target_threshold - current_aqi
    
    # Calculate trend factors
    # Fire intensity factor (more fires = faster increase)
    fire_factor = min(fire_count / HIGH_FIRE_COUNT, 2.0) if fire_count > 0 else 0.5
    
    # Wind dispersion factor (lower wind = faster increase)
    wind_factor = max(LOW_WIND_SPEED_KMH / wind_speed, 0.5) if wind_speed > 0 else 2.0
    
    # Stubble burning factor (higher contribution = faster increase)
    stubble_factor = min(stubble_percent / HIGH_STUBBLE_PERCENT, 2.0) if stubble_percent > 0 else 0.5
    
    # Combined trend factor (average of all factors)
    trend_factor = (fire_factor + wind_factor + stubble_factor) / 3.0
    
    # Base rate: assume ~20 AQI points per hour under severe conditions
    base_rate = 20.0
    
    # Calculate hours
    estimated_hours = int(aqi_gap / (base_rate * trend_factor))
    
    # Clamp to reasonable range (1-24 hours)
    estimated_hours = max(1, min(estimated_hours, 24))
    
    return estimated_hours


def _calculate_confidence_level(
    data_quality: dict[str, float],
    has_meteo_data: bool,
    has_cpcb_data: bool,
    has_nasa_data: bool,
    has_dss_data: bool
) -> float:
    """
    Calculate confidence level for prediction based on data quality.
    
    Args:
        data_quality: Dict with completeness and age_hours metrics
        has_meteo_data: Whether meteorological data is available
        has_cpcb_data: Whether CPCB data is available
        has_nasa_data: Whether NASA data is available
        has_dss_data: Whether DSS data is available
        
    Returns:
        Confidence level as percentage (0-100)
    """
    # Start with 100% confidence
    confidence = 100.0
    
    # Reduce based on data completeness
    completeness = data_quality.get("completeness", 0.0)
    confidence *= completeness
    
    # Reduce based on data age (older data = less confidence)
    age_hours = data_quality.get("age_hours", 0.0)
    if age_hours > 6:
        # Reduce confidence by 5% for each hour beyond 6 hours, up to 50% reduction
        age_penalty = min(0.5, (age_hours - 6) * 0.05)
        confidence *= (1.0 - age_penalty)
    
    # Reduce if meteorological data is missing
    if not has_meteo_data:
        confidence *= 0.7  # 30% reduction
    
    # Reduce if critical sensor data is missing
    if not has_cpcb_data:
        confidence *= 0.5  # 50% reduction (CPCB is critical)
    
    if not has_nasa_data:
        confidence *= 0.8  # 20% reduction
    
    if not has_dss_data:
        confidence *= 0.9  # 10% reduction
    
    # Ensure confidence is within valid range
    confidence = max(0.0, min(confidence, 100.0))
    
    return round(confidence, 1)


def _generate_reasoning(
    prediction_result: dict[str, Any],
    current_aqi: float | None,
    fire_count: int | None,
    avg_wind_speed_24h: float | None,
    stubble_burning_percent: float | None
) -> str:
    """
    Generate natural language reasoning statement for prediction.
    
    Args:
        prediction_result: Dict with prediction details
        current_aqi: Current AQI level
        fire_count: Fire count from NASA
        avg_wind_speed_24h: Average wind speed
        stubble_burning_percent: Stubble burning contribution
        
    Returns:
        Natural language reasoning statement in IF-AND-THEN format
    """
    prediction = prediction_result["prediction"]
    estimated_hours = prediction_result["estimated_hours"]
    aqi_category = prediction_result["aqi_category"]
    threshold = prediction_result["threshold"]
    
    # Build reasoning statement with specific values
    conditions = []
    
    if fire_count is not None:
        if fire_count > HIGH_FIRE_COUNT:
            conditions.append(f"SensorIngestAgent reports {fire_count} new fires (exceeding high threshold of {HIGH_FIRE_COUNT})")
        elif fire_count > MODERATE_FIRE_COUNT:
            conditions.append(f"SensorIngestAgent reports {fire_count} new fires (exceeding moderate threshold of {MODERATE_FIRE_COUNT})")
    
    if avg_wind_speed_24h is not None:
        if avg_wind_speed_24h < LOW_WIND_SPEED_KMH:
            conditions.append(f"meteorological data shows low wind speed ({avg_wind_speed_24h:.1f} km/h average over next 24h, below {LOW_WIND_SPEED_KMH} km/h threshold)")
        elif avg_wind_speed_24h < MODERATE_WIND_SPEED_KMH:
            conditions.append(f"meteorological data shows moderate wind speed ({avg_wind_speed_24h:.1f} km/h average over next 24h)")
        else:
            conditions.append(f"meteorological data shows favorable wind speed ({avg_wind_speed_24h:.1f} km/h average over next 24h)")
    
    if stubble_burning_percent is not None:
        if stubble_burning_percent >= HIGH_STUBBLE_PERCENT:
            conditions.append(f"DSS forecasts stubble burning's contribution will rise to {stubble_burning_percent:.0f}% (exceeding {HIGH_STUBBLE_PERCENT}% threshold)")
        elif stubble_burning_percent >= MODERATE_STUBBLE_PERCENT:
            conditions.append(f"DSS forecasts stubble burning's contribution at {stubble_burning_percent:.0f}%")
    
    if current_aqi is not None:
        conditions.append(f"current AQI is {current_aqi:.0f}")
    
    # Construct IF-AND-THEN statement
    if conditions:
        conditions_str = ", AND ".join(conditions)
        
        if threshold > 0 and estimated_hours > 0:
            reasoning = (f"IF {conditions_str}, "
                        f"THEN I predict the AQI will cross the '{aqi_category}' threshold ({threshold}) "
                        f"in approximately {estimated_hours} hours.")
        else:
            reasoning = f"IF {conditions_str}, THEN I predict {prediction.lower()}."
    else:
        reasoning = f"Based on available data, I predict {prediction.lower()}."
    
    return reasoning
