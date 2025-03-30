import React, { useState, useEffect } from 'react';
import './App.css';

// API URL - update this to your backend URL
const API_URL = 'http://0.0.0.0:8000';

// Types
interface UnusualOption {
  underlying_ticker: string;
  option_symbol: string;
  option_type: string;
  strike_price: number;
  expiration_date: string;
  days_to_expiry: number;
  current_volume: number;
  avg_volume: number;
  volume_ratio: number;
  in_the_money: boolean;
  current_stock_price: number;
}

interface ApiStatus {
  status: string;
  api_calls: number;
  max_api_calls: number;
  timestamp: string;
  synthetic_data_mode: boolean;
}

interface SentimentData {
  total_unusual: number;
  calls: number;
  puts: number;
  calls_percentage: number;
  puts_percentage: number;
  bullish_tickers: string[];
  bearish_tickers: string[];
}

function App() {
  const [unusualOptions, setUnusualOptions] = useState<UnusualOption[]>([]);
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [apiStatus, setApiStatus] = useState<ApiStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [tickerData, setTickerData] = useState<any | null>(null);

  // Fetch API status
  const fetchApiStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api-status`);
      const data = await response.json();
      setApiStatus(data);
    } catch (err) {
      console.error('Failed to fetch API status:', err);
    }
  };

  // Fetch data on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Get API status
        await fetchApiStatus();
        
        // Get unusual options
        const optionsResponse = await fetch(`${API_URL}/unusual-options`);
        const optionsData = await optionsResponse.json();
        setUnusualOptions(optionsData);
        
        // Get sentiment data
        const sentimentResponse = await fetch(`${API_URL}/bullish-bearish`);
        const sentimentData = await sentimentResponse.json();
        setSentiment(sentimentData);
        
        setError(null);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to fetch data from the API. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Refresh API status every 30 seconds
    const statusInterval = setInterval(fetchApiStatus, 30000);
    
    return () => clearInterval(statusInterval);
  }, []);
  
  // Fetch ticker data when a ticker is selected
  useEffect(() => {
    if (!selectedTicker) {
      setTickerData(null);
      return;
    }
    
    const fetchTickerData = async () => {
      try {
        const response = await fetch(`${API_URL}/ticker/${selectedTicker}`);
        const data = await response.json();
        setTickerData(data);
      } catch (err) {
        console.error(`Error fetching data for ${selectedTicker}:`, err);
        setTickerData(null);
      }
    };
    
    fetchTickerData();
  }, [selectedTicker]);
  
  // Handle ticker selection
  const handleTickerClick = (ticker: string) => {
    setSelectedTicker(ticker === selectedTicker ? null : ticker);
  };
  
  // Run analysis manually
  const handleRunAnalysis = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_URL}/run-analysis`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      // Refresh data
      window.location.reload();
    } catch (err) {
      console.error('Error running analysis:', err);
      alert('Failed to run analysis. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  // Display loading state
  if (loading && !unusualOptions.length) {
    return <div className="loading">Loading unusual options activity...</div>;
  }

  // Display error state
  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="App">
      <header>
        <h1>Unusual Options Activity Dashboard</h1>
        {apiStatus && (
          <div className={`api-status ${apiStatus.synthetic_data_mode ? 'synthetic' : ''}`}>
            API Calls: {apiStatus.api_calls}/{apiStatus.max_api_calls}
            {apiStatus.synthetic_data_mode && ' (Using synthetic data)'}
          </div>
        )}
        <button className="refresh-button" onClick={handleRunAnalysis}>
          Run Analysis
        </button>
      </header>
      
      {sentiment && (
        <div className="sentiment-section">
          <h2>Market Sentiment</h2>
          <div className="sentiment-chart">
            <div className="sentiment-bar">
              <div 
                className="calls-bar" 
                style={{ width: `${sentiment.calls_percentage}%` }}
              >
                {sentiment.calls_percentage.toFixed(1)}% Calls
              </div>
              <div 
                className="puts-bar" 
                style={{ width: `${sentiment.puts_percentage}%` }}
              >
                {sentiment.puts_percentage.toFixed(1)}% Puts
              </div>
            </div>
            <div className="ticker-lists">
              <div className="bullish-tickers">
                <h3>Top Bullish</h3>
                <ul>
                  {sentiment.bullish_tickers.map(ticker => (
                    <li key={ticker} onClick={() => handleTickerClick(ticker)}>
                      {ticker}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bearish-tickers">
                <h3>Top Bearish</h3>
                <ul>
                  {sentiment.bearish_tickers.map(ticker => (
                    <li key={ticker} onClick={() => handleTickerClick(ticker)}>
                      {ticker}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {selectedTicker && tickerData && (
        <div className="ticker-detail">
          <div className="ticker-header">
            <h2>{selectedTicker} - ${tickerData.current_price}</h2>
            <button className="close-button" onClick={() => setSelectedTicker(null)}>✕</button>
          </div>
          
          <div className="ticker-sentiment">
            <div className="sentiment-bar">
              <div 
                className="calls-bar" 
                style={{ width: `${tickerData.calls_percentage}%` }}
              >
                {tickerData.calls_percentage.toFixed(1)}% Calls
              </div>
              <div 
                className="puts-bar" 
                style={{ width: `${tickerData.puts_percentage}%` }}
              >
                {tickerData.puts_percentage.toFixed(1)}% Puts
              </div>
            </div>
          </div>
          
          <div className="ticker-options">
            <h3>Unusual Options Activity</h3>
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Strike</th>
                  <th>Exp</th>
                  <th>Days</th>
                  <th>Volume</th>
                  <th>Ratio</th>
                  <th>ITM</th>
                </tr>
              </thead>
              <tbody>
                {tickerData.options_activity.map((option: any) => (
                  <tr key={option.option_symbol}>
                    <td className={option.option_type.toLowerCase()}>
                      {option.option_type.toUpperCase()}
                    </td>
                    <td>${option.strike_price}</td>
                    <td>{new Date(option.expiration_date).toLocaleDateString()}</td>
                    <td>{option.days_to_expiry}</td>
                    <td>{option.current_volume.toLocaleString()}</td>
                    <td>{option.volume_ratio.toFixed(1)}x</td>
                    <td>{option.in_the_money ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      <div className="main-table">
        <h2>Unusual Options Activity</h2>
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Type</th>
              <th>Strike</th>
              <th>Exp</th>
              <th>Days</th>
              <th>Volume</th>
              <th>Avg Vol</th>
              <th>Ratio</th>
              <th>ITM</th>
            </tr>
          </thead>
          <tbody>
            {unusualOptions.map((option) => (
              <tr key={option.option_symbol} onClick={() => handleTickerClick(option.underlying_ticker)}>
                <td className="ticker-cell">{option.underlying_ticker}</td>
                <td className={option.option_type.toLowerCase()}>
                  {option.option_type.toUpperCase()}
                </td>
                <td>${option.strike_price}</td>
                <td>{new Date(option.expiration_date).toLocaleDateString()}</td>
                <td>{option.days_to_expiry}</td>
                <td>{option.current_volume.toLocaleString()}</td>
                <td>{Math.round(option.avg_volume).toLocaleString()}</td>
                <td className="ratio">{option.volume_ratio.toFixed(1)}x</td>
                <td>{option.in_the_money ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;