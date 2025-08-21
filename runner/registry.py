"""
Task Registry

Manages plugin discovery and task registration for the automation engine.
"""

import importlib
import inspect
import structlog
from typing import Dict, Type, Any, List
from pathlib import Path
from .tasks.base import Task


class TaskRegistry:
    """Registry for managing task plugins and their discovery."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self._tasks: Dict[str, Type[Task]] = {}
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Auto-discover tasks
        self._discover_tasks()
    
    def _discover_tasks(self) -> None:
        """Automatically discover and register task plugins."""
        tasks_dir = Path(__file__).parent / "tasks"
        
        if not tasks_dir.exists():
            self.logger.warning("Tasks directory not found", path=str(tasks_dir))
            return
        
        # Import all Python files in tasks directory
        for task_file in tasks_dir.glob("*.py"):
            if task_file.name in ["__init__.py", "base.py"]:
                continue
            
            module_name = f"runner.tasks.{task_file.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                # Find Task subclasses in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Task) and 
                        obj != Task):
                        
                        # Register the task
                        task_type = getattr(obj, 'task_type', name.lower())
                        self.register_task(task_type, obj)
                        
                        self.logger.info("Discovered task", 
                                       task_type=task_type, 
                                       module=module_name)
                        
            except Exception as e:
                self.logger.error("Failed to import task module", 
                                module=module_name, error=str(e))
    
    def register_task(self, task_type: str, task_class: Type[Task]) -> None:
        """Register a task class with the registry."""
        if not issubclass(task_class, Task):
            raise ValueError(f"Task class must inherit from Task: {task_class}")
        
        self._tasks[task_type] = task_class
        
        # Extract metadata from task class
        metadata = {
            'description': getattr(task_class, '__doc__', 'No description'),
            'parameters': getattr(task_class, 'parameters', {}),
            'required_parameters': getattr(task_class, 'required_parameters', []),
            'class': task_class
        }
        
        self._task_metadata[task_type] = metadata
        
        self.logger.info("Registered task", task_type=task_type)
    
    def get_task(self, task_type: str) -> Type[Task]:
        """Get a task class by type."""
        if task_type not in self._tasks:
            raise KeyError(f"Unknown task type: {task_type}")
        
        return self._tasks[task_type]
    
    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tasks with their metadata."""
        return {
            task_type: {
                'description': metadata['description'],
                'parameters': metadata['parameters'],
                'required_parameters': metadata['required_parameters']
            }
            for task_type, metadata in self._task_metadata.items()
        }
    
    def get_task_metadata(self, task_type: str) -> Dict[str, Any]:
        """Get metadata for a specific task type."""
        if task_type not in self._task_metadata:
            raise KeyError(f"Unknown task type: {task_type}")
        
        return self._task_metadata[task_type]
    
    def validate_task_config(self, task_type: str, config: Dict[str, Any]) -> List[str]:
        """Validate task configuration and return list of errors."""
        if task_type not in self._task_metadata:
            return [f"Unknown task type: {task_type}"]
        
        errors = []
        metadata = self._task_metadata[task_type]
        
        # Check required parameters
        for param in metadata.get('required_parameters', []):
            if param not in config:
                errors.append(f"Missing required parameter: {param}")
        
        # Validate parameter types if specified
        parameters = metadata.get('parameters', {})
        for param_name, param_value in config.items():
            if param_name in parameters:
                param_spec = parameters[param_name]
                if 'type' in param_spec:
                    expected_type = param_spec['type']
                    if not isinstance(param_value, expected_type):
                        errors.append(f"Parameter {param_name} must be {expected_type.__name__}, got {type(param_value).__name__}")
        
        return errors
    
    def reload_tasks(self) -> None:
        """Reload all task plugins."""
        self.logger.info("Reloading task plugins")
        self._tasks.clear()
        self._task_metadata.clear()
        self._discover_tasks()
    
    def get_available_task_types(self) -> List[str]:
        """Get list of available task types."""
        return list(self._tasks.keys())

    def has_task(self, task_type: str) -> bool:
        """Check if a task type is registered."""
        return task_type in self._tasks
