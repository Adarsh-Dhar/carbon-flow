"""
FHIR Tools for Respiro

Tools for reading and writing FHIR resources to/from S3.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime

from respiro.storage.s3_client import get_s3_client
from respiro.models.fhir_models import (
    create_careplan,
    create_condition,
    create_medication_statement,
    create_observation,
    load_asthma_action_plan
)
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class FHIRTools:
    """Tools for FHIR resource management."""
    
    def __init__(self):
        self.s3_client = get_s3_client()
    
    def save_careplan(
        self,
        patient_id: str,
        careplan_id: str,
        careplan_data: Dict[str, Any]
    ) -> bool:
        """Save CarePlan to S3."""
        return self.s3_client.save_fhir_document(
            patient_id, "CarePlan", careplan_id, careplan_data
        )
    
    def load_careplan(
        self,
        patient_id: str,
        careplan_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load CarePlan from S3."""
        return self.s3_client.load_fhir_document(
            patient_id, "CarePlan", careplan_id
        )
    
    def get_patient_careplans(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all CarePlans for a patient."""
        # This would require listing S3 objects - simplified for now
        # In production, maintain an index
        return []
    
    def save_condition(
        self,
        patient_id: str,
        condition_id: str,
        condition_data: Dict[str, Any]
    ) -> bool:
        """Save Condition to S3."""
        return self.s3_client.save_fhir_document(
            patient_id, "Condition", condition_id, condition_data
        )
    
    def load_condition(
        self,
        patient_id: str,
        condition_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load Condition from S3."""
        return self.s3_client.load_fhir_document(
            patient_id, "Condition", condition_id
        )
    
    def save_medication_statement(
        self,
        patient_id: str,
        medication_id: str,
        medication_data: Dict[str, Any]
    ) -> bool:
        """Save MedicationStatement to S3."""
        return self.s3_client.save_fhir_document(
            patient_id, "MedicationStatement", medication_id, medication_data
        )
    
    def load_medication_statement(
        self,
        patient_id: str,
        medication_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load MedicationStatement from S3."""
        return self.s3_client.load_fhir_document(
            patient_id, "MedicationStatement", medication_id
        )
    
    def get_patient_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all active medications for a patient."""
        # Simplified - in production, maintain an index
        return []
    
    def save_observation(
        self,
        patient_id: str,
        observation_id: str,
        observation_data: Dict[str, Any]
    ) -> bool:
        """Save Observation to S3."""
        return self.s3_client.save_fhir_document(
            patient_id, "Observation", observation_id, observation_data
        )
    
    def create_default_asthma_action_plan(
        self,
        patient_id: str
    ) -> Dict[str, Any]:
        """
        Create a default Asthma Action Plan if none exists.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            CarePlan resource
        """
        activities = [
            {
                "detail": {
                    "kind": "ServiceRequest",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "green-zone",
                            "display": "Green Zone: Continue daily controller medication"
                        }]
                    }
                }
            },
            {
                "detail": {
                    "kind": "ServiceRequest",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "yellow-zone",
                            "display": "Yellow Zone: Increase rescue medication, monitor symptoms"
                        }]
                    }
                }
            },
            {
                "detail": {
                    "kind": "ServiceRequest",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "red-zone",
                            "display": "Red Zone: Seek immediate medical attention"
                        }]
                    }
                }
            }
        ]
        
        careplan = create_careplan(
            patient_id=patient_id,
            title="Asthma Action Plan",
            description="Standard asthma action plan with Green/Yellow/Red zones",
            activities=activities
        )
        
        # Save to S3
        careplan_id = f"asthma-action-plan-{patient_id}"
        self.save_careplan(patient_id, careplan_id, careplan)
        
        return careplan
