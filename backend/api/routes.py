from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.backtest.data_feed import DataFeed
from src.backtest.engine import Backtest
from src.backtest.strategy import SMAWithADXStrategy
from src.utils.logger import setup_logger

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
        # 处理日期字符串并确保UTC时区
        def parse_datetime(dt_str: str) -> datetime:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        
        start_time = parse_datetime(request.startTime)
        end_time = parse_datetime(request.endTime)
        
        logger.info(f"Parsed times - Start: {start_time}, End: {end_time}")
        
        # 获取回看周期
        lookback_days = get_lookback_period(request.interval)
        logger.info(f"Lookback days for {request.interval}: {lookback_days}")
        
        # 获取包含预热期的数据
        data_start = start_time - timedelta(days=lookback_days)
        logger.info(f"Data start time with lookback: {data_start}")
        
        data_feed = DataFeed.from_database(
            symbol=request.symbol,
            interval=request.interval,
            start_time=data_start,
            end_time=end_time,
            resample_from_1m=request.interval not in NO_NEED_RESAMPLE_INTERVALS
        )
        
        logger.info(f"Loaded {len(data_feed.data)} data points")
        
        # 获取策略类
        strategy_class = STRATEGY_MAP.get(request.strategyId)
        
        if not strategy_class:
            raise HTTPException(status_code=400, detail=f"Strategy {request.strategyId} not found")
            
        strategy = strategy_class(**request.params)
        
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
        
        # 格式化结果
        result = {
            "equity": [
                {
                    "timestamp": index.strftime('%Y-%m-%dT%H:%M:%S'),
                    "equity": row['equity'],
                    "position": row['position'],
                    "returns_pct": row['returns_pct']
                }
                for index, row in equity_df.iterrows()
            ],
            "trades": [
                Trade(
                    timestamp=trade.timestamp.strftime('%Y-%m-%dT%H:%M:%S'),
                    action=trade.action,
                    price=trade.price,
                    size=trade.size,
                    pnl=trade.pnl
                ) for trade in backtest.trades
            ],
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
            ],
            "stats": {
                'Total Return (%)': float(equity_df['returns_pct'].iloc[-1]),
                'Annual Return (%)': float(backtest.get_annual_return()),
                'Max Drawdown (%)': float(backtest.get_max_drawdown()),
                'Sharpe Ratio': float(backtest.get_sharpe_ratio()),
                'Win Rate (%)': float(backtest.get_win_rate())
            }
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
                    "timestamp": index.strftime('%Y-%m-%d %H:%M:%S'),
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
        raise HTTPException(status_code=500, detail=str(e)) 