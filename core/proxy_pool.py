#!/usr/bin/env python3
"""
代理池管理器

功能:
- 多代理健康检查
- 自动选择最快可用代理
- 定期更新代理列表
"""

import os
import time
import requests
from typing import Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ProxyInfo:
    """代理信息"""
    address: str
    latency_ms: float = 0.0
    healthy: bool = False
    last_check: Optional[str] = None
    fail_count: int = 0


class ProxyPool:
    """代理池管理器"""
    
    def __init__(self, test_url: str = "http://www.baidu.com", timeout: int = 5):
        self.test_url = test_url
        self.timeout = timeout
        self.proxies: Dict[str, ProxyInfo] = {}
        self.cache_file = Path('./cache/proxy_pool.json')
        
        # 从配置加载代理列表
        self._load_proxies()
    
    def _load_proxies(self):
        """加载代理列表"""
        # 1. 从.env 加载
        proxy = os.getenv('AKSHARE_PROXY')
        if proxy:
            self.proxies[proxy] = ProxyInfo(address=proxy)
        
        # 2. 内置备用代理列表
        backup_proxies = [
            "123.57.214.190:80",
            "114.215.176.116:80",
            "121.196.218.190:80",
        ]
        
        for p in backup_proxies:
            if p not in self.proxies:
                self.proxies[p] = ProxyInfo(address=p)
        
        # 3. 从缓存加载历史数据
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for addr, info in data.items():
                    if addr in self.proxies:
                        self.proxies[addr].latency_ms = info.get('latency_ms', 0)
                        self.proxies[addr].healthy = info.get('healthy', False)
            except:
                pass
    
    def _save_cache(self):
        """保存缓存"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            addr: {
                'latency_ms': info.latency_ms,
                'healthy': info.healthy,
                'last_check': info.last_check,
                'fail_count': info.fail_count
            }
            for addr, info in self.proxies.items()
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _check_proxy(self, proxy: str) -> tuple[bool, float]:
        """检查代理健康度"""
        try:
            start = time.time()
            response = requests.get(
                self.test_url,
                proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'},
                timeout=self.timeout
            )
            latency = (time.time() - start) * 1000
            return response.status_code == 200, latency
        except:
            return False, float('inf')
    
    def health_check(self) -> Dict[str, ProxyInfo]:
        """执行健康检查"""
        print("🔍 代理健康检查...")
        
        for addr, info in self.proxies.items():
            healthy, latency = self._check_proxy(addr)
            info.healthy = healthy
            info.latency_ms = latency
            info.last_check = time.strftime('%Y-%m-%d %H:%M:%S')
            
            if healthy:
                info.fail_count = 0
                print(f"  ✅ {addr}: {latency:.0f}ms")
            else:
                info.fail_count += 1
                print(f"  ❌ {addr}: 失败 (累计{info.fail_count}次)")
        
        self._save_cache()
        return self.proxies
    
    def get_healthy_proxy(self) -> Optional[str]:
        """获取健康代理"""
        # 先检查是否有健康代理
        healthy = [
            (addr, info) for addr, info in self.proxies.items()
            if info.healthy
        ]
        
        if healthy:
            # 按延迟排序，返回最快的
            healthy.sort(key=lambda x: x[1].latency_ms)
            return healthy[0][0]
        
        # 如果没有健康代理，执行一次健康检查
        self.health_check()
        
        # 再次尝试
        healthy = [
            (addr, info) for addr, info in self.proxies.items()
            if info.healthy
        ]
        
        if healthy:
            healthy.sort(key=lambda x: x[1].latency_ms)
            return healthy[0][0]
        
        return None
    
    def install_proxy(self, proxy: Optional[str] = None):
        """安装代理到环境变量"""
        if proxy is None:
            proxy = self.get_healthy_proxy()
        
        if proxy:
            os.environ['HTTP_PROXY'] = f'http://{proxy}'
            os.environ['HTTPS_PROXY'] = f'http://{proxy}'
            print(f"✅ 代理已安装：{proxy}")
        else:
            # 清除代理
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            print("✅ 使用直连模式")


# 单例模式
_proxy_pool: Optional[ProxyPool] = None

def get_proxy_pool() -> ProxyPool:
    """获取代理池单例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool


def install_best_proxy():
    """安装最佳代理"""
    pool = get_proxy_pool()
    pool.install_proxy()
