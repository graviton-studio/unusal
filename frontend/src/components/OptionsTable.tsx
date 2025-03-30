import React from 'react';

interface Option {
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

interface OptionsTableProps {
  options: Option[];
}

const OptionsTable: React.FC<OptionsTableProps> = ({ options }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="options-card">
      <h2 className="options-title">Unusual Options Activity</h2>
      
      <table className="options-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Strike</th>
            <th>Expiration</th>
            <th>Days</th>
            <th>IV%</th>
            <th>Volume</th>
            <th>OI</th>
            <th>Vol/OI</th>
            <th>Price</th>
            <th>ITM</th>
          </tr>
        </thead>
        <tbody>
          {options.map((option) => (
            <tr key={option.option_symbol}>
              <td className={option.option_type.toLowerCase()}>
                {option.option_type.toUpperCase()}
              </td>
              <td>${option.strike_price.toFixed(2)}</td>
              <td>{formatDate(option.expiration_date)}</td>
              <td>{option.days_to_expiry}</td>
              <td>{option.implied_volatility.toFixed(1)}%</td>
              <td>{option.current_volume.toLocaleString()}</td>
              <td>{option.open_interest.toLocaleString()}</td>
              <td className="ratio">{option.volume_ratio.toFixed(1)}x</td>
              <td>${option.last_price.toFixed(2)}</td>
              <td>{option.in_the_money ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default OptionsTable;