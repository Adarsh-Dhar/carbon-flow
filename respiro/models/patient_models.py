"""Pydantic models for patient data."""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class PatientProfile(BaseModel):
    patient_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[Dict[str, float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SessionData(BaseModel):
    session_id: str
    patient_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    state: Dict[str, Any] = {}

class AgentState(BaseModel):
    agent_name: str
    status: str
    last_execution: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
