import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.data_downloader.binance_client import BinanceDataDownloader

def main():
    # 初始化下载器
    downloader = BinanceDataDownloader()
    
    # 下载数据并保存到数据库
    df = downloader.download_historical_data(
        symbol='BTCUSDT',
        interval='1h',  # 1小时K线
        start_time='2024-02-01',
        end_time='2024-02-09',
        save_path='', # 不保存csv文件
        save_to_db=True  # 同时保存到数据库
    )
    
if __name__ == "__main__":
    main() 