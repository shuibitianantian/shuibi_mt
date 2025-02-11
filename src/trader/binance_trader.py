from binance.client import Client
from binance.um_futures import UMFutures  # 添加期货客户端
from binance.enums import *
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
from enum import Enum
from dataclasses import dataclass
from src.utils.logger import setup_logger

class TradeMode(Enum):
    TEST = "test"  # 使用测试网
    LIVE = "live"  # 使用主网

@dataclass
class OrderResult:
    """订单执行结果"""
    symbol: str
    order_id: str
    price: float
    quantity: float
    side: str
    status: str
    type: str
    filled_qty: float = 0.0
    avg_price: float = 0.0

    def __str__(self) -> str:
        """自定义打印格式"""
        return (
            f"\nOrder Details:"
            f"\n  Symbol: {self.symbol}"
            f"\n  Side: {self.side}"
            f"\n  Type: {self.type}"
            f"\n  Status: {self.status}"
            f"\n  Quantity: {self.quantity}"
            f"\n  Filled: {self.filled_qty}"
            f"\n  Price: {self.price if self.price > 0 else 'MARKET'}"
            f"\n  Avg Price: {self.avg_price if self.avg_price > 0 else 'N/A'}"
            f"\n  Order ID: {self.order_id}"
        )

@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    position_amt: float      # 持仓数量（正数为多头，负数为空头）
    entry_price: float       # 开仓均价
    mark_price: float        # 标记价格
    unrealized_pnl: float    # 未实现盈亏
    notional: float         # 名义价值
    position_side: str      # 持仓方向
    liquidation_price: float # 强平价格
    break_even_price: float  # 盈亏平衡价格

    def __str__(self) -> str:
        """自定义打印格式"""
        pnl_percentage = (self.unrealized_pnl / (self.notional - self.unrealized_pnl)) * 100 if self.notional != self.unrealized_pnl else 0
        return (
            f"\nPosition Details:"
            f"\n  Symbol: {self.symbol}"
            f"\n  Side: {self.position_side}"
            f"\n  Size: {self.position_amt}"
            f"\n  Entry Price: {self.entry_price:.2f}"
            f"\n  Mark Price: {self.mark_price:.2f}"
            f"\n  Break Even: {self.break_even_price:.2f}"
            f"\n  Unrealized PNL: {self.unrealized_pnl:.4f} USDT ({pnl_percentage:.2f}%)"
            f"\n  Position Value: {self.notional:.2f} USDT"
            f"\n  Liquidation Price: {self.liquidation_price if self.liquidation_price != '0' else 'N/A'}"
        )

class BinanceTrader:
    def __init__(
        self,
        mode: TradeMode,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ):
        """
        初始化交易器
        
        Args:
            mode: 交易模式 (TEST/LIVE)
            api_key: API密钥（可选，默认从环境变量获取）
            api_secret: API密钥（可选，默认从环境变量获取）
        """
        self.logger = setup_logger('trader')
        self.logger.info(f"Initializing trader in {mode.value} mode")
        
        load_dotenv()
        
        self.mode = mode
        
        # 根据模式选择对应的API密钥和客户端
        if mode == TradeMode.TEST:
            self.client = UMFutures(
                key=api_key or os.getenv('BINANCE_TESTNET_API_KEY'),
                secret=api_secret or os.getenv('BINANCE_TESTNET_API_SECRET'),
                base_url="https://testnet.binancefuture.com"
            )
            self.logger.info("Connected to Binance Testnet")
        else:
            self.client = UMFutures(
                key=api_key or os.getenv('BINANCE_API_KEY'),
                secret=api_secret or os.getenv('BINANCE_API_SECRET')
            )
            self.logger.info("Connected to Binance Mainnet")
    
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """
        下单函数
        
        Args:
            symbol: 交易对
            side: 买卖方向 ('BUY'/'SELL')
            order_type: 订单类型 ('LIMIT'/'MARKET')
            quantity: 数量
            price: 价格（市价单可不传）
        """
        try:
            self.logger.info(f"Placing {order_type} {side} order for {quantity} {symbol} @ {price if price else 'MARKET'}")
            params: Dict[str, Any] = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
            }
            
            if order_type == ORDER_TYPE_LIMIT:
                if not price:
                    raise ValueError("Limit order requires price")
                params['price'] = price
                params['timeInForce'] = TIME_IN_FORCE_GTC
            
            # 执行下单
            order = self.client.new_order(**params)
            
            order_result = OrderResult(
                symbol=order['symbol'],
                order_id=order['orderId'],
                price=float(order.get('price', 0)),
                quantity=float(order['origQty']),
                side=order['side'],
                status=order['status'],
                type=order['type'],
                filled_qty=float(order.get('executedQty', 0)),
                avg_price=float(order.get('avgPrice', 0))
            )
            
            self.logger.info(f"Order placed successfully: {order['orderId']}")
            return order_result
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            raise
    
    def get_account_balance(self, asset: str) -> float:
        """获取账户余额"""
        try:
            account = self.client.balance()
            for balance in account:
                if balance['asset'] == asset:
                    return float(balance['balance'])
            return 0.0
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
            raise
    
    def get_symbol_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            ticker = self.client.ticker_price(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error getting price: {str(e)}")
            raise
    
    def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """
        获取所有持仓信息
        
        Args:
            symbol: 交易对（可选，如果指定则只返回该交易对的持仓）
        
        Returns:
            持仓信息列表
        """
        try:
            positions = self.client.get_position_risk()
            result = []
            
            for pos in positions:
                # 如果指定了symbol且不匹配，则跳过
                if symbol and pos['symbol'] != symbol:
                    continue
                    
                # 只返回有持仓的仓位（持仓数量不为0）
                if float(pos['positionAmt']) != 0:
                    result.append(PositionInfo(
                        symbol=pos['symbol'],
                        position_amt=float(pos['positionAmt']),
                        entry_price=float(pos['entryPrice']),
                        mark_price=float(pos['markPrice']),
                        unrealized_pnl=float(pos['unRealizedProfit']),
                        notional=float(pos['notional']),
                        position_side=pos['positionSide'],
                        liquidation_price=float(pos['liquidationPrice']),
                        break_even_price=float(pos['breakEvenPrice'])
                    ))
            
            return result
            
        except Exception as e:
            print(f"Error getting positions: {str(e)}")
            raise

    def get_leverage(self, symbol: str) -> int:
        """获取交易对的杠杆倍数"""
        try:
            leverage_info = self.client.get_leverage_brackets(symbol=symbol)
            return int(leverage_info[0]['initialLeverage'])
        except Exception as e:
            print(f"Error getting leverage: {str(e)}")
            raise 