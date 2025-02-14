from datetime import datetime

class Trade:
    """交易记录"""
    def __init__(
        self,
        timestamp: datetime,
        action: str,
        price: float,
        size: float,
        pnl: float = 0.0,
        reason: str = ""
    ):
        self.timestamp = timestamp
        self.action = action
        self.price = price
        self.size = size
        self.pnl = pnl
        self.reason = reason 