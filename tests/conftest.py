#!/usr/bin/env python3
"""Root conftest.py - shared pytest configuration for all test directories.

Prevents import side-effects from third-party SDKs (e.g. tushare writing
~/tk.csv on import) so tests can be collected regardless of whether
environment variables like TUSHARE_TOKEN are set.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock


# ─────────────────────────────────────────────────────────────
# 1. Prevent tushare.set_token() side-effect on import.
#    When TUSHARE_TOKEN is set, tushare's module-level code
#    calls ts.set_token() which writes to ~/tk.csv.  In sandboxed
#    environments this raises PermissionError and breaks pytest
#    collection for any test that transitively imports tushare.
# ─────────────────────────────────────────────────────────────
_real_tushare = None
try:
    import tushare as _real_tushare  # noqa: F401
except ImportError:
    pass

if _real_tushare is not None:
    # Neutralize set_token so it doesn't write ~/tk.csv
    _real_tushare.set_token = MagicMock()
else:
    # If tushare isn't installed, inject a fake so imports don't fail
    _fake_tushare = MagicMock()
    _fake_tushare.set_token = MagicMock()
    _fake_tushare.get_token = MagicMock(return_value="fake-token")
    sys.modules.setdefault("tushare", _fake_tushare)


# ─────────────────────────────────────────────────────────────
# 2. Inject fake openclaw_lark module (same reason as above).
#    Some legacy scripts import openclaw_lark and call sys.exit(1)
#    when it's not available, which kills the test runner.
# ─────────────────────────────────────────────────────────────
_fake_feishu = MagicMock()
_fake_feishu.feishu_bitable_app_table_record = MagicMock()
sys.modules.setdefault("openclaw_lark", _fake_feishu)


# ─────────────────────────────────────────────────────────────
# 3. Ensure examples/alpha_research is importable for tests that
#    need legacy modules (virtual_account, data_downloader, etc.)
# ─────────────────────────────────────────────────────────────
_alpha_research_dir = Path(__file__).resolve().parent.parent / 'examples' / 'alpha_research'
if str(_alpha_research_dir) not in sys.path:
    sys.path.insert(0, str(_alpha_research_dir))
