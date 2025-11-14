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
from src.tools import s3_reader_tools, meteo_tools, prediction_tools, output_tools
from src.utils.env_config import configure_llm_from_env

configure_llm_from_env()

TOOL_RESULT_CACHE: dict[str, Any] = {}


def _with_debug_logs(tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap tool functions with debug logging for inputs and outputs."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        timestamp = datetime.utcnow().isoformat()
        debug_kwargs = dict(kwargs)
        security_context = debug_kwargs.pop("security_context", None)
        print(
            f"[DEBUG {timestamp}] Tool `{tool_name}` invoked "
            f"with args={args} kwargs={debug_kwargs} security_context={security_context}"
        )
        result = func(*args, **debug_kwargs)
        TOOL_RESULT_CACHE[tool_name] = result
        print(
            f"[DEBUG {timestamp}] Tool `{tool_name}` completed "
            f"with result_type={type(result).__name__}"
        )
        return result

    return wrapper


def normalize_and_merge_from_cache() -> Any:
    """Normalize and merge using the latest cached DataFrames from previous tools."""
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

    consolidated = storage_tools.normalize_and_merge(cpcb_df, nasa_df, dss_df)
    TOOL_RESULT_CACHE["Normalize and merge data"] = consolidated
    return consolidated


def save_latest_to_s3_from_cache() -> Any:
    """Save the most recent consolidated DataFrame to S3."""
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


# ForecastAgent Tools

read_ingested_data_tool = Tool(
    name="Read ingested data from S3",
    description="Retrieves the latest ingested sensor data from AWS S3 containing CPCB AQI levels, NASA fire counts, and DSS source percentages.",
    func=_with_debug_logs("Read ingested data from S3", s3_reader_tools.read_ingested_data_tool),
    args_schema=_EmptyToolArgs
)

get_meteo_forecast_tool = Tool(
    name="Get meteorological forecast",
    description="Fetches 48-hour wind speed forecast for Delhi from the Open-Meteo API to understand how weather conditions will affect air quality.",
    func=_with_debug_logs("Get meteorological forecast", meteo_tools.get_meteorological_forecast_tool),
    args_schema=_EmptyToolArgs
)


def synthesize_and_predict_from_cache() -> Any:
    """Synthesize sensor and meteorological data to generate AQI prediction."""
    sensor_data = TOOL_RESULT_CACHE.get("Read ingested data from S3")
    meteo_data = TOOL_RESULT_CACHE.get("Get meteorological forecast")
    
    if sensor_data is None:
        raise ValueError(
            "Cannot generate prediction without sensor data. "
            "Run 'Read ingested data from S3' first."
        )
    
    # Meteo data is optional - prediction can proceed with reduced confidence
    if meteo_data is None:
        print("[DEBUG] Meteorological data not available, proceeding with reduced confidence")
        meteo_data = {"error": "Meteorological data not available"}
    
    result = prediction_tools.synthesize_and_predict(sensor_data, meteo_data)
    TOOL_RESULT_CACHE["Synthesize and predict"] = result
    return result


def generate_output_from_cache() -> Any:
    """Generate and save forecast output JSON from prediction data."""
    prediction_data = TOOL_RESULT_CACHE.get("Synthesize and predict")
    
    if prediction_data is None:
        raise ValueError(
            "Cannot generate output without prediction data. "
            "Run 'Synthesize and predict' first."
        )
    
    return output_tools.generate_output_tool(prediction_data)


synthesize_predict_tool = Tool(
    name="Synthesize and predict",
    description="Analyzes fire count data, wind speed forecasts, and DSS source attribution to generate AQI predictions with confidence levels and reasoning.",
    func=_with_debug_logs("Synthesize and predict", synthesize_and_predict_from_cache),
    args_schema=_EmptyToolArgs
)

generate_output_tool_wrapped = Tool(
    name="Generate forecast output",
    description="Formats prediction data into structured JSON with prediction, confidence_level, and reasoning fields, then writes to file and optionally uploads to S3.",
    func=_with_debug_logs("Generate forecast output", generate_output_from_cache),
    args_schema=_EmptyToolArgs
)


# ForecastAgent Agents

data_retrieval_agent = Agent(
    role="Data Collector and Validator",
    goal="Retrieve all necessary input data from S3 and meteorological APIs with validation",
    backstory=(
        "You are the data acquisition specialist who ensures the ForecastAgent has complete, "
        "accurate, and timely input data. You validate data completeness and flag any missing "
        "or stale data sources. Your reliability is critical for generating accurate predictions."
    ),
    tools=[
        read_ingested_data_tool,
        get_meteo_forecast_tool,
    ],
    verbose=True,
)

forecast_analysis_agent = Agent(
    role="Air Quality Forecaster and Reasoner",
    goal="Generate accurate 24-hour AQI predictions with confidence levels and clear reasoning",
    backstory=(
        "You are an expert air quality analyst who understands the complex relationships between "
        "fire events, meteorological conditions, pollution sources, and AQI levels. You synthesize "
        "multiple data streams to predict air quality trends and explain your reasoning clearly for "
        "policy makers. Your predictions enable Delhi to shift from reactive to proactive air quality "
        "management policies."
    ),
    tools=[
        synthesize_predict_tool,
        generate_output_tool_wrapped,
    ],
    verbose=True,
)