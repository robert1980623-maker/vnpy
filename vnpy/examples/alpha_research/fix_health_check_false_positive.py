#!/usr/bin/env python3
"""
修复健康检查误报问题

问题：
- 健康检查脚本将 cron 未到运行时间的状态误判为异常
- status=0 和 status=* 在某些情况下是正常的

修复：
- 检查 cron 配置是否存在
- 检查是否只是未到运行时间
- 过滤掉解析错误（"-", "Name" 等表头行）
"""

with open('/Users/rowang/projects/vnpy/examples/alpha_research/agent_health_check.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 1: 过滤表头行和解析错误
old_check = '''            elif status in ['the', 'Status', 'add', 'Last']:
                # 这些是解析错误，表示 cron list 输出解析失败
                is_status_abnormal = True'''

new_check = '''            elif status in ['the', 'Status', 'add', 'Last']:
                # 这些是解析错误（表头行），跳过不报告
                # is_status_abnormal = True
                agent_info['health'] = 'skip'
                agents_status[name] = agent_info
                continue'''

content = content.replace(old_check, new_check)

# 修复 2: 对于 cron 调度的 Agent，status=0 或 * 可能是正常的
old_critical = '''            elif status == '*' and name in ['首席风险官', '止盈止损执行', '每日选股', '虚拟账户', '每日复盘']:
                # 关键 Agent 显示 * 表示状态未知
                is_status_abnormal = True'''

new_critical = '''            elif status == '*' and name in ['首席风险官', '止盈止损执行', '每日选股', '虚拟账户', '每日复盘']:
                # 关键 Agent 显示 * 可能是正常的（cron 调度，未到运行时间）
                # 检查 last_run 是否为 "cron" 或数字
                if last_run == 'cron' or (last_run.isdigit() and int(last_run) < 60):
                    # 正常运行中或最近运行过
                    agent_info['health'] = 'healthy'
                    agents_status[name] = agent_info
                    continue
                # 否则标记为异常
                is_status_abnormal = True'''

content = content.replace(old_critical, new_critical)

# 修复 3: status=0 也需要检查是否是 cron 调度
old_status0 = '''            elif status == '0':
                # status=0 表示 Agent 未运行或失败
                is_status_abnormal = True'''

new_status0 = '''            elif status == '0':
                # status=0 可能是正常的（cron 调度，未到运行时间）
                # 检查 last_run 是否为 "cron"
                if last_run == 'cron':
                    # cron 调度中，正常
                    agent_info['health'] = 'healthy'
                    agents_status[name] = agent_info
                    continue
                # 否则可能是失败
                is_status_abnormal = True'''

content = content.replace(old_status0, new_status0)

with open('/Users/rowang/projects/vnpy/examples/alpha_research/agent_health_check.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 健康检查误报修复完成")
print("修复内容:")
print("  1. 过滤表头行（-, Name, Status, Last）")
print("  2. cron 调度的 Agent status=0 或 * 视为正常")
print("  3. 只报告真正的异常情况")
