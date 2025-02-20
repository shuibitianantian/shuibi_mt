import sys
from pathlib import Path
import time
from sqlalchemy import text

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent)
sys.path.append(root_path)

from src.database.mysql_client import MySQLClient
from src.utils.logger import setup_logger

def clean_database():
    logger = setup_logger('data_cleaner')
    db = MySQLClient()
    
    try:
        # 删除所有K线数据
        logger.info("Starting to clean kline_data table...")

        # 获取当前记录数
        count_query = "SELECT COUNT(*) FROM kline_data"
        result = db.execute_query(count_query)
        total_records = result[0][0] if result else 0
        
        logger.info(f"Found {total_records} records to delete")
        
        if total_records > 0:
            # 删除所有数据
            with db.engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE kline_data"))
                conn.commit()
            
            logger.info("Successfully deleted all kline data")
            
            # 优化表
            logger.info("Optimizing table...")
            with db.engine.connect() as conn:
                conn.execute(text("OPTIMIZE TABLE kline_data"))
                conn.commit()
            
            logger.info("Table optimization completed")
        
        else:
            logger.info("No data to delete")
        
    except Exception as e:
        logger.error(f"Error cleaning database: {str(e)}")
        raise

def main():
    logger = setup_logger('data_cleaner')
    try:
        # 请求用户确认
        response = input("This will delete ALL data from the database. Are you sure? (yes/no): ")
        
        if response.lower() == 'yes':
            logger.info("Starting database cleanup...")
            clean_database()
            logger.info("Database cleanup completed")
        else:
            logger.info("Operation cancelled by user")
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 