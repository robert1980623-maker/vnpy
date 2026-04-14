#!/usr/bin/env python3
"""
conftest.py - tests/unit/

pytest configuration for all unit tests in this directory.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────
# 1. Inject fake openclaw_lark module BEFORE any test file
#    imports sync_feishu_cache (which imports openclaw_lark at
#    module level and calls sys.exit(1) on ImportError).
# ─────────────────────────────────────────────────────────────
_fake_feishu_module = MagicMock()
_fake_feishu_module.feishu_bitable_app_table_record = MagicMock()
sys.modules["openclaw_lark"] = _fake_feishu_module


# ─────────────────────────────────────────────────────────────
# 2. Prevent sys.exit() in sync_feishu_cache from killing tests.
#    The module calls sys.exit(1) when openclaw_lark import fails;
#    after our inject above it won't, but we also suppress any
#    residual SystemExit at test loader time.
# ─────────────────────────────────────────────────────────────
_original_exit = sys.exit


def _safe_exit(code=0):
    """Swallow sys.exit during test collection / module loading."""
    if code == 1:
        # Only suppress the "FEISHU_AVAILABLE=False" exit(1)
        # Real exits (code != 1) should still propagate
        return
    _original_exit(code)


sys.exit = _safe_exit
