"""
PyPhotoManager - Professional Photo Management Software

A comprehensive photo management application built with PyQt6.
"""

__version__ = "0.1.0"
__author__ = "PyPhotoManager Team"
__description__ = "Professional Photo Management Software"

from .config.manager import ConfigManager, AppConfig
from .database.manager import DatabaseManager
from .utils.logging import LoggingManager

__all__ = [
    "ConfigManager",
    "AppConfig", 
    "DatabaseManager",
    "LoggingManager"
]