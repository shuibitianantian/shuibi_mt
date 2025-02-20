from binance.um_futures import UMFutures
from datetime import datetime
import pandas as pd
from typing import Optional
import os
from dotenv import load_dotenv
from src.utils.logger import setup_logger
from src.database.mysql_client import MySQLClient
import time


class BinanceDataDownloader:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.logger = setup_logger('downloader')
        self.logger.info("Initializing data downloader")
        
        # 加载 .env 文件
        load_dotenv()
        
        # 使用期货客户端
        self.client = UMFutures(
            key=api_key or os.getenv('BINANCE_API_KEY'),
            secret=api_secret or os.getenv('BINANCE_API_SECRET')
        )
        self.db = MySQLClient()
        self.logger.info("Connected to Binance Futures and Database")
    
    def download_historical_data(
        self,
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        save_path: str = '',
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        下载历史K线数据
        
        Args:
            symbol: 交易对
            interval: K线间隔
            start_time: 开始时间 (YYYY-MM-DD)
            end_time: 结束时间 (YYYY-MM-DD)
            save_path: CSV保存路径
            save_to_db: 是否保存到数据库
            
        Returns:
            包含K线数据的DataFrame
        """
        try:
            # 转换时间字符串为UTC时间戳
            start_ts = int(pd.Timestamp(start_time).tz_localize('UTC').timestamp() * 1000)
            end_ts = int(pd.Timestamp(end_time).tz_localize('UTC').timestamp() * 1000)
            
            self.logger.info(f"Downloading {symbol} {interval} data from {start_time} to {end_time}")
            
            # 存储所有K线数据
            all_klines = []
            current_start = start_ts
            
            while current_start < end_ts:
                # 获取一批K线数据
                klines = self.client.klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_ts,
                    limit=1000
                )
                
                if not klines:
                    break
                    
                all_klines.extend(klines)
                
                # 更新开始时间为最后一根K线的收盘时间
                current_start = klines[-1][6]  # close_time
                
                # 添加小延迟避免触发限制
                time.sleep(0.1)
            
            if not all_klines:
                self.logger.warning(f"No data found for {symbol} from {start_time} to {end_time}")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换时间戳为UTC时间
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                             'quote_asset_volume', 'taker_buy_base_asset_volume',
                             'taker_buy_quote_asset_volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            df['number_of_trades'] = df['number_of_trades'].astype(int)
            
            # 设置索引
            df.set_index('timestamp', inplace=True)
            
            # 保存到CSV
            if save_path:
                filename = f"{save_path}/{symbol}_{interval}_{start_time}_{end_time}.csv"
                df.to_csv(filename)
                self.logger.info(f"Data saved to {filename}")
            
            # 保存到数据库
            if save_to_db:
                self.db.save_kline_data(df, symbol, interval)
            
            self.logger.info(f"Downloaded {len(df)} klines")
            return df
        
        except Exception as e:
            self.logger.error(f"Error downloading data: {str(e)}")
            raise
    
    def _convert_time_to_timestamp(self, time_str: str) -> int:
        """
        将时间字符串转换为毫秒时间戳
        
        Args:
            time_str: 时间字符串 (格式: 'YYYY-MM-DD')
            
        Returns:
            毫秒时间戳
        """
        try:
            dt = datetime.strptime(time_str, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)  # 转换为毫秒
        except Exception as e:
            self.logger.error(f"Error converting time string to timestamp: {str(e)}")
            raise 