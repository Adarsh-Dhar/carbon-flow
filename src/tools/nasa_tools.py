import io
import os
from typing import Final

import pandas as pd

from src.utils.api_helpers import make_api_request

# Approximate bounding box covering Punjab & Haryana (lat, lon)
_LAT_MIN: Final[float] = 27.0
_LAT_MAX: Final[float] = 33.6
_LON_MIN: Final[float] = 72.5
_LON_MAX: Final[float] = 77.5


def fetch_nasa_fire_data() -> pd.DataFrame:
    """Fetch fire data from NASA FIRMS API filtered for Punjab & Haryana farm-fire activity."""
    api_key = os.getenv("NASA_MAP_KEY")

    if not api_key:
        print("Error: NASA_MAP_KEY environment variable not found")
        return pd.DataFrame()

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP/world/1"

    response = make_api_request(url)

    if response is None:
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error: Failed to parse NASA fire data - {exc}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Ensure latitude/longitude columns exist for geographic filtering.
    if not {"latitude", "longitude"}.issubset(df.columns):
        print(
            "Warning: NASA FIRMS dataset missing latitude/longitude columns. Returning unfiltered data."
        )
        return df

    regional_df = df[
        df["latitude"].between(_LAT_MIN, _LAT_MAX)
        & df["longitude"].between(_LON_MIN, _LON_MAX)
    ].copy()

    if regional_df.empty:
        print(
            "Warning: No NASA FIRMS records within Punjab/Haryana bounds. Returning original dataset for diagnostics."
        )
        return df

    regional_df.reset_index(drop=True, inplace=True)
    return regional_df
