"""
Structured Logging for Respiro

Provides context-aware logging with S3 archival and error tracking.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict
import json

from respiro.config.settings import get_settings
from respiro.storage.s3_client import get_s3_client


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra context if present
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        if hasattr(record, "patient_id"):
            log_data["patient_id"] = record.patient_id
        
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class S3LogHandler(logging.Handler):
    """Log handler that archives logs to S3."""
    
    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.s3_client = get_s3_client()
        self.log_buffer = []
        self.buffer_size = 100
    
    def emit(self, record: logging.LogRecord):
        """Emit log record to buffer, flush to S3 when buffer is full."""
        try:
            log_entry = json.loads(self.format(record))
            self.log_buffer.append(log_entry)
            
            if len(self.log_buffer) >= self.buffer_size:
                self.flush_to_s3()
        except Exception:
            # Don't let logging errors break the application
            pass
    
    def flush_to_s3(self):
        """Flush log buffer to S3."""
        if not self.log_buffer:
            return
        
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            key = f"logs/application/{timestamp}.json"
            self.s3_client.upload_json(key, {"logs": self.log_buffer})
            self.log_buffer = []
        except Exception as e:
            # Log to stderr if S3 upload fails
            print(f"Failed to flush logs to S3: {e}", file=sys.stderr)
    
    def close(self):
        """Flush remaining logs before closing."""
        self.flush_to_s3()
        super().close()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with structured formatting.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    
    # S3 handler for archival (only in production)
    settings = get_settings()
    if settings.app.environment == "production":
        s3_handler = S3LogHandler(level=logging.INFO)
        logger.addHandler(s3_handler)
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    patient_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Log a message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        context: Optional context dictionary
        patient_id: Optional patient ID
        session_id: Optional session ID
    """
    extra = {}
    if context:
        extra["context"] = context
    if patient_id:
        extra["patient_id"] = patient_id
    if session_id:
        extra["session_id"] = session_id
    
    logger.log(level, message, extra=extra)
