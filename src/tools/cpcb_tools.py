import pandas as pd
import io
import os
from src.utils.api_helpers import make_api_request


def fetch_cpcb_data():
    """Fetch air quality data from CPCB API"""
    # Get API key from environment variable
    api_key = os.getenv('CPCB_API_KEY')
    
    if not api_key:
        print("Error: CPCB_API_KEY environment variable not found")
        return pd.DataFrame()
    
    # Build the request URL
    url = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    params = {
        'api-key': api_key,
        'format': 'csv',
        'limit': 2000
    }
    
    # Make the API request using helper function
    response = make_api_request(url, params=params)
    
    if response:
        # Read CSV data from response text
        df = pd.read_csv(io.StringIO(response.text))
        return df
    else:
        return pd.DataFrame()
