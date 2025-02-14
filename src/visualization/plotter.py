import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Optional

class Plotter:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def plot_candlestick(self, 
                        indicators: Optional[dict] = None,
                        volume: bool = True) -> None:
        """
        绘制K线图和指标
        
        Args:
            indicators: 指标字典，格式为 {'name': series}
            volume: 是否显示成交量
        """
        # 创建子图
        rows = 2 if volume else 1
        fig = make_subplots(rows=rows, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.05,
                           row_heights=[0.7, 0.3] if volume else [1])
        
        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=self.data.index,
                open=self.data['open'],
                high=self.data['high'],
                low=self.data['low'],
                close=self.data['close'],
                name='OHLC'
            ),
            row=1, col=1
        )
        
        # 添加指标
        if indicators:
            for name, series in indicators.items():
                if isinstance(series, tuple):
                    # 处理多线指标（如MACD）
                    for i, s in enumerate(series):
                        fig.add_trace(
                            go.Scatter(
                                x=self.data.index,
                                y=s,
                                name=f"{name}_{i}",
                                line=dict(width=1)
                            ),
                            row=1, col=1
                        )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=self.data.index,
                            y=series,
                            name=name,
                            line=dict(width=1)
                        ),
                        row=1, col=1
                    )
        
        # 添加成交量
        if volume:
            colors = ['red' if row['open'] - row['close'] >= 0 
                     else 'green' for i, row in self.data.iterrows()]
            fig.add_trace(
                go.Bar(
                    x=self.data.index,
                    y=self.data['volume'],
                    name='Volume',
                    marker_color=colors
                ),
                row=2, col=1
            )
        
        # 更新布局
        fig.update_layout(
            title='Market Data Analysis',
            yaxis_title='Price',
            yaxis2_title='Volume' if volume else None,
            xaxis_rangeslider_visible=False
        )
        
        fig.show() 