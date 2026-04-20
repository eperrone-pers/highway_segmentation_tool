"""
Centralized Logging Service for Highway Segmentation GA

This module provides a unified logging interface that can route messages to:
- GUI callback functions (for tkinter integration)
- Console output (print statements)
- File logging (future extension)

Eliminates code duplication of log functions across main.py optimization methods.
"""

from datetime import datetime
from typing import Optional, Callable


class Logger:
    """
    Centralized logger that routes messages to appropriate output destinations.
    
    Supports both GUI integration (via callbacks) and console output with
    consistent formatting and optional timestamping.
    """
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None, 
                 include_timestamp: bool = False, prefix: str = ""):
        """
        Initialize logger with optional callback and formatting options.
        
        Args:
            callback: Optional function to call with log messages (GUI integration)
            include_timestamp: Whether to prefix messages with timestamps
            prefix: Optional prefix to add to all messages
        """
        self.callback = callback
        self.include_timestamp = include_timestamp
        self.prefix = prefix
    
    def log(self, message: str) -> None:
        """
        Log a message using the configured output method.
        
        Args:
            message: The message to log
        """
        formatted_message = self._format_message(message)
        
        if self.callback:
            self.callback(formatted_message)
        else:
            print(formatted_message)
    
    def _format_message(self, message: str) -> str:
        """
        Apply formatting to messages (timestamp, prefix, etc.).
        
        Args:
            message: Raw message to format
            
        Returns:
            Formatted message string
        """
        formatted = message
        
        if self.prefix:
            formatted = f"{self.prefix}{formatted}"
        
        if self.include_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted = f"[{timestamp}] {formatted}"
        
        return formatted
    
    def set_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """
        Update the logging callback (useful for GUI integration).
        
        Args:
            callback: New callback function or None for console output
        """
        self.callback = callback
    
    def set_prefix(self, prefix: str) -> None:
        """
        Update the message prefix.
        
        Args:
            prefix: New prefix string
        """
        self.prefix = prefix


# Convenience function for creating logger instances
def create_logger(callback: Optional[Callable[[str], None]] = None, 
                  include_timestamp: bool = False, 
                  prefix: str = "") -> Logger:
    """
    Create a new Logger instance with the specified configuration.
    
    Args:
        callback: Optional GUI callback function
        include_timestamp: Whether to include timestamps
        prefix: Optional message prefix
    
    Returns:
        Configured Logger instance
    """
    return Logger(callback, include_timestamp, prefix)


# Default logger instance for module-level usage
default_logger = Logger()

def log(message: str) -> None:
    """
    Log a message using the default logger instance.
    
    Args:
        message: Message to log
    """
    default_logger.log(message)


def set_default_callback(callback: Optional[Callable[[str], None]]) -> None:
    """
    Set the callback for the default logger instance.
    
    Args:
        callback: GUI callback function or None for console output
    """
    default_logger.set_callback(callback)