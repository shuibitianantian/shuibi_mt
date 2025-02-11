import sys
from pathlib import Path

# 添加项目根目录到系统路径
root_path = str(Path(__file__).parent.parent.parent)
sys.path.append(root_path)

from src.database.mysql_client import MySQLClient

def main():
    # 测试数据库连接
    try:
        db = MySQLClient()
        print("Database connection successful!")
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")

if __name__ == "__main__":
    main() 