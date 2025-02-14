import logging
from pathlib import Path
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        配置好的日志记录器
    """
    # 获取或创建logger
    logger = logging.getLogger(name)
    
    # 如果logger已经配置过，直接返回
    if logger.handlers:
        return logger
        
    # 禁止传播到父logger
    logger.propagate = False
    
    logger.setLevel(logging.INFO)
    
    # 创建logs目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建并配置文件处理器
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger