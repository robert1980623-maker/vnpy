#!/usr/bin/env python3
"""
飞书通知包装脚本 - 读取最新检查报告并发送critical问题通知
"""

import os
import json
from datetime import datetime
from pathlib import Path
from utils.feishu_notifier import send_critical_alert


def main():
    """主函数：读取最新检查报告并发送通知"""
    reports_dir = Path("reports")
    
    if not reports_dir.exists():
        print("报告目录不存在，跳过通知")
        return
    
    # 查找最新的检查报告文件
    report_files = list(reports_dir.glob("*.json"))
    if not report_files:
        print("未找到检查报告文件")
        return
    
    # 按修改时间排序，获取最新的报告
    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
    
    try:
        with open(latest_report, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 检查是否有critical问题
        critical_issues = []
        
        # 检查报告结构，寻找critical问题
        if isinstance(report_data, dict):
            # 检查不同可能的字段
            for key, value in report_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get('level', '').lower() == 'critical':
                            critical_issues.append(item)
                        elif isinstance(item, dict) and item.get('severity', '').lower() == 'critical':
                            critical_issues.append(item)
                        elif isinstance(item, str) and ('critical' in item.lower() or '严重' in item or '错误' in item):
                            critical_issues.append({'message': item, 'type': 'unknown'})
                elif isinstance(value, dict):
                    if value.get('level', '').lower() == 'critical':
                        critical_issues.append(value)
                    elif value.get('severity', '').lower() == 'critical':
                        critical_issues.append(value)
        
        # 如果报告本身就是列表
        elif isinstance(report_data, list):
            for item in report_data:
                if isinstance(item, dict):
                    if item.get('level', '').lower() == 'critical':
                        critical_issues.append(item)
                    elif item.get('severity', '').lower() == 'critical':
                        critical_issues.append(item)
                    elif isinstance(item, str) and ('critical' in item.lower() or '严重' in item or '错误' in item):
                        critical_issues.append({'message': item, 'type': 'unknown'})
        
        if critical_issues:
            title = f"🚨 系统检查发现 {len(critical_issues)} 个严重问题"
            send_critical_alert(title, critical_issues)
            print(f"已发送critical问题通知，共 {len(critical_issues)} 个问题")
        else:
            print("未发现critical问题，无需发送通知")
    
    except json.JSONDecodeError:
        print(f"无法解析JSON文件: {latest_report}")
    except Exception as e:
        print(f"处理报告文件时出错: {str(e)}")


if __name__ == "__main__":
    main()
