"""
Janus插件配置管理器
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class ConfigManager:
    """Janus插件配置管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.core.config_manager")
        self.plugin_dir = Path(__file__).parent.parent
        self.config_dir = self.plugin_dir / "config"
        
        # 配置文件路径
        self.config_file = self.config_dir / "config.json"
        self.models_file = self.config_dir / "models.json"
        self.settings_file = self.config_dir / "settings.json"
        
        # 配置数据
        self.config = {}
        self.models_config = {}
        self.user_settings = {}
        
        self.logger.info("开始初始化Janus配置管理器")
    
    def initialize(self) -> bool:
        """初始化配置管理器"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # 加载配置文件
            self._load_config()
            self._load_models_config()
            self._load_user_settings()
            
            self.logger.info("Janus配置管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Janus配置管理器初始化失败: {str(e)}")
            return False
    
    def _load_config(self):
        """加载主配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.logger.info(f"加载配置文件成功 - 文件: {self.config_file}")
            else:
                self.logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
                self.config = self._get_default_config()
                self._save_config()
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            self.config = self._get_default_config()
    
    def _load_models_config(self):
        """加载模型配置文件"""
        try:
            if self.models_file.exists():
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    self.models_config = json.load(f)
                self.logger.info(f"加载模型配置文件成功 - 文件: {self.models_file}")
            else:
                self.logger.warning(f"模型配置文件不存在，使用默认配置: {self.models_file}")
                self.models_config = self._get_default_models_config()
                self._save_models_config()
        except Exception as e:
            self.logger.error(f"加载模型配置文件失败: {str(e)}")
            self.models_config = self._get_default_models_config()
    
    def _load_user_settings(self):
        """加载用户设置文件"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.user_settings = json.load(f)
                self.logger.info(f"加载用户设置文件成功 - 文件: {self.settings_file}")
            else:
                self.logger.warning(f"用户设置文件不存在，使用默认设置: {self.settings_file}")
                self.user_settings = self._get_default_user_settings()
                self._save_user_settings()
        except Exception as e:
            self.logger.error(f"加载用户设置文件失败: {str(e)}")
            self.user_settings = self._get_default_user_settings()
    
    def _save_config(self):
        """保存主配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.logger.info("配置文件保存成功")
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")
    
    def _save_models_config(self):
        """保存模型配置文件"""
        try:
            with open(self.models_file, 'w', encoding='utf-8') as f:
                json.dump(self.models_config, f, indent=4, ensure_ascii=False)
            self.logger.info("模型配置文件保存成功")
        except Exception as e:
            self.logger.error(f"保存模型配置文件失败: {str(e)}")
    
    def _save_user_settings(self):
        """保存用户设置文件"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_settings, f, indent=4, ensure_ascii=False)
            self.logger.info("用户设置文件保存成功")
        except Exception as e:
            self.logger.error(f"保存用户设置文件失败: {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "models": {
                "available_models": [
                    {
                        "id": "deepseek-ai/Janus-Pro-1B",
                        "name": "Janus-Pro-1B",
                        "description": "轻量级模型，速度快，适合快速反推",
                        "size": "1B",
                        "download_url": "https://huggingface.co/deepseek-ai/Janus-Pro-1B",
                        "local_path": None,
                        "is_downloaded": False
                    },
                    {
                        "id": "deepseek-ai/Janus-Pro-7B",
                        "name": "Janus-Pro-7B",
                        "description": "高质量模型，精度高，适合详细分析",
                        "size": "7B",
                        "download_url": "https://huggingface.co/deepseek-ai/Janus-Pro-7B",
                        "local_path": None,
                        "is_downloaded": False
                    }
                ],
                "default_model": "deepseek-ai/Janus-Pro-1B",
                "models_directory": "models"
            },
            "reverse_inference": {
                "default_question": "Describe this image in detail.",
                "default_temperature": 0.1,
                "default_top_p": 0.95,
                "default_max_new_tokens": 512,
                "default_seed": 666666666666666,
                "save_results": True,
                "result_file_suffix": ".txt"
            },
            "image_generation": {
                "default_prompt": "A beautiful photo of",
                "default_seed": 666666666666666,
                "default_batch_size": 1,
                "default_cfg_weight": 5.0,
                "default_temperature": 1.0,
                "default_top_p": 0.95,
                "default_image_size": 384
            },
            "system": {
                "use_gpu": True,
                "max_memory_usage": 0.8,
                "cache_enabled": True,
                "cache_size": 100,
                "cache_timeout": 3600,
                "log_level": "INFO",
                "auto_download": True
            }
        }
    
    def _get_default_models_config(self) -> Dict[str, Any]:
        """获取默认模型配置"""
        return {
            "models": [
                {
                    "id": "deepseek-ai/Janus-Pro-1B",
                    "name": "Janus-Pro-1B",
                    "description": "轻量级模型，速度快，适合快速反推",
                    "size": "1B",
                    "parameters": "1B",
                    "download_url": "https://huggingface.co/deepseek-ai/Janus-Pro-1B",
                    "local_path": None,
                    "is_downloaded": False,
                    "download_size": "2.1GB",
                    "requirements": {
                        "min_memory": "4GB",
                        "recommended_memory": "8GB",
                        "gpu_memory": "2GB"
                    }
                },
                {
                    "id": "deepseek-ai/Janus-Pro-7B",
                    "name": "Janus-Pro-7B",
                    "description": "高质量模型，精度高，适合详细分析",
                    "size": "7B",
                    "parameters": "7B",
                    "download_url": "https://huggingface.co/deepseek-ai/Janus-Pro-7B",
                    "local_path": None,
                    "is_downloaded": False,
                    "download_size": "14.2GB",
                    "requirements": {
                        "min_memory": "16GB",
                        "recommended_memory": "32GB",
                        "gpu_memory": "8GB"
                    }
                }
            ],
            "default_model": "deepseek-ai/Janus-Pro-1B",
            "model_types": {
                "reverse_inference": {
                    "supported_models": ["deepseek-ai/Janus-Pro-1B", "deepseek-ai/Janus-Pro-7B"],
                    "default_model": "deepseek-ai/Janus-Pro-1B"
                },
                "image_generation": {
                    "supported_models": ["deepseek-ai/Janus-Pro-1B", "deepseek-ai/Janus-Pro-7B"],
                    "default_model": "deepseek-ai/Janus-Pro-7B"
                }
            }
        }
    
    def _get_default_user_settings(self) -> Dict[str, Any]:
        """获取默认用户设置"""
        return {
            "user_settings": {
                "last_used_model": "deepseek-ai/Janus-Pro-1B",
                "last_used_model_path": None,
                "auto_download_models": True,
                "use_gpu": True,
                "max_memory_usage": 0.8,
                "save_results": True,
                "result_file_suffix": ".txt",
                "cache_enabled": True,
                "cache_size": 100,
                "cache_timeout": 3600
            },
            "reverse_inference_settings": {
                "last_question": "Describe this image in detail.",
                "last_temperature": 0.1,
                "last_top_p": 0.95,
                "last_max_new_tokens": 512,
                "last_seed": 666666666666666
            },
            "image_generation_settings": {
                "last_prompt": "A beautiful photo of",
                "last_seed": 666666666666666,
                "last_batch_size": 1,
                "last_cfg_weight": 5.0,
                "last_temperature": 1.0,
                "last_top_p": 0.95,
                "last_image_size": 384
            },
            "ui_settings": {
                "window_width": 800,
                "window_height": 600,
                "config_dialog_width": 600,
                "config_dialog_height": 500,
                "progress_dialog_width": 500,
                "progress_dialog_height": 300
            }
        }
    
    def get_config(self, key: str = None) -> Any:
        """获取配置值"""
        if key is None:
            return self.config
        return self.config.get(key)
    
    def get_models_config(self, key: str = None) -> Any:
        """获取模型配置值"""
        if key is None:
            return self.models_config
        return self.models_config.get(key)
    
    def get_user_settings(self, key: str = None) -> Any:
        """获取用户设置值"""
        if key is None:
            return self.user_settings
        return self.user_settings.get(key)
    
    def update_config(self, key: str, value: Any):
        """更新配置"""
        self.config[key] = value
        self._save_config()
    
    def update_models_config(self, key: str, value: Any):
        """更新模型配置"""
        self.models_config[key] = value
        self._save_models_config()
    
    def update_user_settings(self, key: str, value: Any):
        """更新用户设置"""
        self.user_settings[key] = value
        self._save_user_settings()
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        return self.models_config.get("models", [])
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取模型信息"""
        models = self.get_available_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息（别名方法）"""
        return self.get_model_by_id(model_id)
    
    def get_default_model(self) -> str:
        """获取默认模型ID"""
        return self.models_config.get("default_model", "deepseek-ai/Janus-Pro-1B")
    
    def get_models_directory(self) -> Path:
        """获取模型目录路径"""
        models_dir = self.config.get("models", {}).get("models_directory", "models")
        return self.plugin_dir / models_dir
    
    def get_reverse_inference_config(self) -> Dict[str, Any]:
        """获取反推配置"""
        return self.config.get("reverse_inference", {})
    
    def get_image_generation_config(self) -> Dict[str, Any]:
        """获取图片生成配置"""
        return self.config.get("image_generation", {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config.get("system", {})
    
    def save_default_config(self, config: Dict[str, Any]):
        """保存默认配置"""
        try:
            # 更新主配置
            self.config.update(config)
            self._save_config()
            
            # 更新用户设置
            if "user_settings" not in self.user_settings:
                self.user_settings["user_settings"] = {}
            
            # 保存模型相关设置
            if "model" in config:
                model_config = config["model"]
                self.user_settings["user_settings"]["last_used_model"] = model_config.get("model_id", "")
                self.user_settings["user_settings"]["last_used_model_path"] = model_config.get("model_path", "")
                self.user_settings["user_settings"]["auto_download_models"] = model_config.get("auto_download", True)
            
            # 保存系统设置
            if "system" in config:
                system_config = config["system"]
                self.user_settings["user_settings"]["use_gpu"] = system_config.get("use_gpu", True)
                self.user_settings["user_settings"]["max_memory_usage"] = system_config.get("max_memory_usage", 0.8)
                self.user_settings["user_settings"]["cache_enabled"] = system_config.get("cache_enabled", True)
                self.user_settings["user_settings"]["cache_size"] = system_config.get("cache_size", 100)
                self.user_settings["user_settings"]["cache_timeout"] = system_config.get("cache_timeout", 3600)
            
            self._save_user_settings()
            self.logger.info("默认配置保存成功")
            
        except Exception as e:
            self.logger.error(f"保存默认配置失败: {str(e)}")
            raise
