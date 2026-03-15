#!/usr/bin/env python3
"""
Agent 报告模板系统

提供标准化的报告模板，确保所有 Agent 输出格式统一、信息完整。

用法:
    from report_templates import get_template, render_report
    
    # 获取模板
    template = get_template('data_download')
    
    # 渲染报告
    report = render_report(template, data={...})
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


# ============================================================================
# 报告模板定义
# ============================================================================

TEMPLATES = {
    # -------------------------------------------------------------------------
    # 1. 数据下载类报告模板
    # -------------------------------------------------------------------------
    'data_download': {
        'name': '数据下载 Agent 报告',
        'icon': '📥',
        'sections': [
            {
                'title': '执行概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'duration_seconds', 'label': '耗时', 'format': 'duration'},
                    {'key': 'items_processed', 'label': '处理数量', 'format': 'number'},
                    {'key': 'success_rate', 'label': '成功率', 'format': 'percentage'},
                ]
            },
            {
                'title': '下载详情',
                'type': 'table',
                'columns': ['股票代码', '数据类别', '状态', '耗时', '错误信息'],
                'max_rows': 20
            },
            {
                'title': '数据分类统计',
                'type': 'table',
                'columns': ['数据类型', '应下载', '已下载', '失败', '成功率'],
                'max_rows': 10
            },
            {
                'title': '问题汇总',
                'type': 'list',
                'item_format': '• {error_type}: {count} 个 - {example}',
                'max_items': 10
            },
        ],
        'footer': '数据下载完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 2. 选股类报告模板
    # -------------------------------------------------------------------------
    'stock_selection': {
        'name': '选股 Agent 报告',
        'icon': '🎯',
        'sections': [
            {
                'title': '选股概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'total_candidates', 'label': '候选股票', 'format': 'number'},
                    {'key': 'selected_count', 'label': '最终选股', 'format': 'number'},
                    {'key': 'selection_rate', 'label': '入选率', 'format': 'percentage'},
                ]
            },
            {
                'title': '最终选股结果',
                'type': 'table',
                'columns': ['股票代码', '股票名称', '入选理由', '评分', '风险提示'],
                'max_rows': 10
            },
            {
                'title': '筛选过程',
                'type': 'table',
                'columns': ['筛选条件', '筛选前数量', '筛选后数量', '淘汰率'],
                'max_rows': 10
            },
            {
                'title': '重点关注',
                'type': 'list',
                'item_format': '• {stock}: {reason}',
                'max_items': 5
            },
        ],
        'footer': '选股完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 3. 交易类报告模板
    # -------------------------------------------------------------------------
    'trading': {
        'name': '交易 Agent 报告',
        'icon': '💰',
        'sections': [
            {
                'title': '交易概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'total_trades', 'label': '总交易数', 'format': 'number'},
                    {'key': 'buy_count', 'label': '买入', 'format': 'number'},
                    {'key': 'sell_count', 'label': '卖出', 'format': 'number'},
                    {'key': 'total_amount', 'label': '交易金额', 'format': 'currency'},
                ]
            },
            {
                'title': '交易明细',
                'type': 'table',
                'columns': ['股票代码', '交易方向', '价格', '数量', '金额', '状态'],
                'max_rows': 20
            },
            {
                'title': '持仓变化',
                'type': 'table',
                'columns': ['股票代码', '原持仓', '新持仓', '变化', '当前市值'],
                'max_rows': 15
            },
            {
                'title': '交易费用',
                'type': 'text',
                'format': '  • 佣金：¥{commission}\n  • 印花税：¥{stamp_tax}\n  • 过户费：¥{transfer_fee}\n  • 合计：¥{total_fee}'
            },
        ],
        'footer': '交易执行完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 4. 风控类报告模板
    # -------------------------------------------------------------------------
    'risk_control': {
        'name': '风控 Agent 报告',
        'icon': '🛡️',
        'sections': [
            {
                'title': '风控概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'risk_level', 'label': '风险等级', 'format': 'risk_level'},
                    {'key': 'total_positions', 'label': '持仓数量', 'format': 'number'},
                    {'key': 'risk_score', 'label': '风险评分', 'format': 'score'},
                ]
            },
            {
                'title': '仓位风险检查',
                'type': 'table',
                'columns': ['股票代码', '持仓占比', '预警线', '状态', '建议'],
                'max_rows': 15
            },
            {
                'title': '止盈止损检查',
                'type': 'table',
                'columns': ['股票代码', '当前价', '成本价', '盈亏率', '触发状态', '操作'],
                'max_rows': 15
            },
            {
                'title': '风险警示',
                'type': 'list',
                'item_format': '⚠️ {warning}',
                'max_items': 10
            },
        ],
        'footer': '风控检查完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 5. 监控类报告模板
    # -------------------------------------------------------------------------
    'monitoring': {
        'name': '监控 Agent 报告',
        'icon': '📊',
        'sections': [
            {
                'title': '监控概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'total_tasks', 'label': '监控任务', 'format': 'number'},
                    {'key': 'healthy_count', 'label': '健康', 'format': 'number'},
                    {'key': 'warning_count', 'label': '警告', 'format': 'number'},
                    {'key': 'error_count', 'label': '异常', 'format': 'number'},
                ]
            },
            {
                'title': '任务状态',
                'type': 'table',
                'columns': ['任务名称', '状态', '上次运行', '下次运行', '连续错误'],
                'max_rows': 20
            },
            {
                'title': '健康度统计',
                'type': 'text',
                'format': '  • 健康率：{health_rate}%\n  • 平均响应时间：{avg_response_time}ms\n  • 系统负载：{system_load}'
            },
            {
                'title': '异常列表',
                'type': 'list',
                'item_format': '❌ {task}: {error}',
                'max_items': 10
            },
        ],
        'footer': '监控检查完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 6. 复盘类报告模板
    # -------------------------------------------------------------------------
    'daily_review': {
        'name': '每日复盘报告',
        'icon': '📝',
        'sections': [
            {
                'title': '今日概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'trading_date', 'label': '交易日期', 'format': 'date'},
                    {'key': 'total_return', 'label': '今日盈亏', 'format': 'currency'},
                    {'key': 'return_rate', 'label': '收益率', 'format': 'percentage'},
                ]
            },
            {
                'title': '持仓表现',
                'type': 'table',
                'columns': ['股票代码', '股票名称', '持仓', '盈亏', '盈亏率', '操作建议'],
                'max_rows': 15
            },
            {
                'title': '交易记录',
                'type': 'table',
                'columns': ['时间', '股票代码', '方向', '价格', '数量', '盈亏'],
                'max_rows': 20
            },
            {
                'title': '今日总结',
                'type': 'text',
                'format': '{summary}'
            },
            {
                'title': '明日计划',
                'type': 'list',
                'item_format': '• {plan}',
                'max_items': 5
            },
        ],
        'footer': '复盘完成 | {timestamp}'
    },
    
    # -------------------------------------------------------------------------
    # 7. 通用报告模板
    # -------------------------------------------------------------------------
    'generic': {
        'name': '通用 Agent 报告',
        'icon': '🤖',
        'sections': [
            {
                'title': '执行概览',
                'type': 'metrics',
                'metrics': [
                    {'key': 'status', 'label': '状态', 'format': 'status'},
                    {'key': 'duration_seconds', 'label': '耗时', 'format': 'duration'},
                    {'key': 'items_processed', 'label': '处理数量', 'format': 'number'},
                    {'key': 'items_success', 'label': '成功', 'format': 'number'},
                    {'key': 'items_failed', 'label': '失败', 'format': 'number'},
                ]
            },
            {
                'title': '详细结果',
                'type': 'table',
                'columns': ['项目', '状态', '详情'],
                'max_rows': 20
            },
            {
                'title': '问题汇总',
                'type': 'list',
                'item_format': '• {issue}',
                'max_items': 10
            },
        ],
        'footer': '报告生成 | {timestamp}'
    },
}


# ============================================================================
# 报告渲染函数
# ============================================================================

def get_template(template_name: str) -> Dict:
    """获取报告模板"""
    return TEMPLATES.get(template_name, TEMPLATES['generic'])


def format_value(value: Any, format_type: str) -> str:
    """格式化值"""
    if value is None:
        return '-'
    
    if format_type == 'status':
        status_map = {
            'success': '✅ 成功',
            'failed': '❌ 失败',
            'warning': '⚠️ 警告',
            'running': '🔄 运行中',
        }
        return status_map.get(value, str(value))
    
    elif format_type == 'duration':
        if isinstance(value, (int, float)):
            if value < 60:
                return f'{value:.2f} 秒'
            elif value < 3600:
                return f'{value/60:.1f} 分钟'
            else:
                return f'{value/3600:.1f} 小时'
        return str(value)
    
    elif format_type == 'percentage':
        if isinstance(value, (int, float)):
            return f'{value*100:.1f}%' if value <= 1 else f'{value:.1f}%'
        return str(value)
    
    elif format_type == 'currency':
        if isinstance(value, (int, float)):
            return f'¥{value:,.2f}'
        return str(value)
    
    elif format_type == 'number':
        if isinstance(value, (int, float)):
            return f'{value:,}'
        return str(value)
    
    elif format_type == 'risk_level':
        risk_map = {
            'low': '🟢 低风险',
            'medium': '🟡 中风险',
            'high': '🔴 高风险',
            'critical': '⚫ 严重风险',
        }
        return risk_map.get(value, str(value))
    
    elif format_type == 'score':
        if isinstance(value, (int, float)):
            return f'{value:.1f}/100'
        return str(value)
    
    elif format_type == 'date':
        return str(value)
    
    else:
        return str(value)


def render_section(section: Dict, data: Dict) -> str:
    """渲染单个章节"""
    lines = []
    title = section['title']
    section_type = section['type']
    
    lines.append(f"\n【{title}】")
    
    if section_type == 'metrics':
        # 渲染指标
        metrics = section.get('metrics', [])
        for metric in metrics:
            key = metric['key']
            label = metric['label']
            format_type = metric.get('format', 'text')
            value = data.get(key, None)
            formatted_value = format_value(value, format_type)
            lines.append(f"  {label}: {formatted_value}")
    
    elif section_type == 'table':
        # 渲染表格
        table_data = data.get('table_data', [])
        columns = section.get('columns', [])
        max_rows = section.get('max_rows', 20)
        
        if not table_data:
            lines.append("  无数据")
        else:
            # 限制行数
            if len(table_data) > max_rows:
                table_data = table_data[:max_rows]
                show_more = f"\n  ... 还有 {len(data.get('table_data', [])) - max_rows} 条（查看完整报告）"
            else:
                show_more = ""
            
            # 计算列宽
            col_widths = []
            for col in columns:
                max_width = len(col)
                for row in table_data:
                    cell_value = str(row.get(col, '-'))
                    max_width = max(max_width, len(cell_value))
                col_widths.append(min(max_width, 20))
            
            # 构建表格
            header = ' │ '.join([col.center(width) for col, width in zip(columns, col_widths)])
            separator = '─┼─'.join(['─' * width for width in col_widths])
            
            lines.append(f"  ┌─{separator}─┐")
            lines.append(f"  │ {header} │")
            lines.append(f"  ├─{separator}─┤")
            
            for row in table_data:
                cells = []
                for col, width in zip(columns, col_widths):
                    cell_value = str(row.get(col, '-'))[:width]
                    cells.append(cell_value.center(width))
                lines.append(f"  │ {' │ '.join(cells)} │")
            
            lines.append(f"  └─{separator}─┘")
            lines.append(show_more)
    
    elif section_type == 'list':
        # 渲染列表
        list_data = data.get('list_data', [])
        item_format = section.get('item_format', '• {item}')
        max_items = section.get('max_items', 10)
        
        if not list_data:
            lines.append("  无")
        else:
            for item in list_data[:max_items]:
                if isinstance(item, dict):
                    try:
                        formatted = item_format.format(**item)
                    except KeyError:
                        formatted = str(item)
                else:
                    formatted = item_format.format(item=item)
                lines.append(f"  {formatted}")
            
            if len(list_data) > max_items:
                lines.append(f"  ... 还有 {len(list_data) - max_items} 项")
    
    elif section_type == 'text':
        # 渲染文本
        text_format = section.get('format', '{text}')
        try:
            formatted = text_format.format(**data)
        except KeyError:
            formatted = data.get('text', '')
        lines.append(formatted)
    
    return '\n'.join(lines)


def render_report(template_name: str, data: Dict, metrics: Dict = None) -> str:
    """渲染完整报告"""
    template = get_template(template_name)
    
    lines = []
    
    # 标题
    icon = template.get('icon', '📊')
    name = template.get('name', 'Agent 报告')
    lines.append("=" * 70)
    lines.append(f"{icon} {name}")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    # 合并数据
    render_data = {**data, **metrics} if metrics else data
    render_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 渲染各章节
    for section in template.get('sections', []):
        section_text = render_section(section, render_data)
        lines.append(section_text)
        lines.append("")
    
    # 底部
    footer_template = template.get('footer', '报告生成 | {timestamp}')
    footer = footer_template.format(**render_data)
    lines.append("=" * 70)
    lines.append(footer)
    lines.append("=" * 70)
    
    return '\n'.join(lines)


# ============================================================================
# 便捷函数
# ============================================================================

def create_data_download_report(data: Dict, metrics: Dict) -> str:
    """创建数据下载报告"""
    return render_report('data_download', data, metrics)


def create_stock_selection_report(data: Dict, metrics: Dict) -> str:
    """创建选股报告"""
    return render_report('stock_selection', data, metrics)


def create_trading_report(data: Dict, metrics: Dict) -> str:
    """创建交易报告"""
    return render_report('trading', data, metrics)


def create_risk_control_report(data: Dict, metrics: Dict) -> str:
    """创建风控报告"""
    return render_report('risk_control', data, metrics)


def create_monitoring_report(data: Dict, metrics: Dict) -> str:
    """创建监控报告"""
    return render_report('monitoring', data, metrics)


def create_daily_review_report(data: Dict, metrics: Dict) -> str:
    """创建复盘报告"""
    return render_report('daily_review', data, metrics)


def create_generic_report(data: Dict, metrics: Dict) -> str:
    """创建通用报告"""
    return render_report('generic', data, metrics)


if __name__ == '__main__':
    # 测试示例
    test_metrics = {
        'status': 'success',
        'duration_seconds': 15.23,
        'items_processed': 14,
        'items_success': 13,
        'items_failed': 1,
    }
    
    test_data = {
        'success_rate': 0.929,
        'table_data': [
            {'股票代码': '600519.SH', '数据类别': '日线', '状态': '✅ 成功', '耗时': '1.2s', '错误信息': '-'},
            {'股票代码': '000858.SZ', '数据类别': '日线', '状态': '✅ 成功', '耗时': '0.9s', '错误信息': '-'},
            {'股票代码': '300750.SZ', '数据类别': '日线', '状态': '❌ 失败', '耗时': '-', '错误信息': '超时'},
        ],
        'list_data': [
            {'error_type': '网络超时', 'count': 1, 'example': '300750.SZ'},
        ],
    }
    
    report = create_data_download_report(test_data, test_metrics)
    print(report)
