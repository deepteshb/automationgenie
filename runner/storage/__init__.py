"""
Storage Package

Provides data storage and persistence for automation results.
"""

from .sqlite import RunDatabase
from .jsonl import JSONLLogger

__all__ = ["RunDatabase", "JSONLLogger"]
