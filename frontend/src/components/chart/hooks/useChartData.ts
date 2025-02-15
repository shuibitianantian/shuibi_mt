import getHistoricalData from "apis/getHistoricalData";
import dayjs from "dayjs";
import { IChartApi, Time } from "lightweight-charts";
import { useCallback, useRef } from "react";

export const useChartData = (candlestickSeriesRef: any) => {
  const isLoadingRef = useRef(false);
  const oldestTimestampRef = useRef<string | null>(null);

  const loadData = useCallback(async (timestamp: string) => {
    if (candlestickSeriesRef && !isLoadingRef.current) {
      isLoadingRef.current = true;
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
      isLoadingRef.current = false;
    }
  }, []);

  const setupScrollHandler = useCallback(
    (chart: IChartApi) => {
      const handleScroll = async (param: any) => {
        if (!param || isLoadingRef.current) return;

        const visibleRange = param.from;
        const loadedRange = candlestickSeriesRef.current.data();
        const oldestLoadedTime = loadedRange[0]?.time;

        const coordinate = chart.timeScale().logicalToCoordinate(visibleRange);
        const visibleTime =
          coordinate !== null
            ? chart.timeScale().coordinateToTime(coordinate)
            : null;

        if (
          !visibleTime ||
          (visibleTime &&
            oldestLoadedTime &&
            visibleTime <= oldestLoadedTime + 1000 * 60 &&
            oldestTimestampRef.current)
        ) {
          await loadData(
            dayjs(oldestTimestampRef.current)
              .subtract(1, "minute")
              .format("YYYY-MM-DD HH:mm:ss")
          );
        }
      };

      chart.timeScale().subscribeVisibleLogicalRangeChange(handleScroll);
      return () =>
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleScroll);
    },
    [loadData]
  );

  return { isLoadingRef, loadData, setupScrollHandler };
};
