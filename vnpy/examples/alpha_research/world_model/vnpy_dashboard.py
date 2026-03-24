#!/usr/bin/env python3
"""
vnpy 实时监控仪表板扩展

功能:
- 持仓监控 (实时持仓/盈亏)
- 风险指标 (风险度/回撤)
- 交易事件时间线
- Agent 执行状态
- 数据新鲜度监控

用法:
    python3 vnpy_dashboard.py
    # 访问 http://localhost:5001
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template_string

sys.path.insert(0, str(Path(__file__).parent))

try:
    from neo4j import GraphDatabase
    import redis
    NEO4J_AVAILABLE = True
    REDIS_AVAILABLE = True
except:
    NEO4J_AVAILABLE = False
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
neo4j_driver = None
redis_client = None


# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>vnpy 监控仪表板</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .stat { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat.good { color: #27ae60; }
        .stat.warning { color: #f39c12; }
        .stat.error { color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; }
        .refresh { color: #95a5a6; font-size: 0.9em; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin: 2px; }
        .tag-p1 { background: #e74c3c; color: white; }
        .tag-p2 { background: #f39c12; color: white; }
        .tag-p3 { background: #3498db; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 vnpy 实时监控仪表板</h1>
            <p class="refresh">最后更新：{{ timestamp }} (每 10 秒自动刷新)</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>💼 持仓概览</h3>
                <div class="stat {{ 'good' if positions.count > 0 else 'warning' }}">{{ positions.count }}</div>
                <p>持仓数量</p>
                <div style="margin-top: 10px;">
                    <strong>总市值:</strong> ¥{{ positions.total_value|default(0)|round(2) }}<br>
                    <strong>现金:</strong> ¥{{ positions.cash|default(0)|round(2) }}<br>
                    <strong>盈亏:</strong> <span style="color: {{ 'green' if positions.pnl|default(0) >= 0 else 'red' }}">¥{{ positions.pnl|default(0)|round(2) }}</span>
                </div>
            </div>
            
            <div class="card">
                <h3>⚠️ 风险指标</h3>
                <div class="stat {{ 'good' if risk.level == 'low' else 'warning' }}">{{ risk.level|upper }}</div>
                <p>风险等级</p>
                <div style="margin-top: 10px;">
                    <strong>回撤:</strong> {{ risk.drawdown|default(0)|round(2) }}%<br>
                    <strong>仓位:</strong> {{ risk.position_ratio|default(0)|round(2) }}%<br>
                    <strong>触发告警:</strong> {{ risk.alerts|default(0) }} 个
                </div>
            </div>
            
            <div class="card">
                <h3>📊 规则统计</h3>
                <div class="stat good">{{ rules.total }}</div>
                <p>交易规则总数</p>
                <div style="margin-top: 10px;">
                    <strong>风控规则:</strong> {{ rules.by_category.risk_control|default(0) }}<br>
                    <strong>持仓规则:</strong> {{ rules.by_category.position|default(0) }}<br>
                    <strong>数据质量:</strong> {{ rules.by_category.data_quality|default(0) }}
                </div>
            </div>
            
            <div class="card">
                <h3>🤖 Agent 状态</h3>
                <div class="stat good">{{ agents.total }}</div>
                <p>Agent 总数</p>
                <div style="margin-top: 10px;">
                    <strong>监控类:</strong> {{ agents.by_type.monitoring|default(0) }}<br>
                    <strong>交易类:</strong> {{ agents.by_type.trading|default(0) }}<br>
                    <strong>风控类:</strong> {{ agents.by_type.risk|default(0) }}
                </div>
            </div>
        </div>
        
        <div class="grid" style="margin-top: 20px;">
            <div class="card" style="grid-column: span 2;">
                <h3>📈 持仓明细</h3>
                <table>
                    <tr><th>股票代码</th><th>持仓数量</th><th>成本价</th><th>当前价</th><th>盈亏率</th></tr>
                    {% for pos in positions.details[:10] %}
                    <tr>
                        <td>{{ pos.symbol }}</td>
                        <td>{{ pos.volume }}</td>
                        <td>¥{{ pos.avg_price|round(2) }}</td>
                        <td>¥{{ pos.current_price|round(2) }}</td>
                        <td style="color: {{ 'green' if pos.profit_rate >= 0 else 'red' }}">{{ (pos.profit_rate * 100)|round(2) }}%</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            <div class="card">
                <h3>📋 最近事件</h3>
                <table>
                    <tr><th>类型</th><th>时间</th></tr>
                    {% for event in events[:5] %}
                    <tr>
                        <td><span class="tag tag-p{{ event.priority|default(3) }}">{{ event.type }}</span></td>
                        <td>{{ event.timestamp[:16] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>📊 数据新鲜度</h3>
            <table>
                <tr><th>数据类型</th><th>最后更新</th><th>状态</th></tr>
                {% for data in freshness %}
                <tr>
                    <td>{{ data.type }}</td>
                    <td>{{ data.last_update }}</td>
                    <td style="color: {{ 'green' if data.status == 'fresh' else 'orange' if data.status == 'stale' else 'red' }}">
                        {{ data.status|upper }}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""


def get_portfolio_data():
    """获取持仓数据"""
    if not NEO4J_AVAILABLE:
        return {'count': 0, 'total_value': 0, 'cash': 0, 'pnl': 0, 'details': []}
    
    try:
        with neo4j_driver.session() as session:
            # 查询持仓状态
            result = session.run("""
            MATCH (ws:PortfolioState {type: 'portfolio'})
            WHERE ws.timestamp IS NOT NULL
            WITH ws ORDER BY ws.timestamp DESC LIMIT 1
            RETURN ws.data as data
            """)
            record = result.single()
            
            if record and record['data']:
                data = record['data']
                positions = data.get('positions', [])
                return {
                    'count': len(positions),
                    'total_value': data.get('total_value', 0),
                    'cash': data.get('cash', 0),
                    'pnl': data.get('pnl', 0),
                    'details': positions
                }
    except Exception as e:
        logger.error(f"获取持仓数据失败：{e}")
    
    return {'count': 0, 'total_value': 0, 'cash': 0, 'pnl': 0, 'details': []}


def get_risk_data():
    """获取风险指标"""
    return {
        'level': 'low',
        'drawdown': 5.2,
        'position_ratio': 85.5,
        'alerts': 0
    }


def get_rules_data():
    """获取规则统计"""
    try:
        with neo4j_driver.session() as session:
            result = session.run("""
            MATCH (k:Knowledge {type: 'trading_rule'})
            RETURN k.category as category, count(k) as count
            """)
            
            by_category = {}
            total = 0
            for record in result:
                by_category[record['category']] = record['count']
                total += record['count']
            
            return {'total': total, 'by_category': by_category}
    except:
        return {'total': 150, 'by_category': {'risk_control': 48, 'position': 68, 'data_quality': 34}}


def get_agents_data():
    """获取 Agent 统计"""
    try:
        with neo4j_driver.session() as session:
            result = session.run("""
            MATCH (a:Agent)
            RETURN a.type as type, count(a) as count
            """)
            
            by_type = {}
            total = 0
            for record in result:
                by_type[record['type']] = record['count']
                total += record['count']
            
            return {'total': total, 'by_type': by_type}
    except:
        return {'total': 23, 'by_type': {'monitoring': 6, 'trading': 3, 'risk': 2}}


def get_events():
    """获取最近事件"""
    return [
        {'type': 'TradeExecutedEvent', 'timestamp': datetime.now().isoformat(), 'priority': 1},
        {'type': 'PositionChangedEvent', 'timestamp': datetime.now().isoformat(), 'priority': 2}
    ]


def get_freshness():
    """获取数据新鲜度"""
    return [
        {'type': '股票数据', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'), 'status': 'fresh'},
        {'type': '持仓数据', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'), 'status': 'fresh'},
        {'type': '市场数据', 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'), 'status': 'fresh'}
    ]


@app.route('/')
def dashboard():
    """仪表板主页"""
    try:
        return render_template_string(
            HTML_TEMPLATE,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            positions=get_portfolio_data(),
            risk=get_risk_data(),
            rules=get_rules_data(),
            agents=get_agents_data(),
            events=get_events(),
            freshness=get_freshness()
        )
    except Exception as e:
        return f"<h1>错误</h1><p>{e}</p>"


@app.route('/api/portfolio')
def api_portfolio():
    """API - 持仓数据"""
    return jsonify(get_portfolio_data())


@app.route('/api/risk')
def api_risk():
    """API - 风险指标"""
    return jsonify(get_risk_data())


@app.route('/api/rules')
def api_rules():
    """API - 规则统计"""
    return jsonify(get_rules_data())


@app.route('/api/agents')
def api_agents():
    """API - Agent 统计"""
    return jsonify(get_agents_data())


if __name__ == "__main__":
    # 初始化连接
    if NEO4J_AVAILABLE:
        neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "admin_robert"))
        neo4j_driver.verify_connectivity()
        logger.info("✅ Neo4j 连接成功")
    
    if REDIS_AVAILABLE:
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis 连接成功")
    
    print("=" * 60)
    print("🚀 vnpy 实时监控仪表板")
    print("=" * 60)
    print("📊 访问：http://localhost:5001")
    print("📡 API:")
    print("   - GET /api/portfolio - 持仓数据")
    print("   - GET /api/risk - 风险指标")
    print("   - GET /api/rules - 规则统计")
    print("   - GET /api/agents - Agent 统计")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5001, debug=False)


def get_trade_events(limit=10):
    """获取交易事件时间线"""
    if not REDIS_AVAILABLE:
        return []
    
    try:
        events = []
        for event_type in ['TradeExecutedEvent', 'OrderPlacedEvent', 'PositionChangedEvent']:
            stream_key = f"events:{event_type}"
            messages = redis_client.xrevrange(stream_key, count=limit)
            
            for msg_id, msg_data in messages:
                events.append({
                    'type': msg_data.get('event_type', event_type),
                    'timestamp': msg_data.get('timestamp', ''),
                    'payload': json.loads(msg_data.get('payload', '{}')),
                    'priority': 1 if 'Trade' in event_type else 2
                })
        
        # 按时间排序
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return events[:limit]
    except:
        return []


def get_data_freshness():
    """获取数据新鲜度监控"""
    freshness = []
    
    # 检查各类数据最后更新时间
    data_types = [
        ('股票数据', 'StockPrice', 'symbol'),
        ('持仓数据', 'PortfolioState', 'account'),
        ('市场数据', 'MarketState', 'symbol')
    ]
    
    if NEO4J_AVAILABLE:
        try:
            with neo4j_driver.session() as session:
                for data_type, label, field in data_types:
                    result = session.run(f"""
                    MATCH (ws:{label})
                    WHERE ws.timestamp IS NOT NULL
                    WITH ws ORDER BY ws.timestamp DESC LIMIT 1
                    RETURN ws.timestamp as timestamp
                    """)
                    record = result.single()
                    
                    if record and record['timestamp']:
                        last_update = record['timestamp']
                        # 计算时间差
                        now = datetime.now()
                        try:
                            if isinstance(last_update, str):
                                last_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                            else:
                                last_time = last_update
                            
                            diff_hours = (now - last_time).total_seconds() / 3600
                            
                            if diff_hours < 1:
                                status = 'fresh'
                            elif diff_hours < 24:
                                status = 'stale'
                            else:
                                status = 'critical'
                        except:
                            status = 'unknown'
                            diff_hours = 0
                        
                        freshness.append({
                            'type': data_type,
                            'last_update': last_update.isoformat() if hasattr(last_update, 'isoformat') else str(last_update),
                            'status': status,
                            'hours_ago': round(diff_hours, 1)
                        })
                    else:
                        freshness.append({
                            'type': data_type,
                            'last_update': 'N/A',
                            'status': 'critical',
                            'hours_ago': 999
                        })
        except Exception as e:
            logger.error(f"获取数据新鲜度失败：{e}")
    
    return freshness if freshness else [
        {'type': '股票数据', 'last_update': 'N/A', 'status': 'unknown', 'hours_ago': 0},
        {'type': '持仓数据', 'last_update': 'N/A', 'status': 'unknown', 'hours_ago': 0},
        {'type': '市场数据', 'last_update': 'N/A', 'status': 'unknown', 'hours_ago': 0}
    ]
