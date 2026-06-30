# Manager Watchdog 实现报告

**文档版本**: 1.0.0  
**创建日期**: 2026-07-01  
**状态**: ✅ 已完成

---

## 📋 概述

实现了一个独立于 Manager 的 Watchdog 监控进程，用于自动检测 Manager 崩溃并执行重启，避免 Issue 堆积。

## 🎯 目标

- **核心功能**: 心跳超时自动重启 Manager
- **独立性**: Watchdog 不依赖 Manager，可独立运行
- **安全性**: 支持 dry-run 模式，可预览不执行
- **状态保护**: 重启前保存 active_tasks 状态
- **可验证性**: 重启后验证 Manager 恢复正常

---

## 📁 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 核心脚本 | `examples/alpha_research/manager_watchdog.py` | Watchdog 主程序 |
| 单元测试 | `examples/alpha_research/tests/unit/test_manager_watchdog.py` | 22 个测试用例 |

---

## 🔧 实现细节

### 1. 心跳检测机制

**心跳文件**: `state/manager.heartbeat`

```json
{
  "timestamp": 1719801600.123,
  "pid": 12345,
  "status": "running"
}
```

**超时阈值**: 90 秒（与 `QuantManager.HEARTBEAT_TIMEOUT` 保持一致）

**检测逻辑**:
```
当前时间 - heartbeat.timestamp > HEARTBEAT_TIMEOUT → 判定为过期
```

### 2. Watchdog 状态机

```
                    ┌──────────────┐
                    │   IDLE       │
                    │  等待检测    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌─────│ 检测心跳文件 │─────┐
              │     └──────────────┘     │
              │                          │
      ┌───────▼───────┐          ┌───────▼───────┐
      │ 心跳正常       │          │ 心跳过期/文件 ││ 缺失
      │ _heartbeat_age │          │ 不存在       │
      │   ≤ 90s       │          └───────┬───────┘
      └───────────────┘                  │
                              ┌──────────▼──────────┐
                              │ Manager 进程是否运行 │
                              └──────────┬──────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         │                               │
                 ┌───────▼───────┐               ┌───────▼───────┐
                 │ 进程运行中     │               │ 进程未运行     │
                 │ → 疑似挂起     │               │ → 异常退出     │
                 └───────┬───────┘               └───────┬───────┘
                         │                               │
                         └───────────┬───────────────────┘
                                     │
                             ┌───────▼───────┐
                             │  执行重启流程  │
                             │ (除非已达上限) │
                             └───────────────┘
```

### 3. 重启流程

```
┌─────────────────────────────────────────────┐
│              重启流程 (7 步)                 │
├─────────────────────────────────────────────┤
│ 1. 保存 active_tasks 快照到内存              │
│ 2. 发送 SIGTERM 到 Manager 进程             │
│ 3. 等待 2 秒 进程退出                       │
│ 4. 如未退出，发送 SIGKILL 强制终止           │
│ 5. 启动新 Manager 进程                      │
│ 6. 等待心跳文件出现且正常更新                │
│ 7. 验证 Manager 恢复正常                    │
└─────────────────────────────────────────────┘
```

### 4. 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--timeout` / `-t` | 90 | 心跳超时阈值（秒） |
| `--interval` / `-i` | 10 | 检测间隔（秒） |
| `--max-restarts` / `-m` | 3 | 最大重启次数 |
| `--base-dir` / `-d` | `./issues` | issues 目录 |
| `--dry-run` / `-n` | False | 干跑模式 |
| `--once` | False | 单次检测后退出 |

### 5. 日志输出

**日志文件**: `logs/watchdog.log`

```
2026-07-01 10:00:00 [INFO] ============================================================
2026-07-01 10:00:00 [INFO] Manager Watchdog 启动
2026-07-01 10:00:00 [INFO] 心跳文件: ./issues/state/manager.heartbeat
2026-07-01 10:00:00 [INFO] 超时阈值: 90s
2026-07-01 10:00:00 [INFO] ============================================================
2026-07-01 10:05:30 [WARNING] ⚠️ Manager 心跳超时: 95.3s > 90s
2026-07-01 10:05:30 [INFO] 开始执行 Manager 重启
2026-07-01 10:05:30 [INFO] 重启原因: 心跳超时 (年龄: 95.3s > 90s)
2026-07-01 10:05:32 [INFO] ✅ Manager 重启完成 (第 1 次)
```

---

## 🧪 测试覆盖

### 测试用例 (22 个)

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| `TestWatchdogConfig` | 3 | 配置初始化、目录创建 |
| `TestHeartbeatOperations` | 8 | 加载、年龄计算、过期判定 |
| `TestManagerProcessDetection` | 3 | 进程检测、异常处理 |
| `TestStateSnapshot` | 3 | 状态快照保存/恢复 |
| `TestRestartFlow` | 3 | 启动/停止流程 |
| `TestCheckAndRestart` | 3 | 检测与重启逻辑 |
| `TestSignalHandling` | 1 | 信号处理器 |
| `TestMainEntry` | 2 | 命令行参数解析 |

---

## 🚀 使用方式

### 1. 持续运行模式（守护进程）

```bash
# 基本运行
python3 examples/alpha_research/manager_watchdog.py

# 干跑模式（只检测不重启）
python3 examples/alpha_research/manager_watchdog.py --dry-run

# 自定义配置
python3 examples/alpha_research/manager_watchdog.py \
  --timeout 60 \
  --interval 5 \
  --max-restarts 5
```

### 2. 单次检测模式（cron 调度）

```bash
# 每分钟检测一次
* * * * * python3 examples/alpha_research/manager_watchdog.py --once

# 每 5 分钟检测一次
*/5 * * * * python3 examples/alpha_research/manager_watchdog.py --once --timeout 60
```

### 3. Docker/Systemd 集成

```ini
# systemd 服务示例 (manager-watchdog.service)
[Unit]
Description=Manager Watchdog Service
After=network.target

[Service]
Type=simple
User=vnpy
WorkingDirectory=/Users/rowang/projects/vnpy
ExecStart=/usr/bin/python3 examples/alpha_research/manager_watchdog.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 🔗 与 Manager 的交互

### Manager 心跳机制（已有）

```python
# manager_interface.py
class QuantManager:
    HEARTBEAT_INTERVAL = 30   # 心跳间隔
    HEARTBEAT_TIMEOUT = 90    # 超时阈值
    
    def _heartbeat_loop(self):
        """后台线程每 30s 更新心跳"""
        while not self._heartbeat_stop.is_set():
            self._write_heartbeat()
            self._heartbeat_stop.wait(self.HEARTBEAT_INTERVAL)
```

### Watchdog 检测机制（新增）

```python
# manager_watchdog.py
class ManagerWatchdog:
    def _check_and_restart(self):
        heartbeat = self._load_heartbeat()
        if self._is_heartbeat_stale(heartbeat):
            self._restart_manager()
```

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                         系统架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐         ┌─────────────────────────┐  │
│   │    Watchdog     │  读取   │     Manager             │  │
│   │   (独立进程)     │────────▶│   (quant_manager)       │  │
│   │                 │         │                         │  │
│   │ - 检测心跳文件   │         │ - 每 30s 写入心跳        │  │
│   │ - 超时重启      │         │ - 管理 active_tasks     │  │
│   │ - 验证恢复      │         │ - 处理 Issue            │  │
│   └────────┬────────┘         └───────────┬─────────────┘  │
│            │                               │                 │
│            │         共享文件              │                 │
│            └───────────────────────────────┘                 │
│                         │                                   │
│            ┌────────────▼────────────┐                        │
│            │   issues/state/        │                        │
│            │   - manager.heartbeat   │                        │
│            │   - manager_state.json  │                        │
│            └─────────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ 注意事项

### 1. 重启限制

- 默认最多连续重启 3 次
- 每次重启间隔至少 30 秒（冷却期）
- 超过限制后记录日志但不继续尝试

### 2. 状态恢复

- Manager 重启后会自动从 `state/manager_state.json` 恢复 `active_tasks`
- Watchdog 保存快照仅用于日志记录，不干预恢复过程

### 3. 进程检测

- 使用 `pgrep -f manager_interface.py` 检测进程
- 如果进程名不匹配，可能导致检测失败

### 4. 启动路径

- Watchdog 会自动查找 `manager_interface.py` 的位置
- 优先查找同目录，否则查找父目录

---

## 📊 性能指标

| 指标 | 预期值 | 说明 |
|------|--------|------|
| 检测延迟 | < 1ms | 读取心跳文件 |
| 重启后恢复时间 | < 5s | 从停止到心跳正常 |
| 内存占用 | < 10MB | Watchdog 进程 |
| CPU 占用 | < 1% | 检测间隔 10s 时 |

---

## 🔮 未来扩展

1. **多 Manager 支持**: 监控多个 Manager 实例
2. **告警集成**: 重启失败时发送通知
3. **指标暴露**: Prometheus 格式的监控指标
4. **热更新**: 支持重新加载配置而不重启

---

## ✅ 验证清单

- [x] 心跳文件检测正确
- [x] 超时判定准确
- [x] 进程启动/停止正常
- [x] Dry-run 模式工作
- [x] 命令行参数解析正确
- [x] 信号处理正常
- [x] 日志输出完整
- [x] 单元测试覆盖核心功能

---

## 📝 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-01 | 1.0.0 | 初始实现 |

---

**维护者**: Atlas (Chief Architect AI)
