import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

class UnusualActivityAnalyzer:
    def __init__(self, db_connection, lookback_period=90):
        """
        Initialize the analyzer
        
        Parameters:
        db_connection: Database connection object
        lookback_period: Number of days to use for baseline calculation
        """
        self.conn = db_connection
        self.lookback_period = lookback_period
    
    def calculate_volume_baseline(self, ticker):
        """Calculate the baseline volume statistics for a ticker"""
        query = f"""
        SELECT date, volume 
        FROM historical_data 
        WHERE ticker = '{ticker}' 
        AND date >= date('now', '-{self.lookback_period} days')
        """
        
        df = pd.read_sql(query, self.conn)
        
        # Calculate statistics
        mean_volume = df['volume'].mean()
        std_volume = df['volume'].std()
        median_volume = df['volume'].median()
        
        return {
            'mean': mean_volume,
            'std': std_volume,
            'median': median_volume
        }
    
    def get_current_volume(self, ticker):
        """Get today's volume for a ticker"""
        query = f"""
        SELECT volume 
        FROM current_data 
        WHERE ticker = '{ticker}' 
        AND date = date('now')
        """
        
        df = pd.read_sql(query, self.conn)
        
        if df.empty:
            return None
        
        return df['volume'].iloc[0]
    
    def calculate_volume_zscore(self, ticker):
        """
        Calculate z-score for current volume compared to baseline
        
        Returns:
        float: z-score of current volume
        """
        baseline = self.calculate_volume_baseline(ticker)
        current_volume = self.get_current_volume(ticker)
        
        if current_volume is None:
            return None
        
        # Calculate z-score
        z_score = (current_volume - baseline['mean']) / baseline['std']
        
        return z_score
    
    def get_top_unusual_volume(self, top_n=20, min_zscore=2.0):
        """
        Get top N stocks with unusual volume
        
        Parameters:
        top_n: Number of top stocks to return
        min_zscore: Minimum z-score to consider unusual
        
        Returns:
        DataFrame: Top N stocks with unusual volume
        """
        # Get all tickers
        query = "SELECT DISTINCT ticker FROM current_data WHERE date = date('now')"
        tickers = pd.read_sql(query, self.conn)['ticker'].tolist()
        
        results = []
        for ticker in tickers:
            z_score = self.calculate_volume_zscore(ticker)
            if z_score is not None and z_score >= min_zscore:
                baseline = self.calculate_volume_baseline(ticker)
                current_volume = self.get_current_volume(ticker)
                
                results.append({
                    'ticker': ticker,
                    'current_volume': current_volume,
                    'avg_volume': baseline['mean'],
                    'volume_zscore': z_score,
                    'volume_multiple': current_volume / baseline['mean']
                })
        
        # Convert to DataFrame and sort
        df_results = pd.DataFrame(results)
        if df_results.empty:
            return pd.DataFrame()
            
        return df_results.sort_values('volume_zscore', ascending=False).head(top_n)
    
    def analyze_options_activity(self, ticker):
        """
        Analyze options activity for a specific ticker
        (This would be implemented based on your options data structure)
        """
        # Implementation depends on how options data is stored
        pass
    
    def get_ticker_unusual_activity(self, ticker):
        """
        Get comprehensive unusual activity analysis for a specific ticker
        
        Parameters:
        ticker: Stock ticker symbol
        
        Returns:
        dict: Analysis results including volume and options metrics
        """
        # Volume analysis
        volume_zscore = self.calculate_volume_zscore(ticker)
        baseline = self.calculate_volume_baseline(ticker)
        current_volume = self.get_current_volume(ticker)
        
        # Options analysis would be added here
        
        return {
            'ticker': ticker,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'volume_metrics': {
                'current_volume': current_volume,
                'avg_volume': baseline['mean'],
                'median_volume': baseline['median'],
                'volume_zscore': volume_zscore,
                'volume_multiple': current_volume / baseline['mean'] if current_volume else None,
                'is_unusual': volume_zscore > 2.0 if volume_zscore else False
            },
            # Options metrics would be added here
        }