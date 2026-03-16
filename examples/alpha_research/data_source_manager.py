#!/usr/bin/env python3
"""
自动数据源选择系统 - DataSourceManager

功能：
1. 数据源健康度评估（响应时间、成功率、数据完整性、限流情况）
2. 智能选择最优数据源
3. 故障自动切换
4. 使用统计记录

作者：OpenClaw
日期：2026-03-16
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """健康度指标"""
    response_time_ms: float = 0.0
    success_rate: float = 1.0
    data_completeness: float = 1.0
    rate_limit_hit: bool = False
    consecutive_failures: int = 0
    last_check_time: Optional[str] = None
    last_success_time: Optional[str] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HealthMetrics':
        return cls(**data)


@dataclass
class UsageStatistics:
    """使用统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    rate_limit_hits: int = 0
    last_used_time: Optional[str] = None
    
    @property
    def avg_response_time_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.total_requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UsageStatistics':
        return cls(**data)


@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str
    priority: int
    enabled: bool = True
    token_env: Optional[str] = None
    rate_limit: Dict[str, int] = field(default_factory=dict)
    endpoints: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DataSourceConfig':
        return cls(
            name=data.get('name', ''),
            priority=data.get('priority', 99),
            enabled=data.get('enabled', True),
            token_env=data.get('token_env'),
            rate_limit=data.get('rate_limit', {}),
            endpoints=data.get('endpoints', [])
        )


class DataSourceManager:
    """
    数据源管理器
    
    核心功能：
    1. 数据源注册与配置
    2. 健康度实时监控
    3. 智能选择最优数据源
    4. 故障自动切换
    5. 使用统计记录
    """
    
    def __init__(self, config_file: str = './data_source_config.json'):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # 数据源状态
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.usage_stats: Dict[str, UsageStatistics] = {}
        self.status: Dict[str, DataSourceStatus] = {}
        
        # 响应时间历史记录（用于计算平滑响应时间）
        self.response_time_history: Dict[str, List[float]] = {}
        
        # 限流跟踪
        self.rate_limit_tracker: Dict[str, List[float]] = {}  # timestamp list
        
        # 锁
        self._lock = threading.RLock()
        
        # 健康检查线程
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = False
        
        # 初始化数据源
        self._initialize_data_sources()
        
        # 加载历史统计
        self._load_statistics()
        
        print(f"✅ DataSourceManager 初始化完成")
        print(f"   已注册 {len(self.data_sources)} 个数据源")
        
        # P0-4 修复：启动健康检查线程
        self.start_health_check()
        for name, ds in self.data_sources.items():
            status = self.status.get(name, DataSourceStatus.UNKNOWN)
            print(f"   - {name}: priority={ds.priority}, status={status.value}")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 默认配置
            return {
                "data_sources": [
                    {"name": "tushare", "priority": 1},
                    {"name": "akshare", "priority": 2},
                    {"name": "sina", "priority": 3}
                ],
                "auto_switch": True,
                "health_check_interval": 300
            }
    
    def _initialize_data_sources(self):
        """初始化数据源"""
        for ds_config in self.config.get('data_sources', []):
            config = DataSourceConfig.from_dict(ds_config)
            if config.enabled:
                self.data_sources[config.name] = config
                self.health_metrics[config.name] = HealthMetrics()
                self.usage_stats[config.name] = UsageStatistics()
                self.status[config.name] = DataSourceStatus.UNKNOWN
                self.response_time_history[config.name] = []
                self.rate_limit_tracker[config.name] = []
    
    def _load_statistics(self):
        """加载历史统计"""
        stats_file = Path(self.config.get('statistics', {}).get('log_file', './logs/data_source_stats.json'))
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, stats in data.get('usage_stats', {}).items():
                    if name in self.usage_stats:
                        self.usage_stats[name] = UsageStatistics.from_dict(stats)
                print(f"   已加载历史统计数据")
            except Exception as e:
                print(f"   ⚠️ 加载历史统计失败：{e}")
    
    def _save_statistics(self):
        """保存统计"""
        stats_file = Path(self.config.get('statistics', {}).get('log_file', './logs/data_source_stats.json'))
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'usage_stats': {name: stats.to_dict() for name, stats in self.usage_stats.items()},
            'health_metrics': {name: metrics.to_dict() for name, metrics in self.health_metrics.items()}
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_data_source(self, name: str, priority: int, 
                            token_env: Optional[str] = None,
                            rate_limit: Optional[Dict[str, int]] = None,
                            endpoints: Optional[List[str]] = None):
        """注册数据源"""
        with self._lock:
            config = DataSourceConfig(
                name=name,
                priority=priority,
                enabled=True,
                token_env=token_env,
                rate_limit=rate_limit or {},
                endpoints=endpoints or []
            )
            self.data_sources[name] = config
            self.health_metrics[name] = HealthMetrics()
            self.usage_stats[name] = UsageStatistics()
            self.status[name] = DataSourceStatus.UNKNOWN
            self.response_time_history[name] = []
            self.rate_limit_tracker[name] = []
            print(f"✅ 已注册数据源：{name} (priority={priority})")
    
    def calculate_health_score(self, name: str) -> float:
        """
        计算数据源健康度评分 (0-100)
        
        评分权重：
        - 成功率：40%
        - 响应时间：30%
        - 数据完整性：20%
        - 限流情况：10%
        """
        if name not in self.health_metrics:
            return 0.0
        
        metrics = self.health_metrics[name]
        
        # 成功率评分 (0-40)
        success_score = metrics.success_rate * 40
        
        # 响应时间评分 (0-30)
        # 响应时间越短，得分越高
        response_threshold = self.config.get('health_check', {}).get('response_time_threshold_ms', 5000)
        if metrics.response_time_ms <= 0:
            response_score = 30
        elif metrics.response_time_ms >= response_threshold:
            response_score = 0
        else:
            response_score = 30 * (1 - metrics.response_time_ms / response_threshold)
        
        # 数据完整性评分 (0-20)
        completeness_score = metrics.data_completeness * 20
        
        # 限流评分 (0-10)
        rate_limit_score = 0 if metrics.rate_limit_hit else 10
        
        # 连续失败惩罚
        failure_penalty = min(metrics.consecutive_failures * 5, 25)
        
        total_score = max(0, success_score + response_score + completeness_score + rate_limit_score - failure_penalty)
        return min(100, total_score)
    
    def update_health_metrics(self, name: str, 
                             response_time_ms: float,
                             success: bool,
                             data_completeness: float = 1.0,
                             rate_limit_hit: bool = False,
                             error: Optional[str] = None):
        """更新健康度指标"""
        with self._lock:
            if name not in self.health_metrics:
                return
            
            metrics = self.health_metrics[name]
            
            # 更新响应时间（使用滑动平均）
            self.response_time_history[name].append(response_time_ms)
            if len(self.response_time_history[name]) > 100:
                self.response_time_history[name].pop(0)
            metrics.response_time_ms = statistics.median(self.response_time_history[name])
            
            # 更新成功率
            if success:
                metrics.consecutive_failures = 0
                metrics.last_success_time = datetime.now().isoformat()
                # 指数移动平均更新成功率
                metrics.success_rate = 0.9 * metrics.success_rate + 0.1 * 1.0
            else:
                metrics.consecutive_failures += 1
                metrics.last_error = error
                metrics.success_rate = 0.9 * metrics.success_rate + 0.1 * 0.0
            
            # 更新数据完整性
            metrics.data_completeness = data_completeness
            
            # 更新限流状态
            metrics.rate_limit_hit = rate_limit_hit
            if rate_limit_hit:
                self.rate_limit_tracker[name].append(time.time())
            
            metrics.last_check_time = datetime.now().isoformat()
            
            # 更新状态
            health_score = self.calculate_health_score(name)
            if health_score >= 80:
                self.status[name] = DataSourceStatus.HEALTHY
            elif health_score >= 50:
                self.status[name] = DataSourceStatus.DEGRADED
            else:
                self.status[name] = DataSourceStatus.UNHEALTHY
    
    def update_usage_stats(self, name: str, 
                          response_time_ms: float,
                          success: bool,
                          rate_limit_hit: bool = False):
        """更新使用统计"""
        with self._lock:
            if name not in self.usage_stats:
                return
            
            stats = self.usage_stats[name]
            stats.total_requests += 1
            stats.total_response_time_ms += response_time_ms
            stats.last_used_time = datetime.now().isoformat()
            
            if success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
            
            if rate_limit_hit:
                stats.rate_limit_hits += 1
    
    def select_best_data_source(self, endpoint: Optional[str] = None) -> Optional[str]:
        """
        智能选择最优数据源
        
        选择策略：
        1. 过滤启用的数据源
        2. 过滤健康状态 >= DEGRADED 的数据源
        3. 检查限流状态
        4. 按优先级和健康度综合评分排序
        5. 返回最优数据源
        """
        with self._lock:
            candidates = []
            
            for name, config in self.data_sources.items():
                if not config.enabled:
                    continue
                
                status = self.status.get(name, DataSourceStatus.UNKNOWN)
                if status == DataSourceStatus.UNHEALTHY:
                    continue
                
                # 检查限流
                if self._is_rate_limited(name):
                    continue
                
                # 计算综合评分
                health_score = self.calculate_health_score(name)
                priority_score = 100 - config.priority * 10  # 优先级越高，得分越高
                
                # 综合评分 = 健康度 * 0.7 + 优先级 * 0.3
                total_score = health_score * 0.7 + max(0, priority_score) * 0.3
                
                candidates.append((name, total_score, config.priority, health_score))
            
            if not candidates:
                # 所有数据源都不可用，返回优先级最高的（即使不健康）
                enabled_sources = [(name, config.priority) 
                                  for name, config in self.data_sources.items() 
                                  if config.enabled]
                if enabled_sources:
                    enabled_sources.sort(key=lambda x: x[1])
                    return enabled_sources[0][0]
                return None
            
            # 按综合评分排序
            candidates.sort(key=lambda x: (-x[1], x[2]))
            
            best = candidates[0]
            print(f"📊 选择数据源：{best[0]} (score={best[1]:.1f}, health={best[3]:.1f}, priority={best[2]})")
            return best[0]
    
    def _is_rate_limited(self, name: str) -> bool:
        """检查是否触发限流"""
        if name not in self.data_sources:
            return False
        
        config = self.data_sources[name]
        rate_limit = config.rate_limit
        
        if not rate_limit:
            return False
        
        now = time.time()
        timestamps = self.rate_limit_tracker.get(name, [])
        
        # 检查每分钟限流
        rpm_limit = rate_limit.get('requests_per_minute', 0)
        if rpm_limit > 0:
            recent_1min = [t for t in timestamps if now - t < 60]
            if len(recent_1min) >= rpm_limit:
                return True
        
        # 检查每天限流
        rpd_limit = rate_limit.get('requests_per_day', 0)
        if rpd_limit > 0:
            recent_1day = [t for t in timestamps if now - t < 86400]
            if len(recent_1day) >= rpd_limit:
                return True
        
        return False
    
    def record_request(self, name: str):
        """记录请求（用于限流跟踪）"""
        with self._lock:
            if name in self.rate_limit_tracker:
                self.rate_limit_tracker[name].append(time.time())
                # 清理旧记录（保留 24 小时）
                now = time.time()
                self.rate_limit_tracker[name] = [t for t in self.rate_limit_tracker[name] if now - t < 86400]
    
    def get_data_source(self, endpoint: Optional[str] = None) -> Optional[str]:
        """
        获取数据源（带自动切换）
        
        这是主入口方法，返回最优数据源名称
        """
        return self.select_best_data_source(endpoint)
    
    def check_rate_limit(self, name: str) -> bool:
        """检查数据源是否可用（未触发限流）"""
        return not self._is_rate_limited(name)
    
    def get_statistics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            if name:
                if name not in self.usage_stats:
                    return {}
                stats = self.usage_stats[name]
                metrics = self.health_metrics.get(name, HealthMetrics())
                usage_dict = stats.to_dict()
                usage_dict['success_rate'] = stats.success_rate
                usage_dict['avg_response_time_ms'] = stats.avg_response_time_ms
                return {
                    'name': name,
                    'status': self.status.get(name, DataSourceStatus.UNKNOWN).value,
                    'health_score': self.calculate_health_score(name),
                    'usage': usage_dict,
                    'metrics': metrics.to_dict()
                }
            else:
                return {
                    name: self.get_statistics(name)
                    for name in self.data_sources.keys()
                }
    
    def start_health_check(self, interval: Optional[int] = None):
        """启动健康检查线程"""
        if interval is None:
            interval = self.config.get('health_check_interval', 300)
        
        if self._health_check_thread and self._health_check_thread.is_alive():
            print(f"⚠️ 健康检查线程已在运行")
            return
        
        self._stop_health_check = False
        self._health_check_thread = threading.Thread(target=self._health_check_loop, args=(interval,), daemon=True)
        self._health_check_thread.start()
        print(f"✅ 健康检查已启动 (interval={interval}s)")
    
    def stop_health_check(self):
        """停止健康检查线程"""
        self._stop_health_check = True
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        print(f"✅ 健康检查已停止")
    
    def _health_check_loop(self, interval: int):
        """健康检查循环"""
        while not self._stop_health_check:
            try:
                self._run_health_check()
                self._save_statistics()
            except Exception as e:
                print(f"❌ 健康检查异常：{e}")
            
            time.sleep(interval)
    
    def _run_health_check(self):
        """
        P0-4 修复：执行健康检查
        
        实际调用数据源 API 测试连通性和响应时间
        """
        print(f"\n🔍 执行数据源健康检查 ({datetime.now().strftime('%H:%M:%S')})")
        
        for name in self.data_sources.keys():
            try:
                health = self._check_single_source_health(name)
                
                # 更新健康度指标
                self.update_health_metrics(
                    name=name,
                    response_time_ms=health.get('response_time', 0),
                    success=health.get('success', False),
                    data_completeness=health.get('completeness', 1.0),
                    rate_limit_hit=health.get('rate_limited', False),
                    error=health.get('error')
                )
                
                # 主数据源故障时发送 Slack 通知
                if not health.get('success', False) and name == 'tushare':
                    self._send_slack_alert(name, health)
                
            except Exception as e:
                print(f"   ❌ {name}: 健康检查异常 - {e}")
                self.update_health_metrics(
                    name=name,
                    response_time_ms=0,
                    success=False,
                    error=str(e)
                )
        
        # 保存统计
        self._save_statistics()
    
    def _check_single_source_health(self, name: str) -> dict:
        """
        P0-4 新增：检查单个数据源健康状态
        
        执行轻量级 API 调用测试连通性和响应时间
        """
        import time
        
        start = time.time()
        try:
            if name == 'tushare':
                # 测试 Tushare 连通性（获取上证指数）
                import tushare as ts
                ts.set_token(os.getenv('TUSHARE_TOKEN', ''))
                pro = ts.pro_api()
                df = pro.index_daily(ts_code='000001.SH', start_date='20260316', end_date='20260316')
                
                return {
                    'success': len(df) > 0,
                    'response_time': (time.time() - start) * 1000,
                    'completeness': 1.0 if len(df) > 0 else 0.0
                }
            
            elif name == 'akshare':
                # 测试 Akshare 连通性
                import akshare as ak
                df = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                                       start_date="20260316", end_date="20260316")
                
                return {
                    'success': len(df) > 0,
                    'response_time': (time.time() - start) * 1000,
                    'completeness': 1.0 if len(df) > 0 else 0.0
                }
            
            elif name == 'sina':
                # 测试 Sina 连通性（简单 HTTP 请求）
                import requests
                response = requests.get('http://hq.sinajs.cn/list=sh000001', timeout=5)
                
                return {
                    'success': response.status_code == 200,
                    'response_time': (time.time() - start) * 1000,
                    'completeness': 1.0 if response.status_code == 200 else 0.0
                }
            
            else:
                return {'success': False, 'response_time': 0, 'error': 'Unknown data source'}
        
        except Exception as e:
            return {
                'success': False,
                'response_time': (time.time() - start) * 1000,
                'error': str(e)
            }
    
    def _send_slack_alert(self, source_name: str, health: dict):
        """
        P0-4 新增：主数据源故障时发送 Slack 通知
        """
        try:
            from alert_notifier import AlertNotifier
            notifier = AlertNotifier()
            
            error_msg = health.get('error', '未知错误')
            notifier.send_alert(
                notifier.create_alert(
                    severity='P1',
                    agent='data_source_manager',
                    error=f'数据源 {source_name} 健康检查失败：{error_msg}',
                    action_taken='已切换到备用数据源',
                    estimated_fix='自动恢复'
                )
            )
            print(f"  📢 已发送 Slack 告警：{source_name} 故障")
        except Exception as e:
            print(f"  ⚠️  Slack 告警发送失败：{e}")
    
    def print_status(self):
        """打印数据源状态"""
        print("\n" + "="*70)
        print("  数据源状态")
        print("="*70)
        print(f"{'数据源':<15} {'状态':<12} {'优先级':<8} {'健康分':<10} {'成功率':<10} {'响应时间':<12}")
        print("-"*70)
        
        for name in sorted(self.data_sources.keys(), key=lambda x: self.data_sources[x].priority):
            status = self.status.get(name, DataSourceStatus.UNKNOWN)
            config = self.data_sources[name]
            metrics = self.health_metrics.get(name, HealthMetrics())
            stats = self.usage_stats.get(name, UsageStatistics())
            
            print(f"{name:<15} {status.value:<12} {config.priority:<8} "
                  f"{self.calculate_health_score(name):<10.1f} {metrics.success_rate:<10.2f} "
                  f"{metrics.response_time_ms:<12.1f}ms")
        
        print("="*70)


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 初始化
    manager = DataSourceManager('./data_source_config.json')
    
    # 打印状态
    manager.print_status()
    
    # 选择数据源
    best = manager.get_data_source()
    print(f"\n✅ 最优数据源：{best}")
    
    # 模拟请求
    if best:
        start = time.time()
        # 模拟请求逻辑
        time.sleep(0.1)
        response_time = (time.time() - start) * 1000
        
        manager.record_request(best)
        manager.update_health_metrics(best, response_time, success=True)
        manager.update_usage_stats(best, response_time, success=True)
    
    # 查看统计
    stats = manager.get_statistics()
    print(f"\n📊 使用统计:")
    for name, data in stats.items():
        print(f"  {name}: {data['usage']['total_requests']} requests, "
              f"success_rate={data['usage']['success_rate']:.2f}")
    
    # 启动健康检查
    manager.start_health_check(interval=60)
    
    # 保持运行
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        manager.stop_health_check()
