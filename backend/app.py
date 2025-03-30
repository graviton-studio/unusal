from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import logging
import yfinance as yf
import pandas as pd
import numpy as np
import statistics
import time
import random
import json
import os
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Options Unusualness API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced cache with TTL and file-based persistence
class EnhancedCache:
    def __init__(self, cache_dir="./cache"):
        self.cache_dir = cache_dir
        self.memory_cache = {
            'ticker_data': {},
            'options_data': {},
            'unusualness_scores': {},
            'last_updated': None,
            'analysis_running': False
        }
        self.ttl = {
            'ticker_data': 3600,  # 1 hour
            'options_data': 3600 * 4,  # 4 hours
            'unusualness_scores': 3600 * 12  # 12 hours
        }
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load cache from disk if available
        self._load_cache()
    
    def _load_cache(self):
        try:
            cache_file = os.path.join(self.cache_dir, "cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    disk_cache = json.load(f)
                    
                # Only use cache entries that haven't expired
                now = datetime.now()
                
                # Load ticker data
                if 'ticker_data' in disk_cache:
                    for ticker, data in disk_cache.get('ticker_data', {}).items():
                        if 'timestamp' in data:
                            cache_time = datetime.fromisoformat(data['timestamp'])
                            if (now - cache_time).total_seconds() < self.ttl['ticker_data']:
                                self.memory_cache['ticker_data'][ticker] = data
                
                # Load options data
                if 'options_data' in disk_cache:
                    for ticker, data in disk_cache.get('options_data', {}).items():
                        if 'timestamp' in data:
                            cache_time = datetime.fromisoformat(data['timestamp'])
                            if (now - cache_time).total_seconds() < self.ttl['options_data']:
                                # Convert JSON lists back to DataFrame for options chains
                                for key in ['calls_near', 'puts_near', 'calls_target', 'puts_target']:
                                    if key in data and isinstance(data[key], list):
                                        data[key] = pd.DataFrame(data[key])
                                
                                if 'historical_data' in data and isinstance(data['historical_data'], dict):
                                    data['historical_data'] = pd.DataFrame(data['historical_data'])
                                
                                self.memory_cache['options_data'][ticker] = data
                
                # Load unusualness scores
                if 'unusualness_scores' in disk_cache:
                    for ticker, data in disk_cache.get('unusualness_scores', {}).items():
                        if 'timestamp' in data:
                            cache_time = datetime.fromisoformat(data['timestamp'])
                            if (now - cache_time).total_seconds() < self.ttl['unusualness_scores']:
                                self.memory_cache['unusualness_scores'][ticker] = data
                
                logger.info(f"Loaded cache with {len(self.memory_cache['ticker_data'])} tickers, "
                          f"{len(self.memory_cache['options_data'])} options datasets, "
                          f"{len(self.memory_cache['unusualness_scores'])} unusualness scores")
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
    
    def _save_cache(self):
        try:
            # Convert datetime objects to ISO format for JSON serialization
            export_cache = {
                'ticker_data': {},
                'options_data': {},
                'unusualness_scores': {}
            }
            
            # Prepare ticker data for export
            for ticker, data in self.memory_cache['ticker_data'].items():
                export_cache['ticker_data'][ticker] = {
                    'price': data['price'],
                    'timestamp': data['timestamp'].isoformat() if isinstance(data['timestamp'], datetime) else data['timestamp']
                }
            
            # Prepare options data for export
            for ticker, data in self.memory_cache['options_data'].items():
                # Convert DataFrame to dict for serialization
                serializable_data = {k: v for k, v in data.items() if k != 'timestamp'}
                
                for key in ['calls_near', 'puts_near', 'calls_target', 'puts_target']:
                    if key in serializable_data and isinstance(serializable_data[key], pd.DataFrame):
                        serializable_data[key] = serializable_data[key].to_dict(orient='records')
                
                if 'historical_data' in serializable_data and isinstance(serializable_data['historical_data'], pd.DataFrame):
                    serializable_data['historical_data'] = {
                        'Close': serializable_data['historical_data']['Close'].tolist() 
                        if 'Close' in serializable_data['historical_data'] else []
                    }
                
                export_cache['options_data'][ticker] = {
                    **serializable_data,
                    'timestamp': data['timestamp'].isoformat() if isinstance(data['timestamp'], datetime) else data['timestamp']
                }
            
            # Prepare unusualness scores for export
            for ticker, data in self.memory_cache['unusualness_scores'].items():
                export_cache['unusualness_scores'][ticker] = {
                    **{k: v for k, v in data.items() if k != 'timestamp'},
                    'timestamp': data['timestamp'].isoformat() if isinstance(data['timestamp'], datetime) else data['timestamp']
                }
            
            # Save to disk
            cache_file = os.path.join(self.cache_dir, "cache.json")
            with open(cache_file, 'w') as f:
                json.dump(export_cache, f)
                
            logger.info("Cache saved to disk")
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def get_ticker_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker in self.memory_cache['ticker_data']:
            data = self.memory_cache['ticker_data'][ticker]
            now = datetime.now()
            timestamp = data['timestamp'] if isinstance(data['timestamp'], datetime) else datetime.fromisoformat(data['timestamp'])
            if (now - timestamp).total_seconds() < self.ttl['ticker_data']:
                return data
        return None
    
    def set_ticker_data(self, ticker: str, price: float):
        ticker = ticker.upper()
        self.memory_cache['ticker_data'][ticker] = {
            'price': price,
            'timestamp': datetime.now()
        }
        # Periodically save cache to disk
        if random.random() < 0.1:  # 10% chance to save on each update
            self._save_cache()
    
    def get_options_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker in self.memory_cache['options_data']:
            data = self.memory_cache['options_data'][ticker]
            now = datetime.now()
            timestamp = data['timestamp'] if isinstance(data['timestamp'], datetime) else datetime.fromisoformat(data['timestamp'])
            if (now - timestamp).total_seconds() < self.ttl['options_data']:
                return data
        return None
    
    def set_options_data(self, ticker: str, data: Dict[str, Any]):
        ticker = ticker.upper()
        self.memory_cache['options_data'][ticker] = {
            **data,
            'timestamp': datetime.now()
        }
        # Periodically save cache to disk
        if random.random() < 0.2:  # 20% chance to save on each update
            self._save_cache()
    
    def get_unusualness_score(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker in self.memory_cache['unusualness_scores']:
            data = self.memory_cache['unusualness_scores'][ticker]
            now = datetime.now()
            timestamp = data['timestamp'] if isinstance(data['timestamp'], datetime) else datetime.fromisoformat(data['timestamp'])
            if (now - timestamp).total_seconds() < self.ttl['unusualness_scores']:
                return data
        return None
    
    def set_unusualness_score(self, ticker: str, data: Dict[str, Any]):
        ticker = ticker.upper()
        self.memory_cache['unusualness_scores'][ticker] = {
            **data,
            'timestamp': datetime.now()
        }
        # Periodically save cache to disk
        if random.random() < 0.3:  # 30% chance to save on each update
            self._save_cache()
    
    def clear(self):
        self.memory_cache = {
            'ticker_data': {},
            'options_data': {},
            'unusualness_scores': {},
            'last_updated': datetime.now(),
            'analysis_running': False
        }
        # Delete cache file
        cache_file = os.path.join(self.cache_dir, "cache.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)

# Initialize cache
cache = EnhancedCache()

# Rate limiting with much longer delays to prevent blocking
last_yahoo_request = datetime.now() - timedelta(seconds=10)
MIN_REQUEST_INTERVAL = 5.0  # 5 seconds between Yahoo Finance requests

def rate_limited_request():
    """Ensure we don't exceed Yahoo Finance rate limits"""
    global last_yahoo_request
    now = datetime.now()
    elapsed = (now - last_yahoo_request).total_seconds()
    
    if elapsed < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - elapsed + random.uniform(0.1, 1.0)  # Add jitter
        logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
    
    last_yahoo_request = datetime.now()

def get_ticker_with_backoff(ticker, max_retries=3):
    """Get Yahoo Finance ticker with exponential backoff for rate limiting"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            rate_limited_request()
            logger.info(f"Attempting to get Yahoo Finance data for {ticker}")
            return yf.Ticker(ticker)
        except Exception as e:
            logger.warning(f"Error getting ticker {ticker} (attempt {retry_count+1}/{max_retries}): {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                # Exponential backoff with jitter
                sleep_time = (2 ** retry_count) * 5 + (random.random() * 3)
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
    
    raise Exception(f"Failed to get ticker after {max_retries} attempts")

def get_options_data(ticker):
    """Fetch options data for given ticker with caching"""
    ticker = ticker.upper()
    
    # Check cache first
    cached_data = cache.get_options_data(ticker)
    if cached_data:
        logger.info(f"Using cached options data for {ticker}")
        return cached_data
    
    try:
        logger.info(f"Fetching fresh options data for {ticker}")
        # Add even longer delay before first request
        time.sleep(random.uniform(1.0, 3.0))
        
        stock = get_ticker_with_backoff(ticker)
        
        # Get all available expiration dates
        try:
            rate_limited_request()
            expiration_dates = stock.options
            
            if not expiration_dates:
                logger.warning(f"No options data available for {ticker}")
                return None
                
            # We'll focus on the nearest expiration date and the one ~30 days out
            nearest_date = expiration_dates[0]
            target_date = None
            
            # Try to find an expiration about a month out
            today = datetime.now().date()
            
            for date in expiration_dates:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                days_out = (date_obj - today).days
                if 20 <= days_out <= 45:
                    target_date = date
                    break
            
            if target_date is None and len(expiration_dates) > 1:
                target_date = expiration_dates[1]
            else:
                target_date = nearest_date
            
            # Get options chains for both dates with extra delays
            rate_limited_request()
            time.sleep(1.0)  # Extra delay
            calls_near = stock.option_chain(nearest_date).calls
            
            rate_limited_request()
            time.sleep(1.0)  # Extra delay
            puts_near = stock.option_chain(nearest_date).puts
            
            rate_limited_request()
            time.sleep(1.0)  # Extra delay
            calls_target = stock.option_chain(target_date).calls
            
            rate_limited_request()
            time.sleep(1.0)  # Extra delay
            puts_target = stock.option_chain(target_date).puts
            
            # Get current stock price and historical data
            current_price = None
            try:
                rate_limited_request()
                time.sleep(1.0)  # Extra delay
                current_price = stock.info.get('regularMarketPrice')
            except Exception as e:
                logger.warning(f"Error getting price from info for {ticker}: {str(e)}")
                current_price = None
            
            if not current_price:
                try:
                    rate_limited_request()
                    time.sleep(1.0)  # Extra delay
                    current_price = stock.history(period="1d")['Close'].iloc[-1]
                except Exception as e:
                    logger.warning(f"Error getting price from history for {ticker}: {str(e)}")
                    # If still no price, try another approach
                    try:
                        current_price = calls_near['strike'].median()  # Use median strike price as estimate
                    except Exception as e:
                        logger.error(f"Could not determine price for {ticker}: {str(e)}")
                        current_price = 100.0  # Default fallback
            
            # Get historical data
            hist_data = None
            try:
                rate_limited_request()
                time.sleep(1.0)  # Extra delay
                hist_data = stock.history(period="60d")
            except Exception as e:
                logger.warning(f"Could not get historical data for {ticker}: {str(e)}")
                hist_data = pd.DataFrame()  # Empty DataFrame
            
            options_data = {
                'calls_near': calls_near,
                'puts_near': puts_near,
                'calls_target': calls_target,
                'puts_target': puts_target,
                'current_price': current_price,
                'historical_data': hist_data,
                'nearest_date': nearest_date,
                'target_date': target_date
            }
            
            # Cache the data
            cache.set_options_data(ticker, options_data)
            
            return options_data
        except Exception as e:
            logger.error(f"Error fetching options chain for {ticker}: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching options data for {ticker}: {str(e)}")
        return None

def calculate_unusualness_score(options_data):
    """Calculate unusualness score based on options data"""
    try:
        scores = []
        
        calls_near = options_data['calls_near']
        puts_near = options_data['puts_near']
        calls_target = options_data['calls_target']
        puts_target = options_data['puts_target']
        current_price = options_data['current_price']
        hist_data = options_data['historical_data']
        
        def calc_vol_oi_ratio(options_df):
            try:
                filtered = options_df[options_df['openInterest'] > 10]
                if len(filtered) == 0:
                    return 0
                    
                ratios = filtered['volume'] / filtered['openInterest']
                ratios = ratios.clip(upper=20)
                return ratios.mean()
            except Exception as e:
                logger.warning(f"Error calculating vol/oi ratio: {str(e)}")
                return 0
        
        vol_oi_calls_near = calc_vol_oi_ratio(calls_near)
        vol_oi_puts_near = calc_vol_oi_ratio(puts_near)
        vol_oi_calls_target = calc_vol_oi_ratio(calls_target)
        vol_oi_puts_target = calc_vol_oi_ratio(puts_target)
        
        avg_vol_oi = np.mean([vol_oi_calls_near, vol_oi_puts_near, 
                            vol_oi_calls_target, vol_oi_puts_target])
        
        vol_oi_score = min(avg_vol_oi / 2, 2)
        scores.append(vol_oi_score)
        
        def calc_pcr(calls, puts):
            try:
                call_value = (calls['volume'] * calls['lastPrice']).sum()
                put_value = (puts['volume'] * puts['lastPrice']).sum()
                
                if call_value == 0:
                    return 5.0
                return put_value / call_value
            except Exception as e:
                logger.warning(f"Error calculating PCR: {str(e)}")
                return 1.0
            
        pcr_near = calc_pcr(calls_near, puts_near)
        pcr_target = calc_pcr(calls_target, puts_target)
        
        pcr_score = min(abs(pcr_near - 0.7) * 1.5, 2) + min(abs(pcr_target - 0.7) * 1.5, 2)
        pcr_score = min(pcr_score, 3)
        scores.append(pcr_score)
        
        if isinstance(hist_data, pd.DataFrame) and 'Close' in hist_data.columns and len(hist_data) >= 20:
            try:
                returns = hist_data['Close'].pct_change().dropna()
                hist_vol = returns.std() * np.sqrt(252) * 100
                
                atm_calls = calls_near[(calls_near['strike'] >= current_price * 0.95) & 
                                    (calls_near['strike'] <= current_price * 1.05)]
                atm_puts = puts_near[(puts_near['strike'] >= current_price * 0.95) & 
                                    (puts_near['strike'] <= current_price * 1.05)]
                
                if len(atm_calls) > 0 and len(atm_puts) > 0:
                    avg_iv = (atm_calls['impliedVolatility'].mean() + atm_puts['impliedVolatility'].mean()) / 2 * 100
                    
                    iv_hv_ratio = avg_iv / hist_vol if hist_vol > 0 else 2
                    
                    iv_score = min(abs(iv_hv_ratio - 1.15) * 3, 3)
                    scores.append(iv_score)
                else:
                    scores.append(1.5)
            except Exception as e:
                logger.warning(f"Error calculating IV/historical vol: {str(e)}")
                scores.append(1.0)
        else:
            scores.append(1.0)
        
        def calc_skew(calls, puts, current_price):
            try:
                otm_calls = calls[calls['strike'] > current_price * 1.1]
                otm_puts = puts[puts['strike'] < current_price * 0.9]
                
                if len(otm_calls) == 0 or len(otm_puts) == 0:
                    return 1.0
                    
                avg_call_iv = otm_calls['impliedVolatility'].mean()
                avg_put_iv = otm_puts['impliedVolatility'].mean()
                
                if avg_call_iv == 0:
                    return 3.0
                    
                skew_ratio = avg_put_iv / avg_call_iv
                
                skew_unusualness = abs(skew_ratio - 1.2) * 3
                return min(skew_unusualness, 2)
            except Exception as e:
                logger.warning(f"Error calculating skew: {str(e)}")
                return 1.0
            
        skew_score = calc_skew(calls_near, puts_near, current_price)
        scores.append(skew_score)
        
        total_score = sum(scores)
        
        scaled_score = max(1, min(10, round(total_score)))
        
        return {
            'score': scaled_score,
            'components': {
                'volume_oi_ratio': round(vol_oi_score, 2),
                'put_call_ratio': round(pcr_score, 2),
                'iv_vs_historical': round(scores[2], 2) if len(scores) > 2 else 0,
                'skew_analysis': round(skew_score, 2)
            },
            'raw_data': {
                'avg_vol_oi': round(avg_vol_oi, 2),
                'pcr_near': round(pcr_near, 2),
                'pcr_target': round(pcr_target, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating unusualness score: {str(e)}")
        return {
            'score': 1,
            'components': {
                'volume_oi_ratio': 0,
                'put_call_ratio': 0,
                'iv_vs_historical': 0,
                'skew_analysis': 0
            },
            'raw_data': {
                'avg_vol_oi': 0,
                'pcr_near': 0,
                'pcr_target': 0
            }
        }

def interpret_score(score, components, raw_data):
    """Provide interpretation of the unusualness score"""
    interpretation = []
    
    if score <= 3:
        interpretation.append(f"Score {score}/10: Options activity appears normal.")
    elif score <= 6:
        interpretation.append(f"Score {score}/10: Options show somewhat unusual activity.")
    else:
        interpretation.append(f"Score {score}/10: Options show highly unusual activity!")
    
    vol_oi = components['volume_oi_ratio']
    if vol_oi > 1.5:
        interpretation.append("• High volume relative to open interest suggests unusual trading activity.")
    
    pcr = components['put_call_ratio']
    if pcr > 2:
        pcr_raw = raw_data['pcr_near']
        if pcr_raw > 1.5:
            interpretation.append("• Put-Call ratio is unusually high, suggesting bearish sentiment or hedging.")
        elif pcr_raw < 0.4:
            interpretation.append("• Put-Call ratio is unusually low, suggesting extreme bullish sentiment.")
    
    iv = components['iv_vs_historical']
    if iv > 2:
        interpretation.append("• Implied volatility is significantly different from historical volatility, suggesting unusual expectations.")
    
    skew = components['skew_analysis']
    if skew > 1.5:
        interpretation.append("• Options skew is unusual, indicating asymmetric expectations for price movement.")
    
    return interpretation

def get_unusual_options(ticker):
    """Get unusual options for a ticker with caching"""
    ticker = ticker.upper()
    
    options_data = get_options_data(ticker)
    if not options_data:
        return []
        
    current_price = options_data['current_price']
    nearest_date = options_data['nearest_date']
    calls_near = options_data['calls_near']
    puts_near = options_data['puts_near']
    
    unusual_options = []
    
    try:
        for idx, call in calls_near.iterrows():
            if call['volume'] > 10 and call['openInterest'] > 0:
                vol_oi_ratio = min(call['volume'] / call['openInterest'], 20) if call['openInterest'] > 10 else 0
                
                if vol_oi_ratio >= 2:  # Lowered threshold to find more unusual options
                    expiry_date = datetime.strptime(nearest_date, '%Y-%m-%d').date()
                    days_to_expiry = (expiry_date - datetime.now().date()).days
                    
                    unusual_options.append({
                        'underlying_ticker': ticker,
                        'option_symbol': f"{ticker}C{int(call['strike']*100)}",
                        'option_type': 'call',
                        'strike_price': float(call['strike']),
                        'expiration_date': nearest_date,
                        'days_to_expiry': days_to_expiry,
                        'current_volume': int(call['volume']),
                        'open_interest': int(call['openInterest']),
                        'implied_volatility': round(float(call['impliedVolatility']) * 100, 2),
                        'volume_ratio': round(vol_oi_ratio, 2),
                        'in_the_money': float(call['strike']) < current_price,
                        'current_stock_price': float(current_price),
                        'last_price': round(float(call['lastPrice']), 2)
                    })
        
        for idx, put in puts_near.iterrows():
            if put['volume'] > 10 and put['openInterest'] > 0:
                vol_oi_ratio = min(put['volume'] / put['openInterest'], 20) if put['openInterest'] > 10 else 0
                
                if vol_oi_ratio >= 2:  # Lowered threshold to find more unusual options
                    expiry_date = datetime.strptime(nearest_date, '%Y-%m-%d').date()
                    days_to_expiry = (expiry_date - datetime.now().date()).days
                    
                    unusual_options.append({
                        'underlying_ticker': ticker,
                        'option_symbol': f"{ticker}P{int(put['strike']*100)}",
                        'option_type': 'put',
                        'strike_price': float(put['strike']),
                        'expiration_date': nearest_date,
                        'days_to_expiry': days_to_expiry,
                        'current_volume': int(put['volume']),
                        'open_interest': int(put['openInterest']),
                        'implied_volatility': round(float(put['impliedVolatility']) * 100, 2),
                        'volume_ratio': round(vol_oi_ratio, 2),
                        'in_the_money': float(put['strike']) > current_price,
                        'current_stock_price': float(current_price),
                        'last_price': round(float(put['lastPrice']), 2)
                    })
    except Exception as e:
        logger.error(f"Error processing options for {ticker}: {str(e)}")
    
    unusual_options.sort(key=lambda x: x['volume_ratio'], reverse=True)
    return unusual_options

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Options Unusualness API using Yahoo Finance"}

@app.get("/api-status")
async def get_api_status():
    return {
        "status": "operational",
        "last_yahoo_request": last_yahoo_request.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds_since_last_request": (datetime.now() - last_yahoo_request).total_seconds(),
        "min_request_interval": MIN_REQUEST_INTERVAL,
        "cached_tickers": len(cache.memory_cache['ticker_data']),
        "cached_options": len(cache.memory_cache['options_data']),
        "cached_scores": len(cache.memory_cache['unusualness_scores'])
    }

@app.get("/unusualness-score/{ticker}")
async def get_ticker_unusualness_score(ticker: str):
    try:
        ticker = ticker.upper()
        logger.info(f"Request for unusualness score for {ticker}")
        
        # Check cache first
        cached_score = cache.get_unusualness_score(ticker)
        if cached_score:
            logger.info(f"Using cached unusualness score for {ticker}")
            return cached_score
        
        # Fetch options data (this function has its own caching)
        options_data = get_options_data(ticker)
        if not options_data:
            logger.warning(f"No options data found for {ticker}")
            return {
                'ticker': ticker,
                'score': 0,
                'interpretation': ["No options data available for this ticker."],
                'components': {
                    'volume_oi_ratio': 0,
                    'put_call_ratio': 0,
                    'iv_vs_historical': 0,
                    'skew_analysis': 0
                },
                'nearest_expiry': None,
                'target_expiry': None
            }
        
        logger.info(f"Calculating unusualness score for {ticker}")
        result = calculate_unusualness_score(options_data)
        
        interpretation = interpret_score(result['score'], result['components'], result['raw_data'])
        
        score_data = {
            'ticker': ticker,
            'current_price': options_data['current_price'],
            'score': result['score'],
            'interpretation': interpretation,
            'components': result['components'],
            'nearest_expiry': options_data['nearest_date'],
            'target_expiry': options_data['target_date']
        }
        
        # Cache the result
        cache.set_unusualness_score(ticker, score_data)
        
        return score_data
    
    except Exception as e:
        logger.error(f"Error calculating unusualness score for {ticker}: {str(e)}")
        # Return a default response with the error message
        return {
            'ticker': ticker,
            'score': 0,
            'interpretation': [f"Error analyzing options: {str(e)}"],
            'components': {
                'volume_oi_ratio': 0,
                'put_call_ratio': 0,
                'iv_vs_historical': 0,
                'skew_analysis': 0
            },
            'nearest_expiry': None,
            'target_expiry': None
        }

@app.get("/ticker/{ticker}")
async def get_ticker_activity(ticker: str):
    try:
        ticker = ticker.upper()
        logger.info(f"Request for options activity for {ticker}")
        
        unusual_options = get_unusual_options(ticker)
        
        if unusual_options:
            current_price = unusual_options[0]['current_stock_price']
        else:
            # Try to get current price
            try:
                cached_data = cache.get_ticker_data(ticker)
                if cached_data:
                    current_price = cached_data['price']
                else:
                    stock = get_ticker_with_backoff(ticker)
                    rate_limited_request()
                    current_price = stock.info.get('regularMarketPrice')
                    if not current_price:
                        rate_limited_request()
                        current_price = stock.history(period="1d")['Close'].iloc[-1]
                    
                    # Cache the price
                    cache.set_ticker_data(ticker, current_price)
            except Exception as e:
                logger.error(f"Error getting price for {ticker}: {str(e)}")
                current_price = None
        
        calls = [opt for opt in unusual_options if opt['option_type'].lower() == 'call']
        puts = [opt for opt in unusual_options if opt['option_type'].lower() == 'put']
        
        calls_volume = sum(opt['current_volume'] for opt in calls)
        puts_volume = sum(opt['current_volume'] for opt in puts)
        total_volume = calls_volume + puts_volume
        
        return {
            'ticker': ticker,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': current_price,
            'has_unusual_activity': len(unusual_options) > 0,
            'options_activity': unusual_options,
            'calls_volume': calls_volume,
            'puts_volume': puts_volume,
            'calls_percentage': (calls_volume / total_volume * 100) if total_volume > 0 else 0,
            'puts_percentage': (puts_volume / total_volume * 100) if total_volume > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting ticker activity for {ticker}: {str(e)}")
        return {
            'ticker': ticker,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': None,
            'has_unusual_activity': False,
            'options_activity': [],
            'calls_volume': 0,
            'puts_volume': 0,
            'calls_percentage': 0,
            'puts_percentage': 0
        }

@app.post("/clear-cache")
async def clear_cache():
    try:
        cache.clear()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bullish-bearish")
async def get_bullish_bearish():
    """Get bullish-bearish breakdown from cached data"""
    try:
        # This is a simplified implementation that looks at cached unusualness scores
        # For a real implementation, you would scan many tickers
        cached_scores = cache.memory_cache['unusualness_scores']
        
        if not cached_scores:
            return {
                'total_unusual': 0,
                'calls': 0,
                'puts': 0,
                'calls_percentage': 0,
                'puts_percentage': 0,
                'bullish_tickers': [],
                'bearish_tickers': []
            }
        
        # Determine bullish/bearish from component scores
        ticker_sentiment = {}
        for ticker, data in cached_scores.items():
            if 'components' in data and 'put_call_ratio' in data['components']:
                pcr = data['components']['put_call_ratio']
                if pcr > 1.5:
                    # High put-call ratio suggests bearishness
                    ticker_sentiment[ticker] = -pcr
                elif pcr < 0.7:
                    # Low put-call ratio suggests bullishness
                    ticker_sentiment[ticker] = 2 - pcr  # Invert so higher values = more bullish
                else:
                    # Neutral
                    ticker_sentiment[ticker] = 0
        
        # Get top bullish and bearish tickers
        sentiment_items = list(ticker_sentiment.items())
        bullish = sorted(sentiment_items, key=lambda x: x[1], reverse=True)
        bearish = sorted(sentiment_items, key=lambda x: x[1])
        
        bullish_tickers = [t[0] for t in bullish[:5] if t[1] > 0]
        bearish_tickers = [t[0] for t in bearish[:5] if t[1] < 0]
        
        # Count number of bullish vs bearish tickers
        bull_count = sum(1 for v in ticker_sentiment.values() if v > 0)
        bear_count = sum(1 for v in ticker_sentiment.values() if v < 0)
        total = bull_count + bear_count
        
        if total == 0:
            return {
                'total_unusual': len(cached_scores),
                'calls': 0,
                'puts': 0,
                'calls_percentage': 50,
                'puts_percentage': 50,
                'bullish_tickers': bullish_tickers,
                'bearish_tickers': bearish_tickers
            }
        
        return {
            'total_unusual': len(cached_scores),
            'calls': bull_count,
            'puts': bear_count,
            'calls_percentage': (bull_count / total * 100) if total > 0 else 0,
            'puts_percentage': (bear_count / total * 100) if total > 0 else 0,
            'bullish_tickers': bullish_tickers,
            'bearish_tickers': bearish_tickers
        }
    except Exception as e:
        logger.error(f"Error getting bullish-bearish breakdown: {str(e)}")
        return {
            'total_unusual': 0,
            'calls': 0,
            'puts': 0,
            'calls_percentage': 0,
            'puts_percentage': 0,
            'bullish_tickers': [],
            'bearish_tickers': []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)