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
    
    # 获取所有持仓
    positions = test_trader.get_positions()
    for pos in positions:
        print(pos)
    
    # 获取特定交易对的持仓
    btc_positions = test_trader.get_positions(symbol='BTCUSDT')
    if btc_positions:
        pos = btc_positions[0]
        print(f"BTC Position: {pos.position_amt} @ {pos.entry_price}")
    
    # # 下市价单
    # order = test_trader.place_order(
    #     symbol='BTCUSDT',
    #     side='BUY',
    #     order_type='MARKET',
    #     quantity=0.001
    # )
    
    # print(f"Order placed: {order}")
    
    # 获取余额
    btc_balance = test_trader.get_account_balance('BTC')
    print(f"BTC Balance: {btc_balance}")
    
    # 获取当前价格
    price = test_trader.get_symbol_price('BTCUSDT')
    print(f"Current BTCUSDT price: {price}")

if __name__ == "__main__":
    main() 