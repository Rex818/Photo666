"""
性能监控和统计工具
"""

import time
import threading
import psutil
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque

# 配置日志
logging.basicConfig(level=logging.INFO)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    cpu_percent: float
    thread_id: int
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.logger = logging.getLogger("picman.performance")
        self._lock = threading.Lock()
        
    @contextmanager
    def monitor_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """监控操作的上下文管理器"""
        start_time = time.time()
        memory_before = self._get_memory_usage()
        cpu_before = psutil.cpu_percent()
        thread_id = threading.get_ident()
        
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            memory_after = self._get_memory_usage()
            memory_delta = memory_after - memory_before
            cpu_after = psutil.cpu_percent()
            cpu_percent = (cpu_before + cpu_after) / 2
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_delta,
                cpu_percent=cpu_percent,
                thread_id=thread_id,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            self._record_metrics(metrics)
    
    def monitor_function(self, operation_name: Optional[str] = None, include_args: bool = False):
        """函数装饰器，用于监控函数性能"""
        def decorator(func):
            nonlocal operation_name
            if operation_name is None:
                operation_name = f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                metadata = {}
                if include_args:
                    metadata['args_count'] = len(args)
                    metadata['kwargs_keys'] = list(kwargs.keys())
                
                with self.monitor_operation(operation_name, metadata):
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _record_metrics(self, metrics: PerformanceMetrics):
        """记录性能指标"""
        with self._lock:
            self.metrics_history.append(metrics)
            self.operation_stats[metrics.operation_name].append(metrics.duration)
            
            # 限制每个操作的历史记录数量
            if len(self.operation_stats[metrics.operation_name]) > 100:
                self.operation_stats[metrics.operation_name] = \
                    self.operation_stats[metrics.operation_name][-100:]
        
        # 记录日志
        if metrics.success:
            self.logger.info(
                f"Operation completed: {metrics.operation_name}, "
                f"duration: {metrics.duration:.3f}s, "
                f"memory_delta: {metrics.memory_delta:.2f}MB, "
                f"cpu_percent: {metrics.cpu_percent:.1f}%"
            )
        else:
            self.logger.error(
                f"Operation failed: {metrics.operation_name}, "
                f"duration: {metrics.duration:.3f}s, "
                f"error: {metrics.error_message}"
            )
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """获取特定操作的统计信息"""
        with self._lock:
            durations = self.operation_stats.get(operation_name, [])
            
            if not durations:
                return {"operation": operation_name, "count": 0}
            
            return {
                "operation": operation_name,
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations),
                "recent_avg": sum(durations[-10:]) / min(len(durations), 10)
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有操作的统计信息"""
        with self._lock:
            stats = {}
            for operation_name in self.operation_stats:
                stats[operation_name] = self.get_operation_stats(operation_name)
            
            # 添加总体统计
            total_operations = len(self.metrics_history)
            successful_operations = sum(1 for m in self.metrics_history if m.success)
            
            stats["_summary"] = {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "success_rate": successful_operations / max(total_operations, 1) * 100,
                "total_unique_operations": len(self.operation_stats),
                "monitoring_period": self._get_monitoring_period()
            }
            
            return stats
    
    def _get_monitoring_period(self) -> Dict[str, Any]:
        """获取监控时间段信息"""
        if not self.metrics_history:
            return {"start": None, "end": None, "duration": 0}
        
        start_time = min(m.start_time for m in self.metrics_history)
        end_time = max(m.end_time for m in self.metrics_history)
        
        return {
            "start": datetime.fromtimestamp(start_time).isoformat(),
            "end": datetime.fromtimestamp(end_time).isoformat(),
            "duration": end_time - start_time
        }
    
    def get_slow_operations(self, threshold_seconds: float = 1.0) -> List[PerformanceMetrics]:
        """获取慢操作列表"""
        with self._lock:
            return [m for m in self.metrics_history if m.duration > threshold_seconds]
    
    def get_memory_intensive_operations(self, threshold_mb: float = 50.0) -> List[PerformanceMetrics]:
        """获取内存密集型操作列表"""
        with self._lock:
            return [m for m in self.metrics_history if abs(m.memory_delta) > threshold_mb]
    
    def clear_history(self):
        """清除历史记录"""
        with self._lock:
            self.metrics_history.clear()
            self.operation_stats.clear()
        
        self.logger.info("Performance history cleared")
    
    def export_stats(self, file_path: str):
        """导出统计信息到文件"""
        import json
        
        stats = self.get_all_stats()
        
        # 添加详细的历史记录
        with self._lock:
            history_data = []
            for metrics in self.metrics_history:
                history_data.append({
                    "operation": metrics.operation_name,
                    "start_time": datetime.fromtimestamp(metrics.start_time).isoformat(),
                    "duration": metrics.duration,
                    "memory_delta": metrics.memory_delta,
                    "cpu_percent": metrics.cpu_percent,
                    "success": metrics.success,
                    "error": metrics.error_message,
                    "metadata": metrics.metadata
                })
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "stats": stats,
            "history": history_data
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Performance stats exported to: {file_path}")


# 全局性能监控器实例
_global_monitor = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_monitor
    
    if _global_monitor is None:
        with _monitor_lock:
            if _global_monitor is None:
                _global_monitor = PerformanceMonitor()
    
    return _global_monitor


def monitor_performance(operation_name: Optional[str] = None, include_args: bool = False):
    """性能监控装饰器"""
    return get_performance_monitor().monitor_function(operation_name, include_args)


@contextmanager
def monitor_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """监控操作的上下文管理器"""
    with get_performance_monitor().monitor_operation(operation_name, metadata):
        yield