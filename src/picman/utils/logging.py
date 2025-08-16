"""
Logging utilities for PyPhotoManager.
Provides structured logging with file rotation, console output, and log viewing capabilities.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, List
# import structlog  # 已移除，使用标准logging
import sys
import os
import json
import datetime
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """Log format enumeration."""
    TEXT = "text"
    JSON = "json"
    COLORED = "colored"


class LoggingManager:
    """Manages application logging configuration."""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = None
        self.log_file = None
        self.log_level = LogLevel.INFO
        self.log_format = LogFormat.TEXT
        self.console_enabled = True
        self.file_enabled = True
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
    def setup_logging(self, 
                     level: str = "INFO",
                     log_file: Optional[str] = None,
                     max_file_size: int = 10 * 1024 * 1024,
                     backup_count: int = 5,
                     log_format: Optional[str] = None,
                     console_enabled: bool = True,
                     file_enabled: bool = True) -> logging.Logger:
        """Setup application logging."""
        
        # Use config values if available
        if self.config:
            try:
                level = self.config.get("logging.level", level)
                log_file = self.config.get("logging.file_path", log_file)
                max_file_size = self.config.get("logging.max_file_size", max_file_size)
                backup_count = self.config.get("logging.backup_count", backup_count)
                log_format = self.config.get("logging.format", log_format)
                console_enabled = self.config.get("logging.console_enabled", console_enabled)
                file_enabled = self.config.get("logging.file_enabled", file_enabled)
            except (AttributeError, KeyError):
                # Fallback to direct attribute access if get() method is not available
                try:
                    level = getattr(self.config.logging, "level", level)
                    log_file = getattr(self.config.logging, "file_path", log_file)
                    max_file_size = getattr(self.config.logging, "max_file_size", max_file_size)
                    backup_count = getattr(self.config.logging, "backup_count", backup_count)
                    log_format = getattr(self.config.logging, "format", log_format)
                    console_enabled = getattr(self.config.logging, "console_enabled", console_enabled)
                    file_enabled = getattr(self.config.logging, "file_enabled", file_enabled)
                except AttributeError:
                    pass
        
        # Store settings
        self.log_file = log_file
        try:
            self.log_level = LogLevel[level.upper()]
        except (KeyError, AttributeError):
            self.log_level = LogLevel.INFO
        
        self.console_enabled = console_enabled
        self.file_enabled = file_enabled
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # Set log format
        if isinstance(log_format, str) and log_format.lower() in [f.value for f in LogFormat]:
            self.log_format = LogFormat(log_format.lower())
        else:
            self.log_format = LogFormat.TEXT
        
        # Default format
        text_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level.value)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level.value)
            
            if self.log_format == LogFormat.COLORED:
                try:
                    import colorlog
                    colored_formatter = colorlog.ColoredFormatter(
                        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        log_colors={
                            'DEBUG': 'cyan',
                            'INFO': 'green',
                            'WARNING': 'yellow',
                            'ERROR': 'red',
                            'CRITICAL': 'red,bg_white',
                        }
                    )
                    console_handler.setFormatter(colored_formatter)
                except ImportError:
                    # Fallback to plain text if colorlog is not available
                    console_formatter = logging.Formatter(text_format)
                    console_handler.setFormatter(console_formatter)
            else:
                console_formatter = logging.Formatter(text_format)
                console_handler.setFormatter(console_formatter)
                
            root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.file_enabled and log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level.value)
            
            if self.log_format == LogFormat.JSON:
                # JSON formatter
                class JsonFormatter(logging.Formatter):
                    def format(self, record):
                        log_data = {
                            'timestamp': datetime.datetime.fromtimestamp(record.created).isoformat(),
                            'name': record.name,
                            'level': record.levelname,
                            'message': record.getMessage(),
                            'module': record.module,
                            'line': record.lineno
                        }
                        if record.exc_info:
                            log_data['exception'] = self.formatException(record.exc_info)
                        return json.dumps(log_data)
                
                file_formatter = JsonFormatter()
            else:
                file_formatter = logging.Formatter(text_format)
                
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # 使用标准logging配置，移除structlog依赖
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level.value)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加控制台处理器
        if self.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level.value)
            
            if self.log_format == LogFormat.COLORED:
                # 简单的彩色输出格式
                console_formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            else:
                console_formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger("picman")
        return self.logger
    
    def get_logger(self, name: str = "picman") -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)
    
    def set_level(self, level: str) -> None:
        """Set the log level."""
        try:
            log_level = LogLevel[level.upper()]
            
            # Update root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level.value)
            
            # Update all handlers
            for handler in root_logger.handlers:
                handler.setLevel(log_level.value)
            
            self.log_level = log_level
            self.logger.info(f"Log level set to {level.upper()}")
            
        except KeyError:
            self.logger.error(f"Invalid log level: {level}")
    
    def get_log_entries(self, max_entries: int = 100, 
                       level: Optional[str] = None, 
                       search_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get log entries from the log file.
        
        Args:
            max_entries: Maximum number of entries to return
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            search_text: Filter by text in message
            
        Returns:
            List of log entries as dictionaries
        """
        if not self.log_file or not os.path.exists(self.log_file):
            return []
        
        entries = []
        level_filter = level.upper() if level else None
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read from the end of the file to get the most recent entries
                if self.log_format == LogFormat.JSON:
                    # For JSON logs, read line by line and parse JSON
                    lines = f.readlines()
                    for line in reversed(lines):
                        if len(entries) >= max_entries:
                            break
                            
                        try:
                            entry = json.loads(line.strip())
                            
                            # Apply filters
                            if level_filter and entry.get('level') != level_filter:
                                continue
                                
                            if search_text and search_text.lower() not in entry.get('message', '').lower():
                                continue
                                
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
                else:
                    # For text logs, parse each line
                    lines = f.readlines()
                    for line in reversed(lines):
                        if len(entries) >= max_entries:
                            break
                            
                        # Simple parsing of standard log format
                        try:
                            parts = line.strip().split(' - ', 3)
                            if len(parts) >= 3:
                                timestamp = parts[0]
                                name = parts[1]
                                level_msg = parts[2].split(' ', 1)
                                log_level = level_msg[0]
                                message = level_msg[1] if len(level_msg) > 1 else ""
                                
                                if len(parts) > 3:
                                    message += " - " + parts[3]
                                
                                # Apply filters
                                if level_filter and log_level != level_filter:
                                    continue
                                    
                                if search_text and search_text.lower() not in message.lower():
                                    continue
                                
                                entry = {
                                    'timestamp': timestamp,
                                    'name': name,
                                    'level': log_level,
                                    'message': message
                                }
                                entries.append(entry)
                        except Exception:
                            # Skip lines that don't match expected format
                            continue
        except Exception as e:
            # If there's an error reading the log file, return an error entry
            entries.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'name': 'logging.manager',
                'level': 'ERROR',
                'message': f"Error reading log file: {str(e)}"
            })
        
        return entries
