import React, { useEffect, useRef } from 'react';
import { ColorType, createChart, IChartApi, SeriesMarker, Time } from 'lightweight-charts';
import { BacktestResult } from '../types/strategy';

interface Props {
  data: BacktestResult;
}

interface ChartMarker extends SeriesMarker<Time> {
  text?: string;
}

export const BacktestChart: React.FC<Props> = ({ data }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (chartContainerRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        width: 800,
        height: 400,
        layout: {
          background: {
            type: ColorType.Solid,
            color: '#ffffff',
          },
          textColor: 'rgba(33, 56, 77, 1)',
        },
        grid: {
          vertLines: {
            color: 'rgba(197, 203, 206, 0.5)',
          },
          horzLines: {
            color: 'rgba(197, 203, 206, 0.5)',
          },
        },
      });

      // Add price series
      const mainSeries = chartRef.current.addCandlestickSeries();
      
      // Add equity series
      const equitySeries = chartRef.current.addLineSeries({
        color: 'blue',
        lineWidth: 2,
      });

      // Add trade markers
      data.trades.forEach(trade => {
        mainSeries.setMarkers([
          {
            time: trade.timestamp.split('T')[0],
            position: trade.action === 'BUY' ? 'belowBar' : 'aboveBar',
            color: trade.action === 'BUY' ? 'green' : 'red',
            shape: 'circle',
            text: trade.action
          }
        ]);
      });

      // Set data
      equitySeries.setData(
        data.equity.map(item => ({
          time: item.timestamp,
          value: item.equity
        }))
      );
    }

    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [data]);

  return <div ref={chartContainerRef} />;
}; 