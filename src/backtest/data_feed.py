import pandas as pd
from typing import Optional, List
from datetime import datetime
from src.database.mysql_client import MySQLClient
from src.utils.logger import setup_logger

class DataFeed:
    """数据馈送模块"""
    def __init__(self, df: pd.DataFrame):
        """
        初始化数据馈送
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame，时间索引
        """
        if df.empty:
            raise ValueError("DataFrame is empty")
            
        # 确保索引是 UTC 时区的时间戳
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        
        self.data = df
        self.current_idx = 0
        self.current_time = None  # 当前时间戳
        
        self.logger = setup_logger('data_feed')
        self.logger.info(f"Loaded {len(df)} records from {df.index[0]} to {df.index[-1]}")
    
    def next(self) -> Optional[pd.Series]:
        """返回下一个时间点的数据"""
        if self.current_idx >= len(self.data):
            return None
        
        row = self.data.iloc[self.current_idx]
        self.current_time = self.data.index[self.current_idx]  # 更新当前时间
        self.current_idx += 1
        return row
    
    def get_current_time(self) -> Optional[datetime]:
        """获取当前时间"""
        return self.current_time
    
    def look_back(self, periods: int) -> pd.DataFrame:
        """获取当前时间点之前的历史数据"""
        if self.current_idx == 0:
            return pd.DataFrame()
            
        start_idx = max(0, self.current_idx - periods)
        return self.data.iloc[start_idx:self.current_idx]
    
    def reset(self):
        """重置数据馈送到初始状态"""
        self.current_idx = 0
    
    @classmethod
    def from_database(
        cls,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        resample_from_1m: bool = False
    ):
        """从数据库加载数据"""
        db = MySQLClient()
        df = db.get_kline_data(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            resample_from_1m=resample_from_1m
        )
        
        if df.empty:
            raise ValueError(
                f"No data found for {symbol} {interval} "
                f"from {start_time} to {end_time}"
            )
            
        return cls(df) 