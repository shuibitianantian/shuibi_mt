import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.data_downloader.binance_client import BinanceDataDownloader
from src.trader.binance_trader import BinanceTrader, TradeMode

def main():    
    # 初始化测试模式交易器
    test_trader = BinanceTrader(mode=TradeMode.TEST)
    
    # 获取当前价格
    price = test_trader.get_symbol_price('BTCUSDT')
    print(f"Current BTCUSDT price: {price}")
    
    # 获取交易规则
    rules = test_trader.get_symbol_rules('BTCUSDT')
    
    # 计算最小交易数量（确保名义价值 > 100 USDT）
    min_notional = 100
    min_qty = min_notional / price
    
    # 确保数量大于最小下单数量
    quantity = max(min_qty, rules['min_qty'])
    
    # 调整到合法的步长
    quantity = test_trader.round_step_size(quantity, rules['step_size'])
    
    print(f"Adjusted quantity: {quantity}")
    
    # 下市价单
    test_trader.place_order(
        symbol='BTCUSDT',
        side='BUY',
        order_type='MARKET',
        quantity=quantity
    )
    
    # 获取持仓信息
    positions = test_trader.get_positions()
    for pos in positions:
        print(pos)
    
    # 获取特定交易对的持仓
    btc_positions = test_trader.get_positions(symbol='BTCUSDT')
    if btc_positions:
        pos = btc_positions[0]
        print(f"BTC Position: {pos.position_amt} @ {pos.entry_price}")
    
    # 获取余额
    btc_balance = test_trader.get_account_balance('BTC')
    print(f"BTC Balance: {btc_balance}")

if __name__ == "__main__":
    main() 