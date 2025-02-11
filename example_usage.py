from src.data_downloader.binance_client import BinanceDataDownloader
from src.trader.binance_trader import BinanceTrader, TradeMode

# 下载数据
downloader = BinanceDataDownloader()

df = downloader.download_historical_data(
    symbol='BTCUSDT',
    interval='1m',
    start_time='2025-02-09',
    end_time='2025-02-09',
    save_path='data'
)

# 测试模式
test_trader = BinanceTrader(mode=TradeMode.TEST)

# 实盘模式
# live_trader = BinanceTrader(mode=TradeMode.LIVE)

# 下市价单
order = test_trader.place_order(
    symbol='BTCUSDT',
    side='BUY',
    order_type='MARKET',
    quantity=0.001
)

# 获取余额
btc_balance = test_trader.get_account_balance('BTC')

# 获取当前价格
price = test_trader.get_symbol_price('BTCUSDT') 