import io
import os
from typing import Final

import pandas as pd

from src.utils.api_helpers import make_api_request

# Delhi-centric filtering
_DELHI_STATE_KEYWORDS: Final[tuple[str, ...]] = (
    "delhi",
    "nct of delhi",
    "national capital territory of delhi",
)

_DELHI_CITY_KEYWORDS: Final[tuple[str, ...]] = (
    "delhi",
    "new delhi",
    "north delhi",
    "south delhi",
    "east delhi",
    "west delhi",
)

_DELHI_HOTSPOTS: Final[tuple[str, ...]] = (
    "anand vihar",
    "bawana",
    "mundka",
)


def _matches_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    value_lower = value.lower()
    return any(keyword in value_lower for keyword in keywords)


def _flag_hotspot(station_name: str) -> bool:
    station = station_name.lower()
    return any(hotspot in station for hotspot in _DELHI_HOTSPOTS)


def fetch_cpcb_data() -> pd.DataFrame:
    """Fetch air quality data from CPCB API and focus on the Delhi NCR network."""
    api_key = os.getenv("CPCB_API_KEY")

    if not api_key:
        print("Error: CPCB_API_KEY environment variable not found")
        return pd.DataFrame()

    url = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    params = {
        "api-key": api_key,
        "format": "csv",
        # Fetch a broad sample and then filter locally
        "limit": 5000,
    }

    response = make_api_request(url, params=params)

    if response is None:
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error: Failed to parse CPCB data - {exc}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Defensive: ensure the expected columns exist before filtering
    for expected in ("state", "city", "station"):
        if expected not in df.columns:
            print(f"Warning: CPCB data missing column '{expected}'. Returning raw dataset.")
            df["is_hotspot"] = False
            return df

    def _is_delhi_row(row: pd.Series) -> bool:
        state = str(row["state"]).strip()
        city = str(row["city"]).strip()
        station = str(row["station"]).strip()
        return (
            _matches_keyword(state, _DELHI_STATE_KEYWORDS)
            or _matches_keyword(city, _DELHI_CITY_KEYWORDS)
            or "delhi" in station.lower()
        )

    delhi_df = df[df.apply(_is_delhi_row, axis=1)].copy()

    if delhi_df.empty:
        print(
            "Warning: No CPCB rows matched Delhi filters. Returning original dataset for diagnostics."
        )
        df["is_hotspot"] = df["station"].apply(_flag_hotspot) if "station" in df else False
        return df

    delhi_df["is_hotspot"] = delhi_df["station"].apply(_flag_hotspot)
    return delhi_df.reset_index(drop=True)
