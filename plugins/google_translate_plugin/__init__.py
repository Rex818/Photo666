"""
Google翻译插件
使用免费的googletrans库进行标签翻译
"""

__version__ = "1.0.0"
__author__ = "Photo666 Team"
__description__ = "Google翻译插件"

# 延迟导入，避免相对导入问题
from .plugin import GoogleTranslatePlugin

__all__ = ["GoogleTranslatePlugin"] 