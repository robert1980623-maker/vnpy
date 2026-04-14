# fix_scheduler - VNPY 修复计划调度系统
#
# 功能：
#   - 读取 fix_plan.md 中的任务和优先级
#   - 按 P0/P1/P2 顺序调度任务
#   - 通过 sessions_spawn 委派给对应 Agent
#   - 更新飞书多维表格状态
#   - 失败通知到飞书群
#
# 调度规则：
#   - 后端任务 → Delta
#   - 策略任务 → Charlie
#   - 量化任务 → Golf
#   - QA 任务 → Golf
#
# 优先级规则：
#   - P0: 立即派遣，每周检查，最多重试 5 次
#   - P1: P0 全部完成后开始
#   - P2: P1 全部完成后开始

from .task_dispatcher import FixScheduler

__all__ = ["FixScheduler"]
