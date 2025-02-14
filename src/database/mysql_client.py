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
            UNIQUE KEY unique_kline (symbol, kline_interval, timestamp),
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
        保存K线数据到数据库，自动跳过重复记录
        """
        try:
            # 准备数据
            df = df.reset_index()
            df['symbol'] = symbol
            df['kline_interval'] = interval
            
            # 确保时间戳格式符合MySQL DATETIME格式 (YYYY-MM-DD HH:MM:SS)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 确保所有数值列都是float类型
            numeric_columns = [
                'open', 'high', 'low', 'close', 
                'volume', 'quote_asset_volume',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume'
            ]
            for col in numeric_columns:
                df[col] = df[col].astype(float)
            
            # 确保整数列都是int类型
            df['number_of_trades'] = df['number_of_trades'].astype(int)
            df['close_time'] = df['close_time'].astype(int)
            
            # 只保存需要的列
            columns_to_save = [
                'symbol', 'kline_interval', 'timestamp',
                'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume'
            ]
            df = df[columns_to_save]
            
            # 使用 INSERT IGNORE 语法
            with self.engine.connect() as conn:
                # 获取保存前的记录数
                before_count = pd.read_sql(
                    f"SELECT COUNT(*) as count FROM kline_data WHERE symbol = '{symbol}' AND kline_interval = '{interval}'",
                    conn
                ).iloc[0]['count']
                
                # 构建 INSERT IGNORE 语句
                table_name = 'kline_data'
                columns = ', '.join(columns_to_save)
                placeholders = ', '.join([':' + col for col in columns_to_save])
                
                insert_sql = f"""
                    INSERT IGNORE INTO {table_name} 
                    ({columns}) 
                    VALUES ({placeholders})
                """
                
                # 批量插入数据
                records = df.to_dict('records')
                conn.execute(text(insert_sql), records)
                conn.commit()
                
                # 获取保存后的记录数
                after_count = pd.read_sql(
                    f"SELECT COUNT(*) as count FROM kline_data WHERE symbol = '{symbol}' AND kline_interval = '{interval}'",
                    conn
                ).iloc[0]['count']
                
                saved_count = after_count - before_count
                skipped_count = len(df) - saved_count
                start_time = df['timestamp'].iloc[0]
                end_time = df['timestamp'].iloc[-1]

                return (start_time, end_time, skipped_count, saved_count)
                
        except Exception as e:
            self.logger.error(f"Error saving data to database: {str(e)}")
            raise
    
    def get_kline_data(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        resample_from_1m: bool = False
    ) -> pd.DataFrame:
        """
        从数据库获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线间隔
            start_time: 开始时间
            end_time: 结束时间（不包含）
            resample_from_1m: 是否从1分钟数据重采样（如果为True，会忽略数据库中已有的其他间隔数据）
        """
        try:
            if resample_from_1m and interval != '1m':
                # 先获取1分钟数据
                df = self.get_kline_data(symbol, '1m', start_time, end_time)
                # 然后重采样
                return self.resample_kline_data(df, interval)
            
            # 原有的查询逻辑
            query = f"""
            SELECT 
                timestamp, open, high, low, close, 
                volume, close_time, quote_asset_volume,
                number_of_trades, taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume
            FROM kline_data
            WHERE symbol = '{symbol}'
            AND kline_interval = '{interval}'
            AND timestamp >= '{start_time}' 
            AND timestamp < '{end_time}'
            ORDER BY timestamp ASC
            """
            
            df = pd.read_sql(query, self.engine)
            df.set_index('timestamp', inplace=True)
            self.logger.info(f"Retrieved {len(df)} records from database")
            
            # 确保使用UTC时间
            df.index = pd.to_datetime(df.index, utc=True)
            if resample_from_1m:
                # 对齐到Binance的K线时间
                if interval == '1h':
                    df = df.resample('1H', closed='left', label='left', offset='0h').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    })
                elif interval == '1d':
                    # Binance的日线是从UTC 00:00开始
                    df = df.resample('1D', closed='left', label='left', offset='0h').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    })
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving data from database: {str(e)}")
            raise

    def truncate_table(self):
        """清空K线数据表中的所有数据，但保留表结构"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE kline_data"))
                conn.commit()
            self.logger.info("Successfully truncated kline_data table")
        except Exception as e:
            self.logger.error(f"Error truncating table: {str(e)}")
            raise

    def drop_table(self):
        """完全删除K线数据表（包括表结构）"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS kline_data"))
                conn.commit()
            self.logger.info("Successfully dropped kline_data table")
        except Exception as e:
            self.logger.error(f"Error dropping table: {str(e)}")
            raise

    def get_record_count(self, symbol: str, interval: str) -> int:
        """获取指定交易对和间隔的记录数"""
        with self.engine.connect() as conn:
            result = pd.read_sql(
                f"SELECT COUNT(*) as count FROM kline_data WHERE symbol = '{symbol}' AND kline_interval = '{interval}'",
                conn
            )
            return result.iloc[0]['count']

    def resample_kline_data(
        self,
        df: pd.DataFrame,
        interval: str
    ) -> pd.DataFrame:
        """
        将1分钟K线数据重采样为任意时间间隔
        
        Args:
            df: 原始1分钟K线数据
            interval: 目标时间间隔 (例如: '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w')
            
        Returns:
            重采样后的K线数据
        """
        try:
            # 转换interval格式为pandas resample格式
            interval_map = {
                'm': 'min',  # 分钟
                'h': 'h',    # 小时
                'd': 'D',    # 天
                'w': 'W',    # 周
            }
            
            # 解析interval (例如: '15m' -> '15min')
            number = int(''.join(filter(str.isdigit, interval)))
            unit = interval_map[interval[-1]]
            resample_rule = f'{number}{unit}'
            
            # 确保时间戳是索引
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            
            # 执行重采样
            resampled = df.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'quote_asset_volume': 'sum',
                'number_of_trades': 'sum',
                'taker_buy_base_asset_volume': 'sum',
                'taker_buy_quote_asset_volume': 'sum'
            })
            
            # 删除包含NaN的行
            resampled = resampled.dropna()
            
            self.logger.info(
                f"Resampled data from 1m to {interval}: "
                f"Original records: {len(df)}, "
                f"Resampled records: {len(resampled)}"
            )
            
            return resampled
            
        except Exception as e:
            self.logger.error(f"Error resampling data: {str(e)}")
            raise 