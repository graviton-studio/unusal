import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ScoreDisplay from './ScoreDisplay';
import OptionsTable from './OptionsTable';

// API URL - update this to your backend URL
const API_URL = 'http://localhost:8000';

interface UnusualOption {
  underlying_ticker: string;
  option_symbol: string;
  option_type: string;
  strike_price: number;
  expiration_date: string;
  days_to_expiry: number;
  current_volume: number;
  open_interest: number;
  implied_volatility: number;
  volume_ratio: number;
  in_the_money: boolean;
  current_stock_price: number;
  last_price: number;
}

interface UnusualScoreData {
  ticker: string;
  current_price: number;
  score: number;
  interpretation: string[];
  components: {
    volume_oi_ratio: number;
    put_call_ratio: number;
    iv_vs_historical: number;
    skew_analysis: number;
  };
  nearest_expiry: string;
  target_expiry: string;
}

interface TickerOptionsData {
  ticker: string;
  date: string;
  current_price: number;
  has_unusual_activity: boolean;
  options_activity: UnusualOption[];
  calls_volume: number;
  puts_volume: number;
  calls_percentage: number;
  puts_percentage: number;
}

const ResultsPage: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [scoreData, setScoreData] = useState<UnusualScoreData | null>(null);
  const [optionsData, setOptionsData] = useState<TickerOptionsData | null>(null);
  const [activeTab, setActiveTab] = useState<'score' | 'activity'>('score');

  useEffect(() => {
    const fetchData = async () => {
      if (!ticker) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch unusualness score
        const scoreResponse = await fetch(`${API_URL}/unusualness-score/${ticker}`);
        
        if (!scoreResponse.ok) {
          throw new Error(`Failed to fetch score data: ${scoreResponse.status}`);
        }
        
        const scoreData = await scoreResponse.json();
        setScoreData(scoreData);
        
        // Fetch options activity
        const optionsResponse = await fetch(`${API_URL}/ticker/${ticker}`);
        
        if (!optionsResponse.ok) {
          throw new Error(`Failed to fetch options data: ${optionsResponse.status}`);
        }
        
        const optionsData = await optionsResponse.json();
        setOptionsData(optionsData);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [ticker]);

  const handleBack = () => {
    navigate('/');
  };

  if (loading) {
    return (
      <div>
        <header>
          <div className="container header-content">
            <h1 className="app-title">Options Analyzer</h1>
            <button className="back-button" onClick={handleBack}>
              ← Back to Search
            </button>
          </div>
        </header>
        <div className="container loading-container">
          <p>Loading data for {ticker}...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <header>
          <div className="container header-content">
            <h1 className="app-title">Options Analyzer</h1>
            <button className="back-button" onClick={handleBack}>
              ← Back to Search
            </button>
          </div>
        </header>
        <div className="container error-container">
          <h2 className="error-title">Error Loading Data</h2>
          <p className="error-message">{error}</p>
          <button className="error-button" onClick={handleBack}>
            Go Back to Search
          </button>
        </div>
      </div>
    );
  }

  const scoreColor = (score: number) => {
    if (score <= 3) return '#64748b'; // Normal - gray
    if (score <= 6) return '#f59e0b'; // Somewhat unusual - amber
    return '#ef4444'; // Highly unusual - red
  };

  return (
    <div>
      <header>
        <div className="container header-content">
          <h1 className="app-title">Options Analyzer</h1>
          <button className="back-button" onClick={handleBack}>
            ← Back to Search
          </button>
        </div>
      </header>

      <div className="container results-container">
        <div className="ticker-header">
          <div className="ticker-info">
            <h1>{ticker}</h1>
            <div className="ticker-price">
              ${scoreData?.current_price.toFixed(2)}
            </div>
          </div>
          
          {optionsData && (
            <div className="sentiment-info">
              <div style={{ textAlign: 'right', marginBottom: '4px' }}>
                Call/Put Ratio
              </div>
              <div className="sentiment-bar">
                <div 
                  className="calls-bar" 
                  style={{ width: `${optionsData.calls_percentage}%` }} 
                />
                <div 
                  className="puts-bar" 
                  style={{ width: `${optionsData.puts_percentage}%` }} 
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <div>Calls {optionsData.calls_percentage.toFixed(1)}%</div>
                <div>Puts {optionsData.puts_percentage.toFixed(1)}%</div>
              </div>
            </div>
          )}
        </div>

        <div className="tab-container">
          <div className="tab-buttons">
            <button 
              className={`tab-button ${activeTab === 'score' ? 'active' : ''}`}
              onClick={() => setActiveTab('score')}
            >
              Unusualness Score
            </button>
            <button 
              className={`tab-button ${activeTab === 'activity' ? 'active' : ''}`}
              onClick={() => setActiveTab('activity')}
            >
              Options Activity
            </button>
          </div>
        </div>

        {activeTab === 'score' && scoreData && (
          <ScoreDisplay 
            score={scoreData.score} 
            interpretation={scoreData.interpretation} 
            components={scoreData.components}
            scoreColor={scoreColor(scoreData.score)}
          />
        )}

        {activeTab === 'activity' && optionsData && (
          <OptionsTable options={optionsData.options_activity} />
        )}

        {activeTab === 'activity' && optionsData?.options_activity.length === 0 && (
          <div className="no-data">
            <p>No unusual options activity detected for {ticker}.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsPage;