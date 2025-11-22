from crewai import Agent
from crewai.tools.base_tool import Tool

try:
    from pydantic import BaseModel, ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic < 2
    from pydantic import BaseModel

    ConfigDict = None
from typing import Any, Callable
from datetime import datetime

from src.tools import cpcb_tools, nasa_tools, dss_tools, storage_tools
from src.utils.env_config import configure_llm_from_env

configure_llm_from_env()

TOOL_RESULT_CACHE: dict[str, Any] = {}


def _with_debug_logs(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap tool functions with debug logging for inputs and outputs."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Ensure TOOL_RESULT_CACHE is always a dict
        global TOOL_RESULT_CACHE
        if TOOL_RESULT_CACHE is None or not isinstance(TOOL_RESULT_CACHE, dict):
            TOOL_RESULT_CACHE = {}
        
        timestamp = datetime.utcnow().isoformat()
        debug_kwargs = dict(kwargs)
        security_context = debug_kwargs.pop("security_context", None)
        print(
            f"[DEBUG {timestamp}] Tool `{tool_name}` invoked "
            f"with args={args} kwargs={debug_kwargs} security_context={security_context}"
        )
        try:
            result = func(*args, **debug_kwargs)
            # Only cache if result is not None
            if result is not None:
                TOOL_RESULT_CACHE[tool_name] = result
            print(
                f"[DEBUG {timestamp}] Tool `{tool_name}` completed "
                f"with result_type={type(result).__name__}"
            )
            return result
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR {timestamp}] Tool `{tool_name}` failed: {e}")
            raise

    return wrapper


def normalize_and_merge_from_cache() -> Any:
    """Normalize and merge using the latest cached DataFrames from previous tools."""
    # Ensure TOOL_RESULT_CACHE is always a dict
    global TOOL_RESULT_CACHE
    if TOOL_RESULT_CACHE is None or not isinstance(TOOL_RESULT_CACHE, dict):
        TOOL_RESULT_CACHE = {}
    
    cpcb_df = TOOL_RESULT_CACHE.get("Fetch CPCB data")
    nasa_df = TOOL_RESULT_CACHE.get("Fetch NASA fire data")
    dss_df = TOOL_RESULT_CACHE.get("Fetch DSS pollution data")

    if cpcb_df is None or nasa_df is None or dss_df is None:
        missing = [
            name
            for name, df in (
                ("Fetch CPCB data", cpcb_df),
                ("Fetch NASA fire data", nasa_df),
                ("Fetch DSS pollution data", dss_df),
            )
            if df is None
        ]
        raise ValueError(
            "Cannot normalize and merge without previous tool outputs. "
            f"Missing results from: {', '.join(missing)}"
        )

    try:
        consolidated = storage_tools.normalize_and_merge(cpcb_df, nasa_df, dss_df)
        if consolidated is not None:
            TOOL_RESULT_CACHE["Normalize and merge data"] = consolidated
        return consolidated
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] normalize_and_merge failed: {e}")
        raise


def save_latest_to_s3_from_cache() -> Any:
    """Save the most recent consolidated DataFrame to S3."""
    # Ensure TOOL_RESULT_CACHE is always a dict
    global TOOL_RESULT_CACHE
    if TOOL_RESULT_CACHE is None or not isinstance(TOOL_RESULT_CACHE, dict):
        TOOL_RESULT_CACHE = {}
    
    consolidated_df = TOOL_RESULT_CACHE.get("Normalize and merge data")
    if consolidated_df is None:
        raise ValueError(
            "No consolidated DataFrame available. Run `Normalize and merge data` first."
        )
    return storage_tools.save_to_s3(consolidated_df)


class _EmptyToolArgs(BaseModel):
    security_context: dict | None = None  # allow CrewAI to inject its context

    if ConfigDict:
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - pydantic < 2.x
        class Config:
            extra = "forbid"


cpcb_fetch_tool = Tool(
    name="Fetch CPCB data",
    description="Fetches real-time air quality data from the CPCB data.gov.in API and returns a pandas DataFrame.",
    func=_with_debug_logs("Fetch CPCB data", cpcb_tools.fetch_cpcb_data),
    args_schema=_EmptyToolArgs
)

nasa_fetch_tool = Tool(
    name="Fetch NASA fire data",
    description="Retrieves active fire data from the NASA FIRMS API and returns a pandas DataFrame.",
    func=_with_debug_logs("Fetch NASA fire data", nasa_tools.fetch_nasa_fire_data),
    args_schema=_EmptyToolArgs
)

dss_fetch_tool = Tool(
    name="Fetch DSS pollution data",
    description="Scrapes the DSS pollution source website and returns a pandas DataFrame of extracted items.",
    func=_with_debug_logs("Fetch DSS pollution data", dss_tools.fetch_dss_data),
    args_schema=_EmptyToolArgs
)

normalize_tool = Tool(
    name="Normalize and merge data",
    description="Normalizes CPCB, NASA, and DSS DataFrames and merges them into a consolidated dataset.",
    func=_with_debug_logs("Normalize and merge data", normalize_and_merge_from_cache),
    args_schema=_EmptyToolArgs
)

save_to_s3_tool = Tool(
    name="Save DataFrame to S3",
    description="Uploads a pandas DataFrame to the configured AWS S3 bucket in JSON format.",
    func=_with_debug_logs("Save DataFrame to S3", save_latest_to_s3_from_cache),
    args_schema=_EmptyToolArgs
)

sensor_ingest_agent = Agent(
    role="SensorIngestAgent",
    goal="Continuously ingest and harmonize Delhi NCR pollution data from CPCB, NASA FIRMS, and DSS.",
    backstory=(
        "You operate as the 24/7 real-time watchtower for the NCR's air quality ecosystem. "
        "You connect to Delhi monitoring stations, track regional farm fires, and apportion "
        "pollution sources using the DSS. Your outputs must remain reliable even when "
        "individual feeds return empty results."
    ),
    tools=[
        cpcb_fetch_tool,
        nasa_fetch_tool,
        dss_fetch_tool,
        normalize_tool,
        save_to_s3_tool,
    ],
    verbose=True,
)