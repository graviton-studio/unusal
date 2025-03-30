# Example data ingestion service in Python
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "your_api_key"
BASE_URL = "https://api.marketdata.com/v1/"


def fetch_stock_data(ticker, days=90):
    """Fetch historical and current stock data for a ticker"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Fetch historical data
    url = f"{BASE_URL}stocks/{ticker}/history?from={start_date}&to={end_date}&apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        # Transform to DataFrame and store in database
        df = pd.DataFrame(data['results'])
        s#tore_in_database(df, ticker, 'historical')
    
    # Fetch today's data
    url = f"{BASE_URL}stocks/{ticker}/quote?apiKey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
       # store_in_database(pd.DataFrame([data]), ticker, 'current')
