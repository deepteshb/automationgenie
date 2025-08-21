"""
CSV Helper Utilities

Provides utilities for CSV data export and manipulation.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import structlog


class CSVHelper:
    """Helper class for CSV operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def export_results_to_csv(self, results: Dict[str, Any], output_path: str) -> str:
        """
        Export automation results to CSV format.
        
        Args:
            results: Dictionary containing automation results
            output_path: Path for the output CSV file
            
        Returns:
            Path to the generated CSV file
        """
        try:
            # Prepare data for CSV export
            csv_data = self._prepare_csv_data(results)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                if csv_data:
                    fieldnames = csv_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    writer.writerows(csv_data)
            
            self.logger.info("CSV export completed", 
                           output_path=str(output_file),
                           rows=len(csv_data))
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error("Failed to export results to CSV", error=str(e))
            raise
    
    def _prepare_csv_data(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare data for CSV export."""
        csv_data = []
        
        # Add summary row
        summary = self._generate_summary(results)
        summary_row = {
            'type': 'summary',
            'name': 'Overall Summary',
            'status': summary['status'],
            'total_tasks': summary['total_tasks'],
            'completed_tasks': summary['completed_tasks'],
            'failed_tasks': summary['failed_tasks'],
            'total_duration': f"{summary['total_duration']:.2f}s",
            'timestamp': datetime.now().isoformat()
        }
        csv_data.append(summary_row)
        
        # Add task rows
        for task in results.get('tasks', []):
            task_row = {
                'type': 'task',
                'name': task.get('name', 'Unknown'),
                'task_type': task.get('type', 'Unknown'),
                'status': task.get('status', 'unknown'),
                'duration': f"{task.get('_metadata', {}).get('duration', 0):.2f}s",
                'error': task.get('error', ''),
                'result_summary': self._summarize_for_csv(task.get('result', {}))
            }
            csv_data.append(task_row)
        
        return csv_data
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from results."""
        summary = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_duration': 0.0,
            'status': results.get('status', 'unknown')
        }
        
        tasks = results.get('tasks', [])
        summary['total_tasks'] = len(tasks)
        
        for task in tasks:
            task_status = task.get('status', 'unknown')
            if task_status == 'completed':
                summary['completed_tasks'] += 1
            elif task_status == 'failed':
                summary['failed_tasks'] += 1
            
            # Calculate duration
            if '_metadata' in task:
                duration = task['_metadata'].get('duration', 0)
                summary['total_duration'] += duration
        
        return summary
    
    def _summarize_for_csv(self, result: Any) -> str:
        """Create a CSV-friendly summary of task result."""
        if not result:
            return "No result data"
        
        if isinstance(result, dict):
            # Handle different result types
            if 'stdout' in result:
                stdout = result['stdout']
                if stdout:
                    return f"Output: {len(stdout)} chars"
                else:
                    return "No output"
            
            elif 'status_code' in result:
                return f"HTTP {result['status_code']}"
            
            elif 'return_code' in result:
                return f"Return code: {result['return_code']}"
            
            else:
                return f"Result with {len(result)} fields"
        
        elif isinstance(result, str):
            return f"String result: {len(result)} chars"
        
        else:
            return str(result)[:100]
    
    def export_task_details_to_csv(self, results: Dict[str, Any], output_path: str) -> str:
        """
        Export detailed task information to CSV.
        
        Args:
            results: Dictionary containing automation results
            output_path: Path for the output CSV file
            
        Returns:
            Path to the generated CSV file
        """
        try:
            # Prepare detailed data
            detailed_data = []
            
            for task in results.get('tasks', []):
                result = task.get('result', {})
                
                # Create detailed row
                row = {
                    'task_name': task.get('name', 'Unknown'),
                    'task_type': task.get('type', 'Unknown'),
                    'status': task.get('status', 'unknown'),
                    'duration_seconds': task.get('_metadata', {}).get('duration', 0),
                    'error_message': task.get('error', ''),
                    'command': result.get('command', ''),
                    'return_code': result.get('return_code', ''),
                    'status_code': result.get('status_code', ''),
                    'stdout_length': len(result.get('stdout', '')),
                    'stderr_length': len(result.get('stderr', '')),
                    'url': result.get('url', ''),
                    'method': result.get('method', ''),
                    'working_dir': result.get('working_dir', ''),
                    'timestamp': task.get('_metadata', {}).get('timestamp', '')
                }
                
                detailed_data.append(row)
            
            # Write CSV file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                if detailed_data:
                    fieldnames = detailed_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    writer.writerows(detailed_data)
            
            self.logger.info("Detailed CSV export completed", 
                           output_path=str(output_file),
                           rows=len(detailed_data))
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error("Failed to export detailed task data to CSV", error=str(e))
            raise
    
    def merge_csv_files(self, csv_files: List[str], output_path: str) -> str:
        """
        Merge multiple CSV files into a single file.
        
        Args:
            csv_files: List of CSV file paths to merge
            output_path: Path for the merged output file
            
        Returns:
            Path to the merged CSV file
        """
        try:
            merged_data = []
            fieldnames = set()
            
            # Read all CSV files
            for csv_file in csv_files:
                with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        merged_data.append(row)
                        fieldnames.update(row.keys())
            
            # Write merged CSV file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                if merged_data:
                    writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                    writer.writeheader()
                    writer.writerows(merged_data)
            
            self.logger.info("CSV files merged successfully", 
                           output_path=str(output_file),
                           input_files=len(csv_files),
                           total_rows=len(merged_data))
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error("Failed to merge CSV files", error=str(e))
            raise
    
    def convert_json_to_csv(self, json_data: List[Dict[str, Any]], output_path: str) -> str:
        """
        Convert JSON data to CSV format.
        
        Args:
            json_data: List of dictionaries to convert
            output_path: Path for the output CSV file
            
        Returns:
            Path to the generated CSV file
        """
        try:
            if not json_data:
                raise ValueError("No data to convert")
            
            # Get all field names
            fieldnames = set()
            for item in json_data:
                fieldnames.update(item.keys())
            
            # Write CSV file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                writer.writeheader()
                writer.writerows(json_data)
            
            self.logger.info("JSON to CSV conversion completed", 
                           output_path=str(output_file),
                           rows=len(json_data))
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error("Failed to convert JSON to CSV", error=str(e))
            raise
