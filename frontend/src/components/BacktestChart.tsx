import { CloseSquareFilled, FundTwoTone } from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  DatePicker,
  Drawer,
  Row,
  Select,
  Statistic,
  Tooltip,
  message,
} from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { BacktestConfig, BacktestResult } from "../types/strategy";
import { useChart } from "./chart/hooks/useChart";
import { LoadingSpinner } from "./chart/LoadingSpinner";
import { StrategyBuilder } from "./StrategyBuilder";

export const BacktestChart = () => {
  const [selectedRange, setSelectedRange] = useState<{
    start: number;
    end: number;
  } | null>(null);

  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(
    null
  );
  const [isLoadingBackRest, setIsLoadingBacktest] = useState(false);
  const [timeframe, setTimeframe] = useState("1m");

  const {
    chartContainerRef,
    clearOverlay,
    isLoading: isLoadingData,
  } = useChart({
    data: backtestResult,
    selectRangeConfig: {
      rangeSelection: selectedRange,
      setRangeSelection: setSelectedRange,
    },
    interval: timeframe,
  });

  useEffect(() => {
    clearOverlay();
  }, [timeframe]);

  const [drawerVisible, setDrawerVisible] = useState(false);

  const handleSubmit = async (config: BacktestConfig) => {
    setIsLoadingBacktest(true);
    try {
      console.log(new Date((selectedRange?.start || 0) * 1000).toISOString());
      const response = await fetch("http://localhost:8000/api/backtest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...config,
          symbol: "BTCUSDT",
          startTime: new Date((selectedRange?.start || 0) * 1000).toISOString(),
          endTime: new Date((selectedRange?.end || 0) * 1000).toISOString(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        message.error(errorData.detail || "Failed to run backtest");
        return;
      }

      const data = await response.json();
      setBacktestResult(data);
      setDrawerVisible(false);
    } catch (error) {
      message.error("Network error occurred");
    } finally {
      setIsLoadingBacktest(false);
    }
  };

  return (
    <div style={{ width: "100%" }}>
      {backtestResult !== null && (
        <Row gutter={[8, 8]} style={{ marginBottom: 24 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Total Return"
                value={backtestResult.stats["Total Return (%)"]}
                precision={2}
                suffix="%"
                valueStyle={{
                  color:
                    backtestResult.stats["Total Return (%)"] >= 0
                      ? "#3f8600"
                      : "#cf1322",
                  fontSize: "14px",
                }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Annual Return"
                value={backtestResult.stats["Annual Return (%)"]}
                precision={2}
                suffix="%"
                valueStyle={{
                  color:
                    backtestResult.stats["Annual Return (%)"] >= 0
                      ? "#3f8600"
                      : "#cf1322",
                  fontSize: "14px",
                }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Max Drawdown"
                value={backtestResult.stats["Max Drawdown (%)"]}
                precision={2}
                suffix="%"
                valueStyle={{
                  color: "#cf1322",
                  fontSize: "14px",
                }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Sharpe Ratio"
                value={backtestResult.stats["Sharpe Ratio"]}
                precision={2}
                valueStyle={{
                  color:
                    backtestResult.stats["Sharpe Ratio"] >= 1
                      ? "#3f8600"
                      : "#cf1322",
                  fontSize: "14px",
                }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Win Rate"
                value={backtestResult.stats["Win Rate (%)"]}
                precision={2}
                suffix="%"
                valueStyle={{
                  color:
                    backtestResult.stats["Win Rate (%)"] >= 50
                      ? "#3f8600"
                      : "#cf1322",
                  fontSize: "14px",
                }}
              />
            </Card>
          </Col>
        </Row>
      )}
      <div
        ref={chartContainerRef}
        style={{ width: "100%", position: "relative" }}
      >
        {selectedRange &&
          Boolean(selectedRange.start) &&
          Boolean(selectedRange.end) && (
            <div
              style={{
                position: "absolute",
                top: "10px",
                left: "10px",
                zIndex: 1000,
                background: "rgba(255, 255, 255, 0.9)",
                padding: "8px 12px",
                borderRadius: "4px",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ color: "rgba(0, 0, 0, 0.45)", fontSize: "12px" }}>
                Selected range:
              </span>
              <DatePicker.RangePicker
                showTime
                disabled={true}
                value={[
                  dayjs(selectedRange.start * 1000),
                  dayjs(selectedRange.end * 1000),
                ]}
                style={{
                  border: "none",
                  background: "transparent",
                }}
                suffixIcon={null}
                allowClear={false}
              />
              <Tooltip title="backtest">
                <Button
                  icon={<FundTwoTone />}
                  size="small"
                  type="text"
                  onClick={() => setDrawerVisible(true)}
                />
              </Tooltip>
              <CloseSquareFilled
                style={{
                  color: "#ff4d4f",
                  cursor: "pointer",
                  fontSize: "16px",
                  transition: "all 0.3s",
                  padding: "4px",
                  borderRadius: "50%",
                }}
                onClick={() => clearOverlay()}
              />
            </div>
          )}
        <Select
          onChange={setTimeframe}
          style={{
            width: 100,
            position: "absolute",
            top: 0,
            right: 90,
            zIndex: 100,
          }}
          value={timeframe}
        >
          <Select.Option value="1m">1 min</Select.Option>
          <Select.Option value="5m">5 min</Select.Option>
          <Select.Option value="15m">15 min</Select.Option>
          <Select.Option value="1h">1 hour</Select.Option>
          <Select.Option value="1d">1 Day</Select.Option>
        </Select>
      </div>
      <LoadingSpinner isLoading={isLoadingData || isLoadingBackRest} />
      <Drawer
        title="Strategy Settings"
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        <StrategyBuilder onSubmit={handleSubmit} />
      </Drawer>
    </div>
  );
};
