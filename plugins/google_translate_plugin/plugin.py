#!/usr/bin/env python3
"""
Google翻译插件主文件
使用免费的googletrans库进行标签翻译
"""

import json
import time
import random
from typing import Dict, List, Optional, Any
import structlog
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

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

logger = structlog.get_logger(__name__)


class GoogleTranslatePlugin(Plugin):
    """Google翻译插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "Google翻译插件"
        self.version = "1.0.0"
        self.description = "使用免费的googletrans库进行标签翻译"
        self.author = "Photo666 Team"
        
        # 配置
        self.source_language = "en"
        self.target_language = "zh-CN"
        self.translator = None
        
        # 翻译缓存
        self.translation_cache = {}
        
        # 请求控制参数
        self.max_retries = 3
        self.base_delay = 0.5
        self.max_delay = 2.0
        self.request_interval = 1.0  # 请求间隔（秒）
        self.last_request_time = 0
        
        # 日志记录器
        self.logger = logger
        
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
    
    def initialize(self, app_context: Dict[str, any] = None) -> bool:
        """初始化插件"""
        try:
            # 从应用上下文获取配置
            if app_context:
                config = app_context.get("config", {})
                
                # 更新语言设置
                self.source_language = config.get("source_language", "en")
                self.target_language = config.get("target_language", "zh-CN")
                
                # 更新请求控制参数
                self.max_retries = config.get("max_retries", 3)
                self.base_delay = config.get("base_delay", 0.5)
                self.max_delay = config.get("max_delay", 2.0)
                self.request_interval = config.get("request_interval", 1.0)
            
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
                "type": "select",
                "label": "源语言",
                "description": "源语言代码",
                "default": "en",
                "options": [
                    {"value": "en", "label": "英语"},
                    {"value": "zh-CN", "label": "中文（简体）"},
                    {"value": "zh-TW", "label": "中文（繁体）"},
                    {"value": "ja", "label": "日语"},
                    {"value": "ko", "label": "韩语"},
                    {"value": "fr", "label": "法语"},
                    {"value": "de", "label": "德语"},
                    {"value": "es", "label": "西班牙语"},
                    {"value": "ru", "label": "俄语"},
                    {"value": "auto", "label": "自动检测"}
                ]
            },
            "target_language": {
                "type": "select",
                "label": "目标语言",
                "description": "目标语言代码",
                "default": "zh-CN",
                "options": [
                    {"value": "en", "label": "英语"},
                    {"value": "zh-CN", "label": "中文（简体）"},
                    {"value": "zh-TW", "label": "中文（繁体）"},
                    {"value": "ja", "label": "日语"},
                    {"value": "ko", "label": "韩语"},
                    {"value": "fr", "label": "法语"},
                    {"value": "de", "label": "德语"},
                    {"value": "es", "label": "西班牙语"},
                    {"value": "ru", "label": "俄语"}
                ]
            },
            "max_retries": {
                "type": "integer",
                "label": "最大重试次数",
                "description": "翻译失败时的最大重试次数（默认：3）",
                "default": 3
            },
            "base_delay": {
                "type": "float",
                "label": "基础延迟时间",
                "description": "请求间的基础延迟时间（秒，默认：0.5）",
                "default": 0.5
            },
            "max_delay": {
                "type": "float",
                "label": "最大延迟时间",
                "description": "请求间的最大延迟时间（秒，默认：2.0）",
                "default": 2.0
            },
            "request_interval": {
                "type": "float",
                "label": "请求间隔",
                "description": "连续请求的最小间隔时间（秒，默认：1.0）",
                "default": 1.0
            }
        }
    
    def _wait_for_next_request(self):
        """等待到下一个请求时间"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def translate_text(self, text: str) -> Optional[str]:
        """翻译单个文本（带重试机制）"""
        try:
            # 检查缓存
            if text in self.translation_cache:
                return self.translation_cache[text]
            
            if not self.translator:
                self.logger.warning("Translator not available")
                return None
            
            # 等待请求间隔
            self._wait_for_next_request()
            
            # 重试机制
            for attempt in range(self.max_retries):
                try:
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
                    self.logger.warning(f"Translation attempt {attempt + 1} failed", text=text, error=str(e))
                    
                    if attempt < self.max_retries - 1:
                        # 指数退避延迟
                        delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 0.1), self.max_delay)
                        time.sleep(delay)
                        
                        # 重新创建翻译器实例（可能解决连接问题）
                        try:
                            self.translator = Translator()
                        except Exception:
                            pass
                    else:
                        self.logger.error("Translation failed after all retries", text=text, error=str(e))
                        return None
            
            return None
            
        except Exception as e:
            self.logger.error("Translation failed", text=text, error=str(e))
            return None
    
    def translate_tags(self, tags: List[str]) -> Dict[str, str]:
        """翻译标签列表（带错误处理）"""
        try:
            translations = {}
            failed_tags = []
            
            self.logger.info(f"开始翻译 {len(tags)} 个标签")
            
            for i, tag in enumerate(tags):
                try:
                    if tag in self.translation_cache:
                        translations[tag] = self.translation_cache[tag]
                        self.logger.debug(f"使用缓存翻译: {tag}")
                    else:
                        translation = self.translate_text(tag)
                        if translation and translation != tag:
                            translations[tag] = translation
                            self.translation_cache[tag] = translation
                            self.logger.debug(f"翻译成功: {tag} -> {translation}")
                        else:
                            # 如果翻译失败或翻译结果与原文本相同，使用原标签
                            translations[tag] = tag
                            failed_tags.append(tag)
                            self.logger.warning(f"翻译失败或无效: {tag}")
                    
                    # 每翻译10个标签输出一次进度
                    if (i + 1) % 10 == 0:
                        self.logger.info(f"翻译进度: {i + 1}/{len(tags)}")
                        
                except Exception as e:
                    self.logger.error(f"翻译标签时出错: {tag}", error=str(e))
                    translations[tag] = tag
                    failed_tags.append(tag)
            
            self.logger.info("Tags translated", 
                           count=len(tags), 
                           translated_count=len(translations) - len(failed_tags),
                           failed_count=len(failed_tags))
            
            if failed_tags:
                self.logger.warning(f"翻译失败的标签: {failed_tags}")
            
            return translations
            
        except Exception as e:
            self.logger.error("Failed to translate tags", error=str(e))
            # 返回原标签作为翻译
            return {tag: tag for tag in tags}
    
    def show_translate_dialog(self, parent=None):
        """显示翻译对话框"""
        try:
            self.logger.info("显示Google翻译对话框")
            
            # 这里先显示一个简单的消息框，后续会实现完整的对话框
            from PyQt6.QtWidgets import QMessageBox
            
            if parent:
                QMessageBox.information(
                    parent,
                    "Google翻译",
                    "Google翻译功能正在开发中...\n\n"
                    "功能包括：\n"
                    "• 支持多种语言翻译\n"
                    "• 标签批量翻译\n"
                    "• 翻译结果缓存\n"
                    "• 自定义源语言和目标语言\n"
                    "• 智能重试机制"
                )
            else:
                print("Google翻译功能正在开发中...")
            
            return True
            
        except Exception as e:
            self.logger.error("显示翻译对话框失败", error=str(e))
            return False
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """获取菜单动作"""
        return [
            {
                "menu": "工具",
                "title": "Google翻译",
                "action": "show_translate_dialog",
                "description": "使用Google翻译服务翻译标签"
            }
        ]
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        return [
            {
                "title": "Google翻译",
                "action": "show_translate_dialog",
                "description": "使用Google翻译服务翻译标签",
                "icon": "translate"  # 使用翻译图标
            }
        ]
    
    def get_settings(self) -> Dict[str, any]:
        """获取插件设置"""
        return {
            "source_language": self.source_language,
            "target_language": self.target_language,
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "request_interval": self.request_interval,
            "enabled": self.translator is not None
        }
    
    def update_settings(self, settings: Dict[str, any]) -> bool:
        """更新插件设置"""
        try:
            if "source_language" in settings:
                self.source_language = settings["source_language"]
            if "target_language" in settings:
                self.target_language = settings["target_language"]
            if "max_retries" in settings:
                self.max_retries = settings["max_retries"]
            if "base_delay" in settings:
                self.base_delay = settings["base_delay"]
            if "max_delay" in settings:
                self.max_delay = settings["max_delay"]
            if "request_interval" in settings:
                self.request_interval = settings["request_interval"]
            return True
        except Exception as e:
            self.logger.error("Failed to update settings", error=str(e))
            return False 