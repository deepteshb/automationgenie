"""
JSONL Logger

Provides append-only JSONL (JSON Lines) logging for structured data.
"""

import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog


class JSONLLogger:
    """Append-only JSONL logger for structured logging."""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 10 * 1024 * 1024):
        """
        Initialize JSONL logger.
        
        Args:
            log_dir: Directory for log files
            max_file_size: Maximum file size in bytes before rotation
        """
        self.logger = structlog.get_logger(__name__)
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file
        self.current_file = None
        self.current_file_path = None
    
    def log_event(self, event_type: str, data: Dict[str, Any], 
                 timestamp: Optional[datetime] = None) -> None:
        """
        Log an event to JSONL file.
        
        Args:
            event_type: Type of event (e.g., 'task_start', 'task_complete', 'error')
            data: Event data dictionary
            timestamp: Event timestamp (uses current time if not provided)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Prepare log entry
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        # Write to log file
        self._write_log_entry(log_entry)
    
    def log_task_start(self, task_name: str, task_type: str, config: Dict[str, Any]) -> None:
        """Log task start event."""
        data = {
            'task_name': task_name,
            'task_type': task_type,
            'config': config
        }
        self.log_event('task_start', data)
    
    def log_task_complete(self, task_name: str, task_type: str, 
                         result: Dict[str, Any], duration: float) -> None:
        """Log task completion event."""
        data = {
            'task_name': task_name,
            'task_type': task_type,
            'result': result,
            'duration': duration
        }
        self.log_event('task_complete', data)
    
    def log_task_error(self, task_name: str, task_type: str, 
                      error: str, duration: float) -> None:
        """Log task error event."""
        data = {
            'task_name': task_name,
            'task_type': task_type,
            'error': error,
            'duration': duration
        }
        self.log_event('task_error', data)
    
    def log_pipeline_start(self, pipeline_name: str, config: Dict[str, Any]) -> None:
        """Log pipeline start event."""
        data = {
            'pipeline_name': pipeline_name,
            'config': config
        }
        self.log_event('pipeline_start', data)
    
    def log_pipeline_complete(self, pipeline_name: str, results: Dict[str, Any], 
                            duration: float) -> None:
        """Log pipeline completion event."""
        data = {
            'pipeline_name': pipeline_name,
            'results': results,
            'duration': duration
        }
        self.log_event('pipeline_complete', data)
    
    def _write_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Write a log entry to the current log file."""
        try:
            # Get current log file
            log_file = self._get_current_log_file()
            
            # Write JSON line
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Check if file rotation is needed
            if log_file.stat().st_size > self.max_file_size:
                self._rotate_log_file()
                
        except Exception as e:
            self.logger.error("Failed to write log entry", error=str(e))
    
    def _get_current_log_file(self) -> Path:
        """Get the current log file path."""
        if self.current_file_path is None:
            # Create new log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_file_path = self.log_dir / f"automation_{timestamp}.jsonl"
        
        return self.current_file_path
    
    def _rotate_log_file(self) -> None:
        """Rotate the current log file."""
        if self.current_file_path and self.current_file_path.exists():
            # Compress the current file
            compressed_file = self.current_file_path.with_suffix('.jsonl.gz')
            
            try:
                with open(self.current_file_path, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # Remove original file
                self.current_file_path.unlink()
                
                self.logger.info("Log file rotated", 
                               original=str(self.current_file_path),
                               compressed=str(compressed_file))
                
            except Exception as e:
                self.logger.error("Failed to rotate log file", error=str(e))
        
        # Reset current file path
        self.current_file_path = None
    
    def read_log_entries(self, log_file: str, event_type: Optional[str] = None, 
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Read log entries from a JSONL file.
        
        Args:
            log_file: Path to the log file
            event_type: Filter by event type (optional)
            limit: Maximum number of entries to return (optional)
            
        Returns:
            List of log entries
        """
        entries = []
        log_path = Path(log_file)
        
        try:
            # Handle compressed files
            if log_path.suffix == '.gz':
                import gzip
                with gzip.open(log_path, 'rt', encoding='utf-8') as f:
                    for line in f:
                        if limit and len(entries) >= limit:
                            break
                        
                        try:
                            entry = json.loads(line.strip())
                            if event_type is None or entry.get('event_type') == event_type:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            else:
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if limit and len(entries) >= limit:
                            break
                        
                        try:
                            entry = json.loads(line.strip())
                            if event_type is None or entry.get('event_type') == event_type:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            return entries
            
        except Exception as e:
            self.logger.error("Failed to read log entries", log_file=log_file, error=str(e))
            return []
    
    def get_log_files(self, include_compressed: bool = True) -> List[Path]:
        """
        Get list of available log files.
        
        Args:
            include_compressed: Include compressed log files
            
        Returns:
            List of log file paths
        """
        log_files = []
        
        for file_path in self.log_dir.glob("*.jsonl"):
            log_files.append(file_path)
        
        if include_compressed:
            for file_path in self.log_dir.glob("*.jsonl.gz"):
                log_files.append(file_path)
        
        return sorted(log_files, reverse=True)
    
    def search_logs(self, query: str, log_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search log entries across multiple files.
        
        Args:
            query: Search query (searches in event data)
            log_files: List of log files to search (searches all if not provided)
            
        Returns:
            List of matching log entries
        """
        results = []
        
        if log_files is None:
            log_files = [str(f) for f in self.get_log_files()]
        
        for log_file in log_files:
            entries = self.read_log_entries(log_file)
            
            for entry in entries:
                # Search in event data
                if self._search_in_dict(entry.get('data', {}), query):
                    results.append(entry)
        
        return results
    
    def _search_in_dict(self, data: Dict[str, Any], query: str) -> bool:
        """Recursively search for query in dictionary values."""
        query_lower = query.lower()
        
        for key, value in data.items():
            if isinstance(value, dict):
                if self._search_in_dict(value, query):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self._search_in_dict(item, query):
                        return True
                    elif isinstance(item, str) and query_lower in item.lower():
                        return True
            elif isinstance(value, str) and query_lower in value.lower():
                return True
            elif str(value).lower().find(query_lower) != -1:
                return True
        
        return False
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Clean up old log files.
        
        Args:
            days_to_keep: Number of days to keep log files
            
        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        deleted_count = 0
        
        for log_file in self.get_log_files():
            if log_file.stat().st_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    self.logger.info("Deleted old log file", file=str(log_file))
                except Exception as e:
                    self.logger.error("Failed to delete old log file", 
                                    file=str(log_file), error=str(e))
        
        return deleted_count
