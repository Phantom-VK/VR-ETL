"""Custom exceptions with enriched context and logging."""
from __future__ import annotations

from typing import Any

from src.utils.logger import logger


class VRETLException(Exception):
    """Exception that captures filename and line number for easier debugging."""

    def __init__(self, error_message: str, error_details: Any):
        super().__init__(error_message)
        self.error_message = error_message
        self.exc_info = error_details.exc_info()
        _, _, exc_tb = self.exc_info
        self.lineno = exc_tb.tb_lineno if exc_tb else None
        self.filename = exc_tb.tb_frame.f_code.co_filename if exc_tb else None

    def __str__(self) -> str:
        custom_msg = (
            f"Error occurred in python script name [{self.filename}] "
            f"line number [{self.lineno}] error message [{self.error_message}]"
        )
        logger.error(custom_msg)
        return custom_msg


__all__ = ["VRETLException"]
