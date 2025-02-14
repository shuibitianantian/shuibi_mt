import { useState } from 'react';
import { Layout, DatePicker, Button, Drawer, message, Row, Col, Spin } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { StrategyBuilder } from './components/StrategyBuilder';
import { BacktestChart } from './components/BacktestChart';
import { BacktestConfig, BacktestResult, Strategy } from './types/strategy';
import dayjs, { Dayjs } from 'dayjs';
import './App.css';

const { Header, Content } = Layout;
const { RangePicker } = DatePicker;

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

export default () => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [messageApi, contextHolder] = message.useMessage();
  const [isLoading, setIsLoading] = useState(false);
  const [messageKey, setMessageKey] = useState<string>('');

  const handleSubmit = async (config: BacktestConfig) => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8000/api/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error('Failed to run backtest');
      }

      const result = await response.json();
      setBacktestResult(result);
    } catch (error) {
      console.error('Error running backtest:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout className="app-layout">
      {contextHolder}
      <Header className="header">
        <h1>Shuibi MT</h1>
        <div className="header-controls">
          <Button
            type="primary"
            icon={<SettingOutlined />}
            onClick={() => setDrawerVisible(true)}
          >
            Strategy Settings
          </Button>
        </div>
      </Header>
      <Content className="content">
        <BacktestChart data={backtestResult} />
      </Content>
      <Drawer
        title="Strategy Settings"
        placement="right"
        width={400}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        <StrategyBuilder strategy={defaultStrategy} onSubmit={handleSubmit} />
      </Drawer>
    </Layout>
  );
}; 