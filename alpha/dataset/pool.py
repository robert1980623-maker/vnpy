"""
股票池管理模块

提供股票池的创建、管理和查询功能：
- 指数成分股自动获取
- 自定义股票池管理
- 股票池交集/并集运算
"""

from typing import List, Set, Optional, Dict, Union
from datetime import datetime, date
import json
from pathlib import Path


class StockPool:
    """
    股票池基类
    
    提供股票池的基本操作接口
    """
    
    def __init__(self, name: str = "default"):
        """
        初始化股票池
        
        Args:
            name: 股票池名称
        """
        self.name = name
        self._stocks: Set[str] = set()
        self._metadata: Dict = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "description": ""
        }
    
    def add(self, vt_symbol: Union[str, List[str]]) -> None:
        """
        添加股票到股票池
        
        Args:
            vt_symbol: 股票代码或代码列表
        """
        if isinstance(vt_symbol, str):
            self._stocks.add(vt_symbol)
        else:
            self._stocks.update(vt_symbol)
        self._metadata["updated_at"] = datetime.now().isoformat()
    
    def remove(self, vt_symbol: Union[str, List[str]]) -> None:
        """
        从股票池移除股票
        
        Args:
            vt_symbol: 股票代码或代码列表
        """
        if isinstance(vt_symbol, str):
            self._stocks.discard(vt_symbol)
        else:
            self._stocks.difference_update(vt_symbol)
        self._metadata["updated_at"] = datetime.now().isoformat()
    
    def contains(self, vt_symbol: str) -> bool:
        """
        检查股票是否在股票池中
        
        Args:
            vt_symbol: 股票代码
            
        Returns:
            bool: 是否在股票池中
        """
        return vt_symbol in self._stocks
    
    def get_stocks(self) -> List[str]:
        """
        获取股票池中的所有股票
        
        Returns:
            List[str]: 股票代码列表
        """
        return sorted(list(self._stocks))
    
    def count(self) -> int:
        """
        获取股票池中的股票数量
        
        Returns:
            int: 股票数量
        """
        return len(self._stocks)
    
    def clear(self) -> None:
        """清空股票池"""
        self._stocks.clear()
        self._metadata["updated_at"] = datetime.now().isoformat()
    
    def update_metadata(self, **kwargs) -> None:
        """
        更新股票池元数据
        
        Args:
            **kwargs: 元数据键值对
        """
        self._metadata.update(kwargs)
        self._metadata["updated_at"] = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """
        转换为字典
        
        Returns:
            Dict: 股票池字典表示
        """
        return {
            "name": self.name,
            "stocks": self.get_stocks(),
            "count": self.count(),
            "metadata": self._metadata
        }
    
    def save(self, filepath: Union[str, Path]) -> None:
        """
        保存股票池到文件
        
        Args:
            filepath: 保存路径
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "StockPool":
        """
        从文件加载股票池
        
        Args:
            filepath: 文件路径
            
        Returns:
            StockPool: 加载的股票池
        """
        filepath = Path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pool = cls(name=data["name"])
        pool._stocks = set(data["stocks"])
        pool._metadata = data.get("metadata", {})
        return pool
    
    def __len__(self) -> int:
        return self.count()
    
    def __iter__(self):
        return iter(self.get_stocks())
    
    def __contains__(self, vt_symbol: str) -> bool:
        return self.contains(vt_symbol)
    
    def __repr__(self) -> str:
        return f"StockPool(name='{self.name}', count={self.count()})"


class IndexStockPool(StockPool):
    """
    指数成分股股票池
    
    自动获取和维护指数成分股
    """
    
    # 常见指数代码映射
    INDEX_MAP = {
        "000300.SH": "沪深 300",
        "000016.SH": "上证 50",
        "000905.SH": "中证 500",
        "000852.SH": "中证 1000",
        "399006.SZ": "创业板指",
        "000001.SH": "上证指数",
        "399001.SZ": "深证成指",
    }
    
    def __init__(self, index_code: str, name: Optional[str] = None):
        """
        初始化指数成分股股票池
        
        Args:
            index_code: 指数代码，如 "000300.SH"
            name: 股票池名称（可选，默认使用指数名称）
        """
        if name is None:
            name = self.INDEX_MAP.get(index_code, index_code)
        
        super().__init__(name=name)
        self.index_code = index_code
        self._metadata["type"] = "index"
        self._metadata["index_code"] = index_code
        self._metadata["index_name"] = self.INDEX_MAP.get(index_code, "未知指数")
    
    def update_components(self, components: List[str]) -> None:
        """
        更新指数成分股
        
        Args:
            components: 成分股列表
        """
        self.clear()
        self.add(components)
        self._metadata["last_updated"] = datetime.now().isoformat()
    
    def get_index_info(self) -> Dict:
        """
        获取指数信息
        
        Returns:
            Dict: 指数信息字典
        """
        return {
            "index_code": self.index_code,
            "index_name": self._metadata.get("index_name", ""),
            "component_count": self.count(),
            "last_updated": self._metadata.get("last_updated", "")
        }


class CustomStockPool(StockPool):
    """
    自定义股票池
    
    支持灵活的股票池组合运算
    """
    
    def __init__(self, name: str = "custom"):
        """
        初始化自定义股票池
        
        Args:
            name: 股票池名称
        """
        super().__init__(name=name)
        self._metadata["type"] = "custom"
        self._sub_pools: Dict[str, StockPool] = {}
    
    def add_sub_pool(self, name: str, pool: StockPool) -> None:
        """
        添加子股票池
        
        Args:
            name: 子池名称
            pool: 子股票池对象
        """
        self._sub_pools[name] = pool
    
    def remove_sub_pool(self, name: str) -> Optional[StockPool]:
        """
        移除子股票池
        
        Args:
            name: 子池名称
            
        Returns:
            StockPool: 被移除的子池，不存在则返回 None
        """
        return self._sub_pools.pop(name, None)
    
    def union(self, *pool_names: str) -> List[str]:
        """
        计算多个子池的并集
        
        Args:
            *pool_names: 子池名称列表
            
        Returns:
            List[str]: 并集股票列表
        """
        result: Set[str] = set()
        for name in pool_names:
            if name in self._sub_pools:
                result.update(self._sub_pools[name]._stocks)
        return sorted(list(result))
    
    def intersection(self, *pool_names: str) -> List[str]:
        """
        计算多个子池的交集
        
        Args:
            *pool_names: 子池名称列表
            
        Returns:
            List[str]: 交集股票列表
        """
        if not pool_names:
            return []
        
        result: Set[str] = set(self._sub_pools.get(pool_names[0], StockPool())._stocks)
        for name in pool_names[1:]:
            if name in self._sub_pools:
                result.intersection_update(self._sub_pools[name]._stocks)
            else:
                return []
        return sorted(list(result))
    
    def difference(self, pool_name1: str, pool_name2: str) -> List[str]:
        """
        计算两个子池的差集
        
        Args:
            pool_name1: 第一个子池名称
            pool_name2: 第二个子池名称
            
        Returns:
            List[str]: 差集股票列表（在 pool1 但不在 pool2）
        """
        if pool_name1 not in self._sub_pools:
            return []
        if pool_name2 not in self._sub_pools:
            return self._sub_pools[pool_name1].get_stocks()
        
        result = self._sub_pools[pool_name1]._stocks - self._sub_pools[pool_name2]._stocks
        return sorted(list(result))
    
    def get_sub_pool_names(self) -> List[str]:
        """
        获取所有子池名称
        
        Returns:
            List[str]: 子池名称列表
        """
        return list(self._sub_pools.keys())


def create_index_pool(index_code: str, components: Optional[List[str]] = None) -> IndexStockPool:
    """
    创建指数成分股股票池
    
    Args:
        index_code: 指数代码
        components: 成分股列表（可选）
        
    Returns:
        IndexStockPool: 创建的股票池
    """
    pool = IndexStockPool(index_code)
    if components:
        pool.update_components(components)
    return pool


def create_custom_pool(name: str = "custom") -> CustomStockPool:
    """
    创建自定义股票池
    
    Args:
        name: 股票池名称
        
    Returns:
        CustomStockPool: 创建的股票池
    """
    return CustomStockPool(name=name)
