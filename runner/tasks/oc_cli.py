"""
OpenShift CLI Task

Executes OpenShift CLI commands for cluster management and operations.
"""

import subprocess
import json
import structlog
from typing import Dict, Any, List, Optional
from .base import Task
from ..errors import TaskExecutionError


class OpenShiftCLITask(Task):
    """Task for executing OpenShift CLI commands."""
    
    task_type = "oc_cli"
    description = "Execute OpenShift CLI commands"
    
    parameters = {
        'command': {'type': str, 'description': 'OC command to execute'},
        'args': {'type': list, 'description': 'Additional command arguments'},
        'namespace': {'type': str, 'description': 'Target namespace'},
        'output_format': {'type': str, 'description': 'Output format (json, yaml, etc.)'},
        'timeout': {'type': int, 'description': 'Command timeout in seconds'},
        'credentials': {'type': dict, 'description': 'Authentication credentials'}
    }
    
    required_parameters = ['command']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.oc_path = self.get_parameter('oc_path', 'oc')
    
    def pre_execute(self) -> None:
        """Pre-execution setup for OpenShift CLI."""
        super().pre_execute()
        
        # Check if oc CLI is available
        if not self._check_oc_cli():
            raise TaskExecutionError(
                "OpenShift CLI (oc) not found or not accessible",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        
        # Authenticate if credentials provided
        credentials = self.get_parameter('credentials')
        if credentials:
            self._authenticate(credentials)
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute OpenShift CLI command.
        
        Returns:
            Dictionary containing command results
        """
        command = self.require_parameter('command')
        args = self.get_parameter('args', [])
        namespace = self.get_parameter('namespace')
        output_format = self.get_parameter('output_format', 'json')
        timeout = self.get_parameter('timeout', 300)
        
        # Build command
        cmd = [self.oc_path, command] + args
        
        # Add namespace if specified
        if namespace:
            cmd.extend(['-n', namespace])
        
        # Add output format
        if output_format:
            cmd.extend(['-o', output_format])
        
        self.logger.info("Executing OpenShift command", 
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
    
    def _check_oc_cli(self) -> bool:
        """Check if OpenShift CLI is available."""
        try:
            result = subprocess.run(
                [self.oc_path, 'version'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _authenticate(self, credentials: Dict[str, Any]) -> None:
        """Authenticate with OpenShift cluster."""
        auth_method = credentials.get('method', 'token')
        
        if auth_method == 'token':
            token = credentials.get('token')
            server = credentials.get('server')
            
            if not token or not server:
                raise TaskExecutionError(
                    "Token authentication requires 'token' and 'server' credentials",
                    task_name=self.config.get('name'),
                    task_type=self.task_type
                )
            
            # Login with token
            cmd = [self.oc_path, 'login', '--token', token, '--server', server]
            
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info("Successfully authenticated with OpenShift cluster")
            except subprocess.CalledProcessError as e:
                raise TaskExecutionError(
                    f"Authentication failed: {e.stderr}",
                    task_name=self.config.get('name'),
                    task_type=self.task_type
                )
        
        elif auth_method == 'username_password':
            username = credentials.get('username')
            password = credentials.get('password')
            server = credentials.get('server')
            
            if not all([username, password, server]):
                raise TaskExecutionError(
                    "Username/password authentication requires 'username', 'password', and 'server'",
                    task_name=self.config.get('name'),
                    task_type=self.task_type
                )
            
            # Login with username/password
            cmd = [self.oc_path, 'login', '-u', username, '-p', password, '--server', server]
            
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info("Successfully authenticated with OpenShift cluster")
            except subprocess.CalledProcessError as e:
                raise TaskExecutionError(
                    f"Authentication failed: {e.stderr}",
                    task_name=self.config.get('name'),
                    task_type=self.task_type
                )
    
    def _parse_output(self, output: str, format_type: str) -> Any:
        """Parse command output based on format."""
        if not output.strip():
            return None
        
        if format_type == 'json':
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output
        
        elif format_type == 'yaml':
            try:
                import yaml
                return yaml.safe_load(output)
            except (ImportError, yaml.YAMLError):
                return output
        
        else:
            return output
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get OpenShift cluster information."""
        try:
            result = subprocess.run(
                [self.oc_path, 'cluster-info'],
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                'cluster_info': result.stdout,
                'return_code': result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                'error': e.stderr,
                'return_code': e.returncode
            }
    
    def get_project_list(self) -> List[str]:
        """Get list of available projects."""
        try:
            result = subprocess.run(
                [self.oc_path, 'get', 'projects', '-o', 'jsonpath={.items[*].metadata.name}'],
                capture_output=True,
                text=True,
                check=True
            )
            
            return result.stdout.split()
        except subprocess.CalledProcessError:
            return []
