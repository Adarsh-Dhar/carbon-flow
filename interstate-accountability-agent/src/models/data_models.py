"""
Data models for InterState-AccountabilityAgent.

Defines Pydantic models for border stations, fire events, correlation results,
legal citations, and CAQM reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BorderStation(BaseModel):
    """Model for a border monitoring station with surge detection."""
    
    name: str = Field(description="Station name")
    latitude: float = Field(description="Station latitude")
    longitude: float = Field(description="Station longitude")
    border: str = Field(description="Adjacent state/province")
    district: str = Field(description="Delhi district")
    aqi: float | None = Field(default=None, description="Current AQI reading")
    pm25: float | None = Field(default=None, description="PM2.5 concentration")
    pm10: float | None = Field(default=None, description="PM10 concentration")
    timestamp: str | None = Field(default=None, description="Data timestamp")
    is_surge: bool = Field(default=False, description="Whether this station has a surge")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BorderStation:
        """Create from dictionary."""
        return cls(**data)


class FireEvent(BaseModel):
    """Model for a NASA FIRMS fire event."""
    
    latitude: float = Field(description="Fire latitude")
    longitude: float = Field(description="Fire longitude")
    brightness: float | None = Field(default=None, description="Fire brightness temperature")
    confidence: float | None = Field(default=None, description="Fire detection confidence")
    acq_date: str | None = Field(default=None, description="Acquisition date")
    acq_time: str | None = Field(default=None, description="Acquisition time")
    state: str | None = Field(default=None, description="State where fire occurred")
    district: str | None = Field(default=None, description="District where fire occurred")
    distance_km: float | None = Field(default=None, description="Distance to border station in km")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FireEvent:
        """Create from dictionary."""
        return cls(**data)


class CorrelationResult(BaseModel):
    """Model for fire correlation analysis results."""
    
    state: str = Field(description="State name")
    fire_count: int = Field(description="Number of fires in this state")
    districts: list[str] = Field(default_factory=list, description="Districts with fires")
    avg_distance_km: float = Field(description="Average distance to border station in km")
    is_high_contribution: bool = Field(default=False, description="Whether this state has high contribution")
    fire_events: list[FireEvent] = Field(default_factory=list, description="List of fire events")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = self.dict()
        result["fire_events"] = [fe.to_dict() for fe in self.fire_events]
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorrelationResult:
        """Create from dictionary."""
        fire_events_data = data.pop("fire_events", [])
        fire_events = [FireEvent.from_dict(fe) if isinstance(fe, dict) else fe for fe in fire_events_data]
        data["fire_events"] = fire_events
        return cls(**data)


class LegalCitations(BaseModel):
    """Model for legal citations in CAQM reports."""
    
    caqm_direction: str = Field(
        default="CAQM Direction No. 95",
        description="CAQM Direction reference"
    )
    enforcement_authority: str = Field(
        default="Section 12 of the CAQM Act, 2021",
        description="Enforcement authority reference"
    )
    enforcement_request: str = Field(
        default="Requesting immediate enforcement action as per Section 12 of the CAQM Act.",
        description="Enforcement request statement"
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalCitations:
        """Create from dictionary."""
        return cls(**data)


class CAQMReport(BaseModel):
    """Model for a complete CAQM accountability report."""
    
    report_id: str = Field(description="Unique report ID")
    timestamp: str = Field(description="Report generation timestamp")
    executive_summary: str = Field(description="Executive summary of the report")
    surge_details: dict[str, Any] = Field(default_factory=dict, description="Surge station details")
    fire_correlation: dict[str, Any] = Field(default_factory=dict, description="Fire correlation analysis")
    stubble_burning_percent: float | None = Field(default=None, description="Stubble burning contribution percentage")
    reasoning: str = Field(description="IF-AND-THEN reasoning statement")
    confidence_score: float = Field(description="Confidence score (30.0-100.0)")
    data_quality: dict[str, Any] = Field(default_factory=dict, description="Data quality assessment")
    legal_citations: LegalCitations = Field(description="Legal citations")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations list")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = self.dict()
        if isinstance(result.get("legal_citations"), LegalCitations):
            result["legal_citations"] = result["legal_citations"].to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CAQMReport:
        """Create from dictionary."""
        legal_citations_data = data.get("legal_citations", {})
        if isinstance(legal_citations_data, dict):
            data["legal_citations"] = LegalCitations.from_dict(legal_citations_data)
        return cls(**data)

