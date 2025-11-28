"""
Trigger Detection for Sentry Agent

Pattern matching and risk scoring for asthma triggers.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime

from respiro.orchestrator.state import RiskLevel
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class TriggerDetector:
    """Detects asthma triggers from sensor data."""
    
    # Thresholds for trigger detection
    AQI_SEVERE_THRESHOLD = 300
    AQI_HIGH_THRESHOLD = 200
    AQI_MODERATE_THRESHOLD = 100
    
    POLLEN_HIGH_THRESHOLD = 7  # On scale of 0-12
    POLLEN_MODERATE_THRESHOLD = 4
    
    HEART_RATE_ELEVATED_MULTIPLIER = 1.3  # 30% above baseline
    RESPIRATORY_RATE_HIGH = 25  # breaths per minute
    OXYGEN_SATURATION_LOW = 95  # percentage
    
    def detect_triggers(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect asthma triggers from fused sensor data.
        
        Args:
            sensor_data: Fused sensor data
            
        Returns:
            Trigger detection results with risk score and factors
        """
        risk_factors = []
        risk_score = 0.0
        
        # Check air quality
        aqi = sensor_data.get("air_quality", {}).get("aqi", 0)
        if aqi >= self.AQI_SEVERE_THRESHOLD:
            risk_factors.append(f"Severe air quality (AQI: {aqi})")
            risk_score += 0.4
        elif aqi >= self.AQI_HIGH_THRESHOLD:
            risk_factors.append(f"High air quality (AQI: {aqi})")
            risk_score += 0.3
        elif aqi >= self.AQI_MODERATE_THRESHOLD:
            risk_factors.append(f"Moderate air quality (AQI: {aqi})")
            risk_score += 0.15
        
        # Check pollutants
        pollutants = sensor_data.get("air_quality", {}).get("pollutants", {})
        for code, data in pollutants.items():
            value = data.get("value", 0)
            if code == "PM2.5" and value > 55:
                risk_factors.append(f"High PM2.5 ({value} μg/m³)")
                risk_score += 0.2
            elif code == "PM10" and value > 155:
                risk_factors.append(f"High PM10 ({value} μg/m³)")
                risk_score += 0.15
            elif code == "O3" and value > 0.17:
                risk_factors.append(f"High Ozone ({value} ppm)")
                risk_score += 0.15
        
        # Check pollen
        pollen_risk = sensor_data.get("pollen", {}).get("overall_risk", "Unknown")
        tree_pollen = sensor_data.get("pollen", {}).get("tree_pollen", 0)
        grass_pollen = sensor_data.get("pollen", {}).get("grass_pollen", 0)
        weed_pollen = sensor_data.get("pollen", {}).get("weed_pollen", 0)
        
        total_pollen = tree_pollen + grass_pollen + weed_pollen
        if total_pollen >= self.POLLEN_HIGH_THRESHOLD:
            risk_factors.append(f"High pollen levels ({total_pollen})")
            risk_score += 0.25
        elif total_pollen >= self.POLLEN_MODERATE_THRESHOLD:
            risk_factors.append(f"Moderate pollen levels ({total_pollen})")
            risk_score += 0.15
        
        # Check biometrics
        biometrics = sensor_data.get("biometrics", {})
        heart_rate = biometrics.get("heart_rate", 0)
        respiratory_rate = biometrics.get("respiratory_rate", 0)
        oxygen_saturation = biometrics.get("oxygen_saturation", 0)
        peak_flow = biometrics.get("peak_flow", 0)
        
        # Elevated heart rate (assuming baseline of 70)
        if heart_rate > 70 * self.HEART_RATE_ELEVATED_MULTIPLIER:
            risk_factors.append(f"Elevated heart rate ({heart_rate} bpm)")
            risk_score += 0.15
        
        # High respiratory rate
        if respiratory_rate > self.RESPIRATORY_RATE_HIGH:
            risk_factors.append(f"High respiratory rate ({respiratory_rate} bpm)")
            risk_score += 0.2
        
        # Low oxygen saturation
        if oxygen_saturation > 0 and oxygen_saturation < self.OXYGEN_SATURATION_LOW:
            risk_factors.append(f"Low oxygen saturation ({oxygen_saturation}%)")
            risk_score += 0.3
        
        # Low peak flow (assuming normal is 400-600 L/min)
        if peak_flow > 0 and peak_flow < 300:
            risk_factors.append(f"Low peak flow ({peak_flow} L/min)")
            risk_score += 0.25
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = RiskLevel.SEVERE
        elif risk_score >= 0.5:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "timestamp": datetime.utcnow().isoformat()
        }
