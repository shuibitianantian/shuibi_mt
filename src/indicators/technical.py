import pandas as pd
import talib
from typing import Tuple
import numpy as np

class TechnicalIndicators:    
    @staticmethod
    def sma(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """简单移动平均"""
        return talib.SMA(data['close'], timeperiod=period)
    
    @staticmethod
    def ema(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """指数移动平均"""
        return talib.EMA(data['close'], timeperiod=period)
    
    @staticmethod
    def rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """相对强弱指标"""
        return talib.RSI(data['close'], timeperiod=period)
    
    @staticmethod
    def macd(data: pd.DataFrame, 
            fast_period: int = 12, 
            slow_period: int = 26, 
            signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标"""
        macd, signal, hist = talib.MACD(
            data['close'], 
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )
        return macd, signal, hist
    
    @staticmethod
    def bollinger_bands(data: pd.DataFrame, 
                       period: int = 20, 
                       std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带"""
        upper, middle, lower = talib.BBANDS(
            data['close'],
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev
        )
        return upper, middle, lower
    
    @staticmethod
    def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """平均真实范围"""
        return talib.ATR(
            data['high'],
            data['low'],
            data['close'],
            timeperiod=period
        )
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算 ADX (Average Directional Index)
        
        Args:
            df: 包含 'high', 'low', 'close' 列的 DataFrame
            period: ADX 计算周期
            
        Returns:
            ADX 值的 Series
        """
        # 计算 True Range (TR)
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

        # 计算平滑 ATR（Wilder’s Smoothing）
        atr = tr.ewm(span=period, adjust=False).mean()

        # 计算 Directional Movement (DM)
        up_move = high.diff()
        down_move = low.diff()

        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), -down_move, 0)

        # 转换 pos_dm 和 neg_dm 为 pd.Series
        pos_dm = pd.Series(pos_dm, index=df.index)
        neg_dm = pd.Series(neg_dm, index=df.index)

        # 计算平滑 +DM 和 -DM
        pos_dm_smooth = pos_dm.ewm(span=period, adjust=False).mean()
        neg_dm_smooth = neg_dm.ewm(span=period, adjust=False).mean()

        # 计算 Directional Indicators (DI)
        pdi = 100 * (pos_dm_smooth / atr).fillna(0)
        ndi = 100 * (neg_dm_smooth / atr).fillna(0)

        # 计算 DX 并处理除零错误
        dx = 100 * abs(pdi - ndi) / np.where((pdi + ndi) == 0, 1, (pdi + ndi))

        # 计算 ADX
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx
    
    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算 RSI (Relative Strength Index)"""
        close = df['close']
        delta = close.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """计算 MACD (Moving Average Convergence Divergence)"""
        close = df['close']
        
        # 计算快线和慢线
        exp1 = close.ewm(span=fast_period, adjust=False).mean()
        exp2 = close.ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线和信号线
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # 计算MACD柱状图
        hist = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'hist': hist
        })
    
    @staticmethod
    def sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算简单移动平均线"""
        return df['close'].rolling(window=period).mean() 