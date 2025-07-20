"""
GPS位置查询插件 - PicMan集成版本

自动读取照片GPS信息并查询地理位置，在照片信息面板中显示位置信息。
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

# 添加插件目录到路径
plugin_dir = Path(__file__).parent / "gps_location_plugin"
if str(plugin_dir) not in sys.path:
    sys.path.insert(0, str(plugin_dir))

try:
    from picman.plugins.base import MetadataPlugin, PluginInfo
except ImportError:
    # 如果无法导入，创建简单的基类
    class MetadataPlugin:
        def __init__(self):
            self.logger = structlog.get_logger(f"picman.plugins.{self.__class__.__name__}")
        
        def extract_metadata(self, image_path: str) -> Dict[str, Any]:
            return {}
        
        def write_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
            return True
    
    class PluginInfo:
        def __init__(self, name, version, description, author):
            self.name = name
            self.version = version
            self.description = description
            self.author = author

try:
    from gps_extractor import GPSExtractor
    from location_api import LocationAPIClient
    from cache_manager import LocationCache
    from config_manager import PluginConfig
    from models import GPSCoordinate, LocationInfo
    from exceptions import (
        GPSLocationError, PluginInitializationError, 
        PluginNotAvailableError, format_error_for_user
    )
except ImportError as e:
    print(f"Failed to import GPS plugin modules: {e}")
    # 创建空的占位符类
    class GPSExtractor:
        def extract_gps_from_picman_data(self, photo_data):
            return None
    
    class LocationAPIClient:
        def query_location(self, coordinate):
            return None
    
    class LocationCache:
        def get(self, coordinate):
            return None
        def set(self, coordinate, location):
            pass
    
    class PluginConfig:
        def is_enabled(self):
            return False
        def get_api_config(self):
            return {}
        def get_cache_config(self):
            return {}
    
    class GPSCoordinate:
        def __init__(self, latitude, longitude, altitude=None):
            self.latitude = latitude
            self.longitude = longitude
            self.altitude = altitude
    
    class LocationInfo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        def to_display_string(self, format_type="short"):
            return "位置信息不可用"


class GPSLocationPlugin(MetadataPlugin):
    """GPS位置查询插件主类
    
    提供GPS坐标提取和位置查询功能的主要接口。
    """
    
    def __init__(self):
        super().__init__()
        self.logger = structlog.get_logger("picman.plugins.gps_location")
        
        # 插件状态
        self._initialized = False
        self._available = False
        
        # 核心组件
        self.config: Optional[PluginConfig] = None
        self.gps_extractor: Optional[GPSExtractor] = None
        self.api_client: Optional[LocationAPIClient] = None
        self.cache: Optional[LocationCache] = None
        
        # 应用上下文
        self.app_context: Dict[str, Any] = {}
        
        self.logger.info("GPS Location Plugin instance created")
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name="GPS位置查询插件",
            version="1.0.0",
            description="自动读取照片GPS信息并查询地理位置",
            author="PicMan开发团队"
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.logger.info("Initializing GPS Location Plugin")
            self.app_context = app_context
            
            # 初始化配置管理器
            self._init_config()
            
            # 检查插件是否启用
            if not self.config.is_enabled():
                self.logger.info("Plugin is disabled in config")
                return True  # 返回True但不设置为可用
            
            # 初始化核心组件
            self._init_components()
            
            # 验证组件状态
            self._validate_components()
            
            self._initialized = True
            self._available = True
            
            self.logger.info("GPS Location Plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Plugin initialization failed", error=str(e))
            self._initialized = False
            self._available = False
            return False
    
    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            self.logger.info("Shutting down GPS Location Plugin")
            
            # 清理资源
            if self.cache:
                # 可以在这里执行缓存清理等操作
                pass
            
            self._initialized = False
            self._available = False
            
            self.logger.info("GPS Location Plugin shutdown successfully")
            return True
            
        except Exception as e:
            self.logger.error("Plugin shutdown failed", error=str(e))
            return False
    
    def _init_config(self):
        """初始化配置管理器"""
        try:
            self.config = PluginConfig()
            
            # 验证配置
            errors = self.config.validate()
            if errors:
                self.logger.warning("Config validation errors", errors=errors)
                
        except Exception as e:
            raise PluginInitializationError(f"配置初始化失败: {str(e)}", "config")
    
    def _init_components(self):
        """初始化核心组件"""
        try:
            # 初始化GPS提取器
            self.gps_extractor = GPSExtractor()
            
            # 初始化API客户端
            api_config = self.config.get_api_config()
            self.api_client = LocationAPIClient(api_config)
            
            # 初始化缓存管理器
            cache_config = self.config.get_cache_config()
            if cache_config.get('enabled', True):
                precision = cache_config.get('coordinate_precision', 0.001)
                self.cache = LocationCache(precision=precision)
            
        except Exception as e:
            raise PluginInitializationError(f"组件初始化失败: {str(e)}", "components")
    
    def _validate_components(self):
        """验证组件状态"""
        if not self.gps_extractor:
            raise PluginInitializationError("GPS提取器初始化失败", "gps_extractor")
        
        if not self.api_client:
            raise PluginInitializationError("API客户端初始化失败", "api_client")
        
        # 检查是否有可用的API
        available_apis = self.api_client.get_available_apis()
        if not available_apis:
            self.logger.warning("No available location APIs")
    
    def extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """提取图片元数据（GPS信息）"""
        try:
            if not self._available:
                return {}
            
            # 提取GPS坐标
            coordinate = self.gps_extractor.extract_gps_from_file(image_path)
            if not coordinate:
                return {}
            
            # 查询位置信息
            location = self.query_location(coordinate)
            
            # 返回元数据
            metadata = {
                "gps_latitude": coordinate.latitude,
                "gps_longitude": coordinate.longitude,
                "gps_altitude": coordinate.altitude,
            }
            
            if location:
                metadata.update({
                    "location_country": location.country,
                    "location_state": location.state_province,
                    "location_city": location.city,
                    "location_district": location.district,
                    "location_street": location.street,
                    "location_full_address": location.full_address,
                    "location_formatted_address": location.formatted_address,
                    "location_source_api": location.source_api,
                })
            
            return metadata
            
        except Exception as e:
            self.logger.error("Failed to extract GPS metadata", error=str(e))
            return {}
    
    def write_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """写入元数据（GPS插件不支持写入）"""
        return True
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息"""
        try:
            if not self._available:
                return None
            
            # 检查缓存
            if self.cache:
                cached_location = self.cache.get(coordinate)
                if cached_location:
                    self.logger.debug("Location found in cache", coordinate=str(coordinate))
                    return cached_location
            
            # 查询API
            location = self.api_client.query_location(coordinate)
            
            # 缓存结果
            if location and self.cache:
                self.cache.set(coordinate, location)
            
            return location
            
        except Exception as e:
            self.logger.error("Failed to query location", error=str(e))
            return None
    
    def query_location_from_photo_data(self, photo_data: Dict[str, Any]) -> Optional[LocationInfo]:
        """从PicMan照片数据中查询位置信息"""
        try:
            if not self._available:
                return None
            
            # 从照片数据中提取GPS坐标
            coordinate = self.gps_extractor.extract_gps_from_picman_data(photo_data)
            if not coordinate:
                return None
            
            # 查询位置信息
            return self.query_location(coordinate)
            
        except Exception as e:
            self.logger.error("Failed to query location from photo data", error=str(e))
            return None
    
    def is_available(self) -> bool:
        """检查插件是否可用"""
        return self._available
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取插件状态信息"""
        return {
            "initialized": self._initialized,
            "available": self._available,
            "config_enabled": self.config.is_enabled() if self.config else False,
            "cache_enabled": self.cache is not None,
            "api_available": self.api_client is not None,
        } 