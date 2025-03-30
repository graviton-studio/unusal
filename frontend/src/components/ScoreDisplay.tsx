import React from 'react';

interface ScoreDisplayProps {
  score: number;
  interpretation: string[];
  components: {
    volume_oi_ratio: number;
    put_call_ratio: number;
    iv_vs_historical: number;
    skew_analysis: number;
  };
  scoreColor: string;
}

const ScoreDisplay: React.FC<ScoreDisplayProps> = ({ score, interpretation, components, scoreColor }) => {
  const formatToday = () => {
    const date = new Date();
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getInterpretationTitle = () => {
    if (score <= 3) return 'Normal Options Activity';
    if (score <= 6) return 'Somewhat Unusual Activity';
    return 'Highly Unusual Activity!';
  };

  return (
    <div className="score-card">
      <div className="score-header">
        <h2 className="score-title">Options Unusualness Score</h2>
        <div className="date-display">{formatToday()}</div>
      </div>

      <div className="score-display">
        <div 
          className="score-circle" 
          style={{ 
            backgroundColor: scoreColor,
            boxShadow: `0 0 20px ${scoreColor}40`
          }}
        >
          {score}
        </div>

        <div className="score-interpretation">
          <h3 className="interpretation-title">{getInterpretationTitle()}</h3>
          
          {interpretation.length > 0 ? (
            <ul className="interpretation-list">
              {interpretation.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>No specific observations for this ticker.</p>
          )}
        </div>
      </div>

      <div className="component-grid">
        <div className="component-card">
          <div className="component-name">Volume to Open Interest</div>
          <div className="component-value" style={{ color: components.volume_oi_ratio > 1.5 ? '#ef4444' : '#64748b' }}>
            {components.volume_oi_ratio.toFixed(2)}
          </div>
        </div>

        <div className="component-card">
          <div className="component-name">Put-Call Ratio</div>
          <div className="component-value" style={{ color: components.put_call_ratio > 2 ? '#ef4444' : '#64748b' }}>
            {components.put_call_ratio.toFixed(2)}
          </div>
        </div>

        <div className="component-card">
          <div className="component-name">IV vs Historical</div>
          <div className="component-value" style={{ color: components.iv_vs_historical > 2 ? '#ef4444' : '#64748b' }}>
            {components.iv_vs_historical.toFixed(2)}
          </div>
        </div>

        <div className="component-card">
          <div className="component-name">Options Skew</div>
          <div className="component-value" style={{ color: components.skew_analysis > 1.5 ? '#ef4444' : '#64748b' }}>
            {components.skew_analysis.toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScoreDisplay;