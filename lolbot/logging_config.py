import logging
import os
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """Configure application-wide logging.

    Sets up a formatted stream handler for stdout and optionally a rotating file handler.
    Log level and file destination can be configured via arguments or environment variables.
    """
    log_level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, log_level_name, logging.INFO)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        file_path = log_file or os.getenv("LOG_FILE")
        if file_path:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    # Suppress verbose discord.http logs when log level is INFO or higher
    if numeric_level >= logging.INFO:
        logging.getLogger("discord.http").setLevel(logging.WARNING)

    return root_logger

