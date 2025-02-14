import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.database.mysql_client import MySQLClient
from src.indicators.technical import TechnicalIndicators
from src.visualization.plotter import Plotter
from src.utils.logger import setup_logger

def main():
    logger = setup_logger('strategy_research')
    
    # 从数据库获取数据
    db = MySQLClient()
    
    # 方法2：从1分钟数据重采样得到15分钟数据
    df_15m_resampled = db.get_kline_data(
        symbol='BTCUSDT',
        interval='1d',
        start_time=datetime(2020, 1, 1),
        end_time=datetime(2020, 2, 1),
        resample_from_1m=True  # 启用重采样
    )

    logger.info(f"Loaded {len(df_15m_resampled)} records from database")
    
    # 计算技术指标
    ti = TechnicalIndicators()
    
    # 计算各种指标
    sma20 = ti.sma(df_15m_resampled, period=20)
    sma50 = ti.sma(df_15m_resampled, period=50)
    # rsi = ti.rsi(df_15m)
    # macd_data = ti.macd(df_15m)
    bb_data = ti.bollinger_bands(df_15m_resampled)
    
    # 创建绘图器
    plotter = Plotter(df_15m_resampled)
    
    # 绘制K线图和移动平均线
    plotter.plot_candlestick(
        indicators={
            'SMA20': sma20,
            'SMA50': sma50,
            'BB': bb_data
        }
    )
    
    logger.info("Analysis completed")

if __name__ == "__main__":
    main() 