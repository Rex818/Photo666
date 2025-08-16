"""
Translation utilities for PyPhotoManager.
Provides internationalization support.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranslationManager:
    """Manages application translations."""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = logger
        self.translations = {}
        self.current_language = "en"  # Default language
        
        # Load available translations
        self.load_translations()
        
        # Set initial language from config if available
        if self.config:
            self.set_language(self.config.get("ui.language", "zh_CN"))
    
    def load_translations(self):
        """Load all available translations."""
        try:
            # Get translations directory
            base_dir = Path(__file__).parent.parent.parent.parent  # Go up to project root
            translations_dir = base_dir / "translations"
            
            if not translations_dir.exists():
                translations_dir.mkdir(parents=True, exist_ok=True)
                self._create_default_translations(translations_dir)
            
            # Load each translation file
            for file_path in translations_dir.glob("*.json"):
                language_code = file_path.stem
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.translations[language_code] = json.load(f)
                    self.logger.info(f"Loaded translation for language: {language_code}")
                except Exception as e:
                    self.logger.error(f"Failed to load translation for language {language_code}: {str(e)}")
            
            # If no translations were loaded, create default ones
            if not self.translations:
                self._create_default_translations(translations_dir)
                
        except Exception as e:
            self.logger.error(f"Failed to load translations: {str(e)}")
            # Ensure we at least have English
            if "en" not in self.translations:
                self.translations["en"] = {}
    
    def _create_default_translations(self, translations_dir: Path):
        """Create default translation files."""
        # English (default)
        en_translations = {
            "app.title": "PyPhotoManager - Professional Photo Management",
            "menu.file": "File",
            "menu.file.import_photos": "Import Photos...",
            "menu.file.import_folder": "Import Folder...",
            "menu.file.export": "Export",
            "menu.file.export_selected": "Export Selected Photos...",
            "menu.file.export_album": "Export Album...",
            "menu.file.exit": "Exit",
            "menu.edit": "Edit",
            "menu.edit.select_all": "Select All",
            "menu.edit.deselect_all": "Deselect All",
            "menu.edit.delete_selected": "Delete Selected Photos",
            "menu.view": "View",
            "menu.view.refresh": "Refresh",
            "menu.view.thumbnails": "Thumbnails",
            "menu.view.list": "List",
            "menu.view.details": "Details",
            "menu.view.show_albums": "Show Albums Panel",
            "menu.view.show_tags": "Show Tags Panel",
            "menu.album": "Album",
            "menu.album.new": "New Album...",
            "menu.album.add_selected": "Add Selected to Album...",
            "menu.tools": "Tools",
            "menu.tools.batch_process": "Batch Process...",
            "menu.tools.manage_tags": "Manage Tags...",
            "menu.tools.settings": "Settings...",
            "menu.plugins": "Plugins",
            "menu.plugins.manage": "Manage Plugins...",
            "menu.help": "Help",
            "menu.help.contents": "Help Contents",
            "menu.help.log_viewer": "Log Viewer",
            "menu.help.about": "About",
            "ui.search": "Search:",
            "ui.search.placeholder": "Search photos...",
            "ui.search.button": "Search",
            "ui.filter.min_rating": "Min Rating:",
            "ui.filter.favorites_only": "Favorites Only",
            "ui.view": "View:",
            "ui.filter": "Filter:",
            "ui.filter.all_photos": "All Photos",
            "ui.filter.favorites": "Favorites",
            "ui.filter.recent": "Recent",
            "ui.filter.untagged": "Untagged",
            "ui.status.ready": "Ready",
            "ui.status.photos_count": "{0} photos",
            "dialog.import.title": "Import Photos",
            "dialog.import.progress": "Importing photos...",
            "dialog.import.cancel": "Cancel",
            "dialog.import.complete": "Import Complete",
            "dialog.import.result": "Imported {0} of {1} photos.",
            "dialog.import.folder.progress": "Importing photos from directory...",
            "dialog.import.folder.complete": "Import completed!",
            "dialog.import.folder.result": "Imported: {0}\nSkipped: {1}\nErrors: {2}",
            "dialog.import.error": "Import Error",
            "dialog.import.error.message": "Import failed: {0}",
            "dialog.no_selection": "No Selection",
            "dialog.no_selection.message": "No photos selected.",
            "dialog.delete.title": "Delete Photos",
            "dialog.delete.confirm": "Are you sure you want to delete {0} selected photos?",
            "dialog.delete.success": "Photos deleted successfully.",
            "dialog.add_to_album.title": "Add to Album",
            "dialog.add_to_album.not_implemented": "Album selector not implemented yet.",
            "dialog.export.title": "Export Photos",
            "dialog.export.select_dir": "Select Export Directory",
            "dialog.export.result": "Exporting {0} photos to {1}.",
            "dialog.export_album.title": "Export Album",
            "dialog.export_album.not_implemented": "Album export not implemented yet.",
            "dialog.help.title": "Help",
            "dialog.help.not_implemented": "Help documentation not implemented yet.",
            "dialog.about.title": "About PyPhotoManager",
            "dialog.about.message": "PyPhotoManager v0.1.0\n\nProfessional Photo Management Software\nBuilt with PyQt6 and Python",
            "settings.language": "Language:",
            "settings.language.en": "English",
            "settings.language.zh": "中文 (Chinese)",
            "settings.apply": "Apply",
            "settings.cancel": "Cancel",
            "settings.save": "Save",
            "settings.title": "Settings"
        }
        
        # Chinese
        zh_translations = {
            "app.title": "PyPhotoManager - 专业照片管理",
            "menu.file": "文件",
            "menu.file.import_photos": "导入照片...",
            "menu.file.import_folder": "导入文件夹...",
            "menu.file.export": "导出",
            "menu.file.export_selected": "导出选中照片...",
            "menu.file.export_album": "导出相册...",
            "menu.file.exit": "退出",
            "menu.edit": "编辑",
            "menu.edit.select_all": "全选",
            "menu.edit.deselect_all": "取消全选",
            "menu.edit.delete_selected": "删除选中照片",
            "menu.view": "视图",
            "menu.view.refresh": "刷新",
            "menu.view.thumbnails": "缩略图",
            "menu.view.list": "列表",
            "menu.view.details": "详情",
            "menu.view.show_albums": "显示相册面板",
            "menu.view.show_tags": "显示标签面板",
            "menu.album": "相册",
            "menu.album.new": "新建相册...",
            "menu.album.add_selected": "添加选中照片到相册...",
            "menu.tools": "工具",
            "menu.tools.batch_process": "批量处理...",
            "menu.tools.manage_tags": "管理标签...",
            "menu.tools.settings": "设置...",
            "menu.plugins": "插件",
            "menu.plugins.manage": "管理插件...",
            "menu.help": "帮助",
            "menu.help.contents": "帮助内容",
            "menu.help.log_viewer": "日志查看器",
            "menu.help.about": "关于",
            "ui.search": "搜索:",
            "ui.search.placeholder": "搜索照片...",
            "ui.search.button": "搜索",
            "ui.filter.min_rating": "最低评分:",
            "ui.filter.favorites_only": "仅收藏",
            "ui.view": "视图:",
            "ui.filter": "筛选:",
            "ui.filter.all_photos": "所有照片",
            "ui.filter.favorites": "收藏",
            "ui.filter.recent": "最近",
            "ui.filter.untagged": "未标记",
            "ui.status.ready": "就绪",
            "ui.status.photos_count": "{0} 张照片",
            "dialog.import.title": "导入照片",
            "dialog.import.progress": "正在导入照片...",
            "dialog.import.cancel": "取消",
            "dialog.import.complete": "导入完成",
            "dialog.import.result": "已导入 {0} 张照片，共 {1} 张。",
            "dialog.import.folder.progress": "正在从目录导入照片...",
            "dialog.import.folder.complete": "导入完成！",
            "dialog.import.folder.result": "已导入: {0}\n已跳过: {1}\n错误: {2}",
            "dialog.import.error": "导入错误",
            "dialog.import.error.message": "导入失败: {0}",
            "dialog.no_selection": "未选择",
            "dialog.no_selection.message": "未选择照片。",
            "dialog.delete.title": "删除照片",
            "dialog.delete.confirm": "确定要删除 {0} 张选中的照片吗？",
            "dialog.delete.success": "照片已成功删除。",
            "dialog.add_to_album.title": "添加到相册",
            "dialog.add_to_album.not_implemented": "相册选择器尚未实现。",
            "dialog.export.title": "导出照片",
            "dialog.export.select_dir": "选择导出目录",
            "dialog.export.result": "正在导出 {0} 张照片到 {1}。",
            "dialog.export_album.title": "导出相册",
            "dialog.export_album.not_implemented": "相册导出尚未实现。",
            "dialog.help.title": "帮助",
            "dialog.help.not_implemented": "帮助文档尚未实现。",
            "dialog.about.title": "关于 PyPhotoManager",
            "dialog.about.message": "PyPhotoManager v0.1.0\n\n专业照片管理软件\n使用 PyQt6 和 Python 构建",
            "settings.language": "语言:",
            "settings.language.en": "English",
            "settings.language.zh": "中文 (Chinese)",
            "settings.apply": "应用",
            "settings.cancel": "取消",
            "settings.save": "保存",
            "settings.title": "设置"
        }
        
        # Save translation files
        with open(translations_dir / "en.json", "w", encoding="utf-8") as f:
            json.dump(en_translations, f, ensure_ascii=False, indent=2)
        
        with open(translations_dir / "zh.json", "w", encoding="utf-8") as f:
            json.dump(zh_translations, f, ensure_ascii=False, indent=2)
        
        # Load the translations
        self.translations["en"] = en_translations
        self.translations["zh"] = zh_translations
        
        self.logger.info("Created default translations for languages: en, zh")
    
    def set_language(self, language_code: str) -> bool:
        """Set the current language."""
        if language_code in self.translations:
            self.current_language = language_code
            if self.config:
                self.config.set("ui.language", language_code)
            self.logger.info(f"Language changed to: {language_code}")
            return True
        else:
            self.logger.warning(f"Language not available: {language_code}, available: {list(self.translations.keys())}")
            return False
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages with their display names."""
        languages = {
            "en": "English",
            "zh": "中文 (Chinese)"
        }
        # Only return languages that we actually have translations for
        return {code: name for code, name in languages.items() if code in self.translations}
    
    def translate(self, key: str, *args) -> str:
        """
        Translate a key to the current language.
        
        Args:
            key: Translation key
            *args: Format arguments for the translated string
            
        Returns:
            Translated string
        """
        # Get translation from current language
        translation = self.translations.get(self.current_language, {}).get(key)
        
        # Fall back to English if not found
        if translation is None and self.current_language != "en":
            translation = self.translations.get("en", {}).get(key)
        
        # Use key as fallback if not found in any language
        if translation is None:
            translation = key
        
        # Format with arguments if provided
        if args:
            try:
                translation = translation.format(*args)
            except Exception as e:
                self.logger.error(f"Error formatting translation key '{key}' with args {args}: {str(e)}")
        
        return translation
    
    def tr(self, key: str, *args) -> str:
        """Shorthand for translate."""
        return self.translate(key, *args)