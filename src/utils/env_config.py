import os
from typing import Optional

from dotenv import load_dotenv

# Default OpenAI-compatible endpoint for Gemini models.
_GEMINI_OPENAI_COMPAT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _get_env(name: str) -> Optional[str]:
    """Helper for mypy and to keep os.getenv lookups consistent."""
    return os.getenv(name)


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

