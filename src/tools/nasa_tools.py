import pandas as pd
import io
import os
from src.utils.api_helpers import make_api_request


def fetch_nasa_fire_data():
    """Fetch fire data from NASA FIRMS API"""
    api_key = os.getenv('NASA_MAP_KEY')
    
    if not api_key:
        print("Error: NASA_MAP_KEY environment variable not found")
        return pd.DataFrame()
    
    url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP/world/1'
    
    response = make_api_request(url)

    if response is None:
        return pd.DataFrame()

    try:
        return pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        print(f"Error: Failed to parse NASA fire data - {str(e)}")
        return pd.DataFrame()
