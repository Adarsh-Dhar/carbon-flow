"""
Centralized S3 Storage Layer for Respiro

Handles all S3 operations for patient data, FHIR documents, memory backups, and session logs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """Centralized S3 client for Respiro."""
    
    def __init__(self):
        settings = get_settings()
        self.bucket_name = settings.aws.s3_bucket_name
        self.region = settings.aws.region
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=settings.aws.access_key_id,
            aws_secret_access_key=settings.aws.secret_access_key
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError))
    )
    def upload_json(
        self,
        key: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload JSON data to S3.
        
        Args:
            key: S3 object key
            data: Data to upload (will be JSON serialized)
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        try:
            body = json.dumps(data, default=str, ensure_ascii=False)
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body.encode('utf-8'),
                ContentType='application/json',
                **extra_args
            )
            logger.info(f"Uploaded JSON to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload JSON to {key}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError))
    )
    def download_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse JSON from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            Parsed JSON data or None if not found
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Key not found in S3: {key}")
                return None
            logger.error(f"Failed to download JSON from {key}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {key}: {e}")
            raise
    
    def save_patient_data(self, patient_id: str, data: Dict[str, Any]) -> bool:
        """Save patient data to S3."""
        key = f"patients/{patient_id}/data.json"
        return self.upload_json(key, data, metadata={"patient_id": patient_id})
    
    def load_patient_data(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Load patient data from S3."""
        key = f"patients/{patient_id}/data.json"
        return self.download_json(key)
    
    def save_fhir_document(
        self,
        patient_id: str,
        resource_type: str,
        resource_id: str,
        fhir_resource: Dict[str, Any]
    ) -> bool:
        """Save FHIR resource to S3."""
        key = f"fhir/{patient_id}/{resource_type}/{resource_id}.json"
        metadata = {
            "patient_id": patient_id,
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        return self.upload_json(key, fhir_resource, metadata=metadata)
    
    def load_fhir_document(
        self,
        patient_id: str,
        resource_type: str,
        resource_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load FHIR resource from S3."""
        key = f"fhir/{patient_id}/{resource_type}/{resource_id}.json"
        return self.download_json(key)
    
    def save_memory_backup(self, patient_id: str, memory_data: Dict[str, Any]) -> bool:
        """Save vector memory backup to S3."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"memory-backups/{patient_id}/{timestamp}.json"
        metadata = {"patient_id": patient_id, "backup_timestamp": timestamp}
        return self.upload_json(key, memory_data, metadata=metadata)
    
    def save_session_log(self, session_id: str, log_data: Dict[str, Any]) -> bool:
        """Save session log to S3."""
        key = f"sessions/{session_id}/log.json"
        metadata = {"session_id": session_id}
        return self.upload_json(key, log_data, metadata=metadata)
    
    def list_patient_sessions(self, patient_id: str) -> List[str]:
        """List all session IDs for a patient."""
        prefix = f"sessions/{patient_id}/"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            sessions = []
            if 'CommonPrefixes' in response:
                for prefix_info in response['CommonPrefixes']:
                    session_id = prefix_info['Prefix'].split('/')[-2]
                    sessions.append(session_id)
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions for patient {patient_id}: {e}")
            return []
    
    def load_latest_session(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest session for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest session log data or None if not found
        """
        try:
            sessions = self.list_patient_sessions(patient_id)
            if not sessions:
                return None
            
            # Load all sessions and find the latest
            latest_session = None
            latest_timestamp = None
            
            for session_id in sessions:
                log_data = self.download_json(f"sessions/{session_id}/log.json")
                if log_data:
                    updated_at = log_data.get("updated_at") or log_data.get("created_at")
                    if updated_at:
                        try:
                            from datetime import datetime
                            session_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                            if latest_timestamp is None or session_time > latest_timestamp:
                                latest_timestamp = session_time
                                latest_session = log_data
                        except Exception:
                            continue
            
            return latest_session
        except Exception as e:
            logger.error(f"Failed to load latest session for patient {patient_id}: {e}")
            return None


# Global S3 client instance
_s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    """Get or create the global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client
