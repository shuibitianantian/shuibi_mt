import React, { useState } from "react";
import {
  Form,
  Input,
  InputNumber,
  DatePicker,
  Button,
  Select,
  Space,
  Row,
  Col,
} from "antd";
import { BacktestConfig, Strategy } from "../types/strategy";
import dayjs from "dayjs";

interface Props {
  onSubmit: (config: BacktestConfig) => void;
}

const strategies: Strategy[] = [
  {
    id: "sma-adx",
    name: "SMA with ADX Strategy",
    description: "A simple moving average strategy with ADX filter",
    params: [
      {
        name: "fast_period",
        type: "number" as const,
        default: 5,
        min: 2,
        max: 200,
        description: "Fast moving average period",
      },
      {
        name: "slow_period",
        type: "number" as const,
        default: 20,
        min: 5,
        max: 200,
        description: "Slow moving average period",
      },
    ],
  },
  {
    id: "macd",
    name: "MACD Strategy",
    description: "Moving Average Convergence Divergence strategy",
    params: [
      {
        name: "fast_period",
        type: "number" as const,
        default: 12,
        min: 2,
        max: 100,
        description: "Fast EMA period",
      },
      {
        name: "slow_period",
        type: "number" as const,
        default: 26,
        min: 5,
        max: 200,
        description: "Slow EMA period",
      },
      {
        name: "signal_period",
        type: "number" as const,
        default: 9,
        min: 2,
        max: 50,
        description: "Signal line period",
      },
    ],
  },
  // 可以添加更多策略...
];

export const StrategyBuilder: React.FC<Props> = ({ onSubmit }) => {
  const [form] = Form.useForm();
  const [selectedStrategy, setSelectedStrategy] = useState(strategies[0]);

  const handleStrategyChange = (strategyId: string) => {
    const strategy = strategies.find((s) => s.id === strategyId);
    if (strategy) {
      setSelectedStrategy(strategy);
      // 重置表单值为新策略的默认值
      form.setFieldsValue({
        ...strategy.params.reduce(
          (acc, param) => ({
            ...acc,
            [param.name]: param.default,
          }),
          {}
        ),
      });
    }
  };

  const handleSubmit = (values: any) => {
    const config: BacktestConfig = {
      strategyId: selectedStrategy.id,
      params: {},
      symbol: values.symbol,
      interval: values.interval,
      initialCapital: values.initialCapital,
    };

    selectedStrategy.params.forEach((param) => {
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
        symbol: "BTCUSDT",
        interval: "1d",
        initialCapital: 10000,
        dateRange: [dayjs().subtract(1, "year"), dayjs()],
        ...selectedStrategy.params.reduce(
          (acc, param) => ({
            ...acc,
            [param.name]: param.default,
          }),
          {}
        ),
      }}
    >
      <Select
        value={selectedStrategy.id}
        onChange={handleStrategyChange}
        style={{ width: "100%", marginBottom: 16 }}
      >
        {strategies.map((strategy) => (
          <Select.Option key={strategy.id} value={strategy.id}>
            {strategy.name}
          </Select.Option>
        ))}
      </Select>

      <p style={{ color: "rgba(0, 0, 0, 0.45)", margin: 0, fontSize: 12 }}>
        {selectedStrategy.description}
      </p>

      <div>
        <h4>Strategy Parameters</h4>
        <Row gutter={[16, 0]}>
          {selectedStrategy.params.map((param) => (
            <Col span={12} key={param.name}>
              <Form.Item
                label={param.name}
                name={param.name}
                tooltip={param.description}
                style={{ marginBottom: 12 }}
              >
                <InputNumber
                  min={param.min}
                  max={param.max}
                  style={{ width: "100%" }}
                />
              </Form.Item>
            </Col>
          ))}
        </Row>
      </div>
      <div>
        <h4 style={{ marginBottom: 16 }}>Backtest Settings</h4>
        <Row gutter={[16, 0]}>
          <Col span={12}>
            <Form.Item label="Interval" name="interval">
              <Select style={{ width: "100%" }}>
                <Select.Option value="1m">1 Minute</Select.Option>
                <Select.Option value="5m">5 Minutes</Select.Option>
                <Select.Option value="15m">15 Minutes</Select.Option>
                <Select.Option value="1h">1 Hour</Select.Option>
                <Select.Option value="4h">4 Hours</Select.Option>
                <Select.Option value="1d">1 Day</Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Initial Capital" name="initialCapital">
              <InputNumber
                style={{ width: "100%" }}
                formatter={(value) =>
                  `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
                }
                parser={(value) => value!.replace(/\$\s?|(,*)/g, "")}
              />
            </Form.Item>
          </Col>
        </Row>
      </div>

      <Form.Item>
        <Button type="primary" htmlType="submit" block>
          Run Backtest
        </Button>
      </Form.Item>
    </Form>
  );
};
