"""
配置管理器
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from plugins.florence2_reverse_plugin.utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.plugin_dir = Path(__file__).parent.parent
        self.config_dir = self.plugin_dir / "config"
        self.config_file = self.config_dir / "config.json"
        self.models_file = self.config_dir / "models.json"
        
        self.config = {}
        self.models_config = {}
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """初始化配置管理器"""
        try:
            # 确保配置目录存在
            FileUtils.ensure_directory(str(self.config_dir))
            
            # 加载配置文件
            self._load_config()
            self._load_models_config()
            
            self.is_initialized = True
            logger.info("配置管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"配置管理器初始化失败: {str(e)}")
            return False
    
    def _load_config(self):
        """加载主配置文件"""
        try:
            if self.config_file.exists():
                self.config = FileUtils.load_json_file(str(self.config_file))
                logger.info(f"加载配置文件成功 - 文件: {self.config_file}")
            else:
                # 创建默认配置
                self.config = self._get_default_config()
                self.save_config()
                logger.info(f"创建默认配置文件 - 文件: {self.config_file}")
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            self.config = self._get_default_config()
    
    def _load_models_config(self):
        """加载模型配置文件"""
        try:
            if self.models_file.exists():
                self.models_config = FileUtils.load_json_file(str(self.models_file))
                logger.info(f"加载模型配置文件成功 - 文件: {self.models_file}")
            else:
                # 创建默认模型配置
                self.models_config = self._get_default_models_config()
                self.save_models_config()
                logger.info(f"创建默认模型配置文件 - 文件: {self.models_file}")
                
        except Exception as e:
            logger.error(f"加载模型配置文件失败: {str(e)}")
            self.models_config = self._get_default_models_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "models": {
                "default_model": "microsoft/Florence-2-base",
                "available_models": [
                    "microsoft/Florence-2-base",
                    "microsoft/Florence-2-base-ft",
                    "microsoft/Florence-2-large",
                    "microsoft/Florence-2-large-ft",
                    "MiaoshouAI/Florence-2-base-PromptGen-v1.5",
                    "MiaoshouAI/Florence-2-large-PromptGen-v1.5"
                ]
            },
            "inference": {
                "precision": "fp16",
                "attention": "sdpa",
                "max_new_tokens": 1024,
                "num_beams": 3,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.9
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
            }
        }
    
    def _get_default_models_config(self) -> Dict[str, Any]:
        """获取默认模型配置"""
        return {
            "microsoft/Florence-2-base": {
                "name": "Florence-2 Base",
                "description": "Microsoft Florence-2 基础模型",
                "size": "1.2GB",
                "tasks": ["caption", "detailed_caption", "prompt_gen_tags"],
                "recommended": True,
                "download_url": "https://huggingface.co/microsoft/Florence-2-base"
            },
            "microsoft/Florence-2-base-ft": {
                "name": "Florence-2 Base (Fine-tuned)",
                "description": "Microsoft Florence-2 基础模型（微调版）",
                "size": "1.2GB",
                "tasks": ["caption", "detailed_caption", "prompt_gen_tags"],
                "recommended": False,
                "download_url": "https://huggingface.co/microsoft/Florence-2-base-ft"
            },
            "microsoft/Florence-2-large": {
                "name": "Florence-2 Large",
                "description": "Microsoft Florence-2 大型模型",
                "size": "3.8GB",
                "tasks": ["caption", "detailed_caption", "prompt_gen_tags"],
                "recommended": False,
                "download_url": "https://huggingface.co/microsoft/Florence-2-large"
            },
            "microsoft/Florence-2-large-ft": {
                "name": "Florence-2 Large (Fine-tuned)",
                "description": "Microsoft Florence-2 大型模型（微调版）",
                "size": "3.8GB",
                "tasks": ["caption", "detailed_caption", "prompt_gen_tags"],
                "recommended": False,
                "download_url": "https://huggingface.co/microsoft/Florence-2-large-ft"
            },
            "MiaoshouAI/Florence-2-base-PromptGen-v1.5": {
                "name": "Florence-2 PromptGen v1.5",
                "description": "优化的提示词生成模型",
                "size": "1.2GB",
                "tasks": ["prompt_gen_tags", "caption"],
                "recommended": True,
                "download_url": "https://huggingface.co/MiaoshouAI/Florence-2-base-PromptGen-v1.5"
            },
            "MiaoshouAI/Florence-2-large-PromptGen-v1.5": {
                "name": "Florence-2 Large PromptGen v1.5",
                "description": "大型优化提示词生成模型",
                "size": "3.8GB",
                "tasks": ["prompt_gen_tags", "caption"],
                "recommended": False,
                "download_url": "https://huggingface.co/MiaoshouAI/Florence-2-large-PromptGen-v1.5"
            }
        }
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            return FileUtils.save_json_file(str(self.config_file), self.config)
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def save_models_config(self) -> bool:
        """保存模型配置文件"""
        try:
            return FileUtils.save_json_file(str(self.models_file), self.models_config)
        except Exception as e:
            logger.error(f"保存模型配置文件失败: {str(e)}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取配置值失败 {key}: {str(e)}")
            return default
    
    def set_config(self, key: str, value: Any) -> bool:
        """设置配置值"""
        try:
            keys = key.split('.')
            config = self.config
            
            # 遍历到最后一个键
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            # 保存配置
            success = self.save_config()
            if success:
                logger.info(f"配置值设置成功: {key}={value}")
            return success
            
        except Exception as e:
            logger.error(f"设置配置值失败 {key}={value}: {str(e)}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        try:
            return self.models_config.get(model_name)
        except Exception as e:
            logger.error(f"获取模型信息失败 {model_name}: {str(e)}")
            return None
    
    def get_available_models(self) -> list:
        """获取可用模型列表"""
        try:
            return list(self.models_config.keys())
        except Exception as e:
            logger.error(f"获取可用模型列表失败: {str(e)}")
            return []
    
    def get_recommended_models(self) -> list:
        """获取推荐模型列表"""
        try:
            recommended = []
            for model_name, model_info in self.models_config.items():
                if model_info.get("recommended", False):
                    recommended.append(model_name)
            return recommended
        except Exception as e:
            logger.error(f"获取推荐模型列表失败: {str(e)}")
            return []
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        try:
            return self.get_config("models.default_model", "microsoft/Florence-2-base")
        except Exception as e:
            logger.error(f"获取默认模型失败: {str(e)}")
            return "microsoft/Florence-2-base"
    
    def get_inference_config(self) -> Dict[str, Any]:
        """获取推理配置"""
        try:
            return self.get_config("inference", {})
        except Exception as e:
            logger.error(f"获取推理配置失败: {str(e)}")
            return {}
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        try:
            return self.get_config("output", {})
        except Exception as e:
            logger.error(f"获取输出配置失败: {str(e)}")
            return {}
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能配置"""
        try:
            return self.get_config("performance", {})
        except Exception as e:
            logger.error(f"获取性能配置失败: {str(e)}")
            return {}
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        try:
            return self.get_config("ui", {})
        except Exception as e:
            logger.error(f"获取UI配置失败: {str(e)}")
            return {}
    
    def save_as_default_config(self, config: Dict[str, Any]) -> bool:
        """保存为默认配置"""
        try:
            # 更新模型配置
            if "model_name" in config:
                self.set_config("models.default_model", config["model_name"])
            
            # 更新自定义路径配置
            if "custom_path" in config:
                self.set_config("models.custom_path", config["custom_path"])
            else:
                # 如果没有自定义路径，清除配置
                self.set_config("models.custom_path", "")
            
            # 更新描述级别配置
            if "description_level" in config:
                self.set_config("inference.default_level", config["description_level"])
            
            # 强制保存配置
            success = self.save_config()
            if success:
                logger.info("默认配置保存成功")
                logger.info(f"保存的配置: {config}")
            return success
            
        except Exception as e:
            logger.error(f"保存默认配置失败: {str(e)}")
            return False
    
    def get_default_processing_config(self) -> Dict[str, Any]:
        """获取默认处理配置"""
        try:
            return {
                "model_name": self.get_default_model(),
                "custom_path": self.get_config("models.custom_path", ""),
                "description_level": self.get_config("inference.default_level", "normal"),
                "inference_config": self.get_inference_config()
            }
        except Exception as e:
            logger.error(f"获取默认处理配置失败: {str(e)}")
            return {} 