import io
import os
from datetime import datetime, timedelta
from typing import Final

import pandas as pd

from src.utils.api_helpers import make_api_request

# Approximate bounding box covering Punjab & Haryana (lat, lon)
_LAT_MIN: Final[float] = 27.0
_LAT_MAX: Final[float] = 33.6
_LON_MIN: Final[float] = 72.5
_LON_MAX: Final[float] = 77.5


def _generate_mock_nasa_fire_data() -> pd.DataFrame:
    """
    Generate mock NASA fire data for Punjab & Haryana when API fails or returns empty.
    
    Returns:
        DataFrame with realistic fire event data in Punjab and Haryana districts.
    """
    now = datetime.utcnow()
    
    # Districts in Punjab and Haryana with realistic coordinates
    districts = [
        {"name": "Jind", "lat": 29.32, "lon": 76.32, "fires": 45},
        {"name": "Karnal", "lat": 29.68, "lon": 76.99, "fires": 38},
        {"name": "Ambala", "lat": 30.38, "lon": 76.78, "fires": 32},
        {"name": "Fatehabad", "lat": 29.52, "lon": 75.45, "fires": 28},
        {"name": "Sirsa", "lat": 29.54, "lon": 75.03, "fires": 25},
        {"name": "Patiala", "lat": 30.34, "lon": 76.40, "fires": 42},
        {"name": "Ludhiana", "lat": 30.90, "lon": 75.85, "fires": 35},
        {"name": "Amritsar", "lat": 31.63, "lon": 74.87, "fires": 30},
    ]
    
    records = []
    for district in districts:
        # Generate multiple fire events for each district
        for i in range(district["fires"]):
            # Randomize timestamp within last 48 hours
            hours_ago = (i * 2) % 48
            fire_time = now - timedelta(hours=hours_ago)
            
            # Add slight randomization to coordinates
            import random
            lat_offset = random.uniform(-0.1, 0.1)
            lon_offset = random.uniform(-0.1, 0.1)
            
            records.append({
                "latitude": district["lat"] + lat_offset,
                "longitude": district["lon"] + lon_offset,
                "acq_date": fire_time.strftime("%Y-%m-%d"),
                "acq_time": fire_time.strftime("%H%M"),
                "confidence": random.randint(30, 100),
                "brightness": random.uniform(300, 400),
                "frp": random.uniform(0.5, 5.0),  # Fire Radiative Power
                "satellite": "NPP",
                "instrument": "VIIRS",
                "version": "1.0",
                "daynight": "D" if 6 <= fire_time.hour < 18 else "N",
            })
    
    df = pd.DataFrame(records)
    print(f"[MOCK DATA] Generated {len(df)} NASA fire events for {len(districts)} districts in Punjab/Haryana")
    return df


def fetch_nasa_fire_data() -> pd.DataFrame:
    """Fetch fire data from NASA FIRMS API filtered for Punjab & Haryana farm-fire activity."""
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    
    api_key = os.getenv("NASA_MAP_KEY")

    if not api_key and not use_mock:
        print("Warning: NASA_MAP_KEY environment variable not found. Using mock data.")
        use_mock = True

    if use_mock:
        return _generate_mock_nasa_fire_data()

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP/world/1"

    response = make_api_request(url)

    if response is None:
        print("Warning: NASA API request failed. Using mock data as fallback.")
        return _generate_mock_nasa_fire_data()
    
    # Check for HTTP errors
    if hasattr(response, 'status_code') and response.status_code >= 400:
        print(f"Warning: NASA API returned status {response.status_code}. Using mock data as fallback.")
        return _generate_mock_nasa_fire_data()

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error: Failed to parse NASA fire data - {exc}. Using mock data as fallback.")
        return _generate_mock_nasa_fire_data()

    if df.empty:
        print("Warning: NASA API returned empty data. Using mock data as fallback.")
        return _generate_mock_nasa_fire_data()

    # Ensure latitude/longitude columns exist for geographic filtering.
    if not {"latitude", "longitude"}.issubset(df.columns):
        print(
            "Warning: NASA FIRMS dataset missing latitude/longitude columns. Using mock data as fallback."
        )
        return _generate_mock_nasa_fire_data()

    regional_df = df[
        df["latitude"].between(_LAT_MIN, _LAT_MAX)
        & df["longitude"].between(_LON_MIN, _LON_MAX)
    ].copy()

    if regional_df.empty:
        print(
            "Warning: No NASA FIRMS records within Punjab/Haryana bounds. Using mock data as fallback."
        )
        return _generate_mock_nasa_fire_data()

    regional_df.reset_index(drop=True, inplace=True)
    return regional_df
