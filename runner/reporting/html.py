"""
HTML Reporter

Generates HTML reports using Jinja2 templates for automation results.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
import structlog


class HTMLReporter:
    """Generates HTML reports for automation results."""
    
    def __init__(self, template_dir: Optional[str] = None):
        self.logger = structlog.get_logger(__name__)
        
        # Set up Jinja2 environment
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default to templates directory relative to this file
            self.template_dir = Path(__file__).parent.parent.parent / "templates"
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
    
    def generate_report(self, results: Dict[str, Any], output_dir: str) -> str:
        """
        Generate HTML report from automation results.
        
        Args:
            results: Dictionary containing automation results
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated HTML file
        """
        try:
            # Prepare template context
            context = self._prepare_context(results)
            
            # Load and render template
            template = self.env.get_template('report.html.j2')
            html_content = template.render(**context)
            
            # Create output directory if it doesn't exist
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"automation_report_{timestamp}.html"
            file_path = output_path / filename
            
            # Write HTML file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info("HTML report generated", 
                           file_path=str(file_path),
                           output_dir=output_dir)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error("Failed to generate HTML report", error=str(e))
            raise
    
    def _prepare_context(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context data for template rendering."""
        context = {
            'report_title': 'Automation Report',
            'generated_at': datetime.now().isoformat(),
            'results': results,
            'summary': self._generate_summary(results),
            'task_results': self._process_task_results(results),
            'errors': self._extract_errors(results),
            'warnings': self._extract_warnings(results)
        }
        
        # Add metadata
        if 'run_id' in results:
            context['run_id'] = results['run_id']
        
        if 'pipeline' in results:
            context['pipeline_name'] = Path(results['pipeline']).stem
        
        return context
    
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
    
    def _process_task_results(self, results: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Process and format task results for display."""
        processed_tasks = []
        
        for task in results.get('tasks', []):
            processed_task = {
                'name': task.get('name', 'Unknown'),
                'type': task.get('type', 'Unknown'),
                'status': task.get('status', 'unknown'),
                'duration': 0.0,
                'error': task.get('error'),
                'result_summary': self._summarize_task_result(task)
            }
            
            # Extract duration from metadata
            if '_metadata' in task:
                processed_task['duration'] = task['_metadata'].get('duration', 0.0)
            
            processed_tasks.append(processed_task)
        
        return processed_tasks
    
    def _summarize_task_result(self, task: Dict[str, Any]) -> str:
        """Create a summary of task result for display."""
        result = task.get('result', {})
        
        if not result:
            return "No result data"
        
        # Handle different result types
        if isinstance(result, dict):
            if 'stdout' in result:
                stdout = result['stdout']
                if stdout:
                    # Truncate long output
                    if len(stdout) > 200:
                        return f"{stdout[:200]}... (truncated)"
                    return stdout
                else:
                    return "Command executed (no output)"
            
            elif 'status_code' in result:
                return f"HTTP {result['status_code']}"
            
            elif 'return_code' in result:
                return f"Return code: {result['return_code']}"
            
            else:
                return f"Result with {len(result)} fields"
        
        elif isinstance(result, str):
            if len(result) > 200:
                return f"{result[:200]}... (truncated)"
            return result
        
        else:
            return str(result)[:200]
    
    def _extract_errors(self, results: Dict[str, Any]) -> list[str]:
        """Extract error messages from results."""
        errors = []
        
        for task in results.get('tasks', []):
            if task.get('status') == 'failed':
                error = task.get('error')
                if error:
                    errors.append(f"{task.get('name', 'Unknown task')}: {error}")
        
        return errors
    
    def _extract_warnings(self, results: Dict[str, Any]) -> list[str]:
        """Extract warning messages from results."""
        warnings = []
        
        # Add warnings based on task results
        for task in results.get('tasks', []):
            result = task.get('result', {})
            
            # Check for non-zero return codes
            if isinstance(result, dict) and result.get('return_code', 0) != 0:
                warnings.append(f"{task.get('name', 'Unknown task')}: Non-zero return code {result['return_code']}")
            
            # Check for HTTP error status codes
            if isinstance(result, dict) and 'status_code' in result:
                status_code = result['status_code']
                if 400 <= status_code < 600:
                    warnings.append(f"{task.get('name', 'Unknown task')}: HTTP {status_code}")
        
        return warnings
    
    def generate_custom_report(self, template_name: str, context: Dict[str, Any], 
                             output_path: str) -> str:
        """
        Generate a custom HTML report using a specific template.
        
        Args:
            template_name: Name of the template file
            context: Template context data
            output_path: Path for the output file
            
        Returns:
            Path to the generated HTML file
        """
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(**context)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write HTML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info("Custom HTML report generated", 
                           template=template_name,
                           output_path=str(output_file))
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error("Failed to generate custom HTML report", 
                            template=template_name,
                            error=str(e))
            raise
