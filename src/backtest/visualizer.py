import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict
import mplfinance as mpf
from datetime import datetime
from .models import Trade

class BacktestVisualizer:
    """回测结果可视化"""
    def __init__(self, price_data: pd.DataFrame, trades: List[Trade], equity_curve: pd.DataFrame):
        self.price_data = price_data.copy()
        # 确保索引是datetime类型
        if not isinstance(self.price_data.index, pd.DatetimeIndex):
            self.price_data.index = pd.to_datetime(self.price_data.index)
        
        # 准备OHLCV数据
        self.price_data = self.price_data[['open', 'high', 'low', 'close', 'volume']]
        
        self.trades = trades
        self.equity_curve = equity_curve
    
    def plot_results(self):
        """绘制回测结果"""
        # 创建两个子图，比例为 8:2（价格+权益:成交量）
        fig, (ax1, ax_volume) = plt.subplots(2, 1, figsize=(15, 10), 
                                             height_ratios=[8, 2], 
                                             gridspec_kw={'hspace': 0})
        
        # 绘制价格和权益（主图）
        color_price = 'black'
        ax1.set_ylabel('Price / Equity', color=color_price)
        price_line = ax1.plot(self.price_data.index, self.price_data['close'], 
                              color=color_price, label='Price', alpha=0.7)
        
        color_equity = 'blue'
        equity_line = ax1.plot(self.equity_curve.index, self.equity_curve['equity'], 
                               color=color_equity, label='Equity', linestyle='--')
        
        ax1.tick_params(axis='y', labelcolor=color_price)
        
        # 添加持仓背景色
        self._add_position_background(ax1)
        
        # 使用小圆点标记交易点位
        for trade in self.trades:
            if trade.action == 'BUY':
                ax1.plot(trade.timestamp, trade.price, 'o', 
                         color='white', markersize=4, label='Buy',
                         markeredgewidth=1.5, markeredgecolor='green')
            elif trade.action == 'SELL':
                ax1.plot(trade.timestamp, trade.price, 'o', 
                         color='white', markersize=4, label='Sell',
                         markeredgewidth=1.5, markeredgecolor='red')
        
        # 绘制成交量（底部图）
        volume = self.price_data['volume']
        ax_volume.bar(self.price_data.index, volume, color='gray', alpha=0.3)
        ax_volume.set_ylabel('Volume')
        ax_volume.yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
        ax_volume.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        
        # 合并所有图例
        lines = price_line + equity_line
        labels = ['Price', 'Equity']
        
        # 添加Buy/Sell标记的图例（去重）
        handles, trade_labels = ax1.get_legend_handles_labels()
        by_label = dict(zip(trade_labels, handles))
        for label, handle in by_label.items():
            if label not in labels:
                lines.append(handle)
                labels.append(label)
        
        # 显示图例
        fig.legend(lines, labels, loc='upper right', bbox_to_anchor=(0.98, 0.98))
        
        # 添加网格
        ax1.grid(True, alpha=0.3)
        ax_volume.grid(True, alpha=0.3)
        
        # 设置标题
        plt.suptitle('Backtest Results', y=0.95)
        
        # 添加回测报告文本
        stats = self.generate_statistics()
        report_text = (
            f"Initial Capital: ${self.equity_curve['equity'].iloc[0]:,.0f}\n"
            f"Final Equity: ${self.equity_curve['equity'].iloc[-1]:,.0f}\n"
            f"Total Return: {stats['Total Return (%)']:.1f}%\n"
            f"Annual Return: {stats['Annual Return (%)']:.1f}%\n"
            f"Max Drawdown: {stats['Max Drawdown (%)']:.1f}%\n"
            f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}\n"
            f"Win Rate: {stats['Win Rate (%)']:.1f}%\n"
            f"Number of Trades: {len(self.trades)}"
        )
        
        # 调整布局以适应文本框
        plt.subplots_adjust(right=0.85, top=0.90)
        
        # 在图表右上角添加文本框
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.3)
        fig.text(0.87, 0.82, report_text,
                 fontsize=9,
                 verticalalignment='top',
                 horizontalalignment='left',
                 bbox=props,
                 family='monospace')  # 使用等宽字体使数字对齐
        
        # 显示图形
        plt.show()
    
    def generate_statistics(self) -> Dict[str, float]:
        """生成回测统计数据"""
        stats = {}
        
        # 计算收益相关指标
        initial_equity = self.equity_curve['equity'].iloc[0]
        final_equity = self.equity_curve['equity'].iloc[-1]
        returns = self.equity_curve['returns_pct'].iloc[-1]
        
        # 计算最大回撤
        rolling_max = self.equity_curve['equity'].expanding().max()
        drawdowns = (self.equity_curve['equity'] - rolling_max) / rolling_max * 100
        max_drawdown = drawdowns.min()
        
        # 计算年化收益率
        days = max((self.equity_curve.index[-1] - self.equity_curve.index[0]).days, 1)
        annual_return = (((final_equity / initial_equity) ** (365 / days)) - 1) * 100
        
        stats['Total Return (%)'] = returns
        stats['Annual Return (%)'] = annual_return
        stats['Max Drawdown (%)'] = max_drawdown
        stats['Sharpe Ratio'] = self._calculate_sharpe_ratio()
        stats['Win Rate (%)'] = self._calculate_win_rate()
        
        return stats
        
    def _calculate_win_rate(self) -> float:
        """计算胜率"""
        if not self.trades:
            return 0
        
        # 按交易组计算胜率（从开仓到平仓算一次交易）
        trades_by_group = []
        current_group = {'entry_price': None, 'exit_price': None, 'pnl': 0}
        
        for trade in self.trades:
            if trade.action == 'BUY':
                current_group['entry_price'] = trade.price
            elif trade.action == 'SELL' and current_group['entry_price'] is not None:
                current_group['exit_price'] = trade.price
                current_group['pnl'] = trade.pnl
                trades_by_group.append(current_group.copy())
                current_group = {'entry_price': None, 'exit_price': None, 'pnl': 0}
        
        if not trades_by_group:
            return 0
        
        winning_trades = sum(1 for trade in trades_by_group if trade['pnl'] > 0)
        return winning_trades / len(trades_by_group) * 100
        
    def _calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        if not self.equity_curve['returns_pct'].std():
            return 0
        return self.equity_curve['returns_pct'].mean() / self.equity_curve['returns_pct'].std() * (252 ** 0.5)

    def _add_position_background(self, ax):
        """添加持仓背景色"""
        # 创建持仓和收益的DataFrame
        position_df = pd.DataFrame(self.equity_curve)
        
        # 找到所有持仓区间
        in_position = False
        start_idx = None
        entry_equity = None
        
        for i in range(len(position_df)):
            current_pos = position_df['position'].iloc[i]
            current_equity = position_df['equity'].iloc[i]
            
            if current_pos > 0 and not in_position:
                # 开始新的持仓区间
                start_idx = position_df.index[i]
                entry_equity = current_equity
                in_position = True
            elif (current_pos == 0 or i == len(position_df)-1) and in_position:
                # 结束当前持仓区间
                end_idx = position_df.index[i]
                
                # 计算这段持仓的收益
                exit_equity = current_equity
                equity_return = (exit_equity - entry_equity) / entry_equity
                
                # 根据实际盈亏设置颜色
                color = 'lightgreen' if equity_return > 0 else 'lightcoral'
                
                # 设置最小和最大透明度
                MIN_ALPHA = 0.15  # 最小透明度
                MAX_ALPHA = 0.5   # 最大透明度
                
                # 根据收益率计算透明度，但确保至少有最小透明度
                alpha = min(MAX_ALPHA, max(MIN_ALPHA, abs(equity_return) * 3))
                
                # 添加背景色
                ax.axvspan(start_idx, end_idx, color=color, alpha=alpha)
                
                in_position = False
                entry_equity = None 