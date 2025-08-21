"""
Shell Command Task

Executes general shell commands with proper environment and output handling.
"""

import subprocess
import os
import structlog
from typing import Dict, Any, List, Optional
from .base import Task
from ..errors import TaskExecutionError


class ShellTask(Task):
    """Task for executing shell commands."""
    
    task_type = "shell"
    description = "Execute shell commands"
    
    parameters = {
        'command': {'type': str, 'description': 'Shell command to execute'},
        'args': {'type': list, 'description': 'Additional command arguments'},
        'working_dir': {'type': str, 'description': 'Working directory for command'},
        'env_vars': {'type': dict, 'description': 'Environment variables to set'},
        'timeout': {'type': int, 'description': 'Command timeout in seconds'},
        'shell': {'type': bool, 'description': 'Execute in shell (True) or directly (False)'},
        'capture_output': {'type': bool, 'description': 'Capture command output'}
    }
    
    required_parameters = ['command']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.shell_path = self.get_parameter('shell_path', '/bin/bash')
    
    def pre_execute(self) -> None:
        """Pre-execution setup for shell commands."""
        super().pre_execute()
        
        # Set up working directory
        working_dir = self.get_parameter('working_dir')
        if working_dir:
            if not os.path.exists(working_dir):
                raise TaskExecutionError(
                    f"Working directory does not exist: {working_dir}",
                    task_name=self.config.get('name'),
                    task_type=self.task_type
                )
            os.chdir(working_dir)
            self.logger.info("Changed working directory", directory=working_dir)
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute shell command.
        
        Returns:
            Dictionary containing command results
        """
        command = self.require_parameter('command')
        args = self.get_parameter('args', [])
        env_vars = self.get_parameter('env_vars', {})
        timeout = self.get_parameter('timeout', 300)
        shell = self.get_parameter('shell', True)
        capture_output = self.get_parameter('capture_output', True)
        
        # Build command
        if shell:
            # Execute in shell
            if args:
                full_command = f"{command} {' '.join(args)}"
            else:
                full_command = command
            cmd = [self.shell_path, '-c', full_command]
        else:
            # Execute directly
            cmd = [command] + args
        
        # Prepare environment
        env = os.environ.copy()
        env.update(env_vars)
        
        self.logger.info("Executing shell command", 
                        command=' '.join(cmd) if not shell else full_command,
                        working_dir=os.getcwd(),
                        timeout=timeout)
        
        try:
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env,
                check=False  # Don't raise exception on non-zero return code
            )
            
            return {
                'command': ' '.join(cmd) if not shell else full_command,
                'stdout': result.stdout if capture_output else None,
                'stderr': result.stderr if capture_output else None,
                'return_code': result.returncode,
                'working_dir': os.getcwd(),
                'env_vars': list(env_vars.keys()) if env_vars else None
            }
            
        except subprocess.TimeoutExpired:
            raise TaskExecutionError(
                f"Command timed out after {timeout} seconds",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        except FileNotFoundError as e:
            raise TaskExecutionError(
                f"Command not found: {e}",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
        except Exception as e:
            raise TaskExecutionError(
                f"Command execution failed: {e}",
                task_name=self.config.get('name'),
                task_type=self.task_type
            )
    
    def post_execute(self, result: Dict[str, Any]) -> None:
        """Post-execution processing for shell commands."""
        super().post_execute(result)
        
        # Log command result
        return_code = result.get('return_code', -1)
        if return_code == 0:
            self.logger.info("Shell command completed successfully", 
                           return_code=return_code)
        else:
            self.logger.warning("Shell command completed with non-zero return code", 
                              return_code=return_code,
                              stderr=result.get('stderr'))
    
    def check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in the system.
        
        Args:
            command: Command to check
            
        Returns:
            True if command exists
        """
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.
        
        Returns:
            Dictionary with system information
        """
        info = {}
        
        # OS information
        try:
            result = subprocess.run(
                ['uname', '-a'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info['uname'] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Python version
        info['python_version'] = f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        
        # Working directory
        info['working_directory'] = os.getcwd()
        
        # Environment variables (non-sensitive)
        env_vars = {}
        for key, value in os.environ.items():
            if not any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                env_vars[key] = value
        info['environment_variables'] = env_vars
        
        return info
    
    def execute_with_retry(self, max_retries: int = 3, retry_delay: int = 5) -> Dict[str, Any]:
        """
        Execute command with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dictionary containing command results
        """
        import time
        
        for attempt in range(max_retries + 1):
            try:
                result = self.execute()
                
                # Check if command was successful
                if result.get('return_code') == 0:
                    return result
                
                # If not successful and we have more retries
                if attempt < max_retries:
                    self.logger.warning(f"Command failed, retrying in {retry_delay} seconds", 
                                      attempt=attempt + 1,
                                      max_retries=max_retries)
                    time.sleep(retry_delay)
                else:
                    return result
                    
            except TaskExecutionError as e:
                if attempt < max_retries:
                    self.logger.warning(f"Command execution failed, retrying in {retry_delay} seconds", 
                                      attempt=attempt + 1,
                                      max_retries=max_retries,
                                      error=str(e))
                    time.sleep(retry_delay)
                else:
                    raise
        
        # This should not be reached, but just in case
        return {'error': 'Max retries exceeded', 'return_code': -1}
