from datetime import datetime, timedelta

def validate_timeframe(start_time: str, end_time: str) -> bool:
    """验证时间范围是否有效"""
    try:
        start = datetime.strptime(start_time, '%Y-%m-%d')
        end = datetime.strptime(end_time, '%Y-%m-%d')
        return start < end
    except ValueError:
        return False

def get_valid_intervals() -> list:
    """返回有效的时间间隔列表"""
    return ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

def format_filename(symbol: str, interval: str, start_time: str, end_time: str) -> str:
    """格式化文件名"""
    return f"{symbol}_{interval}_{start_time}_{end_time}".replace(" ", "_") 