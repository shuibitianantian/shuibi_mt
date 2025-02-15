import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import pytz

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from src.data_downloader.binance_client import BinanceDataDownloader
from src.database.mysql_client import MySQLClient
from src.utils.logger import setup_logger

def get_latest_timestamp(db_client: MySQLClient, symbol: str, interval: str) -> datetime:
    """获取数据库中最新的数据时间"""
    query = f"""
        SELECT MAX(timestamp) as latest
        FROM kline_data
        WHERE symbol = "{symbol}"
        AND kline_interval = "{interval}"
    """
    result = db_client.execute_query(query)
    latest = result[0][0] if result and result[0][0] else None
    
    if not latest:
        # 如果没有数据，返回2020年初
        return datetime(2020, 1, 1, tzinfo=pytz.UTC)
    
    # 确保返回的时间有时区信息
    if latest.tzinfo is None:
        latest = pytz.UTC.localize(latest)
    return latest

def download_latest_data():
    # 初始化日志记录器和下载器
    logger = setup_logger('latest_downloader')
    downloader = BinanceDataDownloader()
    db_client = MySQLClient()
    
    symbol = 'BTCUSDT'
    intervals = ['1m', '5m', '15m', '1h', '1d']  # 支持多个时间周期
    
    try:
        for interval in intervals:
            # 获取最新数据时间
            latest_time = get_latest_timestamp(db_client, symbol, interval)
            # 确保当前时间有时区信息
            current_time = datetime.now(pytz.UTC)
            
            logger.info(f"Checking {interval} data:")
            logger.info(f"Latest data timestamp: {latest_time}")
            logger.info(f"Current time: {current_time}")
            
            # 计算下载批次大小（根据时间间隔调整）
            if interval == '1m':
                batch_days = 7  # 分钟级数据每次下载7天
            elif interval in ['5m', '15m']:
                batch_days = 15  # 5分钟和15分钟数据每次下载15天
            else:
                batch_days = 30  # 其他间隔每次下载30天
            
            current_start = latest_time
            retry_count = 0
            max_retries = 3
            
            while current_start < current_time:
                # 计算当前批次的结束时间
                current_end = min(current_start + timedelta(days=batch_days), current_time)
                try:
                    # 下载数据
                    df = downloader.download_historical_data(
                        symbol=symbol,
                        interval=interval,
                        start_time=current_start.strftime('%Y-%m-%d'),
                        end_time=current_end.strftime('%Y-%m-%d'),
                        save_to_db=True
                    )
                    
                    if df is not None and not df.empty:
                        logger.info(f"Downloaded {interval} data from {current_start} to {current_end}, "
                                  f"records: {len(df)}")
                        current_start = current_end
                        retry_count = 0  # 重置重试计数
                    else:
                        raise Exception("Downloaded DataFrame is empty")
                    
                    # 添加延时以避免触发频率限制
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error downloading {interval} data for period {current_start} "
                                f"to {current_end}: {str(e)}")
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        logger.error(f"Max retries reached for {interval} data, moving to next interval")
                        break
                    
                    # 指数退避重试
                    wait_time = 2 ** retry_count
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

def main():
    logger = setup_logger('latest_downloader')
    try:
        download_latest_data()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    main() 