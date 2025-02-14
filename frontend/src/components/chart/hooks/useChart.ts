import {
    ColorType,
    createChart,
    IChartApi,
    SeriesMarker,
    SeriesMarkerPosition,
    Time,
} from "lightweight-charts";
import { useEffect, useRef } from "react";
import { BacktestResult } from "types/strategy";
import { useChartData } from "./useChartData";
import dayjs from "dayjs";

interface IUseChartProps {
    data: BacktestResult | null;
}

interface ChartMarker extends SeriesMarker<Time> {
    position: SeriesMarkerPosition;
    color: string;
    shape: "circle" | "arrowUp" | "arrowDown";
    text?: string;
    size?: number;
}

export const useChart = ({ data }: IUseChartProps) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const legendRef = useRef<HTMLDivElement | null>(null);
    const candlestickSeriesRef = useRef<any>(null);

    const { isLoadingRef, loadData, setupScrollHandler } =
        useChartData(candlestickSeriesRef);

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
                    background: {
                        type: ColorType.Solid,
                        color: "#ffffff",
                    },
                    textColor: "rgba(33, 56, 77, 1)",
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
                    timeFormatter: (time: number) => {
                        const date = new Date(time * 1000);
                        return date.toLocaleDateString();
                    },
                },
                timeScale: {
                    timeVisible: true, // 显示具体时间
                    secondsVisible: false, // 不显示秒
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
                    // 配置右侧价格轴（K线图）
                    visible: true,
                    autoScale: true,
                },
                leftPriceScale: {
                    // 配置左侧价格轴（权益曲线）
                    visible: true,
                    borderVisible: true,
                    autoScale: true,
                    borderColor: "rgba(197, 203, 206, 0.4)",
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

            // 配置主图（K线图）的价格轴
            chartRef.current.priceScale("right").applyOptions({
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.4, // 为下方图表留出更多空间
                },
            });

            // 配置权益曲线的价格轴
            chartRef.current.priceScale("left").applyOptions({
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.4, // 与主图保持一致
                },
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

                // 添加 legend 显示 OHLC 数据
                legendRef.current = document.createElement("div");
                const legend = legendRef.current;
                legend.style.position = "absolute";
                legend.style.padding = "8px";
                legend.style.fontSize = "12px";
                legend.style.background = "rgba(255, 255, 255, 0.9)";
                legend.style.borderRadius = "4px";
                legend.style.boxShadow = "0 2px 5px rgba(0,0,0,0.1)";
                legend.style.pointerEvents = "none"; // 避免干扰鼠标事件
                legend.style.zIndex = "3"; // 确保显示在最上层
                chartContainerRef.current.appendChild(legend);

                chartRef.current.subscribeCrosshairMove((param) => {
                    if (param.time && param.point) {
                        const price = param.seriesData.get(candlestickSeries) as any;
                        const trade = data.trades.find(
                            (t) => new Date(t.timestamp).getTime() / 1000 === param.time
                        );
                        const equity = data.equity.find(
                            (e) => new Date(e.timestamp).getTime() / 1000 === param.time
                        );

                        if (price) {
                            // 设置 tooltip 位置跟随鼠标
                            legend.style.left = `${param.point.x + 15}px`; // 偏移以避免遮挡十字线
                            legend.style.top = `${param.point.y + 15}px`;

                            // 使用不同颜色显示 OHLC
                            const closeColor =
                                price.close >= price.open ? "#26a69a" : "#ef5350";
                            legend.innerHTML = `
                            <div style="color: #666">Open: ${price.open.toFixed(
                                2
                            )}</div>
                            <div style="color: #26a69a">High: ${price.high.toFixed(
                                2
                            )}</div>
                            <div style="color: #ef5350">Low: ${price.low.toFixed(
                                2
                            )}</div>
                            <div style="color: ${closeColor}">Close: ${price.close.toFixed(
                                2
                            )}</div>
                            ${equity
                                    ? `
                                <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #eee;">
                                    <div style="color: rgba(41, 98, 255, 0.8)">
                                        Position: ${equity.position.toFixed(
                                        3
                                    )} BTC
                                    </div>
                                </div>
                            `
                                    : ""
                                }
                            ${trade
                                    ? `
                                <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #eee;">
                                    <div style="color: ${trade.action === "BUY"
                                        ? "#26a69a"
                                        : "#ef5350"
                                    }">
                                        ${trade.action} @ ${trade.price.toFixed(
                                        2
                                    )}
                                        <br/>Size: ${trade.size.toFixed(3)} BTC
                                        <br/>PnL: $${trade.pnl.toFixed(2)}
                                    </div>
                                </div>
                            `
                                    : ""
                                }
                        `;
                            legend.style.display = "block";
                        }
                    } else {
                        legend.style.display = "none";
                    }
                });

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
    }, [setupScrollHandler]);

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

    return {
        chartContainerRef,
        chartRef,
        isLoadingRef,
    };
};
