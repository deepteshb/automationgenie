"""
Automation Tool Runner Package

This package provides the core automation engine for executing
pipelines and tasks across various platforms and services.
"""

__version__ = "1.0.0"
__author__ = "Automation Team"

from .engine import Engine
from .registry import TaskRegistry
from .cli import cli

__all__ = ["Engine", "TaskRegistry", "cli"]
