import {
  createChart,
  IChartApi,
  SeriesMarker,
  SeriesMarkerPosition,
  Time,
  CrosshairMode,
  LineStyle,
  PriceFormat,
  ChartOptions,
  DeepPartial,
  CrosshairOptions,
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
  setHighlightedTradeTime: (time: string | null) => void;
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
  setHighlightedTradeTime,
}: IUseChartProps) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const legendRef = useRef<HTMLDivElement | null>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const selectionStartRef = useRef<number | null>(null);
  const selectionEndRef = useRef<number | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const hasUsedInitialDataRef = useRef(false);
  const markerTooltipRef = useRef<HTMLDivElement | null>(null);

  const { loadData, setupScrollHandler, oldestTimestampRef } = useChartData(
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

  const loadInitialData = useCallback(() => {
    const today = dayjs().format("YYYY-MM-DD HH:mm:ss");
    loadData(today);
  }, [loadData]);

  // 初始加载数据
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // 设置图表和滚动监听
  useEffect(() => {
    if (chartContainerRef.current && !chartRef.current) {
      const crosshairOptions: DeepPartial<CrosshairOptions> = {
        mode: CrosshairMode.Magnet,
        vertLine: {
          labelVisible: true,
          labelBackgroundColor: "#404040",
          style: LineStyle.Dotted,
          width: 1,
          color: "rgba(33, 56, 77, 0.1)",
          visible: true,
        },
        horzLine: {
          labelVisible: true,
          labelBackgroundColor: "#404040",
          style: LineStyle.Dotted,
          width: 1,
          color: "rgba(33, 56, 77, 0.1)",
          visible: true,
        },
      };

      // 在 priceFormat 配置中添加
      const priceFormat: DeepPartial<PriceFormat> = {
        type: "price",
        precision: 2,
        minMove: 0.01,
      };

      // 在创建图表时的配置中
      const chartOptions: DeepPartial<ChartOptions> = {
        layout: {
          background: { color: "#ffffff" },
          textColor: "#333",
          fontSize: 12,
          fontFamily: "-apple-system, system-ui, sans-serif",
        },
        grid: {
          vertLines: { color: "#f0f0f0" },
          horzLines: { color: "#f0f0f0" },
        },
        crosshair: crosshairOptions,
        rightPriceScale: {
          borderColor: "#f0f0f0",
          visible: true,
          scaleMargins: {
            top: 0.1,
            bottom: 0.4,
          },
          alignLabels: false,
          borderVisible: false,
          entireTextOnly: true,
        },
        leftPriceScale: {
          borderColor: "#f0f0f0",
          visible: Boolean(data),
          scaleMargins: {
            top: 0.1,
            bottom: 0.4,
          },
        },
        timeScale: {
          borderColor: "#f0f0f0",
          timeVisible: true,
          secondsVisible: true,
          tickMarkFormatter: (time: number) => formatTime(time, interval),
        },
        localization: {
          locale: "en-US",
          priceFormatter: (price: number) => price.toFixed(2),
          timeFormatter: (time: number) => formatTime(time, interval),
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
        },
        handleScale: {
          mouseWheel: true,
          pinch: true,
        },
      };

      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: window.innerHeight - 80,
        ...chartOptions,
      });

      // 添加K线图
      const candlestickSeries = chartRef.current.addCandlestickSeries({
        upColor: "#26a69a",
        downColor: "#ef5350",
        borderVisible: false,
        wickUpColor: "#26a69a",
        wickDownColor: "#ef5350",
        priceScaleId: "right",
        lastValueVisible: true,
        priceLineVisible: true,
        priceFormat: priceFormat,
      });

      candlestickSeriesRef.current = candlestickSeries;

      // 添加 legend 显示 OHLC 数据
      legendRef.current = document.createElement("div");
      const legend = legendRef.current;
      legend.style.position = "absolute";
      legend.style.left = !Boolean(data) ? "0px" : "70px";
      legend.style.top = "0px"; // 完全贴合顶部
      legend.style.padding = "6px 12px";
      legend.style.fontSize = "12px";
      legend.style.fontFamily = "monospace";
      legend.style.color = "#131722";
      legend.style.background = "transparent"; // 移除背景色
      legend.style.zIndex = "3";
      legend.style.userSelect = "none"; // 防止文字被选中

      chartContainerRef.current.appendChild(legend);

      // 修改 subscribeCrosshairMove 事件处理
      chartRef.current.subscribeCrosshairMove((param) => {
        if (param.time && param.point) {
          const price = param.seriesData.get(
            candlestickSeriesRef.current
          ) as any;

          const trade = data?.trades?.find(
            (t) => new Date(t.timestamp + "Z").getTime() / 1000 === param.time
          );

          if (price) {
            legend.innerHTML = `
              <div style="font-family: -apple-system, system-ui, sans-serif; padding: 4px 8px; line-height: 1.5">
                <div style="display: flex; gap: 12px; align-items: center; border-bottom: ${
                  trade ? "1px solid rgba(0,0,0,0.05)" : "none"
                }; padding-bottom: ${trade ? "4px" : "0"}">
                  <span style="font-weight: 500; color: #666">
                    ${formatTime(param.time as number, interval)}
                  </span>
                  <div style="display: flex; gap: 8px">
                    <span style="display: flex; gap: 4px">
                      <span style="color: #888">O</span>
                      <span style="color: ${
                        price.open >= price.close ? "#ef5350" : "#26a69a"
                      }; font-weight: 500">
                        ${price.open.toFixed(2)}
                      </span>
                    </span>
                    <span style="display: flex; gap: 4px">
                      <span style="color: #888">H</span>
                      <span style="color: #26a69a; font-weight: 500">
                        ${price.high.toFixed(2)}
                      </span>
                    </span>
                    <span style="display: flex; gap: 4px">
                      <span style="color: #888">L</span>
                      <span style="color: #ef5350; font-weight: 500">
                        ${price.low.toFixed(2)}
                      </span>
                    </span>
                    <span style="display: flex; gap: 4px">
                      <span style="color: #888">C</span>
                      <span style="color: ${
                        price.open <= price.close ? "#26a69a" : "#ef5350"
                      }; font-weight: 500">
                        ${price.close.toFixed(2)}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            `;
            legend.style.display = "block";

            // 检查是否悬停在交易标记上
            if (trade) {
              setHighlightedTradeTime(trade.timestamp);
            } else {
              setHighlightedTradeTime(null);
            }
          }
        } else {
          legend.style.display = "none";
        }
      });

      // 添加权益曲线作为子图
      const equitySeries = chartRef.current.addLineSeries({
        lineWidth: 1,
        priceScaleId: "left",
        title: "Equity",
        visible: true,
        lastValueVisible: true,
        priceFormat: {
          type: "price",
          precision: 2,
          minMove: 0.01,
        },
      });

      // 添加持仓量柱状图
      const positionSeries = chartRef.current.addHistogramSeries({
        color: "rgba(41, 98, 255, 0.3)",
        priceScaleId: "position", // 使用独立的价格轴
        title: "Position",
        priceFormat: {
          type: "volume",
          precision: 3,
        },
        base: 0,
      });

      // 配置持仓量价格轴
      chartRef.current.priceScale("position").applyOptions({
        scaleMargins: {
          top: 0.9, // 改为0.85，将持仓量图表下移
          bottom: 0.0, // 保持紧贴底部
        },
        visible: true,
        borderVisible: true,
        borderColor: "rgba(41, 98, 255, 0.4)",
        autoScale: true,
      });

      if (data) {
        candlestickSeriesRef.current.setData(
          data.price_data.map((item) => ({
            time: (new Date(item.timestamp + "Z").getTime() / 1000) as Time,
            open: item.open,
            high: item.high,
            low: item.low,
            close: item.close,
          }))
        );

        // 添加交易标记
        const markers: ChartMarker[] = data.trades.map((trade) => ({
          time: (new Date(trade.timestamp + "Z").getTime() / 1000) as Time,
          position: trade.action === "BUY" ? "belowBar" : "aboveBar",
          color: trade.action === "BUY" ? "#26a69a" : "#ef5350",
          shape: trade.action === "BUY" ? "arrowUp" : "arrowDown",
          size: 1, // 增大标记尺寸
          text: "",
        }));

        candlestickSeriesRef.current.setMarkers(markers);

        // 设置权益数据
        equitySeries.setData(
          data.equity.map((item) => ({
            time: (new Date(item.timestamp + "Z").getTime() / 1000) as Time,
            value: item.equity,
          }))
        );

        // 设置持仓量数据
        positionSeries.setData(
          data.equity.map((item) => ({
            time: (new Date(item.timestamp + "Z").getTime() / 1000) as Time,
            value: item.position,
            color:
              item.position > 0
                ? "rgba(38, 166, 154, 0.5)" // 多仓颜色
                : item.position <= 0
                ? "rgba(239, 83, 80, 0.5)" // 空仓颜色
                : "rgba(41, 98, 255, 0.3)", // 无仓位颜色
          }))
        );

        // 自动调整图表大小
        chartRef.current.timeScale().fitContent();

        if (!hasUsedInitialDataRef.current) {
          hasUsedInitialDataRef.current = true;
          oldestTimestampRef.current = data.price_data[0].timestamp;
        }
      }

      // 设置滚动监听
      const cleanup = setupScrollHandler(chartRef.current);

      return () => {
        cleanup();
        hasUsedInitialDataRef.current = false;
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

    if (data && overlayRef.current) {
      // remove overlay
      overlayRef.current.style.display = "none";
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
        (param.sourceEvent?.metaKey || param.sourceEvent?.ctrlKey) &&
        !data
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
        (param.sourceEvent?.metaKey || param.sourceEvent?.ctrlKey) &&
        !data
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
  }, [interval, data]);

  return {
    chartContainerRef,
    chartRef,
    isLoading,
    selectionStartRef,
    selectionEndRef,
    clearOverlay,
    loadInitialData,
    candlestickSeriesRef,
  };
};
