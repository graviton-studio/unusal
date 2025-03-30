import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SearchPage: React.FC = () => {
  const [ticker, setTicker] = useState('');
  const navigate = useNavigate();

  const popularTickers = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
    'META', 'NVDA', 'SPY', 'QQQ', 'AMD'
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (ticker.trim()) {
      navigate(`/ticker/${ticker.trim().toUpperCase()}`);
    }
  };

  const handlePopularTickerClick = (symbol: string) => {
    navigate(`/ticker/${symbol}`);
  };

  return (
    <div className="search-container">
      <h1 className="search-title">Options Unusualness Analyzer</h1>
      <p className="search-subtitle">
        Analyze options activity and detect unusual patterns with our advanced scoring system.
      </p>

      <form className="search-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="search-input"
          placeholder="Enter stock ticker (e.g., AAPL)"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          autoFocus
        />
        <button type="submit" className="search-button">
          Analyze Options
        </button>
      </form>

      <div className="popular-tickers">
        <h3 className="popular-tickers-title">POPULAR TICKERS</h3>
        <div className="ticker-chips">
          {popularTickers.map((symbol) => (
            <div
              key={symbol}
              className="ticker-chip"
              onClick={() => handlePopularTickerClick(symbol)}
            >
              {symbol}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchPage;