import pandas as pd
import boto3
import os
from datetime import datetime


def save_to_s3(df):
    """
    Save a pandas DataFrame to AWS S3 as JSON.
    
    Args:
        df: pandas DataFrame to save
    """
    # Get S3 bucket name from environment variable
    bucket_name = os.getenv('S3_BUCKET_NAME')
    
    if not bucket_name:
        print("Error: S3_BUCKET_NAME environment variable not found")
        return
    
    try:
        # Convert DataFrame to JSON string
        json_data = df.to_json(orient="records")
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"data/aqi_data_{timestamp}.json"
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json_data,
            ContentType='application/json'
        )
        
        message = f"Success: Data uploaded to s3://{bucket_name}/{s3_key}"
        print(message)
        return message
        
    except Exception as e:
        print(f"Error: Failed to upload to S3 - {str(e)}")

def normalize_and_merge(cpcb_df, nasa_df, dss_df):
    # Normalize CPCB DataFrame
    cpcb_normalized = cpcb_df.copy()
    if 'date' in cpcb_normalized.columns:
        cpcb_normalized['date'] = pd.to_datetime(cpcb_normalized['date'])
    # Add data_source column to identify the data source (CPCB/NASA/DSS)
    cpcb_normalized['data_source'] = 'CPCB'
    
    # Normalize NASA DataFrame
    nasa_normalized = nasa_df.copy()
    if 'date' in nasa_normalized.columns:
        nasa_normalized['date'] = pd.to_datetime(nasa_normalized['date'])
    nasa_normalized['data_source'] = 'NASA'
    
    # Normalize DSS DataFrame
    # IMPORTANT: DSS DataFrame has 'source' column with pollution source names (Stubble burning, Transport, etc.)
    # We need to preserve this, so we add 'data_source' instead of overwriting 'source'
    dss_normalized = dss_df.copy()
    if 'date' in dss_normalized.columns:
        dss_normalized['date'] = pd.to_datetime(dss_normalized['date'])
    dss_normalized['data_source'] = 'DSS'
    # Preserve the original 'source' field which contains pollution source names
    
    # Merge the three normalized DataFrames
    consolidated_df = pd.concat([cpcb_normalized, nasa_normalized, dss_normalized], 
                               ignore_index=True, sort=False)
    
    return consolidated_df
