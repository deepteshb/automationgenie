"""
Base Task

Abstract base class for all automation tasks.
"""

import time
import structlog
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..errors import TaskExecutionError


class Task(ABC):
    """Abstract base class for automation tasks."""
    
    # Task metadata
    task_type: str = "base"
    description: str = "Base task class"
    
    # Parameter specifications
    parameters: Dict[str, Dict[str, Any]] = {}
    required_parameters: List[str] = []
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize task with configuration.
        
        Args:
            config: Task configuration dictionary
        """
        self.config = config
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate task configuration."""
        errors = []
        
        # Check required parameters
        for param in self.required_parameters:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        # Validate parameter types if specified
        for param_name, param_value in self.config.items():
            if param_name in self.parameters:
                param_spec = self.parameters[param_name]
                if 'type' in param_spec:
                    expected_type = param_spec['type']
                    if not isinstance(param_value, expected_type):
                        errors.append(
                            f"Parameter {param_name} must be {expected_type.__name__}, "
                            f"got {type(param_value).__name__}"
                        )
        
        if errors:
            raise TaskExecutionError(
                f"Configuration validation failed: {'; '.join(errors)}",
                task_name=self.config.get('name', 'unknown'),
                task_type=self.task_type
            )
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute the task.
        
        Returns:
            Dictionary containing task results
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        pass
    
    def pre_execute(self) -> None:
        """
        Pre-execution setup and validation.
        
        Override in subclasses for custom pre-execution logic.
        """
        self.logger.info("Task pre-execution started", 
                        task_name=self.config.get('name'),
                        task_type=self.task_type)
    
    def post_execute(self, result: Dict[str, Any]) -> None:
        """
        Post-execution cleanup and processing.
        
        Args:
            result: Task execution result
        """
        self.logger.info("Task post-execution completed", 
                        task_name=self.config.get('name'),
                        task_type=self.task_type,
                        result_keys=list(result.keys()))
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete task execution cycle.
        
        Returns:
            Dictionary containing task results
        """
        start_time = time.time()
        task_name = self.config.get('name', 'unknown')
        
        try:
            self.logger.info("Task execution started", 
                           task_name=task_name,
                           task_type=self.task_type)
            
            # Pre-execution
            self.pre_execute()
            
            # Execute task
            result = self.execute()
            
            # Post-execution
            self.post_execute(result)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add metadata to result
            result['_metadata'] = {
                'task_name': task_name,
                'task_type': self.task_type,
                'duration': duration,
                'status': 'completed',
                'timestamp': time.time()
            }
            
            self.logger.info("Task execution completed", 
                           task_name=task_name,
                           duration=duration,
                           status='completed')
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.error("Task execution failed", 
                            task_name=task_name,
                            duration=duration,
                            error=str(e))
            
            # Return error result
            return {
                '_metadata': {
                    'task_name': task_name,
                    'task_type': self.task_type,
                    'duration': duration,
                    'status': 'failed',
                    'timestamp': time.time(),
                    'error': str(e)
                }
            }
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get a parameter value from configuration.
        
        Args:
            name: Parameter name
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default
        """
        return self.config.get(name, default)
    
    def require_parameter(self, name: str) -> Any:
        """
        Get a required parameter value from configuration.
        
        Args:
            name: Parameter name
            
        Returns:
            Parameter value
            
        Raises:
            TaskExecutionError: If parameter is missing
        """
        value = self.config.get(name)
        if value is None:
            raise TaskExecutionError(
                f"Required parameter '{name}' not found in configuration",
                task_name=self.config.get('name', 'unknown'),
                task_type=self.task_type
            )
        return value
    
    def log_parameter_access(self, parameter_name: str, masked: bool = False) -> None:
        """
        Log parameter access for audit purposes.
        
        Args:
            parameter_name: Name of the parameter accessed
            masked: Whether the parameter value should be masked in logs
        """
        if masked:
            self.logger.debug("Accessed sensitive parameter", 
                            parameter=parameter_name,
                            masked=True)
        else:
            value = self.config.get(parameter_name)
            self.logger.debug("Accessed parameter", 
                            parameter=parameter_name,
                            value=value)
