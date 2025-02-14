import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.trader.binance_trader import BinanceTrader, TradeMode

def main():    
    # 初始化测试模式交易器
    test_trader = BinanceTrader(mode=TradeMode.TEST)
    
    # 获取当前价格
    price = test_trader.get_symbol_price('BTCUSDT')
    print(f"Current BTCUSDT price: {price}")
    
    # 下限价单（故意设置一个不太可能成交的价格）
    order = test_trader.place_order(
        symbol='BTCUSDT',
        side='BUY',
        order_type='LIMIT',
        quantity=0.002,  # 确保大于最小名义价值
        price=round(price * 0.9, 1)  # 比市价低10%
    )
        
    # 取消特定订单
    test_trader.cancel_order('BTCUSDT', order.order_id)
    
    # 或者取消所有订单
    # test_trader.cancel_all_orders('BTCUSDT')

if __name__ == "__main__":
    main() 