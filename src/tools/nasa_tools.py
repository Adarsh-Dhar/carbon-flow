import pandas as pd
import io
import os
from src.utils.api_helpers import make_api_request


def fetch_nasa_fire_data():
    # Get the API key from environment variable
    api_key = os.getenv('NASA_MAP_KEY')
    
    if not api_key:
        print("Error: NASA_MAP_KEY environment variable not found")
        return pd.DataFrame()
    
    # Build the request URL
    url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP/world/1'
    
    # Make the API request using helper function
    response = make_api_request(url)
    
    if response:
        # Use pandas to read the CSV data
        df = pd.read_csv(io.StringIO(response.text))
        return df
    else:
        return pd.DataFrame()
