import os
from typing import Optional

from dotenv import load_dotenv

# Default OpenAI-compatible endpoint for Gemini models.
_GEMINI_OPENAI_COMPAT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _get_env(name: str) -> Optional[str]:
    """Helper for mypy and to keep os.getenv lookups consistent."""
    return os.getenv(name)


def get_s3_bucket_name() -> str:
    """
    Get the S3 bucket name for reading ingested sensor data.
    
    Returns:
        S3 bucket name from environment
        
    Raises:
        ValueError: If S3_BUCKET_NAME is not set
    """
    bucket_name = _get_env("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is required")
    return bucket_name


def get_forecast_output_dir() -> str:
    """
    Get the output directory for forecast JSON files.
    
    Returns:
        Output directory path (defaults to 'forecast-agent/output')
    """
    return _get_env("FORECAST_OUTPUT_DIR") or "forecast-agent/output"


def get_forecast_upload_to_s3() -> bool:
    """
    Check if forecast outputs should be uploaded to S3.
    
    Returns:
        True if FORECAST_UPLOAD_TO_S3 is set to 'true', False otherwise
    """
    upload_flag = _get_env("FORECAST_UPLOAD_TO_S3")
    return upload_flag is not None and upload_flag.lower() in ("true", "1", "yes")


def get_aws_region() -> str:
    """
    Get the AWS region for S3 operations.
    
    Returns:
        AWS region (defaults to 'ap-south-1' for Delhi)
    """
    return _get_env("AWS_DEFAULT_REGION") or "ap-south-1"


def validate_required_env_vars() -> None:
    """
    Validate that all required environment variables are set.
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    load_dotenv()
    
    required_vars = {
        "GEMINI_API_KEY": "Google Gemini API key for LLM",
        "S3_BUCKET_NAME": "AWS S3 bucket name for sensor data",
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not _get_env(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables:\n" + "\n".join(f"  - {var}" for var in missing_vars)
        )


def configure_llm_from_env() -> None:
    """
    Configure CrewAI's underlying LLM provider, allowing Gemini keys to stand in for OpenAI.

    CrewAI currently expects an OpenAI-compatible API by default. Gemini 1.5+ exposes an
    OpenAI-compatible endpoint, so when a user only provides ``GEMINI_API_KEY`` we wire it up
    to the expected ``OPENAI_*`` environment variables.
    """
    # Load .env once at startup to populate the process environment.
    load_dotenv()

    openai_key = _get_env("OPENAI_API_KEY")
    gemini_key = _get_env("GEMINI_API_KEY")

    if not openai_key and gemini_key:
        # Re-map Gemini credentials into the OpenAI-compatible environment variables.
        os.environ["OPENAI_API_KEY"] = gemini_key

        # Respect any user-provided override while falling back to Google's compatibility URL.
        base_url = _get_env("OPENAI_BASE_URL") or _GEMINI_OPENAI_COMPAT_BASE_URL
        os.environ["OPENAI_BASE_URL"] = base_url

        # CrewAI also checks for this alias in some versions, so set it for completeness.
        os.environ.setdefault("OPENAI_API_BASE", base_url)

        # Select a Gemini model that is available through the OpenAI-compatible endpoint.
        gemini_model = (
            _get_env("GEMINI_MODEL_NAME")
            or _get_env("MODEL")
            or _get_env("MODEL_NAME")
            or _get_env("OPENAI_MODEL_NAME")
            or "gemini-2.0-flash"
        )

        # Ensure CrewAI picks up the Gemini model instead of its OpenAI default.
        os.environ["OPENAI_MODEL_NAME"] = gemini_model
        os.environ.setdefault("MODEL_NAME", gemini_model)
        os.environ.setdefault("MODEL", gemini_model)

    # If neither key is supplied, leave error handling to CrewAI so the user sees the standard message.

