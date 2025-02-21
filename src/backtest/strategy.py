from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from src.indicators.technical import TechnicalIndicators
from datetime import datetime
from src.utils.logger import setup_logger

class Strategy:
    """策略基类"""
    def __init__(self):
        self.ti = TechnicalIndicators()
        self.position = 0
        self.logger = setup_logger('strategy')
        
        # 风控参数（默认无限制）
        self.position_limit = 1.0  # 允许满仓
        self.min_cash_reserve = 0.0  # 不要求保留现金
        self.min_trade_interval = pd.Timedelta(minutes=0)  # 无交易间隔限制
        self.max_trades_per_day = float('inf')  # 无每日交易次数限制
        self.max_drawdown = 1.0  # 允许100%回撤
        self.stop_loss = float('inf')  # 无止损
        self.take_profit = float('inf')  # 无止盈
        
        # 交易状态
        self.last_trade_time = None
        self.last_trade_date = None
        self.daily_trades = 0
        self.current_drawdown = 0
        self.peak_equity = 0
        self.entry_price = None
        
        # 由回测引擎更新的状态
        self.current_capital = 0
        self.initial_capital = 0
        self.current_equity = 0

    @property
    def lookback_periods(self) -> int:
        """获取策略所需的最小回看周期数"""
        raise NotImplementedError("Strategy must implement lookback_periods")

    def check_risk_limits(self, current_time: datetime, signal: Dict[str, Any]) -> bool:
        """检查风控限制"""
        # 检查最小现金保留
        min_cash = self.min_cash_reserve * self.initial_capital
        # 如果资金接近0或小于0，就不允许交易
        if self.current_capital < min_cash:
            return False
            
        # 检查交易间隔
        if self.last_trade_time is not None:
            time_since_last_trade = current_time - self.last_trade_time
            if time_since_last_trade < self.min_trade_interval:
                return False
        
        # 检查每日交易次数限制
        current_date = current_time.date()
        if current_date != self.last_trade_date:
            self.daily_trades = 0
            self.last_trade_date = current_date
        if self.daily_trades >= self.max_trades_per_day:
            return False
            
        # 检查回撤限制
        if self.peak_equity == 0:  # 初始化 peak_equity
            self.peak_equity = max(self.current_equity, self.initial_capital)
        elif self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        
        # 计算当前回撤
        if self.peak_equity > 0:  # 避免除以零
            self.current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
            if self.current_drawdown > self.max_drawdown:
                return False
        
        return True

    def check_position_exit(self, current_price: float) -> Optional[Dict[str, Any]]:
        """检查是否需要退出仓位（止盈止损）"""
        if self.position > 0 and self.entry_price is not None:
            returns = (current_price - self.entry_price) / self.entry_price
            
            # 止损
            if returns < -self.stop_loss:
                return {
                    'action': 'SELL',
                    'size': 1.0,
                    'is_percent': True,
                    'price': current_price,
                    'reason': f'Stop Loss at {returns:.2%}'
                }
            
            # 止盈
            if returns > self.take_profit:
                return {
                    'action': 'SELL',
                    'size': 1.0,
                    'is_percent': True,
                    'price': current_price,
                    'reason': f'Take Profit at {returns:.2%}'
                }
        
        return None

    def update_trade_stats(self, current_time: datetime, price: float):
        """更新交易统计"""
        self.last_trade_time = current_time
        self.daily_trades += 1
        if self.position > 0:
            self.entry_price = price

    def on_data(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """处理每个时间点的数据并返回交易信号"""
        # 获取策略信号
        signal = self.generate_signal(current_data, history)

        if signal and self.check_risk_limits(current_data.name, signal):
            return signal
        
        # 如果没有策略信号，检查是否需要退出仓位
        exit_signal = self.check_position_exit(current_data['close'])

        if exit_signal:
            return exit_signal
            
        return None

    def generate_signal(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """生成交易信号（由子类实现）"""
        raise NotImplementedError("Strategy must implement generate_signal method")

    def calculate_position_size(self, capital: float, price: float) -> float:
        """计算最大仓位大小"""
        return (capital * self.position_limit) / price


class SMAWithADXStrategy(Strategy):
    """带ADX过滤的双均线策略"""
    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
        adx_period: int = 14,
        adx_threshold: float = 25,
    ):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        
    @property
    def lookback_periods(self) -> int:
        """
        获取策略所需的最小回看周期数
        对于SMA策略，需要max(fast_period, slow_period, adx_period)个周期的数据
        """
        return max(self.fast_period, self.slow_period, self.adx_period)
    
    def generate_signal(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """生成交易信号"""
        if len(history) < self.lookback_periods:
            return None
            
        # 计算快慢均线
        fast_ma = self.ti.sma(history, period=self.fast_period).iloc[-1]
        slow_ma = self.ti.sma(history, period=self.slow_period).iloc[-1]
        
        # 计算ADX
        adx = self.ti.adx(history, period=self.adx_period).iloc[-1]
        current_price = current_data['close']

        # 只在趋势强度足够时交易
        if adx > self.adx_threshold:
            if fast_ma > slow_ma:  # 多头信号
                return {
                    'action': 'BUY',
                    'size': 1,
                    'is_percent': True,
                    'price': current_price,
                    'reason': f'Golden Cross with ADX={adx:.1f}',
                    'adjust_size': True  # 允许自动调整size
                }
            elif fast_ma < slow_ma:  # 空头信号
                return {
                    'action': 'SELL',
                    'size': 1,  # 卖出100%持仓
                    'is_percent': True,  # 标记为百分比交易
                    'price': current_price,
                    'reason': f'Death Cross with ADX={adx:.1f}'
                }
        return None


class SMASlopeStrategy(Strategy):
    """基于均线斜率的策略"""
    def __init__(self, fast_period: int = 50, slow_period: int = 120, slope_periods: int = 5):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.slope_periods = slope_periods
        self.slope_threshold = 0.0001  # 斜率阈值
        self.lookback_periods = max(slow_period, fast_period) + slope_periods
        self.position_limit = 0.95
    
    def on_data(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(history) < self.lookback_periods:
            return None
            
        # 计算均线
        fast_ma = self.ti.sma(history, period=self.fast_period)
        slow_ma = self.ti.sma(history, period=self.slow_period)
        
        # 计算慢均线斜率
        slope = (slow_ma.iloc[-1] - slow_ma.iloc[-self.slope_periods]) / self.slope_periods
        current_price = current_data['close']
        
        # 只在趋势足够强时交易
        if abs(slope) > self.slope_threshold:
            if fast_ma.iloc[-1] > slow_ma.iloc[-1] and self.position <= 0:
                return {
                    'action': 'BUY',
                    'size': 0.01,
                    'price': current_price,
                    'reason': f'Golden Cross with slope={slope:.6f}'
                }
            elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and self.position >= 0:
                return {
                    'action': 'SELL',
                    'size': 0.01,
                    'price': current_price,
                    'reason': f'Death Cross with slope={slope:.6f}'
                }
        return None


class SMADeviationStrategy(Strategy):
    """基于价格偏离度的策略"""
    def __init__(self, fast_period: int = 50, slow_period: int = 120):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.max_deviation = 0.03  # 最大允许偏离度 3%
        self.lookback_periods = max(slow_period, fast_period)
        self.position_limit = 0.95
    
    def on_data(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(history) < self.lookback_periods:
            return None
            
        # 计算均线
        fast_ma = self.ti.sma(history, period=self.fast_period).iloc[-1]
        slow_ma = self.ti.sma(history, period=self.slow_period).iloc[-1]
        current_price = current_data['close']
        
        # 计算价格与慢均线的偏离度
        price_deviation = abs(current_price - slow_ma) / slow_ma
        
        # 避免过度偏离的交易
        if price_deviation < self.max_deviation:
            if fast_ma > slow_ma and self.position <= 0:
                return {
                    'action': 'BUY',
                    'size': 0.01,
                    'price': current_price,
                    'reason': f'Golden Cross with deviation={price_deviation:.2%}'
                }
            elif fast_ma < slow_ma and self.position >= 0:
                return {
                    'action': 'SELL',
                    'size': 0.01,
                    'price': current_price,
                    'reason': f'Death Cross with deviation={price_deviation:.2%}'
                }
        return None


class SMAMultiIndicatorStrategy(Strategy):
    """多指标综合策略"""
    def __init__(self, fast_period: int = 50, slow_period: int = 120):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = 14
        self.adx_threshold = 25
        self.rsi_period = 14
        self.lookback_periods = max(slow_period, fast_period) + self.adx_period
        self.position_limit = 0.95
    
    def on_data(self, current_data: pd.Series, history: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(history) < self.lookback_periods:
            return None
            
        # 计算各种指标
        fast_ma = self.ti.sma(history, period=self.fast_period).iloc[-1]
        slow_ma = self.ti.sma(history, period=self.slow_period).iloc[-1]
        adx = self.ti.adx(history, period=self.adx_period).iloc[-1]
        rsi = self.ti.rsi(history, period=self.rsi_period).iloc[-1]
        macd = self.ti.macd(history)
        macd_hist = macd['hist'].iloc[-1]
        
        current_price = current_data['close']
        
        # 综合判断趋势强度
        uptrend_strong = (
            adx > self.adx_threshold and
            rsi > 60 and
            macd_hist > 0
        )
        
        downtrend_strong = (
            adx > self.adx_threshold and
            rsi < 40 and
            macd_hist < 0
        )
        
        if fast_ma > slow_ma and uptrend_strong and self.position <= 0:
            return {
                'action': 'BUY',
                'size': 0.01,
                'price': current_price,
                'reason': f'Strong Uptrend: ADX={adx:.1f}, RSI={rsi:.1f}'
            }
        elif fast_ma < slow_ma and downtrend_strong and self.position >= 0:
            return {
                'action': 'SELL',
                'size': 0.01,
                'price': current_price,
                'reason': f'Strong Downtrend: ADX={adx:.1f}, RSI={rsi:.1f}'
            }
        return None 