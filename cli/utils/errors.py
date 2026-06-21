"""Unified exception classes with exit code mapping."""
from __future__ import annotations

import sys
from typing import Any


# Exit codes per design doc §4.5
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_CONFIG_ERROR = 3
EXIT_VALIDATION_ERROR = 4
EXIT_DEPENDENCY_ERROR = 5
EXIT_TIMEOUT = 6
EXIT_CIRCUIT_BREAKER = 7
EXIT_INTERRUPTED = 130


class CLIError(Exception):
    """Base exception for all CLI errors."""
    exit_code: int = EXIT_GENERAL_ERROR

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        return self.message


class ConfigError(CLIError):
    """Configuration file error (exit code 3)."""
    exit_code = EXIT_CONFIG_ERROR


class ValidationError(CLIError):
    """Data/business validation error (exit code 4)."""
    exit_code = EXIT_VALIDATION_ERROR


class DependencyError(CLIError):
    """External dependency failure (exit code 5)."""
    exit_code = EXIT_DEPENDENCY_ERROR


class TimeoutError(CLIError):
    """Task timeout (exit code 6)."""
    exit_code = EXIT_TIMEOUT


class CircuitBreakerError(CLIError):
    """Circuit breaker triggered (exit code 7)."""
    exit_code = EXIT_CIRCUIT_BREAKER


def handle_error(error: Exception) -> int:
    """Convert exception to exit code.

    Returns the exit code; also prints user-friendly message to stderr.
    """
    import click
    if isinstance(error, CLIError):
        click.echo(f"Error: {error.message}", err=True)
        if error.details:
            for key, val in error.details.items():
                click.echo(f"  {key}: {val}", err=True)
        return error.exit_code
    elif isinstance(error, KeyboardInterrupt):
        click.echo("\nInterrupted by user", err=True)
        return EXIT_INTERRUPTED
    elif isinstance(error, SystemExit):
        return error.code if isinstance(error.code, int) else EXIT_GENERAL_ERROR
    else:
        click.echo(f"Unexpected error: {error}", err=True)
        return EXIT_GENERAL_ERROR


def exit_with_error(error: Exception) -> None:
    """Print error and exit with appropriate code."""
    code = handle_error(error)
    sys.exit(code)
