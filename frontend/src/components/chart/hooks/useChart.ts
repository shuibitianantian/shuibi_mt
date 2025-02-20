import {
  ColorType,
  createChart,
  IChartApi,
  SeriesMarker,
  SeriesMarkerPosition,
  Time,
} from "lightweight-charts";
import { useCallback, useEffect, useRef, useState } from "react";
import { BacktestResult } from "types/strategy";
import { useChartData } from "./useChartData";
import dayjs from "dayjs";

interface IUseChartProps {
  data: BacktestResult | null;
  selectRangeConfig?: {
    rangeSelection: { start: number; end: number } | null;
    setRangeSelection: (range: { start: number; end: number } | null) => void;
  };
  interval: string;
}

interface ChartMarker extends SeriesMarker<Time> {
  position: SeriesMarkerPosition;
  color: string;
  shape: "circle" | "arrowUp" | "arrowDown";
  text?: string;
  size?: number;
}

export const useChart = ({
  data,
  selectRangeConfig,
  interval,
}: IUseChartProps) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const legendRef = useRef<HTMLDivElement | null>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const selectionStartRef = useRef<number | null>(null);
  const selectionEndRef = useRef<number | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { loadData, setupScrollHandler } = useChartData(
    candlestickSeriesRef,
    interval,
    setIsLoading
  );

  const formatTime = useCallback((time: number, interval: string) => {
    const date = new Date(time * 1000);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");

    switch (interval) {
      case "1m":
      case "5m":
      case "15m":
        return `${month}/${day} ${hours}:${minutes}`;
      case "1h":
        return `${month}/${day} ${hours}:00`;
      case "1d":
        return `${year}/${month}/${day}`;
      default:
        return `${month}/${day} ${hours}:${minutes}`;
    }
  }, []);

  const clearOverlay = useCallback(() => {
    if (overlayRef.current) {
      overlayRef.current.style.display = "none";
      overlayRef.current.style.width = "0px";
      selectionStartRef.current = null;
      selectionEndRef.current = null;
      selectRangeConfig?.setRangeSelection(null);
      chartRef.current?.applyOptions({
        handleScroll: true,
        handleScale: true,
      });
    }
  }, [selectRangeConfig]);

  // 初始加载数据
  useEffect(() => {
    const yesterday = dayjs().subtract(1, "day").format("YYYY-MM-DD HH:mm:ss");
    loadData(yesterday);
  }, [loadData]);

  // 设置图表和滚动监听
  useEffect(() => {
    if (chartContainerRef.current && !chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: window.innerHeight - 200,
        layout: {
          textColor: "rgba(33, 56, 77, 1)",
          background: { type: ColorType.Solid, color: "#ffffff" },
        },
        crosshair: {
          mode: 1,
          vertLine: {
            width: 1,
            color: "rgba(33, 56, 77, 0.1)",
            style: 0,
            labelBackgroundColor: "rgba(33, 56, 77, 0.1)",
            labelVisible: true,
          },
          horzLine: {
            visible: true,
            labelVisible: true,
            color: "rgba(33, 56, 77, 0.1)",
            width: 1,
            style: 0,
            labelBackgroundColor: "rgba(33, 56, 77, 0.1)",
          },
        },
        localization: {
          locale: "en-US",
          priceFormatter: (price: number) => price.toFixed(2),
          timeFormatter: (time: number) => formatTime(time, interval),
        },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderVisible: false,
          tickMarkFormatter: (time: number) => formatTime(time, interval),
        },
        grid: {
          vertLines: {
            color: "rgba(197, 203, 206, 0.2)",
          },
          horzLines: {
            color: "rgba(197, 203, 206, 0.2)",
          },
        },
        rightPriceScale: {
          visible: true,
          autoScale: true,
          borderVisible: false,
          scaleMargins: {
            top: 0.1,
            bottom: 0.4, // 为下方图表留出更多空间
          },
        },
        leftPriceScale: {
          visible: true,
          autoScale: true,
          borderVisible: false,
          scaleMargins: {
            top: 0.1,
            bottom: 0.4, // 为下方图表留出更多空间
          },
        },
      });

      // 添加K线图
      const candlestickSeries = chartRef.current.addCandlestickSeries({
        upColor: "#26a69a",
        downColor: "#ef5350",
        borderVisible: false,
        wickUpColor: "#26a69a",
        wickDownColor: "#ef5350",
        lastValueVisible: false,
        priceLineVisible: false,
        priceFormat: {
          type: "price",
          precision: 2,
          minMove: 0.01,
        },
      });

      candlestickSeriesRef.current = candlestickSeries;

      // 添加权益曲线作为子图
      const equitySeries = chartRef.current.addLineSeries({
        color: "rgba(76, 175, 80, 1)",
        lineWidth: 1,
        priceScaleId: "left",
        title: "Equity",
        lastValueVisible: true,
        priceLineVisible: false,
        priceFormat: {
          type: "price",
          precision: 2,
          minMove: 0.01,
        },
      });

      // 添加持仓量柱状图
      const positionSeries = chartRef.current.addHistogramSeries({
        color: "rgba(41, 98, 255, 0.3)",
        priceScaleId: "position",
        title: "Position",
        lastValueVisible: true,
        priceFormat: {
          type: "volume",
          precision: 3,
        },
        // 根据持仓方向改变颜色
        base: 0,
      });

      // 配置持仓量价格轴
      chartRef.current.priceScale("position").applyOptions({
        scaleMargins: {
          top: 0.7, // 将持仓量图表移到更下方
          bottom: 0.0, // 紧贴底部
        },
        visible: true,
        borderVisible: true,
        borderColor: "rgba(41, 98, 255, 0.4)",
        autoScale: true,
      });

      // 添加 legend 显示 OHLC 数据
      legendRef.current = document.createElement("div");
      const legend = legendRef.current;
      legend.style.position = "absolute";
      legend.style.padding = "12px";
      legend.style.fontSize = "12px";
      legend.style.background = "rgba(255, 255, 255, 0.95)";
      legend.style.border = "1px solid rgba(0, 0, 0, 0.1)";
      legend.style.borderRadius = "6px";
      legend.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.15)";
      legend.style.pointerEvents = "none";
      legend.style.zIndex = "3";
      legend.style.display = "none";
      legend.style.minWidth = "200px";
      chartContainerRef.current.appendChild(legend);

      chartRef.current.subscribeCrosshairMove((param) => {
        if (param.time && param.point) {
          const price = param.seriesData.get(candlestickSeries) as any;
          const trade = data?.trades.find(
            (t) => new Date(t.timestamp).getTime() / 1000 === param.time
          );
          const equity = data?.equity.find(
            (e) => new Date(e.timestamp).getTime() / 1000 === param.time
          );

          if (price) {
            const color = price.close >= price.open ? "#26a69a" : "#ef5350";
            legend.innerHTML = `
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="background: rgba(0, 0, 0, 0.02); padding: 8px; border-radius: 4px;">
                  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div style="display: flex; justify-content: space-between; min-width: 20px;">
                      <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">Open</span>
                      <span style="color: ${color}; font-family: monospace;">${price.open.toFixed(
              2
            )}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; min-width: 20px;">
                      <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">High</span>
                      <span style="color: ${color}; font-family: monospace;">${price.high.toFixed(
              2
            )}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; min-width: 20px;">
                      <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">Low</span>
                      <span style="color: ${color}; font-family: monospace;">${price.low.toFixed(
              2
            )}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; min-width: 20px;">
                      <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">Close</span>
                      <span style="color: ${color}; font-family: monospace;">${price.close.toFixed(
              2
            )}</span>
                    </div>
                  </div>
                  ${
                    equity
                      ? `
                      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0, 0, 0, 0.06);">
                        <div style="display: flex; justify-content: space-between; min-width: 260px;">
                          <span style="color: rgba(0, 0, 0, 0.45)">Position</span>
                          <span style="color: rgba(41, 98, 255, 0.8); font-family: monospace;">
                            ${equity.position.toFixed(3)} BTC
                          </span>
                        </div>
                      </div>
                      `
                      : ""
                  }
                </div>
                ${
                  trade
                    ? `
                    <div style="background: ${
                      trade.action === "BUY"
                        ? "rgba(38, 166, 154, 0.1)"
                        : "rgba(239, 83, 80, 0.1)"
                    }; padding: 8px; border-radius: 4px;">
                      <div style="color: ${
                        trade.action === "BUY" ? "#26a69a" : "#ef5350"
                      }">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; min-width: 260px;">
                          <span style="margin-right: 12px;">${
                            trade.action
                          }</span>
                          <span style="font-family: monospace;">${trade.price.toFixed(
                            2
                          )}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; min-width: 260px;">
                          <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">Size</span>
                          <span style="font-family: monospace;">${trade.size.toFixed(
                            3
                          )} BTC</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; min-width: 260px;">
                          <span style="color: rgba(0, 0, 0, 0.45); margin-right: 12px;">PnL</span>
                          <span style="color: ${
                            trade.pnl >= 0 ? "#26a69a" : "#ef5350"
                          }; font-family: monospace;">
                            ${trade.pnl >= 0 ? "+" : ""}$${trade.pnl.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                    `
                    : ""
                }
              </div>
            `;

            // 更新 legend 位置
            const container =
              chartContainerRef.current?.getBoundingClientRect();
            if (container) {
              const x = param.point.x + 20;
              const y = param.point.y + 20;

              const legendWidth = legend.offsetWidth;
              const legendHeight = legend.offsetHeight;

              let finalX = x;
              let finalY = y;

              if (x + legendWidth > container.width) {
                finalX = x - legendWidth - 40;
              }

              if (y + legendHeight > container.height) {
                finalY = y - legendHeight - 40;
              }

              legend.style.left = `${finalX}px`;
              legend.style.top = `${finalY}px`;
            }

            legend.style.display = "block";
          }
        } else {
          legend.style.display = "none";
        }
      });

      if (data) {
        // 设置K线数据
        candlestickSeries.setData(
          data.price_data.map((item) => ({
            time: (new Date(item.timestamp).getTime() / 1000) as Time,
            open: item.open,
            high: item.high,
            low: item.low,
            close: item.close,
          }))
        );

        // 添加交易标记
        const markers: ChartMarker[] = data.trades.map((trade) => ({
          time: (new Date(trade.timestamp).getTime() / 1000) as Time,
          position:
            trade.action === "BUY"
              ? "belowBar"
              : ("aboveBar" as SeriesMarkerPosition),
          color: trade.action === "BUY" ? "#26a69a" : "#ef5350",
          shape: trade.action === "BUY" ? "arrowUp" : "arrowDown",
          text: "",
          size: 1,
        }));

        candlestickSeries.setMarkers(markers);

        // 设置权益数据
        equitySeries.setData(
          data.equity.map((item) => ({
            time: (new Date(item.timestamp).getTime() / 1000) as Time,
            value: item.equity,
          }))
        );

        // 设置持仓量数据
        positionSeries.setData(
          data.equity.map((item) => ({
            time: (new Date(item.timestamp).getTime() / 1000) as Time,
            value: item.position,
            color:
              item.position > 0
                ? "rgba(38, 166, 154, 0.5)" // 多仓颜色
                : item.position < 0
                ? "rgba(239, 83, 80, 0.5)" // 空仓颜色
                : "rgba(41, 98, 255, 0.3)", // 无仓位颜色
          }))
        );

        // 自动调整图表大小
        chartRef.current.timeScale().fitContent();
      }

      // 设置滚动监听
      const cleanup = setupScrollHandler(chartRef.current);

      return () => {
        cleanup();
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }
        if (legendRef.current && legendRef.current.parentNode) {
          legendRef.current.parentNode.removeChild(legendRef.current);
        }
      };
    }
  }, [setupScrollHandler, data]);

  // 添加窗口大小变化的处理
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: window.innerHeight - 200, // 减去头部和统计信息的高度
        });
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 添加选择区域的处理
  useEffect(() => {
    if (!chartRef.current) return;

    // 创建 overlay div
    if (!overlayRef.current) {
      const overlay = document.createElement("div");
      overlayRef.current = overlay;
      overlay.style.position = "absolute";
      overlay.style.backgroundColor = "rgba(0, 0, 0, 0.05)";
      overlay.style.pointerEvents = "none";
      overlay.style.display = "none";
      overlay.style.zIndex = "2";
    }

    if (chartContainerRef.current) {
      const element =
        chartContainerRef.current.querySelectorAll("table tr td")[1];
      if (element) {
        element.appendChild(overlayRef.current);
      }
    }

    const handleMouseMove = (param: any) => {
      if (
        param.time &&
        selectionStartRef.current &&
        (param.sourceEvent?.metaKey || param.sourceEvent?.ctrlKey)
      ) {
        selectionEndRef.current = param.time as number;

        if (chartContainerRef.current) {
          const start = Math.min(
            selectionStartRef.current,
            selectionEndRef.current
          );
          const end = Math.max(
            selectionStartRef.current,
            selectionEndRef.current
          );

          selectRangeConfig?.setRangeSelection({ start, end });
          // 获取时间坐标
          const startX = chartRef.current
            ?.timeScale()
            .timeToCoordinate(start as Time);
          const endX = chartRef.current
            ?.timeScale()
            .timeToCoordinate(end as Time);

          if (startX && endX && overlayRef.current) {
            const rect = chartContainerRef.current.getBoundingClientRect();
            overlayRef.current.style.display = "block";
            overlayRef.current.style.left = `${startX}px`;
            overlayRef.current.style.width = `${endX - startX}px`;
            overlayRef.current.style.top = "0";
            overlayRef.current.style.height = `${rect.height}px`;
          }
        }
      }
    };

    const handleMouseDown = (param: any) => {
      if (
        selectionStartRef.current === null &&
        param.time &&
        (param.sourceEvent?.metaKey || param.sourceEvent?.ctrlKey)
      ) {
        selectionStartRef.current = param.time as number;
        chartRef.current?.applyOptions({
          handleScroll: false,
          handleScale: false,
        });
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      //   清除选择
      if (e.metaKey || e.ctrlKey) {
        if (selectionStartRef.current && selectionEndRef.current) {
          clearOverlay();
        }
      }
    };

    const handleKeyUp = () => {
      selectionStartRef.current = null;
      selectionEndRef.current = null;
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    chartRef.current.subscribeClick(handleMouseDown);
    chartRef.current.subscribeCrosshairMove(handleMouseMove);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      chartRef.current?.unsubscribeClick(handleMouseDown);
      chartRef.current?.unsubscribeCrosshairMove(handleMouseMove);

      if (overlayRef.current) {
        overlayRef.current.remove();
      }
    };
  }, [interval]);

  return {
    chartContainerRef,
    chartRef,
    isLoading,
    selectionStartRef,
    selectionEndRef,
    clearOverlay,
  };
};
