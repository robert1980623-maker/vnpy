"""
vn.py 基础设施配置管理
提供基础设施的抽象层和故障转移机制
"""
import redis
from abc import ABC, abstractmethod
from typing import Optional, Any
import logging

class CacheInterface(ABC):
    """缓存接口抽象类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        pass

    @abstractmethod
    def publish(self, channel: str, message: str) -> int:
        pass

class RedisCache(CacheInterface):
    """Redis缓存实现"""

    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self.client.ping()
            self.available = True
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}")
            self.available = False

    def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            return self.client.get(key)
        except Exception:
            return None

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        if not self.available:
            return False
        try:
            return self.client.set(key, value, ex=expire)
        except Exception:
            return False

    def publish(self, channel: str, message: str) -> int:
        if not self.available:
            return 0
        try:
            return self.client.publish(channel, message)
        except Exception:
            return 0

class MemoryCache(CacheInterface):
    """内存缓存实现（Redis不可用时的降级方案）"""

    def __init__(self):
        self._data = {}
        self.available = True

    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        self._data[key] = value
        return True

    def publish(self, channel: str, message: str) -> int:
        print(f"[Memory Cache] Message published to {channel}: {message}")
        return 1

class CacheFactory:
    """缓存工厂类，提供合适的缓存实例"""

    @staticmethod
    def create_cache(cache_type: str = 'auto'):
        if cache_type == 'auto':
            redis_cache = RedisCache()
            if redis_cache.available:
                logging.info("Using Redis cache")
                return redis_cache
            else:
                logging.info("Redis unavailable, using memory cache")
                return MemoryCache()
        elif cache_type == 'memory':
            return MemoryCache()
        return MemoryCache()

# 全局缓存实例
cache_instance = CacheFactory.create_cache()
