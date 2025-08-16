"""
实时系统监控工具
"""

import time
import threading
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import json
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SystemSnapshot:
    """系统快照数据"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    disk_free_gb: float
    open_files: int
    threads: int
    db_size_mb: float
    cache_hit_rate: float
    active_operations: int


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, 
                 db_path: str = "data/picman.db",
                 history_size: int = 1000,
                 alert_thresholds: Optional[Dict[str, float]] = None):
        
        self.db_path = Path(db_path)
        self.history_size = history_size
        self.snapshots: deque = deque(maxlen=history_size)
        self.logger = logger
        
        # 默认警告阈值
        self.alert_thresholds = alert_thresholds or {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "disk_free_gb": 1.0,
            "open_files": 100,
            "db_size_mb": 1000.0
        }
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        
        # 警告回调
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # 统计信息
        self._alerts_sent = 0
        self._last_alert_time = {}
        self._alert_cooldown = 300  # 5分钟冷却时间
    
    def start_monitoring(self, interval: float = 30.0):
        """开始监控"""
        if self._monitoring:
            self.logger.warning("Monitor is already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info(f"System monitoring started with interval: {interval}")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        self.logger.info("System monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self._monitoring:
            try:
                snapshot = self._take_snapshot()
                
                with self._lock:
                    self.snapshots.append(snapshot)
                
                # 检查警告条件
                self._check_alerts(snapshot)
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Monitor loop error: {str(e)}")
                time.sleep(interval)
    
    def _take_snapshot(self) -> SystemSnapshot:
        """获取系统快照"""
        try:
            process = psutil.Process()
            
            # 基本系统信息
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            # 磁盘信息
            disk_usage = psutil.disk_usage('.')
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            disk_free_gb = disk_usage.free / 1024**3
            
            # 进程信息
            open_files = len(process.open_files())
            threads = process.num_threads()
            
            # 数据库大小
            db_size_mb = 0
            if self.db_path.exists():
                db_size_mb = self.db_path.stat().st_size / 1024 / 1024
            
            # 缓存命中率（需要从缓存管理器获取）
            cache_hit_rate = 0.0
            try:
                from .cache_manager import get_cache_manager
                cache_stats = get_cache_manager().get_stats()
                cache_hit_rate = cache_stats.get("memory_cache", {}).get("hit_rate", 0.0)
            except Exception:
                pass
            
            # 活跃操作数（需要从性能监控器获取）
            active_operations = 0
            try:
                from .performance_monitor import get_performance_monitor
                perf_stats = get_performance_monitor().get_all_stats()
                active_operations = len([
                    op for op in perf_stats.keys() 
                    if op != "_summary"
                ])
            except Exception:
                pass
            
            return SystemSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                open_files=open_files,
                threads=threads,
                db_size_mb=db_size_mb,
                cache_hit_rate=cache_hit_rate,
                active_operations=active_operations
            )
            
        except Exception as e:
            self.logger.error(f"Failed to take system snapshot: {str(e)}")
            # 返回默认快照
            return SystemSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                open_files=0,
                threads=0,
                db_size_mb=0.0,
                cache_hit_rate=0.0,
                active_operations=0
            )
    
    def _check_alerts(self, snapshot: SystemSnapshot):
        """检查警告条件"""
        current_time = time.time()
        
        # 检查各项指标
        alerts = []
        
        if snapshot.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append(("high_cpu", {
                "current": snapshot.cpu_percent,
                "threshold": self.alert_thresholds["cpu_percent"]
            }))
        
        if snapshot.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append(("high_memory", {
                "current": snapshot.memory_percent,
                "threshold": self.alert_thresholds["memory_percent"],
                "memory_mb": snapshot.memory_mb
            }))
        
        if snapshot.disk_usage_percent > self.alert_thresholds["disk_usage_percent"]:
            alerts.append(("high_disk_usage", {
                "current": snapshot.disk_usage_percent,
                "threshold": self.alert_thresholds["disk_usage_percent"],
                "free_gb": snapshot.disk_free_gb
            }))
        
        if snapshot.disk_free_gb < self.alert_thresholds["disk_free_gb"]:
            alerts.append(("low_disk_space", {
                "current": snapshot.disk_free_gb,
                "threshold": self.alert_thresholds["disk_free_gb"]
            }))
        
        if snapshot.open_files > self.alert_thresholds["open_files"]:
            alerts.append(("too_many_files", {
                "current": snapshot.open_files,
                "threshold": self.alert_thresholds["open_files"]
            }))
        
        if snapshot.db_size_mb > self.alert_thresholds["db_size_mb"]:
            alerts.append(("large_database", {
                "current": snapshot.db_size_mb,
                "threshold": self.alert_thresholds["db_size_mb"]
            }))
        
        # 发送警告（考虑冷却时间）
        for alert_type, alert_data in alerts:
            last_alert = self._last_alert_time.get(alert_type, 0)
            
            if current_time - last_alert > self._alert_cooldown:
                self._send_alert(alert_type, alert_data)
                self._last_alert_time[alert_type] = current_time
    
    def _send_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """发送警告"""
        self._alerts_sent += 1
        
        # 记录日志
        self.logger.warning(f"System alert triggered: {alert_type}, data: {alert_data}")
        
        # 调用回调函数
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {str(e)}")
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加警告回调函数"""
        self._alert_callbacks.append(callback)
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        with self._lock:
            if not self.snapshots:
                return {"status": "no_data"}
            
            latest = self.snapshots[-1]
            
            return {
                "timestamp": datetime.fromtimestamp(latest.timestamp).isoformat(),
                "cpu_percent": latest.cpu_percent,
                "memory_mb": latest.memory_mb,
                "memory_percent": latest.memory_percent,
                "disk_usage_percent": latest.disk_usage_percent,
                "disk_free_gb": latest.disk_free_gb,
                "open_files": latest.open_files,
                "threads": latest.threads,
                "db_size_mb": latest.db_size_mb,
                "cache_hit_rate": latest.cache_hit_rate,
                "active_operations": latest.active_operations,
                "monitoring": self._monitoring,
                "alerts_sent": self._alerts_sent
            }
    
    def get_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取历史数据"""
        cutoff_time = time.time() - (minutes * 60)
        
        with self._lock:
            history = []
            for snapshot in self.snapshots:
                if snapshot.timestamp >= cutoff_time:
                    history.append({
                        "timestamp": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                        "cpu_percent": snapshot.cpu_percent,
                        "memory_mb": snapshot.memory_mb,
                        "memory_percent": snapshot.memory_percent,
                        "disk_usage_percent": snapshot.disk_usage_percent,
                        "disk_free_gb": snapshot.disk_free_gb,
                        "open_files": snapshot.open_files,
                        "threads": snapshot.threads,
                        "db_size_mb": snapshot.db_size_mb,
                        "cache_hit_rate": snapshot.cache_hit_rate,
                        "active_operations": snapshot.active_operations
                    })
            
            return history
    
    def get_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """获取统计信息"""
        history = self.get_history(minutes)
        
        if not history:
            return {"status": "no_data"}
        
        # 计算统计信息
        cpu_values = [h["cpu_percent"] for h in history]
        memory_values = [h["memory_mb"] for h in history]
        
        stats = {
            "period_minutes": minutes,
            "sample_count": len(history),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values)
            },
            "current": history[-1] if history else None,
            "alerts_in_period": self._count_recent_alerts(minutes)
        }
        
        return stats
    
    def _count_recent_alerts(self, minutes: int) -> int:
        """统计最近的警告数量"""
        cutoff_time = time.time() - (minutes * 60)
        
        recent_alerts = 0
        for alert_time in self._last_alert_time.values():
            if alert_time >= cutoff_time:
                recent_alerts += 1
        
        return recent_alerts
    
    def export_data(self, file_path: str, hours: int = 24):
        """导出监控数据"""
        history = self.get_history(hours * 60)
        stats = self.get_statistics(hours * 60)
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "period_hours": hours,
            "statistics": stats,
            "history": history,
            "alert_thresholds": self.alert_thresholds,
            "total_alerts": self._alerts_sent
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Monitor data exported to: {file_path}")
    
    def clear_history(self):
        """清除历史数据"""
        with self._lock:
            self.snapshots.clear()
            self._alerts_sent = 0
            self._last_alert_time.clear()
        
        self.logger.info("Monitor history cleared")


# 全局监控器实例
_global_monitor = None
_monitor_lock = threading.Lock()


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例"""
    global _global_monitor
    
    if _global_monitor is None:
        with _monitor_lock:
            if _global_monitor is None:
                _global_monitor = SystemMonitor()
    
    return _global_monitor


def start_system_monitoring(interval: float = 30.0):
    """启动系统监控"""
    monitor = get_system_monitor()
    monitor.start_monitoring(interval)


def stop_system_monitoring():
    """停止系统监控"""
    monitor = get_system_monitor()
    monitor.stop_monitoring()


def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    monitor = get_system_monitor()
    return monitor.get_current_status()