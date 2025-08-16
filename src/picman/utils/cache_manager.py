"""
缓存管理器 - 提供多级缓存支持
"""

import time
import threading
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Callable, TypeVar, Generic
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from collections import OrderedDict
import weakref

T = TypeVar('T')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.created_at


class LRUCache(Generic[T]):
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.logger = logger
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            # 更新访问信息
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            
            self._hits += 1
            return entry.value
    
    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        with self._lock:
            current_time = time.time()
            
            # 如果key已存在，更新值
            if key in self._cache:
                entry = self._cache[key]
                entry.value = value
                entry.created_at = current_time
                entry.last_accessed = current_time
                entry.ttl = ttl or self.default_ttl
                self._cache.move_to_end(key)
                return
            
            # 检查是否需要清理空间
            while len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # 添加新条目
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                ttl=ttl or self.default_ttl
            )
            
            self._cache[key] = entry
    
    def _evict_lru(self) -> None:
        """清理最少使用的条目"""
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            self._evictions += 1
            self.logger.debug("Cache entry evicted: %s", key)
    
    def remove(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.debug("Expired cache entries cleaned: %d", len(expired_keys))
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
                "total_requests": total_requests
            }


class DiskCache:
    """磁盘缓存实现"""
    
    def __init__(self, cache_dir: str, max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._lock = threading.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用哈希避免文件名过长或包含特殊字符
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # 检查是否过期
            if 'ttl' in data and data['ttl'] is not None:
                if time.time() - data['created_at'] > data['ttl']:
                    cache_path.unlink(missing_ok=True)
                    return None
            
            # 更新访问时间
            data['last_accessed'] = time.time()
            data['access_count'] = data.get('access_count', 0) + 1
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            return data['value']
            
        except Exception as e:
            self.logger.warning("Failed to read cache file %s: %s", key, str(e))
            cache_path.unlink(missing_ok=True)
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        cache_path = self._get_cache_path(key)
        
        data = {
            'value': value,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'access_count': 1,
            'ttl': ttl
        }
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            # 检查磁盘使用量
            self._cleanup_if_needed()
            
        except Exception as e:
            self.logger.error("Failed to write cache file %s: %s", key, str(e))
    
    def _cleanup_if_needed(self) -> None:
        """如果需要则清理磁盘缓存"""
        with self._lock:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            max_size_bytes = self.max_size_mb * 1024 * 1024
            
            if total_size <= max_size_bytes:
                return
            
            # 获取所有缓存文件及其访问时间
            cache_files = []
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    cache_files.append((
                        cache_file,
                        data.get('last_accessed', 0),
                        cache_file.stat().st_size
                    ))
                except Exception:
                    # 损坏的文件直接删除
                    cache_file.unlink(missing_ok=True)
            
            # 按访问时间排序，删除最旧的文件
            cache_files.sort(key=lambda x: x[1])
            
            current_size = total_size
            target_size = max_size_bytes * 0.8  # 清理到80%
            
            for cache_file, _, file_size in cache_files:
                if current_size <= target_size:
                    break
                
                cache_file.unlink(missing_ok=True)
                current_size -= file_size
            
            self.logger.info("Disk cache cleaned up: freed_mb=%s", (total_size - current_size) / 1024 / 1024)
    
    def clear(self) -> None:
        """清空磁盘缓存"""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
            
            self.logger.info("Disk cache cleared")


class CacheManager:
    """多级缓存管理器"""
    
    def __init__(self, 
                 memory_cache_size: int = 1000,
                 disk_cache_dir: Optional[str] = None,
                 disk_cache_size_mb: int = 100,
                 default_ttl: Optional[float] = None):
        
        self.memory_cache = LRUCache(memory_cache_size, default_ttl)
        self.disk_cache = DiskCache(disk_cache_dir, disk_cache_size_mb) if disk_cache_dir else None
        self.logger = logger
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（先内存后磁盘）"""
        # 先尝试内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 再尝试磁盘缓存
        if self.disk_cache:
            value = self.disk_cache.get(key)
            if value is not None:
                # 将磁盘缓存的值提升到内存缓存
                self.memory_cache.put(key, value)
                return value
        
        return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None, 
            memory_only: bool = False) -> None:
        """设置缓存值"""
        # 总是放入内存缓存
        self.memory_cache.put(key, value, ttl)
        
        # 如果不是仅内存模式且有磁盘缓存，也放入磁盘缓存
        if not memory_only and self.disk_cache:
            self.disk_cache.put(key, value, ttl)
    
    def remove(self, key: str) -> None:
        """删除缓存条目"""
        self.memory_cache.remove(key)
        if self.disk_cache:
            cache_path = self.disk_cache._get_cache_path(key)
            cache_path.unlink(missing_ok=True)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.memory_cache.clear()
        if self.disk_cache:
            self.disk_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "memory_cache": self.memory_cache.get_stats()
        }
        
        if self.disk_cache:
            cache_files = list(self.disk_cache.cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            stats["disk_cache"] = {
                "file_count": len(cache_files),
                "total_size_mb": total_size / 1024 / 1024,
                "max_size_mb": self.disk_cache.max_size_mb
            }
        
        return stats
    
    def _cleanup_worker(self) -> None:
        """清理工作线程"""
        while True:
            try:
                time.sleep(300)  # 每5分钟清理一次
                
                # 清理过期的内存缓存
                expired_count = self.memory_cache.cleanup_expired()
                if expired_count > 0:
                    self.logger.debug("Memory cache cleanup completed: expired_count=%s", expired_count)
                
                # 清理磁盘缓存（如果需要）
                if self.disk_cache:
                    self.disk_cache._cleanup_if_needed()
                
            except Exception as e:
                self.logger.error("Cache cleanup error: %s", str(e))


def cached(cache_manager: CacheManager, 
          key_func: Optional[Callable] = None,
          ttl: Optional[float] = None,
          memory_only: bool = False):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成键
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "|".join(key_parts)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_manager.put(cache_key, result, ttl, memory_only)
            
            return result
        
        return wrapper
    return decorator


# 全局缓存管理器实例
_global_cache_manager = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache_manager
    
    if _global_cache_manager is None:
        with _cache_lock:
            if _global_cache_manager is None:
                cache_dir = Path("data/cache")
                _global_cache_manager = CacheManager(
                    memory_cache_size=1000,
                    disk_cache_dir=str(cache_dir),
                    disk_cache_size_mb=100,
                    default_ttl=3600  # 1小时默认TTL
                )
    
    return _global_cache_manager