"""Structured JSON logging configuration."""

import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger to emit structured JSON logs."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        log_handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        log_handler.setFormatter(formatter)
        root_logger.addHandler(log_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return configured logger instance for a given module."""
    return logging.getLogger(name)
