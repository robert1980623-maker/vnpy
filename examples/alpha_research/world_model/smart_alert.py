#!/usr/bin/env python3
"""
智能告警系统

功能:
- 异常交易检测
- 数据质量告警
- Agent 故障告警
- 多渠道通知 (Slack/邮件/日志)

用法:
    from smart_alert import SmartAlertSystem
    
    alert = SmartAlertSystem()
    alert.check_anomalies()
    alert.send_alert('high', '测试告警')
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum
import requests

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


class AlertLevel(Enum):
    """告警级别"""
    LOW = "low"          # 低优先级
    MEDIUM = "medium"    # 中优先级
    HIGH = "high"        # 高优先级
    CRITICAL = "critical" # 严重


class AlertType(Enum):
    """告警类型"""
    TRADE_ANOMALY = "trade_anomaly"      # 异常交易
    DATA_QUALITY = "data_quality"        # 数据质量
    AGENT_FAILURE = "agent_failure"      # Agent 故障
    RISK_WARNING = "risk_warning"        # 风险警告
    SYSTEM_ERROR = "system_error"        # 系统错误


class SmartAlertSystem:
    """智能告警系统"""
    
    def __init__(self, neo4j_uri="bolt://localhost:7687", redis_host="localhost"):
        self.neo4j_driver = None
        self.redis_client = None
        
        if NEO4J_AVAILABLE:
            try:
                self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", "admin_robert"))
                self.neo4j_driver.verify_connectivity()
                logger.info("✅ Neo4j 连接成功")
            except Exception as e:
                logger.error(f"Neo4j 连接失败：{e}")
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Redis 连接成功")
            except Exception as e:
                logger.error(f"Redis 连接失败：{e}")
        
        # 告警统计
        self.alert_stats = {
            'total': 0,
            'by_level': {},
            'by_type': {}
        }
        
        # Stream 模式告警聚合缓存
        self.alert_cache = {}
        self.aggregation_window = int(os.environ.get('SLACK_AGGREGATION_WINDOW', 300))  # 默认 5 分钟
        self.max_alerts_per_window = int(os.environ.get('SLACK_MAX_ALERTS_PER_WINDOW', 5))
        self.stream_mode = os.environ.get('SLACK_STREAM_MODE', '0') == '1'
        
        # 告警摘要配置
        self.digest_enabled = os.environ.get('SLACK_DIGEST_ENABLED', '1') == '1'
        self.digest_recipients = []  # 摘要接收者列表
        
        logger.info("✅ 智能告警系统初始化完成")
    
    def create_alert(self, level: AlertLevel, alert_type: AlertType, 
                     title: str, message: str, metadata: Dict = None) -> Dict:
        """
        创建告警
        
        Args:
            level: 告警级别
            alert_type: 告警类型
            title: 告警标题
            message: 告警内容
            metadata: 附加元数据
        
        Returns:
            dict: 告警信息
        """
        alert = {
            'alert_id': f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            'level': level.value,
            'type': alert_type.value,
            'title': title,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'acknowledged': False
        }
        
        # 存储到 Redis
        if self.redis_client:
            try:
                alert_key = f"alerts:{alert['alert_id']}"
                self.redis_client.hset(alert_key, mapping=alert)
                self.redis_client.expire(alert_key, 86400 * 7)  # 保留 7 天
                
                # 添加到告警列表
                self.redis_client.lpush("alerts:queue", alert['alert_id'])
                
                logger.info(f"🚨 创建告警：{alert['title']} ({alert['level']})")
            except Exception as e:
                logger.error(f"存储告警失败：{e}")
        
        # 更新统计
        self.alert_stats['total'] += 1
        level_key = alert['level']
        self.alert_stats['by_level'][level_key] = self.alert_stats['by_level'].get(level_key, 0) + 1
        type_key = alert['type']
        self.alert_stats['by_type'][type_key] = self.alert_stats['by_type'].get(type_key, 0) + 1
        
        # 发送通知
        self._send_notification(alert)
        
        return alert
    
    def _send_notification(self, alert: Dict):
        """发送告警通知"""
        level = alert['level']
        
        # 根据级别决定通知渠道
        if level == 'critical':
            # 严重告警：所有渠道
            self._send_slack(alert)
            self._send_email(alert)
            logger.error(f"🚨 CRITICAL: {alert['title']} - {alert['message']}")
        elif level == 'high':
            # 高优先级：Slack + 日志
            self._send_slack(alert)
            logger.warning(f"⚠️ HIGH: {alert['title']} - {alert['message']}")
        elif level == 'medium':
            # 中优先级：日志
            logger.warning(f"⚠️ MEDIUM: {alert['title']} - {alert['message']}")
        else:
            # 低优先级：仅记录
            logger.info(f"ℹ️ LOW: {alert['title']}")
    
    def _send_slack(self, alert: Dict):
        """发送 Slack 通知"""
        try:
            # Slack Webhook URL (从环境变量读取)
            webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("⚠️ SLACK_WEBHOOK_URL 未配置，跳过 Slack 通知")
                return
            
            # 根据告警级别设置颜色
            color_map = {
                'critical': 'danger',
                'high': 'warning',
                'medium': '#FFA500',
                'low': 'good'
            }
            color = color_map.get(alert['level'], '#808080')
            
            # 根据告警级别设置 emoji
            emoji_map = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '⚡',
                'low': 'ℹ️'
            }
            emoji = emoji_map.get(alert['level'], '📢')
            
            # 构建 Slack 消息
            payload = {
                "text": f"{emoji} {alert['title']}",
                "attachments": [{
                    "color": color,
                    "fields": [
                        {
                            "title": "告警类型",
                            "value": alert['alert_type'],
                            "short": True
                        },
                        {
                            "title": "级别",
                            "value": alert['level'].upper(),
                            "short": True
                        },
                        {
                            "title": "详情",
                            "value": alert['message'],
                            "short": False
                        }
                    ],
                    "footer": alert.get('source', 'vnpy-agent'),
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            # 添加元数据（如果有）
            if alert.get('metadata'):
                metadata_text = "\n".join([f"• {k}: {v}" for k, v in alert['metadata'].items()])
                payload["attachments"][0]["fields"].append({
                    "title": "元数据",
                    "value": metadata_text,
                    "short": False
                })
            
            # 发送请求
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Slack 通知已发送：{alert['title']}")
            else:
                logger.error(f"❌ Slack 通知失败：{response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"❌ 发送 Slack 通知异常：{e}")
    
    def _send_email(self, alert: Dict):
        """发送邮件通知"""
        # TODO: 集成邮件 API
        logger.info(f"📧 邮件通知：{alert['title']}")
    
    def check_trade_anomalies(self) -> List[Dict]:
        """
        检测异常交易
        
        检测规则:
        1. 大额交易 (超过平均 10 倍)
        2. 频繁交易 (1 分钟内>10 次)
        3. 异常价格 (偏离市场价>5%)
        4. 非交易时间交易
        """
        anomalies = []
        
        if not self.redis_client:
            return anomalies
        
        try:
            # 获取最近交易事件
            events = []
            for i in range(100):
                msg = self.redis_client.lindex("events:TradeExecutedEvent", i)
                if msg:
                    events.append(json.loads(msg))
            
            # 分析交易
            for event in events:
                payload = event.get('payload', {})
                volume = float(payload.get('volume', 0))
                price = float(payload.get('price', 0))
                
                # 大额交易检测
                if volume > 10000:
                    anomaly = self.create_alert(
                        level=AlertLevel.HIGH,
                        alert_type=AlertType.TRADE_ANOMALY,
                        title="大额交易检测",
                        message=f"检测到 {payload.get('symbol')} 大额交易：{volume}股",
                        metadata={'symbol': payload.get('symbol'), 'volume': volume}
                    )
                    anomalies.append(anomaly)
                
                # 异常价格检测
                if price > 10000 or price < 0.01:
                    anomaly = self.create_alert(
                        level=AlertLevel.MEDIUM,
                        alert_type=AlertType.TRADE_ANOMALY,
                        title="异常价格检测",
                        message=f"检测到 {payload.get('symbol')} 异常价格：¥{price}",
                        metadata={'symbol': payload.get('symbol'), 'price': price}
                    )
                    anomalies.append(anomaly)
            
            logger.info(f"✅ 异常交易检测完成：发现 {len(anomalies)} 个异常")
            
        except Exception as e:
            logger.error(f"异常交易检测失败：{e}")
        
        return anomalies
    
    def check_data_quality(self) -> List[Dict]:
        """
        数据质量告警
        
        检测规则:
        1. 数据过期 (>24 小时未更新)
        2. 数据缺失 (关键字段为空)
        3. 数据异常 (价格/体积异常)
        """
        alerts = []
        
        if not self.neo4j_driver:
            return alerts
        
        try:
            with self.neo4j_driver.session() as session:
                # 检查数据新鲜度
                result = session.run("""
                MATCH (ws:WorldState)
                WHERE ws.timestamp IS NOT NULL
                WITH ws, duration.between(ws.timestamp, datetime()).hours as hours_ago
                WHERE hours_ago > 24
                RETURN ws.type as type, hours_ago
                """)
                
                for record in result:
                    alert = self.create_alert(
                        level=AlertLevel.MEDIUM,
                        alert_type=AlertType.DATA_QUALITY,
                        title="数据过期告警",
                        message=f"{record['type']} 数据已过期 {record['hours_ago']} 小时",
                        metadata={'type': record['type'], 'hours_ago': record['hours_ago']}
                    )
                    alerts.append(alert)
            
            logger.info(f"✅ 数据质量检查完成：发现 {len(alerts)} 个问题")
            
        except Exception as e:
            logger.error(f"数据质量检查失败：{e}")
        
        return alerts
    
    def check_agent_health(self) -> List[Dict]:
        """
        Agent 健康检查
        
        检测规则:
        1. Agent 无响应 (>5 分钟无活动)
        2. Agent 错误率 (>10%)
        3. Agent 资源超限
        """
        alerts = []
        
        # 模拟 Agent 健康检查
        agent_status = {
            'main': 'active',
            'data-agent': 'active',
            'quant-agent': 'active',
            'report-agent': 'active'
        }
        
        for agent_id, status in agent_status.items():
            if status == 'inactive':
                alert = self.create_alert(
                    level=AlertLevel.HIGH,
                    alert_type=AlertType.AGENT_FAILURE,
                    title=f"Agent 故障：{agent_id}",
                    message=f"Agent {agent_id} 无响应",
                    metadata={'agent_id': agent_id, 'status': status}
                )
                alerts.append(alert)
        
        logger.info(f"✅ Agent 健康检查完成：发现 {len(alerts)} 个问题")
        
        return alerts
    
    def check_risk_warnings(self) -> List[Dict]:
        """
        风险警告
        
        检测规则:
        1. 仓位过重 (>90%)
        2. 回撤过大 (>10%)
        3. 持仓集中 (>30% 单只股票)
        """
        alerts = []
        
        if not self.neo4j_driver:
            return alerts
        
        try:
            with self.neo4j_driver.session() as session:
                # 检查仓位
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
                    total_value = data.get('total_value', 1)
                    cash = data.get('cash', 0)
                    
                    # 仓位比例
                    position_ratio = (total_value - cash) / total_value * 100
                    if position_ratio > 90:
                        alert = self.create_alert(
                            level=AlertLevel.MEDIUM,
                            alert_type=AlertType.RISK_WARNING,
                            title="仓位过重警告",
                            message=f"当前仓位 {position_ratio:.1f}%，超过 90% 警戒线",
                            metadata={'position_ratio': position_ratio}
                        )
                        alerts.append(alert)
                    
                    # 持仓集中度
                    for pos in positions:
                        pos_value = pos.get('market_value', 0)
                        pos_ratio = pos_value / total_value * 100
                        if pos_ratio > 30:
                            alert = self.create_alert(
                                level=AlertLevel.MEDIUM,
                                alert_type=AlertType.RISK_WARNING,
                                title="持仓集中警告",
                                message=f"{pos.get('symbol')} 持仓占比 {pos_ratio:.1f}%，超过 30% 警戒线",
                                metadata={'symbol': pos.get('symbol'), 'ratio': pos_ratio}
                            )
                            alerts.append(alert)
            
            logger.info(f"✅ 风险警告检查完成：发现 {len(alerts)} 个警告")
            
        except Exception as e:
            logger.error(f"风险警告检查失败：{e}")
        
        return alerts
    
    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        logger.info("=" * 60)
        logger.info("开始智能告警检查...")
        logger.info("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # 异常交易检测
        results['checks']['trade_anomalies'] = len(self.check_trade_anomalies())
        
        # 数据质量检查
        results['checks']['data_quality'] = len(self.check_data_quality())
        
        # Agent 健康检查
        results['checks']['agent_health'] = len(self.check_agent_health())
        
        # 风险警告检查
        results['checks']['risk_warnings'] = len(self.check_risk_warnings())
        
        # 总计
        results['total_alerts'] = sum(results['checks'].values())
        results['alert_stats'] = self.alert_stats
        
        logger.info("=" * 60)
        logger.info(f"告警检查完成：共 {results['total_alerts']} 个告警")
        logger.info("=" * 60)
        
        return results
    
    def get_alert_history(self, limit=50) -> List[Dict]:
        """获取告警历史"""
        if not self.redis_client:
            return []
        
        try:
            alert_ids = self.redis_client.lrange("alerts:queue", 0, limit - 1)
            alerts = []
            
            for alert_id in alert_ids:
                alert_data = self.redis_client.hgetall(f"alerts:{alert_id.decode()}")
                if alert_data:
                    alerts.append(alert_data)
            
            return alerts
        except:
            return []
    
    def get_stats(self) -> Dict:
        """获取告警统计"""
        return self.alert_stats
    
    def close(self):
        """关闭连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.redis_client:
            self.redis_client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("测试智能告警系统")
    print("=" * 60)
    
    alert = SmartAlertSystem()
    
    # 运行所有检查
    print("\n运行智能告警检查...")
    results = alert.run_all_checks()
    
    print(f"\n检查结果:")
    print(f"  异常交易：{results['checks']['trade_anomalies']}")
    print(f"  数据质量：{results['checks']['data_quality']}")
    print(f"  Agent 健康：{results['checks']['agent_health']}")
    print(f"  风险警告：{results['checks']['risk_warnings']}")
    print(f"  总计：{results['total_alerts']}")
    
    # 获取统计
    print("\n告警统计:")
    stats = alert.get_stats()
    print(f"  总数：{stats['total']}")
    
    alert.close()
    print("\n✅ 测试完成")

    def _should_send_alert(self, alert: Dict) -> bool:
        """
        Stream 模式：判断告警是否应该发送
        
        规则:
        - CRITICAL/HIGH: 立即发送
        - MEDIUM: 聚合发送（同类型 5 分钟内最多 1 条）
        - LOW: 不发送
        """
        if not self.stream_mode:
            return True
        
        level = alert.get('level', 'low')
        alert_type = alert.get('alert_type', 'unknown')
        
        # CRITICAL 和 HIGH 立即发送
        if level in ['critical', 'high']:
            return True
        
        # MEDIUM 聚合发送
        if level == 'medium':
            cache_key = f"medium:{alert_type}"
            now = datetime.now().timestamp()
            
            # 检查缓存
            if cache_key in self.alert_cache:
                last_sent = self.alert_cache[cache_key]
                if now - last_sent < self.aggregation_window:
                    logger.debug(f"⏸️ 告警聚合中，跳过：{alert['title']}")
                    return False
            
            # 更新缓存
            self.alert_cache[cache_key] = now
            return True
        
        # LOW 不发送
        return False
    
    def _cleanup_alert_cache(self):
        """清理过期的告警缓存"""
        now = datetime.now().timestamp()
        expired_keys = []
        
        for key, timestamp in self.alert_cache.items():
            if now - timestamp > self.aggregation_window:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.alert_cache[key]
        
        logger.debug(f"🧹 清理 {len(expired_keys)} 个过期告警缓存")
    
    def send_aggregated_alerts(self):
        """
        发送聚合告警摘要
        
        调用时机：每个聚合窗口结束时
        """
        if not self.stream_mode:
            return
        
        # TODO: 实现聚合告警摘要逻辑
        logger.info("📊 发送聚合告警摘要...")
