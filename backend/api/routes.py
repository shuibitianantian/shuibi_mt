from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.backtest.data_feed import DataFeed
from src.backtest.engine import Backtest
from src.backtest.strategy import SMAWithADXStrategy

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

@router.post("/api/backtest", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    try:
        # 处理日期字符串，移除时区信息
        start_time = datetime.strptime(request.startTime.split('T')[0], '%Y-%m-%d')
        end_time = datetime.strptime(request.endTime.split('T')[0], '%Y-%m-%d')
        
        # 确保有足够的历史数据来计算指标
        LOOKBACK_DAYS = 20
        start_time_with_buffer = start_time - timedelta(days=LOOKBACK_DAYS)
        
        # 创建数据源
        data_feed = DataFeed.from_database(
            symbol=request.symbol,
            interval=request.interval,
            start_time=start_time_with_buffer,
            end_time=end_time,
            resample_from_1m=True
        )
        
        # 获取策略类
        strategy_class = STRATEGY_MAP.get(request.strategyId)
        
        if not strategy_class:
            raise HTTPException(status_code=400, detail=f"Strategy {request.strategyId} not found")
            
        strategy = strategy_class(**request.params)
        
        # 创建回测实例 - 使用原始的开始时间
        backtest = Backtest(
            data_feed=data_feed,
            strategy=strategy,
            start_time=start_time,
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
):
    try:
        # 如果没有指定结束时间，使用当前时间前一天
        if end_time:
            end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        else:
            end = datetime.now() - timedelta(days=1)
            
        # 从数据库获取数据
        data_feed = DataFeed.from_database(
            symbol=symbol,
            interval='1m',
            start_time=end - timedelta(minutes=limit),  # 向前获取limit根K线
            end_time=end,
            resample_from_1m=False
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