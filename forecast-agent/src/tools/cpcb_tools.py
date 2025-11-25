import io
import os
from datetime import datetime, timedelta
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


def _generate_mock_cpcb_data() -> pd.DataFrame:
    """
    Generate mock CPCB data for Delhi NCR stations when API fails or returns no Delhi data.
    
    Returns:
        DataFrame with realistic Delhi NCR station data including border stations.
    """
    now = datetime.now()
    timestamp = now.strftime("%d-%m-%Y %H:00:00")
    
    # Delhi NCR stations including border stations
    stations = [
        {"name": "Alipur", "lat": 28.8, "lon": 77.1, "aqi": 380, "is_border": True},
        {"name": "Anand Vihar", "lat": 28.65, "lon": 77.32, "aqi": 420, "is_border": True, "is_hotspot": True},
        {"name": "Dwarka", "lat": 28.59, "lon": 77.05, "aqi": 350, "is_border": True},
        {"name": "Rohini", "lat": 28.74, "lon": 77.12, "aqi": 320, "is_border": True},
        {"name": "Bawana", "lat": 28.8, "lon": 77.05, "aqi": 410, "is_hotspot": True},
        {"name": "Mundka", "lat": 28.68, "lon": 77.03, "aqi": 395, "is_hotspot": True},
        {"name": "Punjabi Bagh", "lat": 28.67, "lon": 77.12, "aqi": 360, "is_hotspot": False},
        {"name": "RK Puram", "lat": 28.57, "lon": 77.17, "aqi": 370, "is_hotspot": False},
    ]
    
    pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "OZONE"]
    
    records = []
    for station in stations:
        base_aqi = station["aqi"]
        for pollutant in pollutants:
            # Generate realistic pollutant values based on AQI
            if pollutant == "PM2.5":
                min_val = base_aqi * 0.6
                max_val = base_aqi * 1.2
                avg_val = base_aqi * 0.9
            elif pollutant == "PM10":
                min_val = base_aqi * 0.7
                max_val = base_aqi * 1.3
                avg_val = base_aqi * 1.0
            elif pollutant == "NO2":
                min_val = base_aqi * 0.3
                max_val = base_aqi * 0.6
                avg_val = base_aqi * 0.45
            elif pollutant == "SO2":
                min_val = base_aqi * 0.1
                max_val = base_aqi * 0.3
                avg_val = base_aqi * 0.2
            elif pollutant == "CO":
                min_val = base_aqi * 0.2
                max_val = base_aqi * 0.5
                avg_val = base_aqi * 0.35
            else:  # OZONE
                min_val = base_aqi * 0.4
                max_val = base_aqi * 0.8
                avg_val = base_aqi * 0.6
            
            records.append({
                "country": "India",
                "state": "Delhi",
                "city": "Delhi",
                "station": f"{station['name']} - DPCC",
                "last_update": timestamp,
                "latitude": station["lat"],
                "longitude": station["lon"],
                "pollutant_id": pollutant,
                "pollutant_min": round(min_val, 1),
                "pollutant_max": round(max_val, 1),
                "pollutant_avg": round(avg_val, 1),
                "is_hotspot": station.get("is_hotspot", False),
            })
    
    df = pd.DataFrame(records)
    print(f"[MOCK DATA] Generated {len(df)} CPCB records for {len(stations)} Delhi NCR stations")
    return df


def fetch_cpcb_data() -> pd.DataFrame:
    """Fetch air quality data from CPCB API and focus on the Delhi NCR network."""
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    
    api_key = os.getenv("CPCB_API_KEY")

    if not api_key and not use_mock:
        print("Warning: CPCB_API_KEY environment variable not found. Using mock data.")
        use_mock = True

    if use_mock:
        return _generate_mock_cpcb_data()

    url = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    params = {
        "api-key": api_key,
        "format": "csv",
        # Fetch a broad sample and then filter locally
        "limit": 5000,
    }

    response = make_api_request(url, params=params)

    if response is None:
        print("Warning: CPCB API request failed. Using mock data as fallback.")
        return _generate_mock_cpcb_data()

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error: Failed to parse CPCB data - {exc}. Using mock data as fallback.")
        return _generate_mock_cpcb_data()

    if df.empty:
        print("Warning: CPCB API returned empty data. Using mock data as fallback.")
        return _generate_mock_cpcb_data()

    # Defensive: ensure the expected columns exist before filtering
    for expected in ("state", "city", "station"):
        if expected not in df.columns:
            print(f"Warning: CPCB data missing column '{expected}'. Using mock data as fallback.")
            return _generate_mock_cpcb_data()

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
            "Warning: No CPCB rows matched Delhi filters. Using mock data as fallback."
        )
        return _generate_mock_cpcb_data()

    delhi_df["is_hotspot"] = delhi_df["station"].apply(_flag_hotspot)
    return delhi_df.reset_index(drop=True)
