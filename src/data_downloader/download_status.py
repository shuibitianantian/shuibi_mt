import uuid
from typing import Dict
from src.database.mysql_client import MySQLClient

class DownloadStatus:
    def __init__(self):
        self.db = MySQLClient()
        self._init_table()
    
    def _init_table(self):
        """初始化状态表"""
        query = """
        CREATE TABLE IF NOT EXISTS download_status (
            task_id VARCHAR(36) PRIMARY KEY,
            state VARCHAR(20) NOT NULL,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.db.execute_query(query)
    
    def start(self) -> str:
        task_id = str(uuid.uuid4())
        query = "INSERT INTO download_status (task_id, state) VALUES (:task_id, :state)"
        self.db.execute_query(query, {"task_id": task_id, "state": "running"})
        return task_id
    
    def complete(self, task_id: str):
        query = "UPDATE download_status SET state = :state WHERE task_id = :task_id"
        self.db.execute_query(query, {"state": "completed", "task_id": task_id})
    
    def fail(self, task_id: str, error: str):
        query = "UPDATE download_status SET state = :state, error = :error WHERE task_id = :task_id"
        self.db.execute_query(query, {"state": "failed", "error": error, "task_id": task_id})
    
    def get_status(self, task_id: str) -> Dict:
        query = "SELECT state, error FROM download_status WHERE task_id = :task_id"
        result = self.db.execute_query(query, {"task_id": task_id})
        if result and result[0]:
            return {"state": result[0][0], "error": result[0][1]}
        return {"state": "unknown"}