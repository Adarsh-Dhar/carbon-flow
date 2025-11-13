from bs4 import BeautifulSoup
import pandas as pd
from src.utils.api_helpers import make_api_request


def fetch_dss_data():
    url = 'https://ews.tropmet.res.in/dss/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Make the API request using helper function
    response = make_api_request(url, headers=headers)
    
    if response:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find data elements - looking for div elements with specific classes
        data_elements = soup.find_all('div', class_='data-item')  # Adjust class name as needed
        
        data_list = []
        for element in data_elements:
            data_dict = {
                'text': element.get_text(strip=True),
                'title': element.get('title', ''),
                'class': ' '.join(element.get('class', []))
            }
            data_list.append(data_dict)
        
        # Convert to DataFrame
        df = pd.DataFrame(data_list)
        return df
    else:
        return pd.DataFrame()
