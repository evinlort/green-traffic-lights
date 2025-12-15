from __future__ import annotations


class PayloadError(Exception):
    """Standardized validation error for API requests."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.payload = {"error": message}
        self.status = status
