import pandas as pd
import io
import os
from src.utils.api_helpers import make_api_request


def fetch_cpcb_data():
    """Fetch air quality data from CPCB API"""
    api_key = os.getenv('CPCB_API_KEY')
    
    if not api_key:
        print("Error: CPCB_API_KEY environment variable not found")
        return pd.DataFrame()
    
    url = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    params = {
        'api-key': api_key,
        'format': 'csv',
        'limit': 2000
    }

    response = make_api_request(url, params=params)

    if response is None:
        return pd.DataFrame()

    try:
        return pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        print(f"Error: Failed to parse CPCB data - {str(e)}")
        return pd.DataFrame()
