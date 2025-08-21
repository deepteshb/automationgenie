"""
Custom Exceptions

Defines custom exceptions with context for the automation tool.
"""

from typing import Dict, Any, Optional


class AutomationError(Exception):
    """Base exception for automation tool errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self):
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class TaskExecutionError(AutomationError):
    """Exception raised when a task fails to execute."""
    
    def __init__(self, message: str, task_name: Optional[str] = None, 
                 task_type: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if task_name:
            context['task_name'] = task_name
        if task_type:
            context['task_type'] = task_type
        
        super().__init__(message, context)


class PipelineExecutionError(AutomationError):
    """Exception raised when a pipeline fails to execute."""
    
    def __init__(self, message: str, pipeline_name: Optional[str] = None, 
                 failed_task: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if pipeline_name:
            context['pipeline_name'] = pipeline_name
        if failed_task:
            context['failed_task'] = failed_task
        
        super().__init__(message, context)


class ConfigurationError(AutomationError):
    """Exception raised when configuration is invalid."""
    
    def __init__(self, message: str, config_file: Optional[str] = None, 
                 config_path: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if config_file:
            context['config_file'] = config_file
        if config_path:
            context['config_path'] = config_path
        
        super().__init__(message, context)


class CredentialError(AutomationError):
    """Exception raised when credential retrieval fails."""
    
    def __init__(self, message: str, credential_type: Optional[str] = None, 
                 credential_name: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if credential_type:
            context['credential_type'] = credential_type
        if credential_name:
            context['credential_name'] = credential_name
        
        super().__init__(message, context)


class ValidationError(AutomationError):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        context = kwargs.copy()
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = value
        
        super().__init__(message, context)


class ConnectionError(AutomationError):
    """Exception raised when connection to external service fails."""
    
    def __init__(self, message: str, service: Optional[str] = None, 
                 endpoint: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if service:
            context['service'] = service
        if endpoint:
            context['endpoint'] = endpoint
        
        super().__init__(message, context)


class TimeoutError(AutomationError):
    """Exception raised when operation times out."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 timeout_seconds: Optional[float] = None, **kwargs):
        context = kwargs.copy()
        if operation:
            context['operation'] = operation
        if timeout_seconds:
            context['timeout_seconds'] = timeout_seconds
        
        super().__init__(message, context)


class ResourceNotFoundError(AutomationError):
    """Exception raised when a required resource is not found."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, 
                 resource_name: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if resource_type:
            context['resource_type'] = resource_type
        if resource_name:
            context['resource_name'] = resource_name
        
        super().__init__(message, context)


class PermissionError(AutomationError):
    """Exception raised when permission is denied."""
    
    def __init__(self, message: str, resource: Optional[str] = None, 
                 action: Optional[str] = None, **kwargs):
        context = kwargs.copy()
        if resource:
            context['resource'] = resource
        if action:
            context['action'] = action
        
        super().__init__(message, context)


def format_error_context(error: Exception) -> Dict[str, Any]:
    """
    Format error context for logging or reporting.
    
    Args:
        error: Exception instance
    
    Returns:
        Dictionary with error context information
    """
    if isinstance(error, AutomationError):
        return {
            'error_type': error.__class__.__name__,
            'message': error.message,
            'context': error.context
        }
    else:
        return {
            'error_type': error.__class__.__name__,
            'message': str(error),
            'context': {}
        }


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: Exception instance
    
    Returns:
        True if the error is retryable, False otherwise
    """
    retryable_errors = (
        ConnectionError,
        TimeoutError,
        # Add other retryable error types as needed
    )
    
    return isinstance(error, retryable_errors)
