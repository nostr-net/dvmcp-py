import logging
import json
import sys
import time
from typing import Any, Dict, Optional, Union

def configure_logging(level: str = "INFO", 
                     format_string: Optional[str] = None,
                     include_timestamp: bool = True) -> None:
    """
    Configure global logging settings for DVMCP
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom log format string
        include_timestamp: Whether to include timestamps in context
    """
    root_logger = logging.getLogger("dvmcp")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        format_string or '%(levelname)s [%(name)s] %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

def get_logger(name: str) -> 'DVMCPLogger':
    """
    Get a configured logger for a specific component
    
    Args:
        name: Component name (typically module or class name)
        
    Returns:
        Configured logger instance
    """
    return DVMCPLogger(name)

class DVMCPLogger:
    """Configurable logging system for DVMCP with context support"""
    
    def __init__(self, name: str):
        """Initialize DVMCP logger for specific component"""
        self.logger = logging.getLogger(f"dvmcp.{name}")
        self.include_timestamp = True
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context data for log output"""
        if self.include_timestamp and 'timestamp' not in context:
            context['timestamp'] = time.time()
        
        try:
            return json.dumps(context)
        except (TypeError, ValueError):
            # Fallback for non-serializable objects
            sanitized = {}
            for k, v in context.items():
                try:
                    json.dumps({k: v})
                    sanitized[k] = v
                except (TypeError, ValueError):
                    sanitized[k] = str(v)
            return json.dumps(sanitized)
    
    def debug(self, message: str, **context) -> None:
        """Log debug message with context"""
        if context:
            message = f"{message} {self._format_context(context)}"
        self.logger.debug(message)
    
    def info(self, message: str, **context) -> None:
        """Log info message with context"""
        if context:
            message = f"{message} {self._format_context(context)}"
        self.logger.info(message)
    
    def warning(self, message: str, **context) -> None:
        """Log warning message with context"""
        if context:
            message = f"{message} {self._format_context(context)}"
        self.logger.warning(message)
    
    def error(self, message: str, **context) -> None:
        """Log error message with context"""
        if context:
            message = f"{message} {self._format_context(context)}"
        self.logger.error(message)
    
    def critical(self, message: str, **context) -> None:
        """Log critical message with context"""
        if context:
            message = f"{message} {self._format_context(context)}"
        self.logger.critical(message)