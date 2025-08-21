"""
AWS CLI Task

Executes AWS CLI commands for cloud resource management and operations.
"""

import subprocess
import json
import structlog
from typing import Dict, Any, List, Optional
from .base import Task
from ..errors import TaskExecutionError


class AWSCLITask(Task):
    """Task for executing AWS CLI commands."""
    
    task_type = "aws_cli"
    description = "Execute AWS CLI commands"
    
    parameters = {
        'command': {'type': str, 'description': 'AWS CLI command to execute'},
        'args': {'type': list, 'description': 'Additional command arguments'},
        'region': {'type': str, 'description': 'AWS region'},
        'output_format': {'type': str, 'description': 'Output format (json, text, table)'},
        'timeout': {'type': int, 'description': 'Command timeout in seconds'},
        'credentials': {'type': dict, 'description': 'AWS credentials configuration'}
    }
    
    required_parameters = ['command']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.aws_path = self.get_parameter('aws_path', 'aws')
    
    def pre_execute(self) -> None:
        """Pre-execution setup for AWS CLI."""
        super().pre_execute()
        
        # Check if AWS CLI is available
        if not self._check_aws_cli():
            raise TaskExecutionError(
                "AWS CLI (aws) not found or not accessible",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        
        # Configure AWS credentials if provided
        credentials = self.get_parameter('credentials')
        if credentials:
            self._configure_credentials(credentials)
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute AWS CLI command.
        
        Returns:
            Dictionary containing command results
        """
        command = self.require_parameter('command')
        args = self.get_parameter('args', [])
        region = self.get_parameter('region')
        output_format = self.get_parameter('output_format', 'json')
        timeout = self.get_parameter('timeout', 300)
        
        # Build command
        cmd = [self.aws_path, command] + args
        
        # Add region if specified
        if region:
            cmd.extend(['--region', region])
        
        # Add output format
        if output_format:
            cmd.extend(['--output', output_format])
        
        self.logger.info("Executing AWS command", 
                        command=' '.join(cmd),
                        timeout=timeout)
        
        try:
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            
            # Parse output
            output = self._parse_output(result.stdout, output_format)
            
            return {
                'command': ' '.join(cmd),
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'output': output,
                'output_format': output_format
            }
            
        except subprocess.TimeoutExpired:
            raise TaskExecutionError(
                f"Command timed out after {timeout} seconds",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        except subprocess.CalledProcessError as e:
            raise TaskExecutionError(
                f"Command failed with return code {e.returncode}: {e.stderr}",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
    
    def _check_aws_cli(self) -> bool:
        """Check if AWS CLI is available."""
        try:
            result = subprocess.run(
                [self.aws_path, '--version'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _configure_credentials(self, credentials: Dict[str, Any]) -> None:
        """Configure AWS credentials."""
        # Set environment variables for AWS credentials
        if 'access_key_id' in credentials:
            import os
            os.environ['AWS_ACCESS_KEY_ID'] = credentials['access_key_id']
            self.log_parameter_access('access_key_id', masked=True)
        
        if 'secret_access_key' in credentials:
            import os
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['secret_access_key']
            self.log_parameter_access('secret_access_key', masked=True)
        
        if 'session_token' in credentials:
            import os
            os.environ['AWS_SESSION_TOKEN'] = credentials['session_token']
            self.log_parameter_access('session_token', masked=True)
        
        if 'region' in credentials:
            import os
            os.environ['AWS_DEFAULT_REGION'] = credentials['region']
        
        self.logger.info("AWS credentials configured")
    
    def _parse_output(self, output: str, format_type: str) -> Any:
        """Parse command output based on format."""
        if not output.strip():
            return None
        
        if format_type == 'json':
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output
        
        else:
            return output
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get AWS account information."""
        try:
            result = subprocess.run(
                [self.aws_path, 'sts', 'get-caller-identity', '--output', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {
                'error': str(e),
                'return_code': getattr(e, 'returncode', -1)
            }
    
    def list_regions(self) -> List[str]:
        """Get list of available AWS regions."""
        try:
            result = subprocess.run(
                [self.aws_path, 'ec2', 'describe-regions', '--output', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            return [region['RegionName'] for region in data.get('Regions', [])]
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []
    
    def get_resource_tags(self, resource_type: str, resource_id: str, region: str = None) -> Dict[str, Any]:
        """
        Get tags for a specific AWS resource.
        
        Args:
            resource_type: Type of resource (e.g., 'ec2', 's3')
            resource_id: ID of the resource
            region: AWS region (optional)
            
        Returns:
            Dictionary containing resource tags
        """
        cmd = [self.aws_path, resource_type, 'describe-tags', '--filters', f'Name=resource-id,Values={resource_id}']
        
        if region:
            cmd.extend(['--region', region])
        
        cmd.extend(['--output', 'json'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return {
                'error': str(e),
                'resource_type': resource_type,
                'resource_id': resource_id
            }
