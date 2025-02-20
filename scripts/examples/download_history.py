import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.data_downloader.binance_client import BinanceDataDownloader
from src.database.mysql_client import MySQLClient
from src.utils.logger import setup_logger

def download_historical_data():
    # 初始化日志记录器和下载器
    logger = setup_logger('history_downloader')
    downloader = BinanceDataDownloader()
    
    # 设置时间范围
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 2, 20)
    
    logger.info(f"Starting download from {start_date.date()} to {end_date.date()}")
    
    # 每次下载30天的数据
    batch_days = 30
    current_start = start_date
    
    while current_start < end_date:
        # 计算当前批次的结束时间
        current_end = min(current_start + timedelta(days=batch_days), end_date)
        
        try:
            # 下载数据
            df = downloader.download_historical_data(
                symbol='BTCUSDT',
                interval='1m',
                start_time=current_start.strftime('%Y-%m-%d'),
                end_time=current_end.strftime('%Y-%m-%d'),
                save_to_db=True
            )
            
            logger.info(f"Downloaded data from {current_start.date()} to {current_end.date()}, "
                       f"records: {len(df)}")
            
            # 移动到下一个时间段
            current_start = current_end
            
            # 添加延时以避免触发频率限制
            time.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error downloading data for period {current_start.date()} "
                        f"to {current_end.date()}: {str(e)}")
            # 如果发生错误，等待longer时间后重试
            time.sleep(5)
            continue

def main():
    logger = setup_logger('history_downloader')
    try:
        download_historical_data()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    main() 