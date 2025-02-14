import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.backtest.data_feed import DataFeed
from src.backtest.strategy import SMAWithADXStrategy, SMASlopeStrategy, SMADeviationStrategy, SMAMultiIndicatorStrategy
from src.backtest.engine import Backtest
from src.utils.logger import setup_logger

def main():
    try:
        # 设置回测时间范围
        start_time = datetime(2020, 2, 1)
        end_time = datetime(2021, 1, 1)
        
        # 加载数据（加载比回测时间范围更长的数据，以便计算指标）
        data_feed = DataFeed.from_database(
            symbol='BTCUSDT',
            interval='1d',
            start_time=start_time - timedelta(days=20),
            end_time=end_time,
            resample_from_1m=True
        )

        # 选择要测试的策略
        strategy = SMAWithADXStrategy(fast_period=5, slow_period=20)
        # # 或
        # strategy = SMASlopeStrategy(fast_period=50, slow_period=120)
        # # 或
        # strategy = SMADeviationStrategy(fast_period=50, slow_period=120)
        # # 或
        # strategy = SMAMultiIndicatorStrategy(fast_period=50, slow_period=120)
        
        # 创建回测引擎
        backtest = Backtest(
            data_feed=data_feed,
            strategy=strategy,
            start_time=start_time,
            end_time=end_time,
            initial_capital=10000,
            commission=0.0004
        )
        # 运行回测
        equity_curve = backtest.run()
        
    except Exception as e:
        logger = setup_logger('backtest_example')
        logger.error(f"Error running backtest: {str(e)}")
        raise

if __name__ == "__main__":
    main() 