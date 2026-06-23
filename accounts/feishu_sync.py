"""
飞书输出同步服务

Phase 2: FeishuSyncService
- 只订阅事件，不参与交易读路径
- 同步失败仅记录日志，不影响交易
- 支持手动触发全量同步
"""
import logging
from typing import Optional

from accounts.event_bus import EventBus, EventType, AccountEvent
from accounts.account_service import AccountService

logger = logging.getLogger(__name__)


class FeishuSyncService:
    """飞书输出同步服务

    设计原则:
    1. 只订阅事件，不参与交易读路径
    2. 同步失败仅记录日志，不影响交易
    3. 支持手动触发全量同步
    """

    def __init__(self, account_service: AccountService, event_bus: EventBus):
        self.service = account_service
        self.bus = event_bus
        self._last_sync_error: Optional[str] = None

        # 订阅事件
        self.bus.subscribe(EventType.TRADE_EXECUTED, self._on_trade)
        self.bus.subscribe(EventType.SNAPSHOT_CREATED, self._on_snapshot)

    def _on_trade(self, event: AccountEvent):
        """交易事件 → 同步到飞书"""
        try:
            self._sync_to_feishu()
            self._last_sync_error = None
        except Exception as e:
            self._last_sync_error = str(e)
            logger.error(f"飞书同步失败 (trade): {e}")

    def _on_snapshot(self, event: AccountEvent):
        """快照事件 → 同步到飞书"""
        try:
            self._sync_to_feishu()
            self._last_sync_error = None
        except Exception as e:
            self._last_sync_error = str(e)
            logger.error(f"飞书同步失败 (snapshot): {e}")

    def _sync_to_feishu(self):
        """执行飞书同步

        1. 读取当前 balance + positions
        2. 调用飞书 API 更新多维表格
        3. 失败抛出异常，由调用方处理
        """
        balance = self.service.get_balance()
        positions = self.service.get_positions()

        # TODO: 调用飞书 API
        # 这部分逻辑从 virtual_account.py 的 sync_to_feishu() 迁移
        logger.info(
            f"飞书同步: cash={balance.cash:.2f}, "
            f"total_assets={balance.total_assets:.2f}, "
            f"positions={len(positions)}"
        )

    def sync_now(self) -> bool:
        """手动触发同步

        Returns:
            True 如果同步成功，False 如果失败
        """
        try:
            self._sync_to_feishu()
            self._last_sync_error = None
            return True
        except Exception as e:
            self._last_sync_error = str(e)
            logger.error(f"手动同步失败: {e}")
            return False

    @property
    def last_sync_error(self) -> Optional[str]:
        """返回最后一次同步的错误信息，成功时为 None"""
        return self._last_sync_error
