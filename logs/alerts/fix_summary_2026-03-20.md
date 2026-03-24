# Alert Fix Summary - 2026-03-20

## Issue
- **Alert Count**: 35 alerts
- **Error**: "Test assertion failed"
- **Time Range**: 2026-03-20 01:28 - 02:21
- **Affected Module**: `examples/alpha_research/backup_manager.py`

## Root Cause
The test file `test_backup_manager.py` was importing `BackupType` and `BackupStatus` from `backup_manager.py`, but these enums were not implemented in the module. This caused import errors when running the tests.

## Fixes Applied

### 1. Added Missing Enums
```python
class BackupType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class BackupStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
```

### 2. Updated BackupInfo Dataclass
- Changed `backup_type: str` to `backup_type: BackupType`
- Changed `status: str` to `status: BackupStatus`
- Added `backup_id`, `is_incremental`, `base_backup_id`, `description` fields

### 3. Fixed File Counting Logic
- Changed from counting all items (including directories) to counting only files
- Before: `sum(1 for _ in item.rglob('*'))`
- After: `sum(1 for f in item.rglob('*') if f.is_file())`

### 4. Added backup_root Alias
- Added `self.backup_root = self.backup_dir` for test compatibility

### 5. Improved Timestamp Format
- Changed from `'%Y%m%d_%H%M%S'` to `'%Y%m%d_%H%M%S_%f')[:-3]` to include milliseconds
- Prevents backup directory collisions when creating multiple backups quickly

## Verification
All 10 tests in `test_backup_manager.py` now pass:
- ✅ 创建每日备份
- ✅ 创建增量备份
- ✅ 创建每周备份
- ✅ 创建每月备份
- ✅ 验证备份
- ✅ 恢复备份
- ✅ 列出备份
- ✅ 备份统计
- ✅ 清理过期备份
- ✅ 定时备份调度

**Result**: 10/10 passed (100%)

## Status
- **Alerts**: All 35 alerts marked as resolved
- **Fixed At**: 2026-03-22 14:57:30
- **Fixed By**: Subagent (vnpy-alert-delta)
