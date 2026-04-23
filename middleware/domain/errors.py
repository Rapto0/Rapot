from __future__ import annotations

from dataclasses import dataclass


class MiddlewareError(Exception):
    """Base error for middleware operations."""


@dataclass(slots=True)
class RiskRejection(MiddlewareError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(slots=True)
class ValidationFailure(MiddlewareError):
    reason: str

    def __str__(self) -> str:
        return self.reason


class DuplicateSignalError(MiddlewareError):
    """Raised when the same signal is received more than once."""


class UnsupportedBrokerError(MiddlewareError):
    """Raised when broker selection cannot be resolved."""
