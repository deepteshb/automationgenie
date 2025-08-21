"""
SQLite Database Storage

Provides SQLite database storage for automation run history and results.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog


class RunDatabase:
    """SQLite database for storing automation run history."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = structlog.get_logger(__name__)
        
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default to data directory
            self.db_path = Path("data/automation.db")
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY,
                        pipeline_name TEXT,
                        config TEXT,
                        status TEXT,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        duration REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create task_results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        task_name TEXT,
                        task_type TEXT,
                        status TEXT,
                        result TEXT,
                        error TEXT,
                        duration REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (run_id) REFERENCES runs (id)
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_runs_start_time ON runs (start_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_results_run_id ON task_results (run_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_results_status ON task_results (status)')
                
                conn.commit()
                
            self.logger.info("Database initialized", db_path=str(self.db_path))
            
        except Exception as e:
            self.logger.error("Failed to initialize database", error=str(e))
            raise
    
    def create_run(self, pipeline_name: str, config: Dict[str, Any]) -> str:
        """
        Create a new run record.
        
        Args:
            pipeline_name: Name of the pipeline
            config: Pipeline configuration
            
        Returns:
            Run ID
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO runs (id, pipeline_name, config, status, start_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    run_id,
                    pipeline_name,
                    json.dumps(config),
                    'running',
                    start_time
                ))
                
                conn.commit()
            
            self.logger.info("Run created", run_id=run_id, pipeline=pipeline_name)
            return run_id
            
        except Exception as e:
            self.logger.error("Failed to create run", error=str(e))
            raise
    
    def update_run(self, run_id: str, results: Dict[str, Any]) -> None:
        """
        Update run with final results.
        
        Args:
            run_id: Run ID to update
            results: Final results dictionary
        """
        end_time = datetime.now()
        status = results.get('status', 'unknown')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate duration
                cursor.execute('SELECT start_time FROM runs WHERE id = ?', (run_id,))
                start_time_str = cursor.fetchone()[0]
                start_time = datetime.fromisoformat(start_time_str)
                duration = (end_time - start_time).total_seconds()
                
                # Update run
                cursor.execute('''
                    UPDATE runs 
                    SET status = ?, end_time = ?, duration = ?
                    WHERE id = ?
                ''', (status, end_time, duration, run_id))
                
                conn.commit()
            
            self.logger.info("Run updated", run_id=run_id, status=status, duration=duration)
            
        except Exception as e:
            self.logger.error("Failed to update run", run_id=run_id, error=str(e))
            raise
    
    def log_task_result(self, run_id: str, task_name: str, result: Dict[str, Any]) -> None:
        """
        Log a task result.
        
        Args:
            run_id: Run ID
            task_name: Name of the task
            result: Task result dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO task_results (run_id, task_name, task_type, status, result, error, duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run_id,
                    task_name,
                    result.get('_metadata', {}).get('task_type', 'unknown'),
                    result.get('_metadata', {}).get('status', 'unknown'),
                    json.dumps(result),
                    result.get('_metadata', {}).get('error'),
                    result.get('_metadata', {}).get('duration', 0)
                ))
                
                conn.commit()
            
            self.logger.debug("Task result logged", run_id=run_id, task=task_name)
            
        except Exception as e:
            self.logger.error("Failed to log task result", run_id=run_id, task=task_name, error=str(e))
            raise
    
    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            Run details dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get run information
                cursor.execute('SELECT * FROM runs WHERE id = ?', (run_id,))
                run_row = cursor.fetchone()
                
                if not run_row:
                    return None
                
                # Get task results
                cursor.execute('SELECT * FROM task_results WHERE run_id = ? ORDER BY timestamp', (run_id,))
                task_rows = cursor.fetchall()
                
                # Build result
                run_details = {
                    'id': run_row['id'],
                    'pipeline_name': run_row['pipeline_name'],
                    'config': json.loads(run_row['config']),
                    'status': run_row['status'],
                    'start_time': run_row['start_time'],
                    'end_time': run_row['end_time'],
                    'duration': run_row['duration'],
                    'created_at': run_row['created_at'],
                    'tasks': []
                }
                
                for task_row in task_rows:
                    task_details = {
                        'name': task_row['task_name'],
                        'type': task_row['task_type'],
                        'status': task_row['status'],
                        'result': json.loads(task_row['result']) if task_row['result'] else None,
                        'error': task_row['error'],
                        'duration': task_row['duration'],
                        'timestamp': task_row['timestamp']
                    }
                    run_details['tasks'].append(task_details)
                
                return run_details
                
        except Exception as e:
            self.logger.error("Failed to get run details", run_id=run_id, error=str(e))
            return None
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent runs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of recent runs
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM runs 
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                runs = []
                for row in cursor.fetchall():
                    run = {
                        'id': row['id'],
                        'pipeline_name': row['pipeline_name'],
                        'status': row['status'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time'],
                        'duration': row['duration'],
                        'created_at': row['created_at']
                    }
                    runs.append(run)
                
                return runs
                
        except Exception as e:
            self.logger.error("Failed to get recent runs", error=str(e))
            return []
    
    def get_runs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get runs by status.
        
        Args:
            status: Status to filter by
            limit: Maximum number of runs to return
            
        Returns:
            List of runs with the specified status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM runs 
                    WHERE status = ?
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (status, limit))
                
                runs = []
                for row in cursor.fetchall():
                    run = {
                        'id': row['id'],
                        'pipeline_name': row['pipeline_name'],
                        'status': row['status'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time'],
                        'duration': row['duration'],
                        'created_at': row['created_at']
                    }
                    runs.append(run)
                
                return runs
                
        except Exception as e:
            self.logger.error("Failed to get runs by status", status=status, error=str(e))
            return []
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run and its associated task results.
        
        Args:
            run_id: Run ID to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete task results first (foreign key constraint)
                cursor.execute('DELETE FROM task_results WHERE run_id = ?', (run_id,))
                
                # Delete run
                cursor.execute('DELETE FROM runs WHERE id = ?', (run_id,))
                
                conn.commit()
            
            self.logger.info("Run deleted", run_id=run_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete run", run_id=run_id, error=str(e))
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total runs
                cursor.execute('SELECT COUNT(*) FROM runs')
                total_runs = cursor.fetchone()[0]
                
                # Runs by status
                cursor.execute('SELECT status, COUNT(*) FROM runs GROUP BY status')
                runs_by_status = dict(cursor.fetchall())
                
                # Total task results
                cursor.execute('SELECT COUNT(*) FROM task_results')
                total_tasks = cursor.fetchone()[0]
                
                # Tasks by status
                cursor.execute('SELECT status, COUNT(*) FROM task_results GROUP BY status')
                tasks_by_status = dict(cursor.fetchall())
                
                # Average run duration
                cursor.execute('SELECT AVG(duration) FROM runs WHERE duration IS NOT NULL')
                avg_duration = cursor.fetchone()[0] or 0
                
                return {
                    'total_runs': total_runs,
                    'runs_by_status': runs_by_status,
                    'total_tasks': total_tasks,
                    'tasks_by_status': tasks_by_status,
                    'average_run_duration': avg_duration
                }
                
        except Exception as e:
            self.logger.error("Failed to get statistics", error=str(e))
            return {}
