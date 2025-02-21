from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import sys
import os
import pandas as pd
import subprocess

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.backtest.data_feed import DataFeed
from src.backtest.engine import Backtest
from src.backtest.strategy import SMAWithADXStrategy
from src.utils.logger import setup_logger
from src.data_downloader.download_status import DownloadStatus  # 添加一个状态管理类

router = APIRouter()

class Trade(BaseModel):
    timestamp: datetime
    action: str
    price: float
    size: float
    pnl: float

class BacktestResult(BaseModel):
    equity: List[Dict[str, Any]]
    trades: List[Trade]
    stats: Dict[str, float]
    price_data: List[Dict[str, Any]]

class BacktestRequest(BaseModel):
    strategyId: str
    params: Dict[str, Any]
    symbol: str
    interval: str
    startTime: str
    endTime: str
    initialCapital: float

STRATEGY_MAP = {
    'sma-adx': SMAWithADXStrategy
}

NO_NEED_RESAMPLE_INTERVALS = ['1m', '5m' , '15m', '1h', '1d']

def get_lookback_period(interval: str) -> int:
    """
    根据时间间隔获取合适的回看周期
    
    Args:
        interval: 时间间隔 (1m, 5m, 15m, 1h, 4h, 1d 等)
        
    Returns:
        回看天数
    """
    # 将时间间隔转换为分钟
    interval_map = {
        'm': 1,
        'h': 60,
        'd': 1440,
        'w': 10080,
    }
    
    unit = interval[-1]  # 获取单位 (m/h/d/w)
    number = int(interval[:-1])  # 获取数字
    interval_minutes = number * interval_map[unit]
    
    # 根据不同的时间间隔设置不同的回看周期
    if interval_minutes <= 60:  # 小时级别及以下
        return 3  # 3天数据用于计算指标
    elif interval_minutes <= 240:  # 4小时及以下
        return 7  # 7天数据
    elif interval_minutes <= 1440:  # 日线
        return 30  # 30天数据
    else:  # 周线及以上
        return 90  # 90天数据

@router.post("/api/backtest", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    logger = setup_logger('backtest_api')
    try:
        def parse_datetime(dt_str: str) -> datetime:
            # 直接解析 ISO 格式的时间字符串
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        start_time = parse_datetime(request.startTime)
        end_time = parse_datetime(request.endTime)
        
        logger.info(f"Parsed times - Start: {start_time}, End: {end_time}")

        # 获取策略类
        strategy_class = STRATEGY_MAP.get(request.strategyId)
        if not strategy_class:
            raise HTTPException(status_code=400, detail=f"Strategy {request.strategyId} not found")
            
        strategy = strategy_class(**request.params)
        
        # 根据策略和时间间隔计算需要的预热数据量
        def calculate_lookback_time(interval: str, periods: int) -> timedelta:
            """根据时间间隔和所需周期数计算回看时间"""
            interval_map = {
                'm': timedelta(minutes=1),
                'h': timedelta(hours=1),
                'd': timedelta(days=1),
                'w': timedelta(weeks=1),
            }
            
            unit = interval[-1]
            number = int(interval[:-1])
            base_delta = interval_map[unit] * number
            
            return base_delta * periods
            
        # 计算需要的预热时间
        lookback_time = calculate_lookback_time(request.interval, strategy.lookback_periods)
        # 添加一些额外的缓冲时间
        lookback_time = lookback_time * 1.2  # 或其他合适的倍数
        
        logger.info(f"Strategy requires {strategy.lookback_periods} periods lookback")
        logger.info(f"Calculated lookback time: {lookback_time}")
        
        # 获取包含预热期的数据
        data_start = start_time - lookback_time
        
        data_feed = DataFeed.from_database(
            symbol=request.symbol,
            interval=request.interval,
            start_time=data_start,
            end_time=end_time,
            resample_from_1m=request.interval not in NO_NEED_RESAMPLE_INTERVALS
        )
        
        logger.info(f"Loaded {len(data_feed.data)} data points")
        
        # 创建回测实例 - 使用用户选择的开始时间
        backtest = Backtest(
            data_feed=data_feed,
            strategy=strategy,
            start_time=start_time,  # 用户选择的开始时间
            end_time=end_time,
            initial_capital=request.initialCapital,
            enable_report=False
        )
        
        # 运行回测
        equity_df = backtest.run()
        
        # 只返回回测时间范围内的数据
        mask = (data_feed.data.index >= start_time) & (data_feed.data.index <= end_time)
        backtest_data = data_feed.data[mask]
        
        # 格式化结果
        result = {
            "equity": [
                {
                    "timestamp": index.strftime('%Y-%m-%dT%H:%M:%S'),
                    "equity": row["equity"],
                    "position": row["position"]
                }
                for index, row in equity_df.iterrows()
            ],
            "trades": [
                {
                    "timestamp": trade.timestamp.strftime('%Y-%m-%dT%H:%M:%S'),
                    "action": trade.action,
                    "price": trade.price,
                    "size": trade.size,
                    "pnl": trade.pnl
                }
                for trade in backtest.trades
            ],
            "stats": backtest.get_stats(),
            "price_data": [
                {
                    "timestamp": index.strftime('%Y-%m-%dT%H:%M:%S'),
                    "open": row['open'],
                    "high": row['high'],
                    "low": row['low'],
                    "close": row['close'],
                    "volume": row['volume']
                }
                for index, row in backtest_data.iterrows()
            ]
        }
        
        return result
    except Exception as e:
        # 返回空结果而不是抛出错误
        return {
            "trades": [],
            "equity": [],
            "price_data": [],
            "stats": {
                "Total Return (%)": 0,
                "Annual Return (%)": 0,
                "Max Drawdown (%)": 0,
                "Sharpe Ratio": 0,
                "Win Rate (%)": 0,
            }
        }

@router.get("/api/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    end_time: Optional[str] = None,  # 结束时间，不传则为当前时间
    limit: int = 1000,  # 每次加载的K线数量
    interval: str = '1m'
):
    try:
        # 如果没有指定结束时间，使用当前时间前一天
        if end_time:
            end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        else:
            end = datetime.now() - timedelta(days=1)
            
        # 计算开始时间（根据limit和interval计算）
        interval_minutes = {
            'm': 1,
            'h': 60,
            'd': 1440,
            'w': 10080,
        }
        
        unit = interval[-1]  # 获取单位 (m/h/d/w)
        number = int(interval[:-1])  # 获取数字
        minutes_per_candle = number * interval_minutes[unit]
        
        # 计算需要往前推多少时间
        total_minutes = minutes_per_candle * limit
        start = end - timedelta(minutes=total_minutes)
            
        # 从数据库获取数据
        data_feed = DataFeed.from_database(
            symbol=symbol,
            interval=interval,
            start_time=start,
            end_time=end,
            resample_from_1m=interval not in NO_NEED_RESAMPLE_INTERVALS
        )
        
        return {
            "price_data": [
                {
                    "timestamp": index.strftime('%Y-%m-%dT%H:%M:%S'),
                    "open": row['open'],
                    "high": row['high'],
                    "low": row['low'],
                    "close": row['close'],
                    "volume": row['volume']
                }
                for index, row in data_feed.data.iterrows()
            ]
        }
    except Exception as e:
        return {
            "price_data": []
        }

download_status = DownloadStatus()

@router.post("/api/download-latest")
async def start_download():
    try:
        # 设置下载状态为进行中
        taskId = download_status.start()
        # 异步执行下载脚本，并传入状态ID
        subprocess.Popen([sys.executable, "../scripts/download_latest.py", str(taskId)])
        return {"taskId": taskId}
    except Exception as e:
        # 修复错误处理的调用
        download_status.fail(taskId, str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/download-status/{task_id}")
async def get_download_status(task_id: str):
    status = download_status.get_status(task_id)
    return status 