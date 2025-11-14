"""Data models and schemas for ForecastAgent.

This module defines dataclasses for sensor data, meteorological forecasts,
and prediction outputs used throughout the ForecastAgent system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CPCBData:
    """CPCB (Central Pollution Control Board) air quality data.
    
    Attributes:
        aqi: Air Quality Index value (0-500+)
        timestamp: When the measurement was taken
        station: Name of the monitoring station
        pm25: PM2.5 concentration in µg/m³ (optional)
        pm10: PM10 concentration in µg/m³ (optional)
    """
    aqi: float
    timestamp: datetime
    station: str
    pm25: float | None = None
    pm10: float | None = None
    
    def validate(self) -> bool:
        """Validate required fields are present and valid.
        
        Returns:
            True if all required fields are valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.aqi < 0:
            raise ValueError(f"AQI must be non-negative, got {self.aqi}")
        if not self.station:
            raise ValueError("Station name cannot be empty")
        if self.pm25 is not None and self.pm25 < 0:
            raise ValueError(f"PM2.5 must be non-negative, got {self.pm25}")
        if self.pm10 is not None and self.pm10 < 0:
            raise ValueError(f"PM10 must be non-negative, got {self.pm10}")
        return True


@dataclass
class NASAFireData:
    """NASA FIRMS fire detection data.
    
    Attributes:
        fire_count: Number of fires detected
        region: Geographic region of fire detection
        timestamp: When the data was collected
        confidence_high: Number of high-confidence fire detections (optional)
    """
    fire_count: int
    region: str
    timestamp: datetime
    confidence_high: int | None = None
    
    def validate(self) -> bool:
        """Validate required fields are present and valid.
        
        Returns:
            True if all required fields are valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.fire_count < 0:
            raise ValueError(f"Fire count must be non-negative, got {self.fire_count}")
        if not self.region:
            raise ValueError("Region cannot be empty")
        if self.confidence_high is not None and self.confidence_high < 0:
            raise ValueError(f"Confidence high must be non-negative, got {self.confidence_high}")
        if self.confidence_high is not None and self.confidence_high > self.fire_count:
            raise ValueError(f"Confidence high ({self.confidence_high}) cannot exceed fire count ({self.fire_count})")
        return True


@dataclass
class DSSData:
    """DSS (Decision Support System) pollution source attribution data.
    
    Attributes:
        stubble_burning_percent: Percentage contribution from stubble burning
        vehicular_percent: Percentage contribution from vehicles
        industrial_percent: Percentage contribution from industry
        dust_percent: Percentage contribution from dust (optional)
        timestamp: When the data was generated
    """
    stubble_burning_percent: float
    vehicular_percent: float
    industrial_percent: float
    timestamp: datetime
    dust_percent: float | None = None
    
    def validate(self) -> bool:
        """Validate required fields are present and valid.
        
        Returns:
            True if all required fields are valid
            
        Raises:
            ValueError: If validation fails
        """
        if not (0 <= self.stubble_burning_percent <= 100):
            raise ValueError(f"Stubble burning percent must be 0-100, got {self.stubble_burning_percent}")
        if not (0 <= self.vehicular_percent <= 100):
            raise ValueError(f"Vehicular percent must be 0-100, got {self.vehicular_percent}")
        if not (0 <= self.industrial_percent <= 100):
            raise ValueError(f"Industrial percent must be 0-100, got {self.industrial_percent}")
        if self.dust_percent is not None and not (0 <= self.dust_percent <= 100):
            raise ValueError(f"Dust percent must be 0-100, got {self.dust_percent}")
        return True


@dataclass
class SensorData:
    """Combined sensor data from all sources.
    
    Attributes:
        cpcb: CPCB air quality data
        nasa: NASA fire detection data
        dss: DSS source attribution data
        data_quality: Dictionary containing quality metrics (completeness, age_hours)
    """
    cpcb: CPCBData
    nasa: NASAFireData
    dss: DSSData
    data_quality: dict[str, float]
    
    def validate(self) -> bool:
        """Validate all sensor data components.
        
        Returns:
            True if all components are valid
            
        Raises:
            ValueError: If validation fails
        """
        self.cpcb.validate()
        self.nasa.validate()
        self.dss.validate()
        
        if 'completeness' not in self.data_quality:
            raise ValueError("data_quality must contain 'completeness' key")
        if 'age_hours' not in self.data_quality:
            raise ValueError("data_quality must contain 'age_hours' key")
        
        completeness = self.data_quality['completeness']
        if not (0 <= completeness <= 1):
            raise ValueError(f"Completeness must be 0-1, got {completeness}")
        
        age_hours = self.data_quality['age_hours']
        if age_hours < 0:
            raise ValueError(f"Age hours must be non-negative, got {age_hours}")
        
        return True


@dataclass
class HourlyWindSpeed:
    """Hourly wind speed forecast data point.
    
    Attributes:
        timestamp: Time of the forecast
        wind_speed_kmh: Wind speed in kilometers per hour
    """
    timestamp: datetime
    wind_speed_kmh: float
    
    def validate(self) -> bool:
        """Validate wind speed data.
        
        Returns:
            True if data is valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.wind_speed_kmh < 0:
            raise ValueError(f"Wind speed must be non-negative, got {self.wind_speed_kmh}")
        return True


@dataclass
class MeteorologicalForecast:
    """Meteorological forecast data.
    
    Attributes:
        hourly_wind_speed: List of hourly wind speed forecasts
        location: Dictionary containing location information (latitude, longitude, city)
        forecast_retrieved_at: When the forecast was retrieved
    """
    hourly_wind_speed: list[HourlyWindSpeed]
    location: dict[str, float | str]
    forecast_retrieved_at: datetime
    
    def validate(self) -> bool:
        """Validate meteorological forecast data.
        
        Returns:
            True if all data is valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.hourly_wind_speed:
            raise ValueError("hourly_wind_speed cannot be empty")
        
        for wind_data in self.hourly_wind_speed:
            wind_data.validate()
        
        required_location_keys = {'latitude', 'longitude', 'city'}
        if not required_location_keys.issubset(self.location.keys()):
            raise ValueError(f"location must contain keys: {required_location_keys}")
        
        return True


@dataclass
class AQIPrediction:
    """Air Quality Index prediction.
    
    Attributes:
        aqi_category: Predicted AQI category (e.g., "Severe", "Very Poor")
        threshold: AQI threshold value
        estimated_hours_to_threshold: Estimated hours until threshold is reached
    """
    aqi_category: str
    threshold: int
    estimated_hours_to_threshold: int
    
    def validate(self) -> bool:
        """Validate AQI prediction data.
        
        Returns:
            True if data is valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.aqi_category:
            raise ValueError("aqi_category cannot be empty")
        if self.threshold < 0:
            raise ValueError(f"Threshold must be non-negative, got {self.threshold}")
        if self.estimated_hours_to_threshold < 0:
            raise ValueError(f"Estimated hours must be non-negative, got {self.estimated_hours_to_threshold}")
        return True


@dataclass
class ForecastOutput:
    """Complete forecast output structure.
    
    Attributes:
        prediction: AQI prediction details
        confidence_level: Confidence level (0-100)
        reasoning: Natural language explanation of the prediction
        timestamp: When the forecast was generated
        data_sources: Dictionary containing metadata about data sources
    """
    prediction: AQIPrediction
    confidence_level: float
    reasoning: str
    timestamp: datetime
    data_sources: dict[str, any]
    
    def validate(self) -> bool:
        """Validate forecast output data.
        
        Returns:
            True if all data is valid
            
        Raises:
            ValueError: If validation fails
        """
        self.prediction.validate()
        
        if not (0 <= self.confidence_level <= 100):
            raise ValueError(f"Confidence level must be 0-100, got {self.confidence_level}")
        
        if not self.reasoning:
            raise ValueError("Reasoning cannot be empty")
        
        if not self.data_sources:
            raise ValueError("data_sources cannot be empty")
        
        return True
