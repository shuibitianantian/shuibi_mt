import {
  FundTwoTone,
  ClearOutlined,
  CloudDownloadOutlined,
} from "@ant-design/icons";
import { Button, Drawer, Select, message, Table, Typography } from "antd";
import { useEffect, useState } from "react";
import { BacktestConfig, BacktestResult } from "../types/strategy";
import { useChart } from "./chart/hooks/useChart";
import { LoadingSpinner } from "./chart/LoadingSpinner";
import { StrategyBuilder } from "./StrategyBuilder";
import { downloadLatestData } from "apis/sync";
import TableDatetime from "./TableDatetime";
import { Time } from "lightweight-charts";

// 添加一个安全的数值格式化函数
const formatNumber = (value: number, precision: number = 2) => {
  if (!isFinite(value)) return "0.00";
  if (Math.abs(value) > 1e6) return value.toExponential(precision);
  return value.toFixed(precision);
};

const StatItem = ({
  title,
  value,
  suffix = "",
}: {
  title: string;
  value: number;
  suffix?: string;
}) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "4px 12px",
      borderRadius: "4px",
      backgroundColor: "rgba(0,0,0,0.02)",
    }}
  >
    <span
      style={{
        color: "rgba(0, 0, 0, 0.45)",
        fontSize: "12px",
        marginBottom: "2px",
      }}
    >
      {title}
    </span>
    <span
      style={{
        color:
          value > 0 ? "#26a69a" : value < 0 ? "#ef5350" : "rgba(0, 0, 0, 0.85)",
        fontSize: "14px",
        fontWeight: "500",
        fontFamily: "monospace",
      }}
    >
      {formatNumber(value)}
      {suffix}
    </span>
  </div>
);

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

  // 添加状态来跟踪当前高亮的交易
  const [highlightedTradeTime, setHighlightedTradeTime] = useState<
    string | null
  >(null);

  const {
    chartContainerRef,
    clearOverlay,
    isLoading: isLoadingData,
    loadInitialData,
    candlestickSeriesRef,
  } = useChart({
    data: backtestResult,
    selectRangeConfig: {
      rangeSelection: selectedRange,
      setRangeSelection: setSelectedRange,
    },
    interval: timeframe,
    setHighlightedTradeTime,
  });

  useEffect(() => {
    clearOverlay();
  }, [timeframe]);

  const [drawerVisible, setDrawerVisible] = useState(false);

  const handleSubmit = async (config: BacktestConfig) => {
    setIsLoadingBacktest(true);
    try {
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

  const handleClear = () => {
    setSelectedRange(null);
    setBacktestResult(null);
    clearOverlay();
    loadInitialData();
  };

  const formatRangeTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);

    switch (timeframe) {
      case "1m":
      case "5m":
      case "15m":
        return date
          .toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })
          .replace(",", "");
      case "1h":
      case "4h":
        return date
          .toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            hour12: false,
          })
          .replace(",", "");
      case "1d":
        return date
          .toLocaleString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          })
          .replace(",", "");
      default:
        return date.toLocaleString();
    }
  };

  // 修改 columns 定义
  const columns = [
    {
      title: "Time",
      dataIndex: "timestamp",
      key: "timestamp",
      render: (text: string) => <TableDatetime time={text} />,
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
      render: (text: string) => (
        <span style={{ color: text === "BUY" ? "#26a69a" : "#ef5350" }}>
          {text}
        </span>
      ),
    },
    {
      title: "Price",
      dataIndex: "price",
      key: "price",
      render: (value: number) => formatNumber(value),
      wdith: 100,
    },
    {
      title: "Size",
      dataIndex: "size",
      key: "size",
      render: (value: number) => (
        <Typography.Text ellipsis={{ tooltip: true }}>
          {formatNumber(value, 3)}
        </Typography.Text>
      ),
    },
    {
      title: "PnL",
      dataIndex: "pnl",
      key: "pnl",
      render: (value: number) => (
        <span
          style={{
            color: value > 0 ? "#26a69a" : value < 0 ? "#ef5350" : "inherit",
          }}
        >
          {formatNumber(value)} %
        </span>
      ),
      width: 100,
    },
    {
      title: "Position",
      dataIndex: "position",
      key: "position",
      render: (value: number) => (
        <span
          style={{
            color: value > 0 ? "#26a69a" : value < 0 ? "#ef5350" : "inherit",
          }}
        >
          {value.toFixed(3)}
        </span>
      ),
    },
    {
      title: "Equity",
      dataIndex: "equity",
      key: "equity",
      render: (value: number) => formatNumber(value),
    },
  ];

  return (
    <div style={{ height: "100%", display: "flex", gap: "8px" }}>
      {/* 左侧图表区域 */}
      <div style={{ flex: "1", position: "relative" }}>
        {/* 选择区域和运行按钮 */}
        <div
          style={{
            position: "absolute",
            top: backtestResult ? 40 : 10,
            right: backtestResult ? 90 : 320,
            zIndex: 200,
          }}
        >
          {selectedRange && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(0, 0, 0, 0.06)",
                padding: "4px 8px",
                borderRadius: "4px",
                border: "1px solid rgba(0, 0, 0, 0.1)",
              }}
            >
              <Button
                type="text"
                icon={
                  <ClearOutlined style={{ fontSize: "12px", opacity: 0.6 }} />
                }
                onClick={handleClear}
                size="small"
                style={{ padding: "0 4px" }}
              />
              <span
                style={{
                  fontSize: "12px",
                  color: "#131722",
                  fontFamily: "monospace",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <span style={{ opacity: 0.6 }}>Range:</span>
                <span style={{ fontWeight: 500 }}>
                  {formatRangeTime(selectedRange.start)}
                </span>
                <span style={{ opacity: 0.6 }}>-</span>
                <span style={{ fontWeight: 500 }}>
                  {formatRangeTime(selectedRange.end)}
                </span>
              </span>
              <Button
                type="primary"
                size="small"
                icon={
                  <FundTwoTone style={{ fontSize: "14px", color: "#fff" }} />
                }
                onClick={() => setDrawerVisible(true)}
                style={{
                  background: "linear-gradient(to right, #1976d2, #2962ff)",
                  borderColor: "transparent",
                  padding: "0 12px",
                  height: "22px",
                  boxShadow: "0 2px 4px rgba(41, 98, 255, 0.1)",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  borderRadius: "3px",
                  fontSize: "12px",
                  fontWeight: 500,
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    "linear-gradient(to right, #1565c0, #1976d2)";
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow =
                    "0 4px 8px rgba(41, 98, 255, 0.2)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    "linear-gradient(to right, #1976d2, #2962ff)";
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow =
                    "0 2px 4px rgba(41, 98, 255, 0.1)";
                }}
              >
                Run
              </Button>
            </div>
          )}
        </div>

        {backtestResult && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: "8px",
              position: "absolute",
              top: 32,
              left: 90,
              padding: "8px",
              borderRadius: "8px",
              backgroundColor: "white",
              boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
              border: "1px solid rgba(0, 0, 0, 0.1)",
              zIndex: 2,
              width: "fit-content",
            }}
          >
            <StatItem
              title="Total Return"
              value={backtestResult.stats["Total Return (%)"]}
              suffix="%"
            />
            <StatItem
              title="Annual Return"
              value={backtestResult.stats["Annual Return (%)"]}
              suffix="%"
            />
            <StatItem
              title="Max Drawdown"
              value={-backtestResult.stats["Max Drawdown (%)"]}
              suffix="%"
            />
            <StatItem
              title="Sharpe"
              value={backtestResult.stats["Sharpe Ratio"]}
            />
            <StatItem
              title="Win Rate"
              value={backtestResult.stats["Win Rate (%)"]}
              suffix="%"
            />
          </div>
        )}

        <div style={{ position: "absolute", top: 10, right: 90, zIndex: 200 }}>
          <Button
            icon={<CloudDownloadOutlined />}
            size="small"
            onClick={downloadLatestData}
            style={{ marginRight: 8 }}
          >
            Sync Data
          </Button>
          <Select
            onChange={setTimeframe}
            value={timeframe}
            size="small"
            style={{ width: 100 }}
          >
            <Select.Option value="1m">1 min</Select.Option>
            <Select.Option value="5m">5 mins</Select.Option>
            <Select.Option value="15m">15 mins</Select.Option>
            <Select.Option value="1h">1 hour</Select.Option>
            <Select.Option value="1d">1 Day</Select.Option>
          </Select>
        </div>

        {/* 图表区域 */}
        <div
          ref={chartContainerRef}
          style={{
            height: "100%",
            borderRadius: "4px",
            overflow: "hidden",
            backgroundColor: "white",
          }}
        >
          <LoadingSpinner isLoading={isLoadingData || isLoadingBackRest} />
        </div>
      </div>

      {/* 右侧交易记录表格 */}
      {backtestResult && (
        <div
          style={{
            width: "800px",
            backgroundColor: "white",
            borderRadius: "4px",
            overflow: "hidden",
          }}
        >
          <Table
            dataSource={backtestResult.trades.map((trade, index) => ({
              ...trade,
              equity: backtestResult.equity[index]?.equity || 0,
              position:
                backtestResult.equity.find(
                  (e) => e.timestamp === trade.timestamp
                )?.position || 0,
            }))}
            columns={columns}
            size="small"
            pagination={false}
            scroll={{ y: "calc(100vh - 200px)" }}
            onRow={(record) => ({
              onMouseEnter: () => {
                setHighlightedTradeTime(record.timestamp);
                // 更新图表标记
                if (candlestickSeriesRef.current && backtestResult) {
                  const markers = backtestResult.trades.map((trade) => ({
                    time: (new Date(trade.timestamp + "Z").getTime() /
                      1000) as Time,
                    position: trade.action === "BUY" ? "belowBar" : "aboveBar",
                    color: trade.action === "BUY" ? "#26a69a" : "#ef5350",
                    shape: trade.action === "BUY" ? "arrowUp" : "arrowDown",
                    size: trade.timestamp === record.timestamp ? 2 : 1,
                    text:
                      trade.timestamp === record.timestamp
                        ? `${trade.action} · ${formatNumber(
                            trade.size,
                            3
                          )} @ ${formatNumber(trade.price)}`
                        : "",
                  }));
                  candlestickSeriesRef.current.setMarkers(markers);
                }
              },
              onMouseLeave: () => {
                setHighlightedTradeTime(null);
                // 恢复原始标记
                if (candlestickSeriesRef.current) {
                  const markers = backtestResult.trades.map((trade) => ({
                    time: (new Date(trade.timestamp + "Z").getTime() /
                      1000) as Time,
                    position: trade.action === "BUY" ? "belowBar" : "aboveBar",
                    color: trade.action === "BUY" ? "#26a69a" : "#ef5350",
                    shape: trade.action === "BUY" ? "arrowUp" : "arrowDown",
                    size: 1,
                    text: "",
                  }));
                  candlestickSeriesRef.current.setMarkers(markers);
                }
              },
              style: {
                backgroundColor:
                  record.timestamp === highlightedTradeTime
                    ? "rgba(0, 0, 0, 0.04)"
                    : "inherit",
              },
            })}
          />
        </div>
      )}

      {/* 策略设置抽屉 */}
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
