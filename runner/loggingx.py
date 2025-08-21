"""
Structured Logging Setup

Configures structured logging with proper formatting and output handling.
"""

import sys
import logging
import structlog
from typing import Optional
from pathlib import Path


def setup_logging(level: str = "INFO", verbose: bool = False, 
                 log_file: Optional[str] = None) -> None:
    """
    Setup structured logging for the automation tool.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        verbose: Enable verbose output with more details
        log_file: Optional file path for logging output
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if verbose:
        # Add more detailed formatting for verbose mode
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Simple JSON-like output for production
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup file logging if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)


def log_execution_context(context: dict, logger: Optional[structlog.BoundLogger] = None) -> None:
    """
    Log execution context information.
    
    Args:
        context: Dictionary containing context information
        logger: Optional logger instance, creates new one if not provided
    """
    if logger is None:
        logger = get_logger(__name__)
    
    logger.info("Execution context", **context)


def log_task_start(task_name: str, task_type: str, config: dict, 
                  logger: Optional[structlog.BoundLogger] = None) -> None:
    """
    Log task execution start.
    
    Args:
        task_name: Name of the task
        task_type: Type of the task
        config: Task configuration
        logger: Optional logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    logger.info("Task execution started",
               task_name=task_name,
               task_type=task_type,
               config=config)


def log_task_completion(task_name: str, duration: float, status: str,
                       result: Optional[dict] = None,
                       logger: Optional[structlog.BoundLogger] = None) -> None:
    """
    Log task execution completion.
    
    Args:
        task_name: Name of the task
        duration: Execution duration in seconds
        status: Task status (completed, failed, etc.)
        result: Optional task result
        logger: Optional logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "task_name": task_name,
        "duration": duration,
        "status": status
    }
    
    if result:
        log_data["result"] = result
    
    logger.info("Task execution completed", **log_data)


def log_pipeline_start(pipeline_name: str, task_count: int,
                      logger: Optional[structlog.BoundLogger] = None) -> None:
    """
    Log pipeline execution start.
    
    Args:
        pipeline_name: Name of the pipeline
        task_count: Number of tasks in the pipeline
        logger: Optional logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    logger.info("Pipeline execution started",
               pipeline_name=pipeline_name,
               task_count=task_count)


def log_pipeline_completion(pipeline_name: str, duration: float, 
                           completed_tasks: int, total_tasks: int,
                           status: str,
                           logger: Optional[structlog.BoundLogger] = None) -> None:
    """
    Log pipeline execution completion.
    
    Args:
        pipeline_name: Name of the pipeline
        duration: Execution duration in seconds
        completed_tasks: Number of completed tasks
        total_tasks: Total number of tasks
        status: Pipeline status
        logger: Optional logger instance
    """
    if logger is None:
        logger = get_logger(__name__)
    
    logger.info("Pipeline execution completed",
               pipeline_name=pipeline_name,
               duration=duration,
               completed_tasks=completed_tasks,
               total_tasks=total_tasks,
               status=status)
