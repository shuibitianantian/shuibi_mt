from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd
from datetime import datetime
from src.config.database import MYSQL_CONFIG
from src.utils.logger import setup_logger

class MySQLClient:
    def __init__(self):
        self.logger = setup_logger('database')
        self.engine = self._create_engine()
        self._init_database()
    
    def _create_engine(self) -> Engine:
        """创建数据库连接引擎"""
        connection_str = (
            f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
            f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
        )
        return create_engine(connection_str)
    
    def _init_database(self):
        """初始化数据库表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS kline_data (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            kline_interval VARCHAR(10) NOT NULL,
            timestamp DATETIME NOT NULL,
            open DECIMAL(20,8) NOT NULL,
            high DECIMAL(20,8) NOT NULL,
            low DECIMAL(20,8) NOT NULL,
            close DECIMAL(20,8) NOT NULL,
            volume DECIMAL(30,8) NOT NULL,
            close_time BIGINT NOT NULL,
            quote_asset_volume DECIMAL(30,8) NOT NULL,
            number_of_trades INT NOT NULL,
            taker_buy_base_asset_volume DECIMAL(30,8) NOT NULL,
            taker_buy_quote_asset_volume DECIMAL(30,8) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_symbol_interval (symbol, kline_interval),
            INDEX idx_timestamp (timestamp)
        )
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
            self.logger.info("Database table initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def save_kline_data(self, df: pd.DataFrame, symbol: str, interval: str):
        """
        保存K线数据到数据库
        
        Args:
            df: K线数据DataFrame
            symbol: 交易对
            interval: K线间隔
        """
        try:
            # 准备数据
            df = df.reset_index()
            df['symbol'] = symbol
            df['kline_interval'] = interval
            
            # 只保存需要的列
            columns_to_save = [
                'symbol', 'kline_interval', 'timestamp',
                'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume'
            ]
            df = df[columns_to_save]
            
            # 保存到数据库
            df.to_sql('kline_data', self.engine, if_exists='append', index=False)
            self.logger.info(f"Saved {len(df)} records to database for {symbol} {interval}")
            
        except Exception as e:
            self.logger.error(f"Error saving data to database: {str(e)}")
            raise
    
    def get_kline_data(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        从数据库获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线间隔
            start_time: 开始时间
            end_time: 结束时间
        """
        try:
            query = f"""
            SELECT 
                timestamp, open, high, low, close, 
                volume, close_time, quote_asset_volume,
                number_of_trades, taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume
            FROM kline_data
            WHERE symbol = '{symbol}'
            AND kline_interval = '{interval}'
            AND timestamp BETWEEN '{start_time}' AND '{end_time}'
            ORDER BY timestamp ASC
            """
            
            df = pd.read_sql(query, self.engine)
            df.set_index('timestamp', inplace=True)
            self.logger.info(f"Retrieved {len(df)} records from database")
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving data from database: {str(e)}")
            raise 