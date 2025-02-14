import { useCallback, useEffect, useRef, useState } from "react";
import { IChartApi, Time } from "lightweight-charts";
import getHistoricalData from "apis/getHistoricalData";

export const useChartData = (
    chart: IChartApi | null,
    candlestickSeriesRef: any
) => {
    const [isLoading, setIsLoading] = useState(false);
    const oldestTimestampRef = useRef<string | null>(null);

    const loadData = useCallback(
        async (timestamp: string) => {
            if (candlestickSeriesRef.current) {
                const newData = await getHistoricalData(timestamp, "BTCUSDT");

                if (newData.price_data.length > 0) {
                    oldestTimestampRef.current = newData.price_data[0].timestamp;

                    const formattedData = newData.price_data.map((item: any) => ({
                        time: (new Date(item.timestamp).getTime() / 1000) as Time,
                        open: item.open,
                        high: item.high,
                        low: item.low,
                        close: item.close,
                        volume: item.volume,
                    }));

                    candlestickSeriesRef.current.setData([
                        ...formattedData,
                        ...candlestickSeriesRef.current.data(),
                    ]);
                }
            }
        },
        []
    );

    useEffect(() => {
        if (!chart || !candlestickSeriesRef) return;

        const handleScroll = async (param: any) => {
            console.log('asdasda')

            if (!param || isLoading) return;

            const visibleRange = param.from;
            const loadedRange = candlestickSeriesRef.current.data();
            const oldestLoadedTime = loadedRange[0]?.time;

            if (
                visibleRange &&
                oldestLoadedTime &&
                visibleRange < oldestLoadedTime * 1.2
            ) {
                await loadMoreData();
            }
        };

        chart.timeScale().subscribeVisibleLogicalRangeChange(handleScroll);

        return () => {
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleScroll);
        };
    }, [chart, candlestickSeriesRef, isLoading]);

    const loadMoreData = async () => {
        if (!oldestTimestampRef.current || isLoading) return;

        try {
            setIsLoading(true);
            loadData(oldestTimestampRef.current);
        } catch (error) {
            console.error("Error loading more data:", error);
        } finally {
            setIsLoading(false);
        }
    };

    return { isLoading, loadData };
};
