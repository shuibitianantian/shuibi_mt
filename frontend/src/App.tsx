import { useState, useEffect } from 'react';
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

function App() {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [historicalData, setHistoricalData] = useState<any>(null);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs(new Date('2020-02-02')),
    dayjs(new Date('2021-01-02'))
  ]);

  const [messageApi, contextHolder] = message.useMessage();
  const [isLoading, setIsLoading] = useState(false);
  const [messageKey, setMessageKey] = useState<string>('');

  // 获取历史数据
  const fetchHistoricalData = async (start: Dayjs, end: Dayjs) => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/historical/BTCUSDT?` +
        `start_time=${start.format('YYYY-MM-DD')}&` +
        `end_time=${end.format('YYYY-MM-DD')}`
      );
      if (!response.ok) {
        throw new Error('Failed to fetch historical data');
      }
      const data = await response.json();
      setHistoricalData(data);
    } catch (error) {
      messageApi.error('Failed to fetch historical data');
    } finally {
      setIsLoading(false);
    }
  };

  // 在组件加载和日期改变时获取历史数据
  useEffect(() => {
    fetchHistoricalData(dateRange[0], dateRange[1]);
  }, [dateRange]);

  const handleSubmit = async (config: BacktestConfig) => {
    const msgKey = 'backtest';
    try {
      setMessageKey(msgKey);
      messageApi.loading({
        content: 'Running backtest...',
        key: msgKey,
        duration: 0,
      });

      const response = await fetch('http://localhost:8000/api/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...config,
          startTime: dateRange[0].format('YYYY-MM-DD'),
          endTime: dateRange[1].format('YYYY-MM-DD'),
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backtest failed: ${errorText}`);
      }

      const result = await response.json();
      console.log('Received result:', result);

      setBacktestResult(result);
      setDrawerVisible(false);

      messageApi.success({
        content: 'Backtest completed',
        key: msgKey,
        duration: 2,
      });
    } catch (error) {
      messageApi.error({
        content: 'Failed to run backtest: ' + (error as Error).message,
        key: msgKey,
        duration: 3,
      });
    }
  };

  return (
    <Layout className="app-layout">
      {contextHolder}
      <Header className="header">
        <h1>Shuibi MT</h1>
        <div className="header-controls">
          <RangePicker
            value={dateRange}
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                setDateRange([dates[0], dates[1]]);
                // fetchHistoricalData 会通过 useEffect 自动调用
              }
            }}
            style={{ marginRight: 16 }}
          />
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
        <div className="chart-section">
          {isLoading ? (
            <div style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Spin size="large" tip="Loading data..." />
            </div>
          ) : (
            historicalData && (
              <BacktestChart
                data={backtestResult || {
                  price_data: historicalData.price_data,
                  equity: [],
                  trades: [],
                  stats: {
                    'Total Return (%)': 0,
                    'Annual Return (%)': 0,
                    'Max Drawdown (%)': 0,
                    'Sharpe Ratio': 0,
                    'Win Rate (%)': 0
                  }
                }}
              />
            )
          )}
        </div>
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
}

export default App; 