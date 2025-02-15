import React from 'react';
import { Form, Input, InputNumber, DatePicker, Button, Select } from 'antd';
import { BacktestConfig, Strategy } from '../types/strategy';
import dayjs from 'dayjs';

interface Props {
  onSubmit: (config: BacktestConfig) => void;
}

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

export const StrategyBuilder: React.FC<Props> = ({ onSubmit }) => {
  const [form] = Form.useForm();

  const strategy = defaultStrategy;

  const handleSubmit = (values: any) => {
    const config: BacktestConfig = {
      strategyId: strategy.id,
      params: {},
      symbol: values.symbol,
      interval: values.interval,
      initialCapital: values.initialCapital
    };

    // 处理策略参数
    strategy.params.forEach(param => {
      config.params[param.name] = values[param.name];
    });

    onSubmit(config);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        symbol: 'BTCUSDT',
        interval: '1d',
        initialCapital: 10000,
        dateRange: [dayjs().subtract(1, 'year'), dayjs()],
        ...strategy.params.reduce((acc, param) => ({
          ...acc,
          [param.name]: param.default
        }), {})
      }}
    >
      <h2>{strategy.name}</h2>
      <p>{strategy.description}</p>

      {/* 策略参数 */}
      {strategy.params.map(param => (
        <Form.Item
          key={param.name}
          label={param.name}
          name={param.name}
          tooltip={param.description}
        >
          <InputNumber
            min={param.min}
            max={param.max}
            style={{ width: 200 }}
          />
        </Form.Item>
      ))}

      {/* 回测配置 */}
      <Form.Item label="Symbol" name="symbol">
        <Input style={{ width: 200 }} />
      </Form.Item>

      <Form.Item label="Interval" name="interval">
        <Select style={{ width: 200 }}>
          <Select.Option value="1m">1 Minute</Select.Option>
          <Select.Option value="5m">5 Minutes</Select.Option>
          <Select.Option value="15m">15 Minutes</Select.Option>
          <Select.Option value="1h">1 Hour</Select.Option>
          <Select.Option value="4h">4 Hours</Select.Option>
          <Select.Option value="1d">1 Day</Select.Option>
        </Select>
      </Form.Item>

      <Form.Item label="Initial Capital" name="initialCapital">
        <InputNumber
          style={{ width: 200 }}
          formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={value => value!.replace(/\$\s?|(,*)/g, '')}
        />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit">
          Run Backtest
        </Button>
      </Form.Item>
    </Form>
  );
}; 