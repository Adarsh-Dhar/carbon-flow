import requests


def make_api_request(url, headers=None, params=None):
    """
    Make an API request with standardized error handling and status code checking.
    
    Args:
        url (str): The URL to make the request to
        headers (dict, optional): HTTP headers to include in the request
        params (dict, optional): Query parameters to include in the request
    
    Returns:
        requests.Response: The response object if successful
        None: If the request fails
    """
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response
        else:
            print(f"Error: API request failed with status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error: Failed to fetch data - {str(e)}")
        return None
