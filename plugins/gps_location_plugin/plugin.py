"""
GPS位置查询插件主类

插件的主要入口点，集成所有功能模块。
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# 添加PicMan源码目录到Python路径
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from picman.plugins.base import Plugin, PluginInfo
except ImportError:
    # 如果无法导入，创建简单的基类
    class Plugin:
        def __init__(self):
            self.logger = logging.getLogger(f"picman.plugins.{self.__class__.__name__}")
        
        def get_info(self):
            pass
        
        def initialize(self, app_context):
            return True
        
        def shutdown(self):
            return True
    
    class PluginInfo:
        def __init__(self, name, version, description, author):
            self.name = name
            self.version = version
            self.description = description
            self.author = author

try:
    from .gps_extractor import GPSExtractor
    from .location_api import LocationAPIClient
    from .cache_manager import LocationCache
    from .config_manager import PluginConfig
    from .models import GPSCoordinate, LocationInfo
    from .exceptions import (
        GPSLocationError, PluginInitializationError, 
        PluginNotAvailableError, format_error_for_user
    )
except ImportError:
    from gps_extractor import GPSExtractor
    from location_api import LocationAPIClient
    from cache_manager import LocationCache
    from config_manager import PluginConfig
    from models import GPSCoordinate, LocationInfo
    from exceptions import (
        GPSLocationError, PluginInitializationError, 
        PluginNotAvailableError, format_error_for_user
    )


class GPSLocationPlugin(Plugin):
    """GPS位置查询插件主类
    
    提供GPS坐标提取和位置查询功能的主要接口。
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("gps_location_plugin.main")
        
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
        """初始化插件
        
        Args:
            app_context: 应用程序上下文
            
        Returns:
            是否初始化成功
        """
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
            self.logger.error(f"Plugin initialization failed - error: {str(e)}")
            self._initialized = False
            self._available = False
            return False
    
    def shutdown(self) -> bool:
        """关闭插件
        
        Returns:
            是否关闭成功
        """
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
            self.logger.error(f"Plugin shutdown failed - error: {str(e)}")
            return False
    
    def _init_config(self):
        """初始化配置管理器"""
        try:
            self.config = PluginConfig()
            
            # 验证配置
            errors = self.config.validate()
            if errors:
                self.logger.warning("Config validation errors: errors=%s", errors)
                # 可以选择重置为默认配置或继续使用
            
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
            self.logger.warning("No available APIs found")
            # 不抛出异常，允许插件在只有缓存的情况下工作
    
    def extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """从图片中提取元数据（包括GPS位置信息）
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            包含位置信息的元数据字典
        """
        if not self.is_available():
            return {}
        
        try:
            # 提取GPS坐标
            coordinate = self.gps_extractor.extract_gps_from_file(image_path)
            if not coordinate:
                self.logger.debug("No GPS coordinates found: %s", image_path)
                return {}
            
            # 查询位置信息
            location_info = self.query_location(coordinate)
            if not location_info:
                return {
                    'gps_coordinate': {
                        'latitude': coordinate.latitude,
                        'longitude': coordinate.longitude,
                        'altitude': coordinate.altitude
                    }
                }
            
            # 返回完整的位置元数据
            return {
                'gps_coordinate': {
                    'latitude': coordinate.latitude,
                    'longitude': coordinate.longitude,
                    'altitude': coordinate.altitude
                },
                'location_info': location_info.to_dict(),
                'location_display': location_info.to_display_string(
                    self.config.get('ui_settings.location_display_format', 'short')
                )
            }
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed - file: {image_path}, error: {str(e)}")
            return {}
    
    def write_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """写入元数据到图片
        
        注意：此插件主要用于读取GPS信息，不支持写入。
        
        Args:
            image_path: 图片文件路径
            metadata: 元数据字典
            
        Returns:
            是否成功（总是返回False，因为不支持写入）
        """
        self.logger.debug("Write metadata not supported by GPS Location Plugin")
        return False
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询GPS坐标对应的位置信息
        
        Args:
            coordinate: GPS坐标
            
        Returns:
            位置信息，查询失败返回None
        """
        if not self.is_available():
            return None
        
        try:
            # 首先尝试从缓存获取
            if self.cache:
                cached_location = self.cache.get_cached_location(coordinate)
                if cached_location:
                    self.logger.debug("Location found in cache")
                    return cached_location
            
            # 缓存未命中，使用API查询
            if not self.api_client:
                self.logger.warning("No API client available")
                return None
            
            location_info = self.api_client.query_location(coordinate)
            
            # 将结果缓存
            if location_info and self.cache and not location_info.is_empty():
                self.cache.cache_location(coordinate, location_info)
            
            return location_info
            
        except Exception as e:
            self.logger.error(f"Location query failed - lat: {coordinate.latitude}, lon: {coordinate.longitude}, error: {str(e)}")
            return None
    
    def query_location_from_photo_data(self, photo_data: Dict[str, Any]) -> Optional[LocationInfo]:
        """从PicMan照片数据中查询位置信息
        
        Args:
            photo_data: PicMan照片数据字典
            
        Returns:
            位置信息，查询失败返回None
        """
        if not self.is_available():
            return None
        
        try:
            # 提取GPS坐标
            coordinate = self.gps_extractor.extract_gps_from_picman_data(photo_data)
            if not coordinate:
                return None
            
            # 查询位置信息
            return self.query_location(coordinate)
            
        except Exception as e:
            self.logger.error(f"Location query from photo data failed - photo_id: {photo_data.get('id')}, error: {str(e)}")
            return None
    
    def batch_query_locations(self, photo_data_list: List[Dict[str, Any]], 
                            progress_callback=None) -> Dict[int, Optional[LocationInfo]]:
        """批量查询多张照片的位置信息
        
        Args:
            photo_data_list: 照片数据列表
            progress_callback: 进度回调函数，接收 (current, total, photo_id) 参数
            
        Returns:
            照片ID到位置信息的映射字典
        """
        if not self.is_available():
            return {}
        
        results = {}
        total = len(photo_data_list)
        
        # 获取批处理延迟设置
        delay = self.config.get('advanced.batch_processing_delay', 1.0)
        
        try:
            for i, photo_data in enumerate(photo_data_list):
                photo_id = photo_data.get('id')
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i + 1, total, photo_id)
                
                # 查询位置信息
                location_info = self.query_location_from_photo_data(photo_data)
                results[photo_id] = location_info
                
                # 添加延迟避免API限制
                if delay > 0 and i < total - 1:
                    import time
                    time.sleep(delay)
            
            self.logger.info("Batch location query completed: total=%s, successful=%s", total, sum(1 for v in results.values() if v))
            return results
            
        except Exception as e:
            self.logger.error(f"Batch location query failed - error: {str(e)}")
            return results
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """获取菜单动作"""
        if not self.is_available():
            return []
        
        return [
            {
                "menu": "工具",
                "title": "查询GPS位置",
                "action": "query_gps_location",
                "description": "查询选中照片的GPS位置信息"
            },
            {
                "menu": "工具",
                "title": "批量查询GPS位置",
                "action": "batch_query_gps_location",
                "description": "批量查询多张照片的GPS位置信息"
            }
        ]
    
    def get_settings(self) -> Dict[str, Any]:
        """获取插件设置"""
        if not self.config:
            return {}
        
        return {
            'config_summary': self.config.get_config_summary(),
            'api_status': self.api_client.get_api_status() if self.api_client else {},
            'cache_stats': self.cache.get_cache_stats() if self.cache else {},
            'plugin_status': {
                'initialized': self._initialized,
                'available': self._available,
                'enabled': self.config.is_enabled()
            }
        }
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """更新插件设置
        
        Args:
            settings: 新的设置字典
            
        Returns:
            是否更新成功
        """
        if not self.config:
            return False
        
        try:
            # 更新配置
            self.config.update(settings)
            
            # 如果API设置发生变化，重新初始化API客户端
            if any(key.startswith('api_settings.') for key in settings.keys()):
                api_config = self.config.get_api_config()
                self.api_client = LocationAPIClient(api_config)
            
            # 如果缓存设置发生变化，重新初始化缓存
            if any(key.startswith('cache_settings.') for key in settings.keys()):
                cache_config = self.config.get_cache_config()
                if cache_config.get('enabled', True):
                    precision = cache_config.get('coordinate_precision', 0.001)
                    self.cache = LocationCache(precision=precision)
                else:
                    self.cache = None
            
            self.logger.info("Plugin settings updated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update settings - error: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """检查插件是否可用
        
        Returns:
            是否可用
        """
        return self._initialized and self._available and (
            self.config and self.config.is_enabled()
        )
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取插件状态信息
        
        Returns:
            状态信息字典
        """
        return {
            'name': self.get_info().name,
            'version': self.get_info().version,
            'initialized': self._initialized,
            'available': self.is_available(),
            'enabled': self.config.is_enabled() if self.config else False,
            'components': {
                'config': self.config is not None,
                'gps_extractor': self.gps_extractor is not None,
                'api_client': self.api_client is not None,
                'cache': self.cache is not None
            },
            'api_status': self.api_client.get_api_status() if self.api_client else {},
            'cache_stats': self.cache.get_cache_stats() if self.cache else {}
        }
    
    def handle_error(self, error: Exception) -> str:
        """处理错误并返回用户友好的消息
        
        Args:
            error: 异常对象
            
        Returns:
            用户友好的错误消息
        """
        if isinstance(error, GPSLocationError):
            return format_error_for_user(error)
        else:
            self.logger.error("Unexpected error: error=%s", str(error))
            return f"插件运行出错: {str(error)}"
    
    def cleanup_cache(self, max_age_days: int = None) -> int:
        """清理过期缓存
        
        Args:
            max_age_days: 最大缓存天数，None使用配置值
            
        Returns:
            清理的条目数量
        """
        if not self.cache:
            return 0
        
        if max_age_days is None:
            max_age_days = self.config.get('cache_settings.max_age_days', 30)
        
        try:
            return self.cache.clear_expired_cache(max_age_days)
        except Exception as e:
            self.logger.error(f"Cache cleanup failed - error: {str(e)}")
            return 0
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的图片格式
        
        Returns:
            支持的文件扩展名列表
        """
        if self.gps_extractor:
            return self.gps_extractor.get_supported_formats()
        return []