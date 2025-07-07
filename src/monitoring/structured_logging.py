#!/usr/bin/env python3
"""Structured logging system with JSON support and file rotation"""

import json
import logging
import logging.handlers
from datetime import datetime
from typing import Any, Dict, Optional

# Constants
BYTES_PER_MB = 1024 * 1024
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class JSONLogFormatter(logging.Formatter):
    """Formats log records as JSON strings for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with extended context"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception traceback if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Merge in any additional context fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        try:
            return json.dumps(log_entry)
        except TypeError:
            # Handle non-serializable data in extra_fields
            sanitized_entry = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in log_entry.items()
            }
            return json.dumps(sanitized_entry)


class StructuredLogger:
    """Enhanced logger supporting structured logging and context"""
    
    def __init__(self, name: str, config: Any):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
            config: Configuration object with attributes:
                    level: Logging level (e.g., 'DEBUG')
                    file: Log file path
                    max_size_mb: Max log file size in MB
                    backup_count: Number of backup files to keep
                    json_logging: Boolean for JSON formatting
                    format: Log format string (if not using JSON)
        """
        self.logger = logging.getLogger(name)
        self.config = config
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Set up logger handlers and formatters"""
        # Set log level
        self.logger.setLevel(self.config.level.upper())
        self.logger.handlers.clear()
        
        # Create rotating file handler
        max_bytes = int(self.config.max_size_mb * BYTES_PER_MB)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.config.file,
            maxBytes=max_bytes,
            backupCount=self.config.backup_count
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        
        # Configure formatter based on settings
        if getattr(self.config, 'json_logging', False):
            formatter = JSONLogFormatter()
        else:
            log_format = getattr(self.config, 'format', DEFAULT_LOG_FORMAT)
            formatter = logging.Formatter(log_format)
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_with_context(
        self,
        level: str,
        message: str,
        **context: Dict[str, Any]
    ) -> None:
        """
        Log message with additional context fields
        
        Args:
            level: Log level ('DEBUG', 'INFO', etc.)
            message: Primary log message
            context: Additional key-value pairs for structured logging
        """
        extra = {'extra_fields': context} if context else {}
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)
    
    def debug(self, message: str, **context: Dict[str, Any]) -> None:
        """Debug level log with context"""
        self.log_with_context('DEBUG', message, **context)
    
    def info(self, message: str, **context: Dict[str, Any]) -> None:
        """Info level log with context"""
        self.log_with_context('INFO', message, **context)
    
    def warning(self, message: str, **context: Dict[str, Any]) -> None:
        """Warning level log with context"""
        self.log_with_context('WARNING', message, **context)
    
    def error(self, message: str, **context: Dict[str, Any]) -> None:
        """Error level log with context"""
        self.log_with_context('ERROR', message, **context)


def get_structured_logger(name: str, config: Any) -> StructuredLogger:
    """
    Get initialized structured logger instance
    
    Args:
        name: Logger name
        config: Logger configuration object
        
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(name, config)