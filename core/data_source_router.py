#!/usr/bin/env python3
"""
智能数据源路由器

功能:
- 健康度评分
- 智能选择最优数据源
- 成本优化 (Tushare 积分消耗最小化)
- 限流检测
"""

import os
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DataSourceHealth:
    """数据源健康度"""
    name: str
    status: DataSourceStatus = DataSourceStatus.UNKNOWN
    success_rate: float = 1.0
    avg_response_ms: float = 0.0
    consecutive_failures: int = 0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    rate_limited: bool = False


@dataclass
class DataSourceCost:
    """数据源成本"""
    name: str
    cost_per_request: int = 0  # Tushare 积分
    daily_limit: int = 0  # 每日限制


class DataSourceRouter:
    """智能数据源路由器"""
    
    def __init__(self):
        self.health: Dict[str, DataSourceHealth] = {
            'tushare': DataSourceHealth(name='tushare'),
            'akshare': DataSourceHealth(name='akshare'),
            'sina': DataSourceHealth(name='sina'),
        }
        
        # 成本配置
        self.cost_config: Dict[str, DataSourceCost] = {
            'tushare': DataSourceCost(
                name='tushare',
                cost_per_request=1,  # 日线数据 1 积分
                daily_limit=5000  # 每日 5000 积分
            ),
            'akshare': DataSourceCost(name='akshare', cost_per_request=0),
            'sina': DataSourceCost(name='sina', cost_per_request=0),
        }
        
        # 优先级配置
        self.priority = {
            'tushare': 1,  # 最高优先级
            'akshare': 2,
            'sina': 3,
        }
        
        # 使用统计
        self.usage_today: Dict[str, int] = {
            'tushare': 0,
            'akshare': 0,
            'sina': 0,
        }
        
        # 缓存状态文件
        self.state_file = Path('./cache/data_source_state.json')
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 恢复使用统计
                self.usage_today = data.get('usage_today', self.usage_today)
            except:
                pass
    
    def _save_state(self):
        """保存状态"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'usage_today': self.usage_today,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def record_success(self, source: str, response_ms: float):
        """记录成功请求"""
        if source not in self.health:
            return
        
        health = self.health[source]
        health.success_rate = 0.9 * health.success_rate + 0.1 * 1.0
        health.consecutive_failures = 0
        health.last_success = time.strftime('%Y-%m-%d %H:%M:%S')
        health.avg_response_ms = (
            0.9 * health.avg_response_ms + 0.1 * response_ms
        )
        
        # 更新状态
        score = self._calculate_health_score(source)
        health.status = (
            DataSourceStatus.HEALTHY if score >= 80 else
            DataSourceStatus.DEGRADED if score >= 50 else
            DataSourceStatus.UNHEALTHY
        )
        
        self._save_state()
    
    def record_failure(self, source: str, rate_limited: bool = False):
        """记录失败请求"""
        if source not in self.health:
            return
        
        health = self.health[source]
        health.success_rate = 0.9 * health.success_rate + 0.1 * 0.0
        health.consecutive_failures += 1
        health.last_failure = time.strftime('%Y-%m-%d %H:%M:%S')
        health.rate_limited = rate_limited
        
        # 更新状态
        score = self._calculate_health_score(source)
        health.status = (
            DataSourceStatus.HEALTHY if score >= 80 else
            DataSourceStatus.DEGRADED if score >= 50 else
            DataSourceStatus.UNHEALTHY
        )
        
        self._save_state()
    
    def _calculate_health_score(self, source: str) -> float:
        """计算健康度评分 (0-100)"""
        if source not in self.health:
            return 0.0
        
        health = self.health[source]
        
        # 成功率 (40 分)
        success_score = health.success_rate * 40
        
        # 响应时间 (30 分) - 越短越好
        if health.avg_response_ms <= 0:
            response_score = 30
        elif health.avg_response_ms >= 5000:
            response_score = 0
        else:
            response_score = 30 * (1 - health.avg_response_ms / 5000)
        
        # 连续失败惩罚 (最高扣 20 分)
        failure_penalty = min(health.consecutive_failures * 5, 20)
        
        # 限流惩罚 (扣 10 分)
        rate_limit_penalty = 10 if health.rate_limited else 0
        
        return max(0, success_score + response_score - failure_penalty - rate_limit_penalty)
    
    def select_best_source(
        self,
        data_type: str = 'daily',
        preferred: Optional[str] = None
    ) -> str:
        """
        选择最优数据源
        
        Args:
            data_type: 数据类型 (daily, fundamental, etc.)
            preferred: 首选数据源 (可选)
        
        Returns:
            最优数据源名称
        """
        candidates = []
        
        for name in ['tushare', 'akshare', 'sina']:
            health = self.health[name]
            
            # 跳过不健康的数据源
            if health.status == DataSourceStatus.UNHEALTHY:
                continue
            
            # 跳过限流的数据源
            if health.rate_limited:
                continue
            
            # 检查 Tushare 积分限制
            if name == 'tushare':
                cost = self.cost_config[name].cost_per_request
                if self.usage_today[name] + cost > self.cost_config[name].daily_limit:
                    continue
            
            # 计算综合评分
            health_score = self._calculate_health_score(name)
            priority_score = (4 - self.priority[name]) * 25  # 优先级越高分数越高
            cost_score = 100 - self.cost_config[name].cost_per_request * 10
            
            # 综合评分 = 健康度*50% + 优先级*30% + 成本*20%
            total_score = (
                health_score * 0.5 +
                priority_score * 0.3 +
                cost_score * 0.2
            )
            
            # 首选数据源加分
            if preferred and name == preferred:
                total_score += 20
            
            candidates.append((name, total_score))
        
        if not candidates:
            # 所有数据源都不可用，返回优先级最高的
            return min(self.priority, key=self.priority.get)
        
        # 返回评分最高的
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]
    
    def record_usage(self, source: str, count: int = 1):
        """记录使用次数"""
        if source in self.usage_today:
            self.usage_today[source] += count
            self._save_state()
    
    def get_usage_summary(self) -> Dict:
        """获取使用摘要"""
        return {
            'tushare': {
                'used': self.usage_today['tushare'],
                'limit': self.cost_config['tushare'].daily_limit,
                'remaining': self.cost_config['tushare'].daily_limit - self.usage_today['tushare'],
            },
            'akshare': {
                'used': self.usage_today['akshare'],
            },
        }
    
    def print_status(self):
        """打印状态"""
        print("=" * 60)
        print("📊 数据源状态")
        print("=" * 60)
        
        for name in ['tushare', 'akshare', 'sina']:
            health = self.health[name]
            score = self._calculate_health_score(name)
            status_icon = {
                DataSourceStatus.HEALTHY: '✅',
                DataSourceStatus.DEGRADED: '⚠️',
                DataSourceStatus.UNHEALTHY: '❌',
                DataSourceStatus.UNKNOWN: '❓',
            }[health.status]
            
            print(f"\n{status_icon} {name.upper()}")
            print(f"  健康度：{score:.0f}/100")
            print(f"  成功率：{health.success_rate*100:.1f}%")
            print(f"  响应时间：{health.avg_response_ms:.0f}ms")
            print(f"  连续失败：{health.consecutive_failures}")
            print(f"  限流状态：{'是' if health.rate_limited else '否'}")
        
        print("\n" + "=" * 60)
        print("📈 今日使用统计")
        print("=" * 60)
        usage = self.get_usage_summary()
        print(f"Tushare: {usage['tushare']['used']}/{usage['tushare']['limit']} (剩余 {usage['tushare']['remaining']})")
        print(f"AKShare: {usage['akshare']['used']} 次")


# 单例模式
_router: Optional[DataSourceRouter] = None

def get_router() -> DataSourceRouter:
    """获取路由器单例"""
    global _router
    if _router is None:
        _router = DataSourceRouter()
    return _router


def select_source(data_type: str = 'daily', preferred: str = None) -> str:
    """选择最优数据源"""
    return get_router().select_best_source(data_type, preferred)
