"""
FHIR Resource Models for Respiro

Defines FHIR-compliant data models for asthma management.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from fhir.resources.careplan import CarePlan, CarePlanActivity
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.reference import Reference


def create_careplan(
    patient_id: str,
    title: str,
    description: str,
    activities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create a FHIR CarePlan resource.
    
    Args:
        patient_id: Patient identifier
        title: Care plan title
        description: Care plan description
        activities: List of activity definitions
        
    Returns:
        CarePlan resource as dict
    """
    careplan = CarePlan(
        status="active",
        intent="plan",
        title=title,
        description=description,
        subject=Reference(reference=f"Patient/{patient_id}"),
        period={
            "start": datetime.utcnow().isoformat()
        },
        activity=[CarePlanActivity(**activity) for activity in activities]
    )
    
    return careplan.dict()


def create_condition(
    patient_id: str,
    code: str,
    display: str,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a FHIR Condition resource.
    
    Args:
        patient_id: Patient identifier
        code: Condition code (e.g., "J45" for asthma)
        display: Human-readable display
        severity: Optional severity
        
    Returns:
        Condition resource as dict
    """
    condition = Condition(
        clinicalStatus={
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
            }]
        },
        verificationStatus={
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed",
                "display": "Confirmed"
            }]
        },
        code={
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": code,
                "display": display
            }]
        },
        subject=Reference(reference=f"Patient/{patient_id}"),
        onsetDateTime=datetime.utcnow().isoformat()
    )
    
    if severity:
        condition.severity = {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": severity,
                "display": severity
            }]
        }
    
    return condition.dict()


def create_medication_statement(
    patient_id: str,
    medication_code: str,
    medication_display: str,
    dosage: str,
    frequency: str,
    status: str = "active"
) -> Dict[str, Any]:
    """
    Create a FHIR MedicationStatement resource.
    
    Args:
        patient_id: Patient identifier
        medication_code: Medication code
        medication_display: Human-readable medication name
        dosage: Dosage instructions
        frequency: Frequency of administration
        status: Medication status
        
    Returns:
        MedicationStatement resource as dict
    """
    medication = MedicationStatement(
        status=status,
        medicationCodeableConcept={
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": medication_code,
                "display": medication_display
            }]
        },
        subject=Reference(reference=f"Patient/{patient_id}"),
        dosage=[{
            "text": dosage,
            "timing": {
                "repeat": {
                    "frequency": 1,
                    "period": 1,
                    "periodUnit": frequency
                }
            }
        }]
    )
    
    return medication.dict()


def create_observation(
    patient_id: str,
    code: str,
    display: str,
    value: Any,
    unit: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a FHIR Observation resource.
    
    Args:
        patient_id: Patient identifier
        code: Observation code (LOINC)
        display: Human-readable display
        value: Observation value
        unit: Optional unit
        
    Returns:
        Observation resource as dict
    """
    observation = Observation(
        status="final",
        code={
            "coding": [{
                "system": "http://loinc.org",
                "code": code,
                "display": display
            }]
        },
        subject=Reference(reference=f"Patient/{patient_id}"),
        effectiveDateTime=datetime.utcnow().isoformat(),
        valueQuantity={
            "value": value,
            "unit": unit or "",
            "system": "http://unitsofmeasure.org",
            "code": unit or ""
        } if isinstance(value, (int, float)) else {
            "valueString": str(value)
        }
    )
    
    return observation.dict()


def load_asthma_action_plan(careplan_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load and parse an Asthma Action Plan from FHIR CarePlan.
    
    Args:
        careplan_data: CarePlan resource data
        
    Returns:
        Parsed action plan with zones and instructions
    """
    activities = careplan_data.get("activity", [])
    
    zones = {
        "green": {"triggers": [], "actions": []},
        "yellow": {"triggers": [], "actions": []},
        "red": {"triggers": [], "actions": []}
    }
    
    for activity in activities:
        detail = activity.get("detail", {})
        kind = detail.get("kind", "")
        code = detail.get("code", {})
        coding = code.get("coding", [{}])[0] if code.get("coding") else {}
        display = coding.get("display", "")
        
        # Parse zone from activity
        if "green" in display.lower() or "green" in kind.lower():
            zones["green"]["actions"].append(display)
        elif "yellow" in display.lower() or "yellow" in kind.lower():
            zones["yellow"]["actions"].append(display)
        elif "red" in display.lower() or "red" in kind.lower():
            zones["red"]["actions"].append(display)
    
    return {
        "title": careplan_data.get("title", "Asthma Action Plan"),
        "description": careplan_data.get("description", ""),
        "zones": zones,
        "status": careplan_data.get("status", "active")
    }
