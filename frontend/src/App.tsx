import { useState } from 'react';
import { Layout, message } from 'antd';
import { StrategyBuilder } from './components/StrategyBuilder';
import { BacktestChart } from './components/BacktestChart';
import { BacktestConfig, BacktestResult, Strategy } from './types/strategy';
import './App.css';

const { Header, Content } = Layout;

const defaultStrategy: Strategy = {
  id: 'sma-adx',
  name: 'SMA with ADX Strategy',
  description: 'A simple moving average strategy with ADX filter',
  params: [
    {
      name: 'fast_period',
      type: 'number' as const,
      default: 5,
      min: 2,
      max: 200,
      description: 'Fast moving average period'
    },
    {
      name: 'slow_period',
      type: 'number' as const,
      default: 20,
      min: 5,
      max: 200,
      description: 'Slow moving average period'
    }
  ]
};

function App() {
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [messageApi, contextHolder] = message.useMessage();

  const handleSubmit = async (config: BacktestConfig) => {
    try {
      messageApi.loading('Running backtest...');
      const response = await fetch('http://localhost:8000/api/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });
      
      if (!response.ok) {
        throw new Error('Backtest failed');
      }
      
      const result = await response.json();
      setBacktestResult(result);
      messageApi.success('Backtest completed');
    } catch (error) {
      console.error('Backtest error:', error);
      messageApi.error('Failed to run backtest');
    }
  };

  return (
    <Layout className="app-layout">
      {contextHolder}
      <Header className="header">
        <h1>Shuibi MT</h1>
      </Header>
      <Content className="content">
        <div className="strategy-section">
          <StrategyBuilder strategy={defaultStrategy} onSubmit={handleSubmit} />
        </div>
        <div className="chart-section">
          {backtestResult && <BacktestChart data={backtestResult} />}
        </div>
      </Content>
    </Layout>
  );
}

export default App; 