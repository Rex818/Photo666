"""
配置管理模块

管理插件的各种配置选项，包括API设置、缓存设置等。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    from .exceptions import ConfigurationError
except ImportError:
    from exceptions import ConfigurationError


class PluginConfig:
    """插件配置管理器
    
    负责加载、保存和验证插件配置。
    """
    
    def __init__(self, config_path: str = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.logger = logging.getLogger("gps_location_plugin.config_manager")
        
        # 设置配置文件路径
        if config_path is None:
            plugin_dir = Path(__file__).parent
            config_path = plugin_dir / "config.json"
        
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        
        # 加载配置
        self._load_config()
        
        self.logger.info(f"Plugin config initialized - path: {str(self.config_path)}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                self.logger.debug("Config loaded from file")
            else:
                # 使用默认配置
                self.config_data = self._get_default_config()
                self._save_config()  # 保存默认配置到文件
                self.logger.info("Created default config file")
                
        except json.JSONDecodeError as e:
            self.logger.error("Config file JSON decode error", error=str(e))
            raise ConfigurationError(f"配置文件JSON格式错误: {str(e)}")
        except Exception as e:
            self.logger.error("Failed to load config", error=str(e))
            raise ConfigurationError(f"配置文件加载失败: {str(e)}")
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加更新时间
            self.config_data['_updated'] = datetime.now().isoformat()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug("Config saved to file")
            
        except Exception as e:
            self.logger.error("Failed to save config", error=str(e))
            raise ConfigurationError(f"配置文件保存失败: {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "api_settings": {
                "priority": ["nominatim", "google", "baidu", "amap"],
                "google_api_key": "",
                "baidu_api_key": "",
                "amap_api_key": "",
                "timeout": 10,
                "retry_count": 3,
                "user_agent": "PicMan GPS Location Plugin/1.0.0"
            },
            "cache_settings": {
                "enabled": True,
                "max_age_days": 30,
                "max_cache_size": 10000,
                "coordinate_precision": 0.001,
                "cleanup_interval_hours": 24
            },
            "ui_settings": {
                "auto_query_on_photo_select": False,
                "show_in_photo_info": True,
                "show_map_link": True,
                "location_display_format": "short",
                "show_coordinates": True
            },
            "logging": {
                "level": "INFO",
                "log_api_calls": True,
                "log_cache_hits": False,
                "log_performance": False
            },
            "advanced": {
                "batch_processing_delay": 1.0,
                "max_concurrent_requests": 3,
                "coordinate_clustering_enabled": True,
                "fallback_to_cache_only": False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键（如 "api_settings.timeout"）
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any, save: bool = True):
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            save: 是否立即保存到文件
        """
        try:
            keys = key.split('.')
            config = self.config_data
            
            # 导航到目标位置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            if save:
                self._save_config()
            
            self.logger.debug("Config value set", key=key, value=value)
            
        except Exception as e:
            self.logger.error("Failed to set config value", key=key, error=str(e))
            raise ConfigurationError(f"设置配置值失败: {key} = {value}")
    
    def update(self, updates: Dict[str, Any], save: bool = True):
        """批量更新配置
        
        Args:
            updates: 更新的配置字典
            save: 是否立即保存到文件
        """
        try:
            for key, value in updates.items():
                self.set(key, value, save=False)
            
            if save:
                self._save_config()
            
            self.logger.debug("Config batch updated", count=len(updates))
            
        except Exception as e:
            self.logger.error("Failed to batch update config", error=str(e))
            raise ConfigurationError(f"批量更新配置失败: {str(e)}")
    
    def validate(self) -> List[str]:
        """验证配置的有效性
        
        Returns:
            错误信息列表，空列表表示配置有效
        """
        errors = []
        
        try:
            # 验证基本结构
            required_sections = ['api_settings', 'cache_settings', 'ui_settings', 'logging']
            for section in required_sections:
                if section not in self.config_data:
                    errors.append(f"缺少配置节: {section}")
            
            # 验证API设置
            api_settings = self.config_data.get('api_settings', {})
            
            # 验证超时时间
            timeout = api_settings.get('timeout', 10)
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("api_settings.timeout 必须是正数")
            
            # 验证重试次数
            retry_count = api_settings.get('retry_count', 3)
            if not isinstance(retry_count, int) or retry_count < 0:
                errors.append("api_settings.retry_count 必须是非负整数")
            
            # 验证API优先级
            priority = api_settings.get('priority', [])
            if not isinstance(priority, list):
                errors.append("api_settings.priority 必须是列表")
            else:
                valid_apis = ['nominatim', 'google', 'baidu', 'amap']
                for api in priority:
                    if api not in valid_apis:
                        errors.append(f"无效的API名称: {api}")
            
            # 验证缓存设置
            cache_settings = self.config_data.get('cache_settings', {})
            
            # 验证缓存有效期
            max_age_days = cache_settings.get('max_age_days', 30)
            if not isinstance(max_age_days, (int, float)) or max_age_days <= 0:
                errors.append("cache_settings.max_age_days 必须是正数")
            
            # 验证缓存大小
            max_cache_size = cache_settings.get('max_cache_size', 10000)
            if not isinstance(max_cache_size, int) or max_cache_size <= 0:
                errors.append("cache_settings.max_cache_size 必须是正整数")
            
            # 验证坐标精度
            precision = cache_settings.get('coordinate_precision', 0.001)
            if not isinstance(precision, (int, float)) or precision <= 0:
                errors.append("cache_settings.coordinate_precision 必须是正数")
            
            # 验证UI设置
            ui_settings = self.config_data.get('ui_settings', {})
            
            # 验证显示格式
            display_format = ui_settings.get('location_display_format', 'short')
            valid_formats = ['full', 'short', 'city_only']
            if display_format not in valid_formats:
                errors.append(f"ui_settings.location_display_format 必须是: {valid_formats}")
            
            # 验证日志设置
            logging_settings = self.config_data.get('logging', {})
            
            # 验证日志级别
            log_level = logging_settings.get('level', 'INFO')
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
            if log_level not in valid_levels:
                errors.append(f"logging.level 必须是: {valid_levels}")
            
        except Exception as e:
            errors.append(f"配置验证异常: {str(e)}")
        
        if errors:
            self.logger.warning("Config validation failed", errors=errors)
        else:
            self.logger.debug("Config validation passed")
        
        return errors
    
    def reset_to_default(self, save: bool = True):
        """重置为默认配置
        
        Args:
            save: 是否立即保存到文件
        """
        try:
            self.config_data = self._get_default_config()
            
            if save:
                self._save_config()
            
            self.logger.info("Config reset to default")
            
        except Exception as e:
            self.logger.error("Failed to reset config", error=str(e))
            raise ConfigurationError(f"重置配置失败: {str(e)}")
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到文件
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            是否成功
        """
        try:
            export_data = self.config_data.copy()
            export_data['_exported'] = datetime.now().isoformat()
            export_data['_version'] = "1.0.0"
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Config exported - path: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error("Config export failed", error=str(e))
            return False
    
    def import_config(self, import_path: str, validate_first: bool = True) -> bool:
        """从文件导入配置
        
        Args:
            import_path: 导入文件路径
            validate_first: 是否先验证配置
            
        Returns:
            是否成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # 移除导出时添加的元数据
            imported_data.pop('_exported', None)
            imported_data.pop('_version', None)
            
            if validate_first:
                # 临时设置配置进行验证
                original_config = self.config_data.copy()
                self.config_data = imported_data
                
                errors = self.validate()
                if errors:
                    # 恢复原配置
                    self.config_data = original_config
                    self.logger.error("Imported config validation failed", errors=errors)
                    return False
            
            # 应用导入的配置
            self.config_data = imported_data
            self._save_config()
            
            self.logger.info(f"Config imported successfully - path: {import_path}")
            return True
            
        except Exception as e:
            self.logger.error("Config import failed", error=str(e))
            return False
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置
        
        Returns:
            API配置字典
        """
        return self.config_data.get('api_settings', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置
        
        Returns:
            缓存配置字典
        """
        return self.config_data.get('cache_settings', {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置
        
        Returns:
            UI配置字典
        """
        return self.config_data.get('ui_settings', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置
        
        Returns:
            日志配置字典
        """
        return self.config_data.get('logging', {})
    
    def is_enabled(self) -> bool:
        """检查插件是否启用
        
        Returns:
            是否启用
        """
        return self.config_data.get('enabled', True)
    
    def set_enabled(self, enabled: bool, save: bool = True):
        """设置插件启用状态
        
        Args:
            enabled: 是否启用
            save: 是否立即保存
        """
        self.set('enabled', enabled, save)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息
        
        Returns:
            配置摘要字典
        """
        api_settings = self.get_api_config()
        cache_settings = self.get_cache_config()
        ui_settings = self.get_ui_config()
        
        # 统计配置的API密钥
        api_keys_configured = []
        if api_settings.get('google_api_key'):
            api_keys_configured.append('google')
        if api_settings.get('baidu_api_key'):
            api_keys_configured.append('baidu')
        if api_settings.get('amap_api_key'):
            api_keys_configured.append('amap')
        
        return {
            'enabled': self.is_enabled(),
            'api_priority': api_settings.get('priority', []),
            'api_keys_configured': api_keys_configured,
            'cache_enabled': cache_settings.get('enabled', True),
            'cache_max_age_days': cache_settings.get('max_age_days', 30),
            'auto_query': ui_settings.get('auto_query_on_photo_select', False),
            'display_format': ui_settings.get('location_display_format', 'short'),
            'config_file': str(self.config_path),
            'last_updated': self.config_data.get('_updated', 'Unknown')
        }
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return self.get(key) is not None