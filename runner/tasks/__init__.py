"""
Tasks Package

Contains task implementations for various automation scenarios.
"""

from .base import Task
from .oc_cli import OpenShiftCLITask
from .aws_cli import AWSCLITask
from .rest_call import RESTCallTask
from .shell import ShellTask

__all__ = [
    "Task",
    "OpenShiftCLITask", 
    "AWSCLITask",
    "RESTCallTask",
    "ShellTask"
]
