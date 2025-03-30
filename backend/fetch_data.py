import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = "bJFusYMHIrD0x31Z197i8n3IxU5ygcpj"
BASE_URL = "https://api.polygon.io/v3"

# In-memory cache
cache = {
    'unusual_options': [],
    'last_updated': None,
    'ticker_data': {}
}

def get_unusual_options_activity():
    """Scan the entire market for unusual options activity using Polygon.io"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/reference/options/contracts?order=volume&sort=desc&limit=100&apiKey={API_KEY}"
    
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to get top volume options: {response.status_code}")
        return []
    
    data = response.json()
    top_volume_options = data.get('results', [])
    
    logger.info(f"Found {len(top_volume_options)} high volume options to analyze")
    
    unusual_options = []
    api_call_count = 0
    max_api_calls =3
    
    for option in top_volume_options:
        if api_call_count >= max_api_calls:
            logger.info(f"Reached API call limit ({max_api_calls})")
            break
            
        ticker = option['ticker']
        option_type = 'call' if option['contract_type'].lower() == 'call' else 'put'
        
        hist_url = f"{BASE_URL}/aggs/ticker/{ticker}/range/5/day/{yesterday}/{today}?apiKey={API_KEY}"
        
        try:
            hist_response = requests.get(hist_url)
            api_call_count += 1
            
            time.sleep(0.12)
            
            if hist_response.status_code == 200:
                hist_data = hist_response.json()
                
                if 'results' in hist_data and hist_data['results']:
                    volumes = [day.get('v', 0) for day in hist_data['results']]
                    
                    if len(volumes) > 1:
                        today_volume = volumes[0]
                        prev_volumes = volumes[1:]
                        avg_volume = sum(prev_volumes) / len(prev_volumes)
                        
                        volume_ratio = today_volume / avg_volume if avg_volume > 0 else 0
                        
                        if volume_ratio >= 3 and today_volume >= 100:
                            underlying = option['underlying_ticker']
                            price = get_stock_price(underlying)
                            
                            itm = False
                            if price and 'strike_price' in option:
                                strike = option['strike_price']
                                itm = (option_type == 'call' and price > strike) or (option_type == 'put' and price < strike)
                            
                            expiry_date = datetime.strptime(option['expiration_date'], '%Y-%m-%d').date()
                            days_to_expiry = (expiry_date - datetime.now().date()).days
                            
                            unusual_options.append({
                                'underlying_ticker': underlying,
                                'option_symbol': ticker,
                                'option_type': option_type,
                                'strike_price': option['strike_price'],
                                'expiration_date': option['expiration_date'],
                                'days_to_expiry': days_to_expiry,
                                'current_volume': today_volume,
                                'avg_volume': avg_volume,
                                'volume_ratio': volume_ratio,
                                'in_the_money': itm,
                                'current_stock_price': price
                            })
                            logger.info(f"Found unusual activity for {ticker}: {volume_ratio:.1f}x volume")
        except Exception as e:
            logger.error(f"Error processing {ticker}: {str(e)}")
    
    # Sort by volume ratio (highest first)
    unusual_options.sort(key=lambda x: x['volume_ratio'], reverse=True)
    
    # Cache the results
    cache['unusual_options'] = unusual_options
    cache['last_updated'] = datetime.now()
    
    logger.info(f"Found {len(unusual_options)} options with unusual activity")
    return unusual_options

def get_stock_price(ticker):
    """Get current stock price for a ticker"""
    if ticker in cache['ticker_data'] and (datetime.now() - cache['ticker_data'][ticker]['timestamp']).seconds < 1800:
        return cache['ticker_data'][ticker]['price']
        
    url = f"{BASE_URL}/last/trade/{ticker}?apiKey={API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                price = data['results']['p']  # Price
                
                # Cache the price
                cache['ticker_data'][ticker] = {
                    'price': price,
                    'timestamp': datetime.now()
                }
                
                return price
    except Exception as e:
        logger.error(f"Error getting price for {ticker}: {str(e)}")
    
    return None

def get_ticker_options(ticker):
    """Get options data for a specific ticker"""
    logger.info(f"Getting options data for {ticker}")
    
    # First, check all unusual options for this ticker
    unusual_options = get_unusual_options_activity()
    ticker_options = [opt for opt in unusual_options if opt['underlying_ticker'].upper() == ticker.upper()]
    
    # If we already have enough data, return it
    if len(ticker_options) >= 5:
        return {
            'ticker': ticker,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': get_stock_price(ticker),
            'has_unusual_activity': len(ticker_options) > 0,
            'options_activity': ticker_options
        }
    
    # Otherwise, get specific options data for this ticker
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/reference/options/contracts?underlying_ticker={ticker}&limit=100&apiKey={API_KEY}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            options_contracts = data.get('results', [])
            
            # Get volume data for each contract
            for contract in options_contracts[:10]:  # Limit to 10 to avoid too many API calls
                contract_ticker = contract['ticker']
                volume_url = f"{BASE_URL}/aggs/ticker/{contract_ticker}/prev?apiKey={API_KEY}"
                
                vol_response = requests.get(volume_url)
                time.sleep(0.12)  # Respect rate limits
                
                if vol_response.status_code == 200:
                    vol_data = vol_response.json()
                    
                    if 'results' in vol_data and vol_data['results']:
                        volume = vol_data['results'][0].get('v', 0)
                        
                        if volume > 100:  # Only consider options with meaningful volume
                            expiry_date = datetime.strptime(contract['expiration_date'], '%Y-%m-%d').date()
                            days_to_expiry = (expiry_date - datetime.now().date()).days
                            
                            option_type = 'call' if contract['contract_type'].lower() == 'call' else 'put'
                            
                            # Check if already in our list
                            if not any(opt['option_symbol'] == contract_ticker for opt in ticker_options):
                                ticker_options.append({
                                    'underlying_ticker': ticker,
                                    'option_symbol': contract_ticker,
                                    'option_type': option_type,
                                    'strike_price': contract['strike_price'],
                                    'expiration_date': contract['expiration_date'],
                                    'days_to_expiry': days_to_expiry,
                                    'current_volume': volume,
                                    'avg_volume': volume / 2,  # Estimate
                                    'volume_ratio': 2.0,  # Estimate
                                    'in_the_money': False,  # Would need more data to determine
                                    'current_stock_price': get_stock_price(ticker)
                                })
    except Exception as e:
        logger.error(f"Error getting options for {ticker}: {str(e)}")
    
    price = get_stock_price(ticker)
    
    # Calculate calls vs puts volumes
    calls = [opt for opt in ticker_options if opt['option_type'].lower() == 'call']
    puts = [opt for opt in ticker_options if opt['option_type'].lower() == 'put']
    
    calls_volume = sum(opt['current_volume'] for opt in calls)
    puts_volume = sum(opt['current_volume'] for opt in puts)
    total_volume = calls_volume + puts_volume
    
    return {
        'ticker': ticker,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'current_price': price,
        'has_unusual_activity': len(ticker_options) > 0,
        'options_activity': ticker_options,
        'calls_volume': calls_volume,
        'puts_volume': puts_volume,
        'calls_percentage': (calls_volume / total_volume * 100) if total_volume > 0 else 0,
        'puts_percentage': (puts_volume / total_volume * 100) if total_volume > 0 else 0
    }

def get_bullish_bearish_breakdown():
    """Analyze unusual options for bullish vs bearish sentiment"""
    unusual_options = get_unusual_options_activity()
    
    if not unusual_options:
        return {
            'total_unusual': 0,
            'calls': 0,
            'puts': 0,
            'calls_percentage': 0,
            'puts_percentage': 0,
            'bullish_tickers': [],
            'bearish_tickers': []
        }
    
    calls = [opt for opt in unusual_options if opt['option_type'].lower() == 'call']
    puts = [opt for opt in unusual_options if opt['option_type'].lower() == 'put']
    
    # Count unusual activity by ticker
    call_volume_by_ticker = {}
    for call in calls:
        ticker = call['underlying_ticker']
        if ticker not in call_volume_by_ticker:
            call_volume_by_ticker[ticker] = 0
        call_volume_by_ticker[ticker] += call['current_volume']
    
    put_volume_by_ticker = {}
    for put in puts:
        ticker = put['underlying_ticker']
        if ticker not in put_volume_by_ticker:
            put_volume_by_ticker[ticker] = 0
        put_volume_by_ticker[ticker] += put['current_volume']
    
    # Get top bullish and bearish tickers
    bullish_tickers = sorted(call_volume_by_ticker.keys(), 
                            key=lambda t: call_volume_by_ticker[t], reverse=True)[:5]
    
    bearish_tickers = sorted(put_volume_by_ticker.keys(), 
                            key=lambda t: put_volume_by_ticker[t], reverse=True)[:5]
    
    # Calculate percentages
    total = len(unusual_options)
    calls_percentage = (len(calls) / total * 100) if total > 0 else 0
    puts_percentage = (len(puts) / total * 100) if total > 0 else 0
    
    return {
        'total_unusual': total,
        'calls': len(calls),
        'puts': len(puts),
        'calls_percentage': calls_percentage,
        'puts_percentage': puts_percentage,
        'bullish_tickers': bullish_tickers,
        'bearish_tickers': bearish_tickers
    }

def run_daily_analysis():
    """Refresh all data"""
    logger.info("Running daily analysis")
    
    # Clear cache
    cache['unusual_options'] = []
    cache['last_updated'] = None
    cache['ticker_data'] = {}
    
    # Get fresh data
    unusual_options = get_unusual_options_activity()
    
    return unusual_options