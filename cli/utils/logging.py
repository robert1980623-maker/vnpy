"""Unified structured logging for VNPY CLI.

Provides JSON and text formatters with trace_id propagation.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# Context variable for trace_id (propagated across async/task boundaries)
_trace_id_var: ContextVar[str | None] = ContextVar('trace_id', default=None)

TRACEPARENT_ENV = 'TRACEPARENT'


def new_trace_id() -> str:
    """Generate a new 16-char hex trace id."""
    return uuid.uuid4().hex[:16]


def get_current_trace_id() -> str:
    """Return current trace_id from context, env var, or create a new one."""
    tid = _trace_id_var.get()
    if tid:
        return tid
    tid = os.environ.get(TRACEPARENT_ENV)
    if tid:
        _trace_id_var.set(tid)
        return tid
    tid = new_trace_id()
    _trace_id_var.set(tid)
    return tid


def set_trace_id(tid: str) -> None:
    """Set trace_id for current context and propagate via env var."""
    _trace_id_var.set(tid)
    os.environ[TRACEPARENT_ENV] = tid


class JSONFormatter(logging.Formatter):
    """Emit JSON lines with standard fields."""

    def __init__(self, *, include_extras: bool = True):
        super().__init__()
        self.include_extras = include_extras

    def format(self, record: logging.LogRecord) -> str:
        trace_id = _trace_id_var.get() or os.environ.get(TRACEPARENT_ENV) or '-'
        payload: dict[str, Any] = {
            'timestamp': self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'trace_id': trace_id,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        # Merge structured extras (avoid clobbering standard keys)
        if self.include_extras:
            for key in ('task', 'phase', 'duration_ms', 'source', 'end',
                        'max', 'force', 'workers', 'command'):
                val = getattr(record, key, None)
                if val is not None:
                    payload[key] = val
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter with trace_id."""

    FORMAT = '%(asctime)s %(levelname)-7s [%(trace_id)s] %(name)s: %(message)s'

    def __init__(self):
        super().__init__(self.FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, 'trace_id'):
            record.trace_id = _trace_id_var.get() or os.environ.get(
                TRACEPARENT_ENV, '-') or '-'
        return super().format(record)


def setup_logging(
    *,
    level: str = 'INFO',
    fmt: str = 'text',
    log_dir: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Configure root logger for CLI.

    Args:
        level: Log level name (DEBUG/INFO/WARNING/ERROR).
        fmt: 'json' or 'text'.
        log_dir: If provided, also log to file in that directory.
        trace_id: Override auto-generated trace_id.
    """
    if trace_id:
        set_trace_id(trace_id)
    else:
        # Ensure a trace_id exists for this process
        get_current_trace_id()

    root = logging.getLogger()
    # Clear existing handlers to avoid duplicates
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    console_handler = logging.StreamHandler(sys.stderr)
    if fmt == 'json':
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter())
    root.addHandler(console_handler)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(
            log_dir, f'vnpy-{time.strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        # File always uses JSON for machine-parseability
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for noisy in ('urllib3', 'requests', 'akshare', 'tushare'):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger (just a wrapper for convenience)."""
    return logging.getLogger(name)
