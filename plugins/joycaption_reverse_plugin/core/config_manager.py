"""
JoyCaption插件配置管理器
负责加载和管理插件配置
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """JoyCaption插件配置管理器"""
    
    def __init__(self):
        self.plugin_dir = Path(__file__).parent.parent
        self.config_dir = self.plugin_dir / "config"
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.core.config_manager")
        
        # 配置文件路径
        self.config_file = self.config_dir / "config.json"
        self.models_file = self.config_dir / "models.json"
        self.caption_types_file = self.config_dir / "caption_types.json"
        
        # 配置数据
        self.config = {}
        self.models_config = {}
        self.caption_types_config = {}
        
        self.initialize()
    
    def initialize(self):
        """初始化配置管理器"""
        try:
            self.logger.info("开始初始化JoyCaption配置管理器")
            
            # 加载主配置
            self.load_config()
            
            # 加载模型配置
            self.load_models_config()
            
            # 加载描述类型配置
            self.load_caption_types_config()
            
            self.logger.info("JoyCaption配置管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"配置管理器初始化失败: {str(e)}")
            raise
    
    def load_config(self):
        """加载主配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.logger.info(f"加载配置文件成功: {self.config_file}")
            else:
                self.logger.warning("配置文件不存在，使用默认配置")
                self.config = self.get_default_config()
                self.save_config()
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            self.config = self.get_default_config()
    
    def load_models_config(self):
        """加载模型配置文件"""
        try:
            if self.models_file.exists():
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    self.models_config = json.load(f)
                self.logger.info(f"加载模型配置文件成功: {self.models_file}")
            else:
                self.logger.warning("模型配置文件不存在")
                self.models_config = {}
        except Exception as e:
            self.logger.error(f"加载模型配置文件失败: {str(e)}")
            self.models_config = {}
    
    def load_caption_types_config(self):
        """加载描述类型配置文件"""
        try:
            if self.caption_types_file.exists():
                with open(self.caption_types_file, 'r', encoding='utf-8') as f:
                    self.caption_types_config = json.load(f)
                self.logger.info(f"加载描述类型配置文件成功: {self.caption_types_file}")
            else:
                self.logger.warning("描述类型配置文件不存在")
                self.caption_types_config = {}
        except Exception as e:
            self.logger.error(f"加载描述类型配置文件失败: {str(e)}")
            self.caption_types_config = {}
    
    def save_config(self):
        """保存配置文件"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info("配置文件保存成功")
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "models": {
                "default_model": "fancyfeast/llama-joycaption-beta-one-hf-llava",
                "available_models": [
                    "fancyfeast/llama-joycaption-beta-one-hf-llava",
                    "fancyfeast/llama-joycaption-alpha-two-hf-llava"
                ]
            },
            "inference": {
                "precision": "Balanced (8-bit)",
                "max_new_tokens": 512,
                "temperature": 0.6,
                "top_p": 0.9,
                "top_k": 0,
                "default_level": "normal",
                "default_caption_type": "Descriptive"
            },
            "output": {
                "save_to_file": True,
                "save_to_database": True,
                "auto_display": True,
                "file_encoding": "utf-8"
            },
            "performance": {
                "batch_size": 4,
                "use_gpu": True,
                "cache_models": True,
                "max_memory_usage": 0.8
            },
            "ui": {
                "show_progress": True,
                "auto_refresh": True,
                "confirm_batch_operation": True
            },
            "description_levels": {
                "simple": {
                    "name": "简单描述",
                    "description": "以词、词组组成的对图片内容的简单描述",
                    "max_tokens": 128
                },
                "normal": {
                    "name": "普通描述",
                    "description": "用简单的自然语句，一般是几句话描述的图片内容",
                    "max_tokens": 256
                },
                "detailed": {
                    "name": "详细描述",
                    "description": "用很多句话组成的对图案细节详细描述的内容",
                    "max_tokens": 512
                }
            }
        }
    
    def get_config(self, key: str, default=None) -> Any:
        """
        获取配置值，支持点分隔的嵌套键
        
        Args:
            key (str): 配置键，支持点分隔的嵌套键，如 "models.default_model"
            default: 默认值，当键不存在时返回
            
        Returns:
            Any: 配置值或默认值
            
        Example:
            >>> get_config("models.default_model")
            "fancyfeast/llama-joycaption-beta-one-hf-llava"
            >>> get_config("inference.temperature", 0.6)
            0.6
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_config(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        return self.models_config.get(model_id)
    
    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        return self.models_config.get("models", {})
    
    def get_default_model(self) -> str:
        """获取默认模型ID"""
        return self.models_config.get("default_model", "fancyfeast/llama-joycaption-beta-one-hf-llava")
    
    def get_caption_types(self) -> Dict[str, Any]:
        """获取描述类型配置"""
        return self.caption_types_config.get("caption_types", {})
    
    def get_memory_configs(self) -> Dict[str, Any]:
        """获取内存配置"""
        return self.models_config.get("memory_efficient_configs", {})
    
    def get_extra_options(self) -> Dict[str, Any]:
        """获取额外选项配置"""
        return self.caption_types_config.get("extra_options", {})
    
    def get_caption_length_choices(self) -> list:
        """获取描述长度选项"""
        return self.caption_types_config.get("caption_lengths", [])
    
    def get_description_levels(self) -> Dict[str, Any]:
        """获取描述级别配置"""
        return self.config.get("description_levels", {})
    
    def get_inference_config(self) -> Dict[str, Any]:
        """获取推理配置"""
        return self.config.get("inference", {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.config.get("output", {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        return self.config.get("performance", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        return self.config.get("ui", {})
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        self._update_nested_dict(self.config, updates)
        self.save_config()
    
    def _update_nested_dict(self, target: Dict[str, Any], updates: Dict[str, Any]):
        """递归更新嵌套字典"""
        for key, value in updates.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def save_as_default_config(self, config: Dict[str, Any]):
        """
        保存当前配置为默认配置，用于快速处理功能
        
        Args:
            config (Dict[str, Any]): 要保存的配置字典，包含模型、推理、输出等参数
            
        Note:
            - 会更新推理配置、模型配置、输出配置等
            - 配置会持久化保存到配置文件
            - 保存后可用于快速处理功能
            
        Returns:
            None: 无返回值
            
        Raises:
            Exception: 保存失败时抛出异常
        """
        try:
            # 更新推理配置
            inference_config = {
                "default_level": config.get("description_level", "normal"),
                "default_caption_type": config.get("caption_type", "Descriptive"),
                "precision": config.get("precision", "Balanced (8-bit)"),
                "max_new_tokens": config.get("max_new_tokens", 512),
                "temperature": config.get("temperature", 0.6),
                "top_p": config.get("top_p", 0.9),
                "top_k": config.get("top_k", 0)
            }
            
            # 更新模型配置
            if "models" not in self.config:
                self.config["models"] = {}
            self.config["models"]["default_model"] = config.get("model_id", "fancyfeast/llama-joycaption-beta-one-hf-llava")
            
            # 更新推理配置
            if "inference" not in self.config:
                self.config["inference"] = {}
            self.config["inference"].update(inference_config)
            
            # 更新输出配置
            if "output" not in self.config:
                self.config["output"] = {}
            self.config["output"].update({
                "save_to_file": config.get("save_to_file", True),
                "save_to_database": config.get("save_to_database", True),
                "auto_display": config.get("auto_display", True)
            })
            
            # 保存配置
            self.save_config()
            self.logger.info("默认配置已保存")
            
        except Exception as e:
            self.logger.error(f"保存默认配置失败: {str(e)}")
            raise
    
    def get_default_processing_config(self) -> Dict[str, Any]:
        """获取默认处理配置（不包含图片路径）"""
        try:
            inference_config = self.get_inference_config()
            output_config = self.get_output_config()
            
            return {
                "model_id": self.get_default_model(),
                "precision": inference_config.get("precision", "Balanced (8-bit)"),
                "caption_type": inference_config.get("default_caption_type", "Descriptive"),
                "caption_length": "any",
                "description_level": inference_config.get("default_level", "normal"),
                "max_new_tokens": inference_config.get("max_new_tokens", 512),
                "temperature": inference_config.get("temperature", 0.6),
                "top_p": inference_config.get("top_p", 0.9),
                "top_k": inference_config.get("top_k", 0),
                "save_to_file": output_config.get("save_to_file", True),
                "save_to_database": output_config.get("save_to_database", True),
                "auto_display": output_config.get("auto_display", True),
                "extra_options": []
            }
        except Exception as e:
            self.logger.error(f"获取默认处理配置失败: {str(e)}")
            return {} 