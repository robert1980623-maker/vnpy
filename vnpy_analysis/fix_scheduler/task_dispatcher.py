#!/usr/bin/env python3
"""
VNPY 修复计划调度系统 - task_dispatcher.py

功能：
  - 读取 fix_plan.md 解析 15 个任务和优先级
  - 按 P0/P1/P2 规则顺序调度
  - 通过 sessions_spawn 委派给对应 Agent
  - 更新飞书多维表格状态
  - 失败发送飞书通知

Agent 分配：
  - 后端任务 → Delta
  - 策略任务 → Charlie
  - 量化任务 → Golf
  - QA 任务 → Golf
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
from vnpy_config import get_scheduler_config, get_config

# ============================================================
# 基础配置
# ============================================================

BASE_DIR = Path("/Users/rowang/projects/vnpy/vnpy_analysis")
FIX_PLAN_PATH = BASE_DIR / "fix_plan.md"
STATE_FILE = BASE_DIR / ".fix_scheduler_state.json"

# 从统一配置读取
_scheduler_cfg = get_scheduler_config()
FEISHU_GROUP_ID = _scheduler_cfg.get("feishu_group_id", "oc_8a2da4516d54e779f8a30d15273347b8")

# 飞书多维表格 App Token（需在部署时配置）
BITABLE_APP_TOKEN = "Sxxxxxxxxxxxxxxxx"  # TODO: 替换为实际 token
BITABLE_TABLE_ID = "tblxxxxxxxxxxxxxxxx"  # TODO: 替换为实际 table_id

# 重试配置（从统一配置读取）
MAX_RETRIES = _scheduler_cfg.get("max_retries", 5)
RETRY_INTERVAL_SECONDS = _scheduler_cfg.get("retry_interval_seconds", 60)  # 1 分钟

# 调度时间
SCHEDULER_START_DATE = datetime(2026, 4, 13, tzinfo=timezone(timedelta(hours=8)))  # 2026-04-13 14:45 CST

# ============================================================
# 任务状态枚举
# ============================================================

class TaskStatus(Enum):
    PENDING = "pending"           # 待派遣
    DISPATCHED = "dispatched"     # 已派遣
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    RETRYING = "retrying"         # 重试中
    BLOCKED = "blocked"           # 被阻塞（P1 等待 P0，P2 等待 P1）


# ============================================================
# 任务数据结构
# ============================================================

@dataclass
class Task:
    id: str              # 例如 "P0-1", "P1-3", "P2-5"
    title: str           # 任务标题
    priority: str       # "P0" / "P1" / "P2"
    severity: str        # "致命" / "高危" / "中"
    files: list[str]     # 涉及文件列表
    estimated_hours: float  # 预估工时（小时）
    team: str            # 建议团队
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    assigned_session: Optional[str] = None  # alpha/bravo/charlie/delta/echo/foxtrot/golf
    created_at: Optional[str] = None
    dispatched_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def agent_session(self) -> str:
        """根据任务类型返回对应的 sessionKey"""
        if self.team in ("后端工程组", "数据工程组"):
            return "delta"
        elif self.team in ("策略研究组",):
            return "charlie"
        elif self.team in ("量化工程组", "QA 组"):
            return "golf"
        else:
            return "delta"  # 默认走 Delta

    def model(self) -> str:
        """返回模型名称"""
        return "minimax-cn/MiniMax-M2.7"


# ============================================================
# fix_plan.md 解析器
# ============================================================

class FixPlanParser:
    """解析 fix_plan.md，提取所有任务"""

    # 团队映射表（优先级高于资源分配表）
    TEAM_OVERRIDES = {
        "P0-1": "后端工程组",
        "P0-2": "后端工程组",
        "P0-3": "策略研究组",
        "P0-4": "策略研究组",
        "P1-1": "后端工程组",
        "P1-2": "后端工程组",
        "P1-3": "后端工程组",
        "P1-4": "量化工程组",
        "P1-5": "后端工程组",
        "P1-6": "量化工程组",
        "P2-1": "后端工程组",
        "P2-2": "量化工程组",
        "P2-3": "QA 组",
        "P2-4": "后端工程组",
        "P2-5": "策略研究组",
    }

    # 工时映射表（小时）
    HOURS_MAP = {
        "P0-1": 2.0,
        "P0-2": 4.0,
        "P0-3": 1.0,
        "P0-4": 4.0,
        "P1-1": 3.0,
        "P1-2": 0.5,
        "P1-3": 2.0,
        "P1-4": 2.0,
        "P1-5": 2.0,
        "P1-6": 1.0,
        "P2-1": 8.0,
        "P2-2": 16.0,
        "P2-3": 8.0,
        "P2-4": 2.0,
        "P2-5": 8.0,
    }

    @staticmethod
    def parse(path: Path) -> list[Task]:
        content = path.read_text(encoding="utf-8")
        tasks: list[Task] = []

        # 从资源分配表构建 team 映射
        team_map = FixPlanParser._build_task_team_map(content)

        # 解析 P0 任务
        tasks.extend(FixPlanParser._parse_section(content, "🔴 P0", "P0", team_map))
        # 解析 P1 任务
        tasks.extend(FixPlanParser._parse_section(content, "🟡 P1", "P1", team_map))
        # 解析 P2 任务
        tasks.extend(FixPlanParser._parse_section(content, "🟢 P2", "P2", team_map))

        return tasks

    @staticmethod
    def _build_task_team_map(content: str) -> dict[str, str]:
        """从资源分配建议表构建 task_id → team 映射"""
        team_map: dict[str, str] = {}

        idx = content.find("资源分配建议")
        if idx == -1:
            return team_map

        table_text = content[idx:idx+1000]

        # 解析表格行：| **后端工程组** | 1-2 人 | P0-1, P0-2 | P1-1, P1-2, P1-3, P1-5 | P2-1, P2-4 | ~3d |
        # 每一行格式：| **团队名** | 人数 | P0任务 | P1任务 | P2任务 | 总工时 |
        row_pattern = re.compile(
            r"\|\s*\*\*(.+?)\*\*\s*\|[^\n|]*\|[^\n|]*\|[^\n|]*\|"
        )
        for m in row_pattern.finditer(table_text):
            team = m.group(1).strip()
            # 找到这一行的任务列（P0, P1, P2 三列）
            row_start = m.start()
            row_end = content.find("\n", row_start + 1)
            row_text = content[row_start:row_end]

            # 分割每列获取任务列表
            cols = [c.strip() for c in row_text.split("|")[2:8]]
            # cols[0]=人数, cols[1]=P0任务, cols[2]=P1任务, cols[3]=P2任务, cols[4]=总工时

            for col_idx in [1, 2, 3]:  # P0, P1, P2 列
                col = cols[col_idx] if col_idx < len(cols) else ""
                for t in col.replace("—", "").split(","):
                    t = t.strip()
                    if t and re.match(r"P\d-\d+", t):
                        team_map[t] = team

        return team_map

    @staticmethod
    def _parse_section(content: str, section_header: str, priority: str, team_map: dict[str, str]) -> list[Task]:
        tasks: list[Task] = []

        # 找到该优先级 section
        section_pattern = re.escape(section_header) + r".*?(?=\n## |\Z)"
        section_match = re.search(section_pattern, content, re.DOTALL)
        if not section_match:
            return tasks

        section_text = section_match.group()

        # 匹配任务块：### P0-1: 标题
        # 严重度行有两种格式：
        #   格式 A: **严重度:** 🟢 中 | **文件:** `xxx` (有文件字段)
        #   格式 B: **严重度:** 🟢 中\n\n**测试覆盖:** (无文件字段)
        task_pattern = re.compile(
            rf"### ({priority}-\d+):\s*(.+?)\n"
            r"\*\*严重度:\*\*\s*([^\n|]+)",
            re.DOTALL
        )

        for match in task_pattern.finditer(section_text):
            task_id = match.group(1)
            title = match.group(2).strip()
            severity = match.group(3).strip()

            # 提取涉及文件
            files = FixPlanParser._extract_files(section_text, match.end())

            # 使用 TEAM_OVERRIDES > team_map > 资源表 的优先级
            team = (
                FixPlanParser.TEAM_OVERRIDES.get(task_id)
                or team_map.get(task_id, "")
            )

            # 工时
            hours = FixPlanParser.HOURS_MAP.get(task_id, 0.0)

            tasks.append(Task(
                id=task_id,
                title=title,
                priority=priority,
                severity=severity,
                files=files,
                estimated_hours=hours,
                team=team,
                created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
            ))

        return tasks

    @staticmethod
    def _extract_files(text: str, start: int) -> list[str]:
        """提取涉及文件列表"""
        files = []
        pattern = re.escape("**文件:**") + r"\s*([^\n]+)"
        match = re.search(pattern, text[start:start+300])
        if match:
            file_str = match.group(1).strip()
            files = [f.strip() for f in file_str.split(",")]
        return files


# ============================================================
# 状态管理
# ============================================================

class SchedulerState:
    """调度状态持久化"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.tasks: list[Task] = []
        self.last_check: Optional[str] = None
        self.week_count: int = 1

    def load(self) -> bool:
        if not self.state_file.exists():
            return False
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.tasks = [Task(**t) for t in data.get("tasks", [])]
            self.last_check = data.get("last_check")
            self.week_count = data.get("week_count", 1)
            # 反序列化 status
            for task in self.tasks:
                if isinstance(task.status, str):
                    task.status = TaskStatus(task.status)
            return True
        except Exception:
            return False

    def save(self):
        def _task_to_dict(t: Task) -> dict:
            d = asdict(t)
            d["status"] = t.status.value  # enum → string
            return d

        data = {
            "tasks": [_task_to_dict(t) for t in self.tasks],
            "last_check": self.last_check,
            "week_count": self.week_count,
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_tasks_by_priority(self, priority: str) -> list[Task]:
        return [t for t in self.tasks if t.priority == priority]

    def all_completed(self, priority: str) -> bool:
        tasks = self.get_tasks_by_priority(priority)
        return all(t.status == TaskStatus.COMPLETED for t in tasks)

    def any_blocked_by_higher_priority(self, task: Task) -> bool:
        """检查是否有更高优先级的任务未完成"""
        if task.priority == "P0":
            return False
        elif task.priority == "P1":
            return not self.all_completed("P0")
        elif task.priority == "P2":
            return not self.all_completed("P1")
        return False


# ============================================================
# 飞书通知
# ============================================================

class FeishuNotifier:
    """发送飞书通知"""

    @staticmethod
    def send_message(text: str) -> bool:
        """发送文本消息到飞书群"""
        try:
            cmd = [
                "openclaw", "message", "send",
                "--channel", "feishu",
                "--to", FEISHU_GROUP_ID,
                "--text", text,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def notify_task_failed(task: Task, error: str) -> None:
        """通知任务失败"""
        message = (
            f"🚨 VNPY 修复任务失败\n\n"
            f"**任务:** {task.id} - {task.title}\n"
            f"**优先级:** {task.priority}\n"
            f"**重试次数:** {task.retry_count}/{MAX_RETRIES}\n"
            f"**错误:** {error[:200]}\n\n"
            f"请及时处理！"
        )
        FeishuNotifier.send_message(message)

    @staticmethod
    def notify_task_completed(task: Task) -> None:
        """通知任务完成"""
        message = (
            f"✅ VNPY 修复任务完成\n\n"
            f"**任务:** {task.id} - {task.title}\n"
            f"**优先级:** {task.priority}\n"
            f"**预估工时:** {task.estimated_hours}h"
        )
        FeishuNotifier.send_message(message)

    @staticmethod
    def notify_all_p0_completed() -> None:
        """P0 全部完成通知"""
        message = (
            f"🎉 P0 阶段完成！\n\n"
            f"所有 P0 致命问题已修复，系统可信度恢复。\n"
            f"现在开始调度 P1 任务..."
        )
        FeishuNotifier.send_message(message)

    @staticmethod
    def notify_all_p1_completed() -> None:
        """P1 全部完成通知"""
        message = (
            f"🎉 P1 阶段完成！\n\n"
            f"所有 P1 高危问题已修复，系统稳定性提升。\n"
            f"现在开始调度 P2 任务..."
        )
        FeishuNotifier.send_message(message)


# ============================================================
# 飞书多维表格更新
# ============================================================

class BitableUpdater:
    """更新飞书多维表格状态"""

    # 字段名映射（需根据实际多维表格字段名调整）
    FIELD_STATUS = "状态"
    FIELD_RETRY_COUNT = "重试次数"
    FIELD_DISPATCHED_AT = "派遣时间"
    FIELD_COMPLETED_AT = "完成时间"
    FIELD_ERROR = "错误信息"

    @staticmethod
    def _get_tenant_access_token() -> str:
        """获取 tenant access token（需实现）"""
        # TODO: 通过飞书开放平台 API 获取 tenant_access_token
        return ""

    @staticmethod
    def update_task_status(record_id: str, fields: dict) -> bool:
        """
        更新多维表格记录
        fields 格式: {"状态": "已完成", "完成时间": 1744550400000}
        """
        try:
            import requests

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records/{record_id}"

            headers = {
                "Authorization": f"Bearer {BitableUpdater._get_tenant_access_token()}",
                "Content-Type": "application/json",
            }

            payload = {"fields": fields}
            resp = requests.patch(url, headers=headers, json=payload, timeout=15)
            return resp.status_code == 200

        except Exception:
            return False

    @staticmethod
    def find_record_id_by_task_id(task_id: str) -> Optional[str]:
        """根据任务 ID 查找多维表格记录 ID"""
        # TODO: 实现通过飞书 API 查询记录
        # 需要调用 feishu_bitable_app_table_record list 接口
        # filter: task_id = task_id
        return None

    @staticmethod
    def mark_completed(task: Task) -> None:
        """标记任务为已完成"""
        record_id = BitableUpdater.find_record_id_by_task_id(task.id)
        if not record_id:
            return

        completed_ts = int(datetime.now(timezone(timedelta(hours=8))).timestamp() * 1000)
        fields = {
            BitableUpdater.FIELD_STATUS: "已完成",
            BitableUpdater.FIELD_COMPLETED_AT: completed_ts,
        }
        BitableUpdater.update_task_status(record_id, fields)

    @staticmethod
    def mark_failed(task: Task) -> None:
        """标记任务为失败"""
        record_id = BitableUpdater.find_record_id_by_task_id(task.id)
        if not record_id:
            return

        fields = {
            BitableUpdater.FIELD_STATUS: "失败",
            BitableUpdater.FIELD_ERROR: task.error_message or "",
        }
        BitableUpdater.update_task_status(record_id, fields)


# ============================================================
# Agent 派遣器
# ============================================================

class AgentDispatcher:
    """通过 sessions_spawn 委派任务"""

    @staticmethod
    def dispatch(task: Task, state: SchedulerState) -> bool:
        """
        使用 openclaw sessions spawn 委派任务
        返回 True 表示派遣成功
        """
        session_key = task.assigned_session or task.agent_session()
        model = task.model()

        # 构建任务描述
        task_desc = f"""## VNPY 修复任务

**任务 ID:** {task.id}
**任务标题:** {task.title}
**优先级:** {task.priority}
**严重度:** {task.severity}
**涉及文件:** {', '.join(task.files)}
**预估工时:** {task.estimated_hours}h
**建议团队:** {task.team}

### 任务描述
请根据 fix_plan.md 中 {task.id} 的修复方案执行代码修复。

### 参考文件
- fix_plan.md: {FIX_PLAN_PATH}
- 涉及文件: {', '.join(task.files)}

### 要求
1. 按照 fix_plan.md 中的验收标准完成修复
2. 修复后更新多维表格状态
3. 如有问题，及时汇报
"""

        try:
            # 调用 sessions_spawn 委派任务
            result = subprocess.run(
                [
                    "openclaw", "sessions", "spawn",
                    "--session", session_key,
                    "--model", model,
                    "--task", task_desc,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                task.status = TaskStatus.DISPATCHED
                task.dispatched_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
                task.assigned_session = session_key
                state.save()
                return True
            else:
                task.error_message = result.stderr or "派遣失败"
                return False

        except Exception as e:
            task.error_message = str(e)
            return False


# ============================================================
# 主调度器
# ============================================================

class FixScheduler:
    """VNPY 修复计划调度器"""

    # P0 任务中哪些可以立即并行，哪些需要等策略组
    P0_IMMEDIATE = ["P0-1", "P0-2"]      # 可立即派遣
    P0_WAIT_STRATEGY = ["P0-3", "P0-4"]  # 需策略组，14:50 派遣

    def __init__(self):
        self.state = SchedulerState(STATE_FILE)
        self._loaded = False

    def initialize(self) -> None:
        """初始化：加载状态或解析任务"""
        if self.state.load():
            print(f"[FixScheduler] 从 {STATE_FILE} 加载状态，共 {len(self.state.tasks)} 个任务")
        else:
            print(f"[FixScheduler] 解析 {FIX_PLAN_PATH}")
            self.state.tasks = FixPlanParser.parse(FIX_PLAN_PATH)
            print(f"[FixScheduler] 解析到 {len(self.state.tasks)} 个任务")
            self.state.save()

        self._loaded = True

    def run(self) -> None:
        """运行一次调度"""
        if not self._loaded:
            self.initialize()

        now = datetime.now(timezone(timedelta(hours=8)))
        self.state.last_check = now.isoformat()

        print(f"\n{'='*60}")
        print(f"[{now.isoformat()}] FixScheduler 运行")
        print(f"{'='*60}")

        # 1. 检查 P0 任务（立即派遣 + 每周检查）
        self._dispatch_p0_tasks()

        # 2. 检查 P1 任务（P0 全部完成后开始）
        if self.state.all_completed("P0"):
            self._dispatch_p1_tasks()
            FeishuNotifier.notify_all_p0_completed()

        # 3. 检查 P2 任务（P1 全部完成后开始）
        if self.state.all_completed("P1"):
            self._dispatch_p2_tasks()
            FeishuNotifier.notify_all_p1_completed()

        # 4. 处理失败重试
        self._handle_retries()

        self.state.save()
        self._print_status()

    def _dispatch_p0_tasks(self) -> None:
        """调度 P0 任务"""
        p0_tasks = self.state.get_tasks_by_priority("P0")

        # 立即派遣 P0-1 和 P0-2
        for task in p0_tasks:
            if task.id in self.P0_IMMEDIATE and task.status == TaskStatus.PENDING:
                if AgentDispatcher.dispatch(task, self.state):
                    print(f"[调度] {task.id} 已派遣到 {task.assigned_session}")
                else:
                    print(f"[错误] {task.id} 派遣失败: {task.error_message}")

        # 14:50 派遣 P0-3 和 P0-4（需要策略组）
        now = datetime.now(timezone(timedelta(hours=8)))
        strategy_dispatch_time = datetime(2026, 4, 13, 14, 50, tzinfo=timezone(timedelta(hours=8)))
        if now >= strategy_dispatch_time:
            for task in p0_tasks:
                if task.id in self.P0_WAIT_STRATEGY and task.status == TaskStatus.PENDING:
                    if AgentDispatcher.dispatch(task, self.state):
                        print(f"[调度] {task.id} 已派遣到 {task.assigned_session}")
                    else:
                        print(f"[错误] {task.id} 派遣失败: {task.error_message}")

    def _dispatch_p1_tasks(self) -> None:
        """调度 P1 任务"""
        p1_tasks = self.state.get_tasks_by_priority("P1")
        for task in p1_tasks:
            if task.status == TaskStatus.PENDING:
                if AgentDispatcher.dispatch(task, self.state):
                    print(f"[调度] {task.id} 已派遣到 {task.assigned_session}")
                else:
                    print(f"[错误] {task.id} 派遣失败: {task.error_message}")

    def _dispatch_p2_tasks(self) -> None:
        """调度 P2 任务"""
        p2_tasks = self.state.get_tasks_by_priority("P2")
        for task in p2_tasks:
            if task.status == TaskStatus.PENDING:
                if AgentDispatcher.dispatch(task, self.state):
                    print(f"[调度] {task.id} 已派遣到 {task.assigned_session}")
                else:
                    print(f"[错误] {task.id} 派遣失败: {task.error_message}")

    def _handle_retries(self) -> None:
        """处理失败任务的重试"""
        for task in self.state.tasks:
            if task.status == TaskStatus.FAILED:
                if task.retry_count < MAX_RETRIES:
                    task.status = TaskStatus.RETRYING
                    task.retry_count += 1
                    if AgentDispatcher.dispatch(task, self.state):
                        print(f"[重试] {task.id} 第 {task.retry_count} 次重试派遣成功")
                    else:
                        print(f"[重试] {task.id} 第 {task.retry_count} 次重试失败")
                        FeishuNotifier.notify_task_failed(task, task.error_message or "重试派遣失败")
                else:
                    print(f"[放弃] {task.id} 已达最大重试次数 ({MAX_RETRIES})")
                    FeishuNotifier.notify_task_failed(task, f"已达最大重试次数 {MAX_RETRIES}")

    def _print_status(self) -> None:
        """打印当前状态"""
        print(f"\n--- 任务状态 ---")
        for task in self.state.tasks:
            print(f"  {task.id:6s} | {task.status.value:12s} | 重试:{task.retry_count}/{MAX_RETRIES} | {task.title[:30]}")

    def mark_completed(self, task_id: str) -> None:
        """标记任务完成（由 Agent 调用）"""
        task = self.state.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
            self.state.save()
            BitableUpdater.mark_completed(task)
            FeishuNotifier.notify_task_completed(task)
            print(f"[完成] {task_id}")

    def mark_failed(self, task_id: str, error: str) -> None:
        """标记任务失败（由 Agent 调用）"""
        task = self.state.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error
            self.state.save()
            print(f"[失败] {task_id}: {error[:100]}")


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="VNPY 修复计划调度器")
    parser.add_argument("--init", action="store_true", help="初始化（重新解析 fix_plan.md）")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--dispatch", type=str, help="派遣指定任务 ID")
    parser.add_argument("--complete", type=str, help="标记任务完成")
    parser.add_argument("--fail", type=str, help="标记任务失败")
    args = parser.parse_args()

    scheduler = FixScheduler()

    if args.init:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        scheduler.initialize()
        print(f"已重新初始化，共 {len(scheduler.state.tasks)} 个任务")

    elif args.status:
        scheduler.initialize()
        scheduler._print_status()

    elif args.dispatch:
        scheduler.initialize()
        task = scheduler.state.get_task(args.dispatch)
        if task:
            if AgentDispatcher.dispatch(task, scheduler.state):
                print(f"已派遣 {args.dispatch} 到 {task.assigned_session}")
            else:
                print(f"派遣失败: {task.error_message}")
        else:
            print(f"未找到任务 {args.dispatch}")

    elif args.complete:
        scheduler.initialize()
        scheduler.mark_completed(args.complete)

    elif args.fail:
        scheduler.initialize()
        scheduler.mark_failed(args.fail, "任务执行失败")

    else:
        # 默认运行
        scheduler.run()


if __name__ == "__main__":
    main()
