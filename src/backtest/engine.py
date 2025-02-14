import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from src.utils.logger import setup_logger
from .data_feed import DataFeed
from .strategy import Strategy
from .visualizer import BacktestVisualizer
from .models import Trade

class Backtest:
    """回测引擎"""
    def __init__(
        self,
        data_feed: DataFeed,
        strategy: Strategy,
        start_time: datetime,
        end_time: datetime,
        initial_capital: float = 10000,
        commission: float = 0.0004,
        enable_report: bool = True  # 添加参数控制报告输出
    ):
        self.logger = setup_logger('backtest')
        self.data = data_feed
        self.strategy = strategy
        
        # 确保时间是 UTC 时区
        self.start_time = pd.to_datetime(start_time).tz_localize('UTC')
        self.end_time = pd.to_datetime(end_time).tz_localize('UTC')
        
        self.initial_capital = initial_capital
        self.commission = commission
        self.enable_report = enable_report  # 保存参数
        
        self.capital = initial_capital
        self.position = 0
        self.position_cost = 0
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.total_commission = 0  # 总手续费
        self.daily_trades = {}  # 每日交易统计
        
    def run(self) -> pd.DataFrame:
        """运行回测"""
        if self.enable_report:
            self.logger.info(f"Starting backtest from {self.start_time} to {self.end_time}...")
        
        while True:
            current_data = self.data.next()
            if current_data is None:
                break
            
            current_time = self.data.get_current_time()
            if current_time < self.start_time:
                continue
            if current_time >= self.end_time:
                break
            
            # 根据策略配置获取回看周期
            lookback_periods = getattr(self.strategy, 'lookback_periods', 100)
            history = self.data.look_back(lookback_periods)
            
            if len(history) < lookback_periods:
                continue  # 等待足够的历史数据

            # 获取策略信号
            signal = self.strategy.on_data(current_data, history)
            
            # 处理信号
            if signal:
                self._process_signal(signal, current_data)
            
            # 计算当前权益和收益率
            current_equity = self._calculate_equity(current_data['close'])
            returns_pct = (current_equity - self.initial_capital) / self.initial_capital * 100

            # 记录权益
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': current_equity if self.position > 0 else self.capital,  # 只在有持仓时计算权益
                'position': self.position,
                'returns_pct': returns_pct
            })
        
        if not self.equity_curve:
            raise ValueError("No data processed during backtest")
        
        # 转换为DataFrame并设置索引
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('timestamp', inplace=True)

        # 创建可视化器
        visualizer = BacktestVisualizer(
            price_data=self.data.data,
            trades=self.trades,
            equity_curve=equity_df
        )
        
        # 生成统计数据
        stats = visualizer.generate_statistics()
        
        if self.enable_report:
            self._print_report(stats)
            # 只在启用报告时绘制结果
            visualizer.plot_results()
        
        return equity_df
    
    def _process_signal(self, signal: Dict[str, Any], current_data: pd.Series):
        """处理交易信号"""
        action = signal['action']
        size = signal['size']
        price = signal['price']
        reason = signal.get('reason', '')
        is_percent = signal.get('is_percent', False)
        adjust_size = signal.get('adjust_size', True)
        current_time = self.data.current_time
        
        # 更新策略状态
        # 处理浮点数精度问题，如果资金接近0，设为0
        if abs(self.capital) < 1e-10:
            self.capital = 0
        
        self.strategy.current_capital = self.capital
        self.strategy.initial_capital = self.initial_capital
        self.strategy.current_equity = self._calculate_equity(current_data['close'])
        
        if action == 'BUY':
            # 如果是百分比，转换为实际数量
            if is_percent:
                available_capital = self.capital
                size = (size * available_capital) / (price * (1 + self.commission))
            
            # 计算最大可买数量
            max_size = self.capital / (price * (1 + self.commission))
            max_size = min(max_size, self.strategy.calculate_position_size(self.capital, price))
            
            # 如果请求的size超过最大可买数量
            if size > max_size:
                if adjust_size:
                    actual_size = max_size
                    reason = f"{reason} (Adjusted Size)"
                else:
                    self.logger.warning(f"[{current_time}] Insufficient capital for BUY order at {price:.2f}")
                    return
            else:
                actual_size = size
            
            # 如果实际可买数量太小，就不执行交易
            if actual_size <= 1e-8:
                self.logger.warning(f"[{current_time}] Size too small for BUY order: {actual_size}")
                return
            
            # 计算总成本（包括手续费）
            cost = actual_size * price * (1 + self.commission)
            
            # 更新持仓成本
            self.position_cost = (self.position_cost * self.position + actual_size * price) / (self.position + actual_size)
            
            # 处理浮点数精度问题
            self.capital = max(0, self.capital - cost)  # 确保资金不会变成负数
            self.position += actual_size
            pnl = 0  # 买入时没有PnL
            
            # 记录交易
            self._record_trade(current_time, action, price, actual_size, pnl, reason)
            
        elif action == 'SELL':
            if self.position <= 0:
                return
            
            if is_percent:
                actual_size = size * self.position
            else:
                actual_size = min(size, self.position)
            
            if actual_size <= 1e-8:
                return
            
            # 计算这笔交易的收益
            entry_value = self.position_cost * actual_size  # 买入成本
            exit_value = price * actual_size * (1 - self.commission)  # 卖出所得（扣除手续费）
            pnl = exit_value - entry_value
            
            # 更新资金和持仓
            self.capital += exit_value
            self.position -= actual_size
            
            # 如果完全平仓，重置持仓成本
            if self.position == 0:
                self.position_cost = 0
            
            # 记录交易
            self._record_trade(current_time, action, price, actual_size, pnl, reason)
    
    def _record_trade(self, current_time, action, price, size, pnl, reason):
        """记录交易"""
        # 记录交易
        self.trades.append(Trade(
            timestamp=current_time,
            action=action,
            price=price,
            size=size,
            pnl=pnl,
            reason=reason
        ))
        
        self.logger.info(
            f"[{current_time}] Executed {action} {size:.4f} units at {price:.2f}, "
            f"PnL: {pnl:.2f}, Avg Cost: {self.position_cost:.2f}, "
            f"Capital: {self.capital:.2f}, Position: {self.position:.4f}"
        )
        
        # 更新策略的交易统计
        self.strategy.update_trade_stats(current_time, price)
        
        # 记录手续费
        commission_cost = size * price * self.commission
        self.total_commission += commission_cost
        
        # 更新每日交易统计
        trade_date = current_time.date()
        if trade_date not in self.daily_trades:
            self.daily_trades[trade_date] = {'count': 0, 'pnl': 0}
        self.daily_trades[trade_date]['count'] += 1
        self.daily_trades[trade_date]['pnl'] += pnl
    
    def _calculate_equity(self, current_price: float) -> float:
        """计算当前权益"""
        if self.position > 0:
            return self.capital + (self.position * current_price)
        return self.capital
    
    def _print_report(self, stats: Dict[str, float]):
        """打印完整的回测报告"""
        # 获取最终数据
        final_price = self.data.data['close'].iloc[-1]
        position_value = self.position * final_price
        final_equity = self.capital + position_value
        
        # 创建分隔线
        separator = "═" * 60
        subseparator = "─" * 60
        
        self.logger.info(f"\n{separator}")
        self.logger.info(f"{'📊 BACKTEST REPORT':^60}")
        self.logger.info(separator)
        
        # 基本信息
        self.logger.info("\n🔎 BASIC INFORMATION")
        self.logger.info(subseparator)
        self.logger.info(f"{'Symbol:':<20} {self.data.data.name if hasattr(self.data.data, 'name') else 'Unknown'}")
        self.logger.info(f"{'Period:':<20} {self.start_time.strftime('%Y-%m-%d')} to {self.end_time.strftime('%Y-%m-%d')}")
        self.logger.info(f"{'Duration:':<20} {(self.end_time - self.start_time).days} days")
        
        # 资金状况
        self.logger.info("\n💰 CAPITAL SUMMARY")
        self.logger.info(subseparator)
        self.logger.info(f"{'Initial Capital:':<20} ${self.initial_capital:,.2f}")
        self.logger.info(f"{'Final Capital:':<20} ${self.capital:,.2f}")
        self.logger.info(f"{'Current Position:':<20} {self.position:.4f} units")
        self.logger.info(f"{'Position Value:':<20} ${position_value:,.2f}")
        self.logger.info(f"{'Final Equity:':<20} ${final_equity:,.2f}")
        
        # 收益分析
        self.logger.info("\n📈 RETURN ANALYSIS")
        self.logger.info(subseparator)
        self.logger.info(f"{'Total Return:':<20} {stats['Total Return (%)']:,.2f}%")
        self.logger.info(f"{'Annual Return:':<20} {self.get_annual_return():,.2f}%")
        self.logger.info(f"{'Max Drawdown:':<20} {self.get_max_drawdown():,.2f}%")
        self.logger.info(f"{'Sharpe Ratio:':<20} {self.get_sharpe_ratio():.2f}")
        
        # 交易统计
        self.logger.info("\n🔄 TRADE STATISTICS")
        self.logger.info(subseparator)
        total_days = (self.end_time - self.start_time).days
        total_trades = len(self.trades)
        trades_per_day = total_trades / total_days if total_days > 0 else 0
        
        self.logger.info(f"{'Number of Trades:':<20} {total_trades}")
        self.logger.info(f"{'Trades per Day:':<20} {trades_per_day:.2f}")
        self.logger.info(f"{'Win Rate:':<20} {self.get_win_rate():.2f}%")
        
        if self.trades:
            total_pnl = self._verify_pnl()
            avg_pnl = total_pnl / total_trades
            winning_trades = [t.pnl for t in self.trades if t.pnl > 0]
            losing_trades = [t.pnl for t in self.trades if t.pnl <= 0]
            
            # 计算风险收益指标
            risk_reward_ratio = abs(self.get_annual_return() / self.get_max_drawdown()) if self.get_max_drawdown() != 0 else float('inf')
            
            # 计算盈亏比
            total_wins = sum(winning_trades) if winning_trades else 0
            total_losses = abs(sum(losing_trades)) if losing_trades else 0
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
            
            self.logger.info(f"{'Risk/Reward Ratio:':<20} {risk_reward_ratio:.2f}")
            self.logger.info(f"{'Profit Factor:':<20} {profit_factor:.2f}")
            self.logger.info(f"{'Total Commission:':<20} ${self.total_commission:,.2f}")
            
            # 添加每日交易统计
            profitable_days = sum(1 for stats in self.daily_trades.values() if stats['pnl'] > 0)
            total_trading_days = len(self.daily_trades)
            if total_trading_days > 0:
                profitable_days_pct = (profitable_days / total_trading_days) * 100
                self.logger.info(f"{'Profitable Days:':<20} {profitable_days_pct:.1f}%")
                
                # 计算最活跃的交易日
                most_active_day = max(self.daily_trades.items(), key=lambda x: x[1]['count'])
                self.logger.info(f"{'Most Active Day:':<20} {most_active_day[0]} ({most_active_day[1]['count']} trades)")
        
        # 结束分隔线
        self.logger.info(f"\n{separator}\n")
    
    def _verify_pnl(self):
        """验证PnL计算的正确性"""
        # 计算总PnL
        total_pnl_from_trades = sum(trade.pnl for trade in self.trades)
        return total_pnl_from_trades

    def get_annual_return(self) -> float:
        """计算年化收益率"""
        if not self.equity_curve:
            return 0
        
        equity_df = pd.DataFrame(self.equity_curve)
        # 确保使用 datetime 对象进行计算
        start_date = pd.to_datetime(equity_df.index[0])
        end_date = pd.to_datetime(equity_df.index[-1])
        total_days = (end_date - start_date).days
        
        if total_days == 0:
            return 0
            
        total_return = (equity_df['equity'].iloc[-1] / self.initial_capital - 1)
        annual_return = (1 + total_return) ** (365 / total_days) - 1
        return annual_return * 100

    def get_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.equity_curve:
            return 0
            
        equity_df = pd.DataFrame(self.equity_curve)
        rolling_max = equity_df['equity'].expanding().max()
        drawdowns = (equity_df['equity'] - rolling_max) / rolling_max * 100
        return abs(float(drawdowns.min()))

    def get_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        if not self.equity_curve:
            return 0
            
        equity_df = pd.DataFrame(self.equity_curve)
        returns = equity_df['equity'].pct_change().dropna()
        if len(returns) == 0 or returns.std() == 0:
            return 0
            
        return (returns.mean() / returns.std()) * (252 ** 0.5)  # 年化

    def get_win_rate(self) -> float:
        """计算胜率"""
        if not self.trades:
            return 0
            
        winning_trades = sum(1 for trade in self.trades if trade.pnl > 0)
        return (winning_trades / len(self.trades)) * 100 