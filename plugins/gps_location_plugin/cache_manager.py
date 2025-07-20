"""
缓存管理模块

管理GPS位置查询结果的缓存，避免重复API调用。
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import structlog

try:
    from .models import GPSCoordinate, LocationInfo, CacheEntry
    from .exceptions import CacheError, CacheDatabaseError
except ImportError:
    from models import GPSCoordinate, LocationInfo, CacheEntry
    from exceptions import CacheError, CacheDatabaseError


class LocationCache:
    """位置信息缓存管理器
    
    使用SQLite数据库存储位置查询结果，支持基于坐标的就近匹配。
    """
    
    def __init__(self, db_path: str = None, precision: float = 0.001):
        """初始化缓存管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
            precision: 坐标匹配精度（度），默认0.001约为100米
        """
        self.logger = structlog.get_logger("gps_location_plugin.cache_manager")
        
        # 设置数据库路径
        if db_path is None:
            # 默认路径：data/plugins/gps_location_plugin/cache.db
            cache_dir = Path("data/plugins/gps_location_plugin")
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "cache.db"
        
        self.db_path = str(db_path)
        self.precision = precision
        
        # 对于内存数据库，保持连接
        self._memory_conn = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(self.db_path)
        
        # 初始化数据库
        self._init_database()
        
        self.logger.info("Location cache initialized", 
                        db_path=self.db_path, precision=self.precision)
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            # 对于内存数据库，使用保持的连接
            if self._memory_conn:
                conn = self._memory_conn
                cursor = conn.cursor()
                need_commit = True
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                need_commit = False
            
            # 创建缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS location_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    country TEXT,
                    state_province TEXT,
                    city TEXT,
                    district TEXT,
                    street TEXT,
                    full_address TEXT,
                    formatted_address TEXT,
                    source_api TEXT,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hit_count INTEGER DEFAULT 0
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_location_cache_coords 
                ON location_cache(latitude, longitude)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_location_cache_created 
                ON location_cache(created_time)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_location_cache_last_used 
                ON location_cache(last_used_time)
            ''')
            
            # 创建配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            if need_commit:
                conn.commit()
            elif not self._memory_conn:
                conn.commit()
                conn.close()
                
        except sqlite3.Error as e:
            raise CacheDatabaseError(f"数据库初始化失败: {str(e)}", self.db_path, str(e))
    
    def get_cached_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """获取缓存的位置信息
        
        Args:
            coordinate: GPS坐标
            
        Returns:
            缓存的位置信息，如果没有找到则返回None
        """
        try:
            # 对于内存数据库，使用保持的连接
            if self._memory_conn:
                conn = self._memory_conn
                cursor = conn.cursor()
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
            # 查找匹配的缓存条目
            cursor.execute('''
                SELECT * FROM location_cache
                WHERE ABS(latitude - ?) <= ? 
                AND ABS(longitude - ?) <= ?
                ORDER BY 
                    (ABS(latitude - ?) + ABS(longitude - ?)) ASC,
                    last_used_time DESC
                LIMIT 1
            ''', (
                coordinate.latitude, self.precision,
                coordinate.longitude, self.precision,
                coordinate.latitude, coordinate.longitude
            ))
            
            row = cursor.fetchone()
            if not row:
                self.logger.debug("No cache hit found", 
                                lat=coordinate.latitude, lon=coordinate.longitude)
                return None
            
            # 解析缓存数据
            cache_data = {
                'id': row[0],
                'latitude': row[1],
                'longitude': row[2],
                'altitude': row[3],
                'country': row[4] or '',
                'state_province': row[5] or '',
                'city': row[6] or '',
                'district': row[7] or '',
                'street': row[8] or '',
                'full_address': row[9] or '',
                'formatted_address': row[10] or '',
                'source_api': row[11] or '',
                'created_time': row[12],
                'last_used_time': row[13],
                'hit_count': row[14] or 0
            }
            
            # 更新使用统计
            self._update_cache_usage(cache_data['id'])
            
            # 创建LocationInfo对象
            location_info = LocationInfo(
                country=cache_data['country'],
                state_province=cache_data['state_province'],
                city=cache_data['city'],
                district=cache_data['district'],
                street=cache_data['street'],
                full_address=cache_data['full_address'],
                formatted_address=cache_data['formatted_address'],
                source_api=cache_data['source_api'] + " (缓存)",
                query_time=datetime.fromisoformat(cache_data['created_time'])
            )
            
            self.logger.debug("Cache hit found", 
                            cache_id=cache_data['id'],
                            hit_count=cache_data['hit_count'] + 1)
            return location_info
                
        except sqlite3.Error as e:
            self.logger.error("Cache query failed", error=str(e))
            raise CacheDatabaseError(f"缓存查询失败: {str(e)}", self.db_path, str(e))
        except Exception as e:
            self.logger.error("Unexpected error in cache query", error=str(e))
            raise CacheError(f"缓存查询异常: {str(e)}", "query")
    
    def cache_location(self, coordinate: GPSCoordinate, location: LocationInfo):
        """缓存位置信息
        
        Args:
            coordinate: GPS坐标
            location: 位置信息
        """
        try:
            # 检查是否已存在相近的缓存
            existing = self.get_cached_location(coordinate)
            if existing and not existing.is_empty():
                self.logger.debug("Similar cache entry already exists, skipping")
                return
            
            # 对于内存数据库，使用保持的连接
            if self._memory_conn:
                conn = self._memory_conn
                cursor = conn.cursor()
                need_commit = True
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                need_commit = False
            
            # 插入新的缓存条目
            cursor.execute('''
                INSERT INTO location_cache (
                    latitude, longitude, altitude,
                    country, state_province, city, district, street,
                    full_address, formatted_address, source_api,
                    created_time, last_used_time, hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                coordinate.latitude,
                coordinate.longitude,
                coordinate.altitude,
                location.country,
                location.state_province,
                location.city,
                location.district,
                location.street,
                location.full_address,
                location.formatted_address,
                location.source_api,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                0
            ))
            
            if need_commit:
                conn.commit()
            elif not self._memory_conn:
                conn.commit()
                conn.close()
            
            self.logger.debug("Location cached successfully", 
                            lat=coordinate.latitude, lon=coordinate.longitude,
                            location=location.to_display_string("short"))
                
        except sqlite3.Error as e:
            self.logger.error("Cache storage failed", error=str(e))
            raise CacheDatabaseError(f"缓存存储失败: {str(e)}", self.db_path, str(e))
        except Exception as e:
            self.logger.error("Unexpected error in cache storage", error=str(e))
            raise CacheError(f"缓存存储异常: {str(e)}", "store")
    
    def _update_cache_usage(self, cache_id: int):
        """更新缓存使用统计
        
        Args:
            cache_id: 缓存条目ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE location_cache 
                    SET last_used_time = ?, hit_count = hit_count + 1
                    WHERE id = ?
                ''', (datetime.now().isoformat(), cache_id))
                conn.commit()
                
        except sqlite3.Error as e:
            self.logger.warning("Failed to update cache usage", 
                              cache_id=cache_id, error=str(e))
    
    def clear_expired_cache(self, max_age_days: int = 30) -> int:
        """清理过期的缓存数据
        
        Args:
            max_age_days: 最大缓存天数
            
        Returns:
            清理的条目数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 删除过期条目
                cursor.execute('''
                    DELETE FROM location_cache 
                    WHERE created_time < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info("Expired cache entries cleared", 
                               count=deleted_count, max_age_days=max_age_days)
                return deleted_count
                
        except sqlite3.Error as e:
            self.logger.error("Cache cleanup failed", error=str(e))
            raise CacheDatabaseError(f"缓存清理失败: {str(e)}", self.db_path, str(e))
    
    def clear_all_cache(self) -> int:
        """清空所有缓存数据
        
        Returns:
            清理的条目数量
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取总数
                cursor.execute('SELECT COUNT(*) FROM location_cache')
                total_count = cursor.fetchone()[0]
                
                # 清空表
                cursor.execute('DELETE FROM location_cache')
                conn.commit()
                
                self.logger.info("All cache entries cleared", count=total_count)
                return total_count
                
        except sqlite3.Error as e:
            self.logger.error("Cache clear failed", error=str(e))
            raise CacheDatabaseError(f"缓存清空失败: {str(e)}", self.db_path, str(e))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总条目数
                cursor.execute('SELECT COUNT(*) FROM location_cache')
                total_count = cursor.fetchone()[0]
                
                # 最近使用的条目数（7天内）
                recent_date = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('''
                    SELECT COUNT(*) FROM location_cache 
                    WHERE last_used_time >= ?
                ''', (recent_date,))
                recent_count = cursor.fetchone()[0]
                
                # 总命中次数
                cursor.execute('SELECT SUM(hit_count) FROM location_cache')
                total_hits = cursor.fetchone()[0] or 0
                
                # 最老的条目
                cursor.execute('''
                    SELECT MIN(created_time) FROM location_cache
                ''')
                oldest_entry = cursor.fetchone()[0]
                
                # 数据库文件大小
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'total_entries': total_count,
                    'recent_entries': recent_count,
                    'total_hits': total_hits,
                    'oldest_entry': oldest_entry,
                    'db_size_bytes': db_size,
                    'db_size_mb': round(db_size / 1024 / 1024, 2),
                    'precision': self.precision
                }
                
        except sqlite3.Error as e:
            self.logger.error("Failed to get cache stats", error=str(e))
            return {'error': str(e)}
    
    def _is_coordinate_match(self, coord1: GPSCoordinate, coord2: GPSCoordinate) -> bool:
        """检查两个坐标是否匹配（在精度范围内）
        
        Args:
            coord1: 第一个坐标
            coord2: 第二个坐标
            
        Returns:
            是否匹配
        """
        lat_diff = abs(coord1.latitude - coord2.latitude)
        lon_diff = abs(coord1.longitude - coord2.longitude)
        
        return lat_diff <= self.precision and lon_diff <= self.precision
    
    def optimize_cache(self, max_entries: int = 10000):
        """优化缓存，删除最少使用的条目
        
        Args:
            max_entries: 最大缓存条目数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查当前条目数
                cursor.execute('SELECT COUNT(*) FROM location_cache')
                current_count = cursor.fetchone()[0]
                
                if current_count <= max_entries:
                    return
                
                # 删除最少使用的条目
                delete_count = current_count - max_entries
                cursor.execute('''
                    DELETE FROM location_cache 
                    WHERE id IN (
                        SELECT id FROM location_cache 
                        ORDER BY hit_count ASC, last_used_time ASC 
                        LIMIT ?
                    )
                ''', (delete_count,))
                
                conn.commit()
                
                self.logger.info("Cache optimized", 
                               deleted=delete_count, remaining=max_entries)
                
        except sqlite3.Error as e:
            self.logger.error("Cache optimization failed", error=str(e))
            raise CacheDatabaseError(f"缓存优化失败: {str(e)}", self.db_path, str(e))
    
    def export_cache(self, export_path: str) -> bool:
        """导出缓存数据到JSON文件
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM location_cache')
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                # 转换为字典列表
                data = []
                for row in rows:
                    entry = dict(zip(columns, row))
                    data.append(entry)
                
                # 写入JSON文件
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.logger.info("Cache exported successfully", 
                               path=export_path, count=len(data))
                return True
                
        except Exception as e:
            self.logger.error("Cache export failed", error=str(e))
            return False
    
    def import_cache(self, import_path: str) -> bool:
        """从JSON文件导入缓存数据
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            是否成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                imported_count = 0
                for entry in data:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO location_cache (
                                latitude, longitude, altitude,
                                country, state_province, city, district, street,
                                full_address, formatted_address, source_api,
                                created_time, last_used_time, hit_count
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            entry.get('latitude'),
                            entry.get('longitude'),
                            entry.get('altitude'),
                            entry.get('country'),
                            entry.get('state_province'),
                            entry.get('city'),
                            entry.get('district'),
                            entry.get('street'),
                            entry.get('full_address'),
                            entry.get('formatted_address'),
                            entry.get('source_api'),
                            entry.get('created_time'),
                            entry.get('last_used_time'),
                            entry.get('hit_count', 0)
                        ))
                        imported_count += 1
                    except sqlite3.Error:
                        continue  # 跳过有问题的条目
                
                conn.commit()
                
                self.logger.info("Cache imported successfully", 
                               path=import_path, count=imported_count)
                return True
                
        except Exception as e:
            self.logger.error("Cache import failed", error=str(e))
            return False