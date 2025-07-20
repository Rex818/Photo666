#!/usr/bin/env python3
"""
Google翻译插件
使用免费的googletrans库进行标签翻译
"""

import json
import time
from typing import Dict, List, Optional
import structlog
# 修复导入路径
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from picman.plugins.base import Plugin, PluginInfo
except ImportError:
    # 如果无法导入，创建简单的基类
    class Plugin:
        def __init__(self):
            pass
    
    class PluginInfo:
        def __init__(self, name, version, description, author):
            self.name = name
            self.version = version
            self.description = description
            self.author = author

# 导入googletrans
try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False


class GoogleTranslatePlugin(Plugin):
    """Google翻译插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "Google翻译插件"
        self.version = "1.0.0"
        self.description = "使用免费的googletrans库进行标签翻译"
        self.author = "PicMan Team"
        
        # 配置
        self.source_language = "en"
        self.target_language = "zh-CN"
        self.translator = None
        
        # 翻译缓存
        self.translation_cache = {}
        
        # 初始化翻译器
        if GOOGLETRANS_AVAILABLE:
            try:
                self.translator = Translator()
                self.logger.info("Google Translate plugin initialized with googletrans")
            except Exception as e:
                self.logger.error("Failed to initialize googletrans translator", error=str(e))
                self.translator = None
        else:
            self.logger.warning("googletrans library not available")
        
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author
        )
    
    def initialize(self, app_context: Dict[str, any]) -> bool:
        """初始化插件"""
        try:
            # 从应用上下文获取配置
            config = app_context.get("config", {})
            
            # 更新语言设置
            self.source_language = config.get("source_language", "en")
            self.target_language = config.get("target_language", "zh-CN")
            
            # 检查翻译器是否可用
            if not self.translator:
                self.logger.warning("Google Translate translator not available")
                return False
            
            self.logger.info("Google Translate plugin initialized with googletrans")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Google Translate plugin", error=str(e))
            return False
    
    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            self.translation_cache.clear()
            self.logger.info("Google Translate plugin shutdown")
            return True
        except Exception as e:
            self.logger.error("Failed to shutdown Google Translate plugin", error=str(e))
            return False
    
    def get_config_schema(self) -> Dict[str, any]:
        """获取配置模式"""
        return {
            "source_language": {
                "type": "string",
                "label": "源语言",
                "description": "源语言代码（默认：en）",
                "default": "en"
            },
            "target_language": {
                "type": "string",
                "label": "目标语言",
                "description": "目标语言代码（默认：zh-CN）",
                "default": "zh-CN"
            }
        }
    
    def translate_text(self, text: str) -> Optional[str]:
        """翻译单个文本"""
        try:
            # 检查缓存
            if text in self.translation_cache:
                return self.translation_cache[text]
            
            if not self.translator:
                self.logger.warning("Translator not available")
                return None
            
            # 使用googletrans进行翻译
            result = self.translator.translate(
                text, 
                src=self.source_language, 
                dest=self.target_language
            )
            
            if result and result.text:
                translation = result.text
                # 缓存结果
                self.translation_cache[text] = translation
                self.logger.debug("Translation successful", text=text, translation=translation)
                return translation
            
            return None
            
        except Exception as e:
            self.logger.error("Translation failed", text=text, error=str(e))
            # 添加延迟避免请求过快
            time.sleep(0.5)
            return None
    
    def translate_tags(self, tags: List[str]) -> Dict[str, str]:
        """翻译标签列表"""
        try:
            translations = {}
            
            for tag in tags:
                if tag in self.translation_cache:
                    translations[tag] = self.translation_cache[tag]
                else:
                    translation = self.translate_text(tag)
                    if translation:
                        translations[tag] = translation
                        self.translation_cache[tag] = translation
                    else:
                        # 如果翻译失败，使用原标签
                        translations[tag] = tag
            
            self.logger.info("Tags translated", count=len(tags), translated_count=len(translations))
            return translations
            
        except Exception as e:
            self.logger.error("Failed to translate tags", error=str(e))
            # 返回原标签作为翻译
            return {tag: tag for tag in tags}
    
    def get_settings(self) -> Dict[str, any]:
        """获取插件设置"""
        return {
            "source_language": self.source_language,
            "target_language": self.target_language,
            "enabled": self.translator is not None
        }
    
    def update_settings(self, settings: Dict[str, any]) -> bool:
        """更新插件设置"""
        try:
            if "source_language" in settings:
                self.source_language = settings["source_language"]
            if "target_language" in settings:
                self.target_language = settings["target_language"]
            return True
        except Exception as e:
            self.logger.error("Failed to update settings", error=str(e))
            return False 