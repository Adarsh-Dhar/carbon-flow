"""
Centralized Configuration Management for Respiro

Validates and provides access to all configuration settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class AWSSettings(BaseSettings):
    """AWS configuration."""
    model_config = {"env_prefix": ""}
    
    region: str = Field(default="us-east-1")
    access_key_id: Optional[str] = Field(default=None)
    secret_access_key: Optional[str] = Field(default=None)
    s3_bucket_name: str = Field(default="respiro-data-bucket")


class BedrockSettings(BaseSettings):
    """Amazon Bedrock configuration."""
    model_config = {"env_prefix": ""}
    
    region: str = Field(default="us-east-1")
    model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")


class GoogleCalendarSettings(BaseSettings):
    """Google Calendar integration settings."""
    model_config = {"env_prefix": ""}
    
    client_id: str = Field(...)
    client_secret: str = Field(...)
    refresh_token: Optional[str] = Field(default=None)
    redirect_uri: str = Field(default="http://localhost:3000/auth/callback")


class HealthKitSettings(BaseSettings):
    """HealthKit/Fitbit integration settings."""
    model_config = {"env_prefix": ""}
    
    healthkit_api_key: Optional[str] = Field(default=None)
    fitbit_client_id: Optional[str] = Field(default=None)
    fitbit_client_secret: Optional[str] = Field(default=None)
    fitbit_access_token: Optional[str] = Field(default=None)
    fitbit_refresh_token: Optional[str] = Field(default=None)


class IoTSettings(BaseSettings):
    """AWS IoT Core settings."""
    model_config = {"env_prefix": ""}
    
    endpoint: str = Field(...)
    thing_name: str = Field(default="respiro-smart-home-device")
    root_ca_path: Optional[str] = Field(default=None)
    certificate_path: Optional[str] = Field(default=None)
    private_key_path: Optional[str] = Field(default=None)


class VectorDBSettings(BaseSettings):
    """Vector database configuration."""
    model_config = {"env_prefix": ""}
    
    db_path: str = Field(default="./respiro/memory/chroma_db")
    backup_s3_prefix: str = Field(default="memory-backups/")


class OpenAISettings(BaseSettings):
    """OpenAI configuration for embeddings."""
    model_config = {"env_prefix": ""}
    
    api_key: str = Field(...)
    model: str = Field(default="text-embedding-3-small")


class FHIRSettings(BaseSettings):
    """FHIR server configuration."""
    model_config = {"env_prefix": ""}
    
    server_url: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)


class APISettings(BaseSettings):
    """External API keys."""
    model_config = {"env_prefix": ""}
    
    google_aqi_api_key: Optional[str] = Field(default=None)
    ambee_api_key: Optional[str] = Field(default=None)
    insurance_api_base_url: Optional[str] = Field(default=None)
    insurance_api_key: Optional[str] = Field(default=None)
    pharmacy_api_base_url: Optional[str] = Field(default=None)
    pharmacy_api_key: Optional[str] = Field(default=None)
    google_maps_api_key: Optional[str] = Field(default=None)


class AppSettings(BaseSettings):
    """Application configuration."""
    model_config = {"env_prefix": ""}
    
    api_server_host: str = Field(default="localhost")
    api_server_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    session_timeout_seconds: int = Field(default=3600)
    max_context_history: int = Field(default=100)
    human_approval_timeout_seconds: int = Field(default=300)
    require_approval_for_critical_actions: bool = Field(default=True)
    max_retries: int = Field(default=3)
    retry_backoff_base_seconds: float = Field(default=1.0)


class RespiroSettings:
    """Main settings class that aggregates all configuration."""
    
    def __init__(self):
        # Load from environment with proper prefixes
        import os
        self.aws = AWSSettings(
            region=os.getenv("AWS_REGION", "us-east-1"),
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            s3_bucket_name=os.getenv("S3_BUCKET_NAME", "respiro-data-bucket")
        )
        self.bedrock = BedrockSettings(
            region=os.getenv("AWS_BEDROCK_REGION", "us-east-1"),
            model_id=os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        )
        self.google_calendar = GoogleCalendarSettings(
            client_id=os.getenv("GOOGLE_CALENDAR_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", ""),
            refresh_token=os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN"),
            redirect_uri=os.getenv("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:3000/auth/callback")
        )
        self.healthkit = HealthKitSettings(
            healthkit_api_key=os.getenv("HEALTHKIT_API_KEY"),
            fitbit_client_id=os.getenv("FITBIT_CLIENT_ID"),
            fitbit_client_secret=os.getenv("FITBIT_CLIENT_SECRET"),
            fitbit_access_token=os.getenv("FITBIT_ACCESS_TOKEN"),
            fitbit_refresh_token=os.getenv("FITBIT_REFRESH_TOKEN")
        )
        self.iot = IoTSettings(
            endpoint=os.getenv("AWS_IOT_ENDPOINT", ""),
            thing_name=os.getenv("AWS_IOT_THING_NAME", "respiro-smart-home-device"),
            root_ca_path=os.getenv("AWS_IOT_ROOT_CA_PATH"),
            certificate_path=os.getenv("AWS_IOT_CERTIFICATE_PATH"),
            private_key_path=os.getenv("AWS_IOT_PRIVATE_KEY_PATH")
        )
        self.vector_db = VectorDBSettings(
            db_path=os.getenv("VECTOR_DB_PATH", "./respiro/memory/chroma_db"),
            backup_s3_prefix=os.getenv("VECTOR_DB_BACKUP_S3_PREFIX", "memory-backups/")
        )
        self.openai = OpenAISettings(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "text-embedding-3-small")
        )
        self.fhir = FHIRSettings(
            server_url=os.getenv("FHIR_SERVER_URL"),
            api_key=os.getenv("FHIR_SERVER_API_KEY")
        )
        self.api = APISettings(
            google_aqi_api_key=os.getenv("GOOGLE_AQI_API_KEY"),
            ambee_api_key=os.getenv("AMBEE_API_KEY"),
            insurance_api_base_url=os.getenv("INSURANCE_API_BASE_URL"),
            insurance_api_key=os.getenv("INSURANCE_API_KEY"),
            pharmacy_api_base_url=os.getenv("PHARMACY_API_BASE_URL"),
            pharmacy_api_key=os.getenv("PHARMACY_API_KEY"),
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY")
        )
        self.app = AppSettings(
            api_server_host=os.getenv("API_SERVER_HOST", "localhost"),
            api_server_port=int(os.getenv("API_SERVER_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            environment=os.getenv("ENVIRONMENT", "development"),
            session_timeout_seconds=int(os.getenv("SESSION_TIMEOUT_SECONDS", "3600")),
            max_context_history=int(os.getenv("MAX_CONTEXT_HISTORY", "100")),
            human_approval_timeout_seconds=int(os.getenv("HUMAN_APPROVAL_TIMEOUT_SECONDS", "300")),
            require_approval_for_critical_actions=os.getenv("REQUIRE_APPROVAL_FOR_CRITICAL_ACTIONS", "true").lower() == "true",
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_base_seconds=float(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "1.0"))
        )
    
    def validate(self) -> list[str]:
        """
        Validate all required settings are present.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required settings
        if not self.google_calendar.client_id:
            errors.append("GOOGLE_CALENDAR_CLIENT_ID is required")
        if not self.google_calendar.client_secret:
            errors.append("GOOGLE_CALENDAR_CLIENT_SECRET is required")
        if not self.iot.endpoint:
            errors.append("AWS_IOT_ENDPOINT is required")
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        
        return errors


# Global settings instance
_settings: Optional[RespiroSettings] = None


def get_settings() -> RespiroSettings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = RespiroSettings()
    return _settings


def validate_settings() -> None:
    """Validate settings and raise ValueError if invalid."""
    settings = get_settings()
    errors = settings.validate()
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
