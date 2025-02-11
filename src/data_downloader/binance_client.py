from binance.client import Client
from datetime import datetime
import pandas as pd
from typing import Optional
import os
from dotenv import load_dotenv
from src.utils.logger import setup_logger
from src.database.mysql_client import MySQLClient

class BinanceDataDownloader:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.logger = setup_logger('downloader')
        self.logger.info("Initializing data downloader")
        
        # 加载 .env 文件
        load_dotenv()
        
        # 如果没有传入api密钥，则使用环境变量中的密钥
        self.client = Client(
            api_key or os.getenv('BINANCE_API_KEY'),
            api_secret or os.getenv('BINANCE_API_SECRET')
        )
        self.db = MySQLClient()
        self.logger.info("Connected to Binance and Database")
        
    def download_historical_data(
        self,
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        save_path: Optional[str] = None,
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        下载指定交易对的历史数据
        
        Args:
            symbol: 交易对，如 'BTCUSDT'
            interval: 时间间隔，如 '1m', '5m', '1h', '1d'
            start_time: 开始时间，格式：'YYYY-MM-DD'
            end_time: 结束时间，格式：'YYYY-MM-DD'
            save_path: 保存路径，如果指定则保存为CSV
            save_to_db: 是否保存到数据库
        """
        try:
            self.logger.info(f"Downloading {symbol} data from {start_time} to {end_time}")
            # 转换时间格式
            start_date = datetime.strptime(start_time, '%Y-%m-%d')
            end_date = datetime.strptime(end_time, '%Y-%m-%d')
            
            # 如果是同一天，确保获取整天数据
            if start_date.date() == end_date.date():
                start_ts = int(start_date.replace(hour=0, minute=0, second=0).timestamp() * 1000)
                end_ts = int(end_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
            else:
                start_ts = int(start_date.timestamp() * 1000)
                end_ts = int(end_date.timestamp() * 1000)

            # 获取K线数据
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_ts,
                end_str=end_ts,
            )

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close',
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据处理
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 转换数值类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            
            self.logger.info(f"Downloaded {len(df)} candles")
            
            # 保存到数据库
            if save_to_db:
                self.db.save_kline_data(df, symbol, interval)
            
            # 保存到文件
            if save_path:
                filename = f"{save_path}/{symbol}_{interval}_{start_time}_{end_time}.csv"
                df.to_csv(filename)
                self.logger.info(f"Data saved to {filename}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error downloading data: {str(e)}")
            raise 