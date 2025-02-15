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
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """下载历史K线数据"""
        try:
            start_ts = self._convert_time_to_timestamp(start_time)
            end_ts = self._convert_time_to_timestamp(end_time)
            all_data = []
            total_downloaded = 0
            total_saved = 0
            batch_count = 0
            
            while start_ts < end_ts:
                batch_count += 1
                
                # 使用期货API获取K线数据
                klines = self.client.klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=start_ts,
                    endTime=end_ts,
                    limit=1000
                )
                
                if not klines:
                    break
                
                # 转换为DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # 处理数据类型
                # 将毫秒时间戳转换为UTC时间
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                
                for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                           'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']:
                    df[col] = df[col].astype(float)
                df['number_of_trades'] = df['number_of_trades'].astype(int)
                
                # 设置索引
                df.set_index('timestamp', inplace=True)
                
                batch_size = len(df)
                total_downloaded += batch_size
                
                # 立即保存到数据库
                if save_to_db:
                    before_count = self.db.get_record_count(symbol, interval)
                    start_time, end_time, skipped_count, saved_count = self.db.save_kline_data(df, symbol, interval)
                    self.logger.info(
                        f"Saved {saved_count} records from {start_time} to {end_time}"
                        + (f" (Skipped {skipped_count})" if skipped_count > 0 else "")
                    )
                    after_count = self.db.get_record_count(symbol, interval)
                    saved_count = after_count - before_count
                    total_saved += saved_count
                    skipped = batch_size - saved_count
                
                # 保存数据用于返回
                all_data.append(df)
                
                # 更新开始时间为最后一条数据的时间
                start_ts = klines[-1][0] + 1
                
                # 添加延时避免触发限制
                time.sleep(0.1)
            
            if not all_data:
                raise ValueError("No data downloaded")
            
            # 合并所有数据
            final_df = pd.concat(all_data)
            
            # 打印总结信息
            if save_to_db and total_downloaded > 0:
                skipped = total_downloaded - total_saved
                self.logger.info(
                    f"Total batches: {batch_count} | "
                    f"Total downloaded: {total_downloaded} | "
                    f"Total saved: {total_saved} | "
                    f"Total skipped: {skipped} | "
                )
            
            return final_df
        
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