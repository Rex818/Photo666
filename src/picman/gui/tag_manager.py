"""
Tag management UI components.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QColorDialog,
    QMessageBox, QInputDialog, QMenu, QFrame, QSplitter, QGroupBox,
    QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QContextMenuEvent, QColor
import structlog

from ..database.manager import DatabaseManager


class TagColorWidget(QFrame):
    """Widget for displaying a tag color."""
    
    def __init__(self, color: str = "#CCCCCC"):
        super().__init__()
        self.color = QColor(color)
        self.setFixedSize(16, 16)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"background-color: {color};")
    
    def set_color(self, color: str):
        """Set the color of the widget."""
        self.color = QColor(color)
        self.setStyleSheet(f"background-color: {color};")


class TagListItem(QListWidgetItem):
    """Tag list item for display in the tag list."""
    
    def __init__(self, tag_data: Dict[str, Any]):
        super().__init__(tag_data.get("name", "Unnamed Tag"))
        self.tag_id = tag_data.get("id", 0)
        self.tag_data = tag_data
        
        # Set tooltip with tag info
        usage_count = tag_data.get("usage_count", 0)
        tooltip = f"{tag_data.get('name')}\nUsed in {usage_count} photos"
        self.setToolTip(tooltip)


class TagDialog(QDialog):
    """Dialog for creating or editing a tag."""
    
    def __init__(self, parent=None, tag_data: Dict[str, Any] = None):
        super().__init__(parent)
        self.tag_data = tag_data or {"color": "#3498db"}  # Default blue color
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Tag Properties")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Tag name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.tag_data.get("name", ""))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Tag color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        
        self.color_widget = TagColorWidget(self.tag_data.get("color", "#3498db"))
        color_layout.addWidget(self.color_widget)
        
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def choose_color(self):
        """Open color dialog to choose a tag color."""
        color = QColorDialog.getColor(QColor(self.tag_data.get("color", "#3498db")), self)
        if color.isValid():
            self.tag_data["color"] = color.name()
            self.color_widget.set_color(color.name())
    
    def get_tag_data(self) -> Dict[str, Any]:
        """Get the tag data from the dialog."""
        self.tag_data["name"] = self.name_edit.text()
        return self.tag_data


class TagManager(QWidget):
    """Tag management widget."""
    
    tag_selected = pyqtSignal(int)  # tag_id
    tags_updated = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.logger = structlog.get_logger("picman.gui.tag_manager")
        
        # 当前选中的照片
        self.current_photo = None
        
        self.init_ui()
        self.load_tags()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部分：标签管理
        top_widget = self.create_tag_management_panel()
        splitter.addWidget(top_widget)
        
        # 下半部分：照片标签显示
        bottom_widget = self.create_photo_tags_panel()
        splitter.addWidget(bottom_widget)
        
        # 设置分割器比例 - 调整5区和6区的比例
        splitter.setSizes([150, 350])  # 标签管理占150，照片标签信息占350
        
        layout.addWidget(splitter)
    
    def create_tag_management_panel(self) -> QWidget:
        """创建AI图片信息面板"""
        panel = QGroupBox("AI图片信息")
        layout = QVBoxLayout(panel)
        
        # AI信息编辑选项
        ai_layout = QHBoxLayout()
        
        # 自动识别开关
        self.enable_auto_detection = QCheckBox("启用自动识别")
        self.enable_auto_detection.setChecked(True)
        self.enable_auto_detection.setToolTip("自动识别图片中的AI生成信息")
        ai_layout.addWidget(self.enable_auto_detection)
        
        # AI插件开关
        self.use_ai_plugin = QCheckBox("使用AI分析插件")
        self.use_ai_plugin.setChecked(False)
        self.use_ai_plugin.setToolTip("使用AI插件进行图片分析")
        ai_layout.addWidget(self.use_ai_plugin)
        
        # 添加配置按钮
        self.ai_config_btn = QPushButton("配置")
        self.ai_config_btn.clicked.connect(self.show_ai_config)
        ai_layout.addWidget(self.ai_config_btn)
        
        # 添加立即分析按钮
        self.analyze_now_btn = QPushButton("立即分析")
        self.analyze_now_btn.clicked.connect(self.analyze_now)
        self.analyze_now_btn.setToolTip("立即分析当前图片")
        ai_layout.addWidget(self.analyze_now_btn)
        
        ai_layout.addStretch()
        layout.addLayout(ai_layout)
        
        # 创建AI信息显示区域的主布局
        ai_display_layout = QVBoxLayout()
        ai_display_layout.setSpacing(10)
        
        # 模型信息区域
        model_group = QGroupBox("模型信息")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(5)
        
        # 模型名称
        model_name_layout = QHBoxLayout()
        model_name_layout.addWidget(QLabel("模型:"))
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("输入模型名称...")
        model_name_layout.addWidget(self.model_name_edit)
        model_layout.addLayout(model_name_layout)
        
        # 模型版本
        model_version_layout = QHBoxLayout()
        model_version_layout.addWidget(QLabel("版本:"))
        self.model_version_edit = QLineEdit()
        self.model_version_edit.setPlaceholderText("输入模型版本...")
        model_version_layout.addWidget(self.model_version_edit)
        model_layout.addLayout(model_version_layout)
        
        ai_display_layout.addWidget(model_group)
        
        # Lora信息区域
        lora_group = QGroupBox("Lora信息")
        lora_layout = QVBoxLayout(lora_group)
        lora_layout.setSpacing(5)
        
        # Lora名称
        lora_name_layout = QHBoxLayout()
        lora_name_layout.addWidget(QLabel("Lora:"))
        self.lora_name_edit = QLineEdit()
        self.lora_name_edit.setPlaceholderText("输入Lora名称...")
        lora_name_layout.addWidget(self.lora_name_edit)
        lora_layout.addLayout(lora_name_layout)
        
        # Lora权重
        lora_weight_layout = QHBoxLayout()
        lora_weight_layout.addWidget(QLabel("权重:"))
        self.lora_weight_edit = QLineEdit()
        self.lora_weight_edit.setPlaceholderText("输入Lora权重...")
        lora_weight_layout.addWidget(self.lora_weight_edit)
        lora_layout.addLayout(lora_weight_layout)
        
        ai_display_layout.addWidget(lora_group)
        
        # 触发词区域
        prompt_group = QGroupBox("触发词")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(5)
        
        # 正面提示词
        positive_prompt_layout = QHBoxLayout()
        positive_prompt_layout.addWidget(QLabel("正面:"))
        self.positive_prompt_edit = QTextEdit()
        self.positive_prompt_edit.setMaximumHeight(60)
        self.positive_prompt_edit.setPlaceholderText("输入正面提示词...")
        positive_prompt_layout.addWidget(self.positive_prompt_edit)
        prompt_layout.addLayout(positive_prompt_layout)
        
        # 负面提示词
        negative_prompt_layout = QHBoxLayout()
        negative_prompt_layout.addWidget(QLabel("负面:"))
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setMaximumHeight(60)
        self.negative_prompt_edit.setPlaceholderText("输入负面提示词...")
        negative_prompt_layout.addWidget(self.negative_prompt_edit)
        prompt_layout.addLayout(negative_prompt_layout)
        
        ai_display_layout.addWidget(prompt_group)
        
        # 其他AI参数区域
        params_group = QGroupBox("其他参数")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(5)
        
        # 采样器
        sampler_layout = QHBoxLayout()
        sampler_layout.addWidget(QLabel("采样器:"))
        self.sampler_edit = QLineEdit()
        self.sampler_edit.setPlaceholderText("输入采样器...")
        sampler_layout.addWidget(self.sampler_edit)
        params_layout.addLayout(sampler_layout)
        
        # 步数
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("步数:"))
        self.steps_edit = QLineEdit()
        self.steps_edit.setPlaceholderText("输入步数...")
        steps_layout.addWidget(self.steps_edit)
        params_layout.addLayout(steps_layout)
        
        # CFG Scale
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("CFG:"))
        self.cfg_edit = QLineEdit()
        self.cfg_edit.setPlaceholderText("输入CFG Scale...")
        cfg_layout.addWidget(self.cfg_edit)
        params_layout.addLayout(cfg_layout)
        
        ai_display_layout.addWidget(params_group)
        
        layout.addLayout(ai_display_layout)
        
        return panel
    
    def show_ai_config(self):
        """显示AI配置对话框"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "AI配置", "AI配置功能正在开发中...")
        except Exception as e:
            self.logger.error("Failed to show AI config", error=str(e))
    
    def analyze_now(self):
        """立即分析当前图片"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "AI分析", "AI分析功能正在开发中...")
        except Exception as e:
            self.logger.error("Failed to analyze image", error=str(e))
    
    def create_photo_tags_panel(self) -> QWidget:
        """创建照片标签显示面板"""
        panel = QGroupBox("照片标签信息")
        layout = QVBoxLayout(panel)
        
        # 翻译插件选项
        plugin_layout = QHBoxLayout()
        
        # 全局翻译开关
        self.enable_global_translation = QCheckBox("启用全局翻译")
        self.enable_global_translation.setChecked(True)
        self.enable_global_translation.setToolTip("自动翻译英文标签为中文")
        plugin_layout.addWidget(self.enable_global_translation)
        
        # 翻译插件开关
        self.use_translation_plugin = QCheckBox("使用Google翻译插件")
        self.use_translation_plugin.setChecked(False)
        self.use_translation_plugin.setToolTip("使用Google翻译插件进行翻译")
        plugin_layout.addWidget(self.use_translation_plugin)
        
        # 添加配置按钮
        self.config_btn = QPushButton("配置")
        self.config_btn.clicked.connect(self.show_plugin_config)
        plugin_layout.addWidget(self.config_btn)
        
        # 添加立即翻译按钮
        self.translate_now_btn = QPushButton("立即翻译")
        self.translate_now_btn.clicked.connect(self.translate_now)
        self.translate_now_btn.setToolTip("立即翻译当前标签")
        plugin_layout.addWidget(self.translate_now_btn)
        
        plugin_layout.addStretch()
        layout.addLayout(plugin_layout)
        
        # 创建标签显示区域的主布局 - 改为垂直排列
        tags_display_layout = QVBoxLayout()
        tags_display_layout.setSpacing(10)
        
        # 简单标签区域
        simple_tags_group = QGroupBox("简单标签")
        simple_tags_layout = QVBoxLayout(simple_tags_group)
        simple_tags_layout.setSpacing(5)
        
        # 简单标签英文区域
        simple_english_layout = QHBoxLayout()
        simple_english_layout.addWidget(QLabel("英文:"))
        self.simple_tags_english = QTextEdit()
        self.simple_tags_english.setMaximumHeight(60)
        self.simple_tags_english.setPlaceholderText("输入英文标签...")
        self.simple_tags_english.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px;")
        simple_english_layout.addWidget(self.simple_tags_english)
        simple_tags_layout.addLayout(simple_english_layout)
        
        # 简单标签中文区域
        simple_chinese_layout = QHBoxLayout()
        simple_chinese_layout.addWidget(QLabel("中文:"))
        self.simple_tags_chinese = QTextEdit()
        self.simple_tags_chinese.setMaximumHeight(60)
        self.simple_tags_chinese.setPlaceholderText("输入中文标签...")
        self.simple_tags_chinese.setStyleSheet("background-color: #e8f4f8; border: 1px solid #ccc; border-radius: 3px;")
        simple_chinese_layout.addWidget(self.simple_tags_chinese)
        simple_tags_layout.addLayout(simple_chinese_layout)
        
        tags_display_layout.addWidget(simple_tags_group)
        
        # 普通标签区域
        normal_tags_group = QGroupBox("普通标签")
        normal_tags_layout = QVBoxLayout(normal_tags_group)
        normal_tags_layout.setSpacing(5)
        
        # 普通标签英文区域
        normal_english_layout = QHBoxLayout()
        normal_english_layout.addWidget(QLabel("英文:"))
        self.normal_tags_english = QTextEdit()
        self.normal_tags_english.setMaximumHeight(80)
        self.normal_tags_english.setPlaceholderText("输入英文标签...")
        self.normal_tags_english.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px;")
        normal_english_layout.addWidget(self.normal_tags_english)
        normal_tags_layout.addLayout(normal_english_layout)
        
        # 普通标签中文区域
        normal_chinese_layout = QHBoxLayout()
        normal_chinese_layout.addWidget(QLabel("中文:"))
        self.normal_tags_chinese = QTextEdit()
        self.normal_tags_chinese.setMaximumHeight(80)
        self.normal_tags_chinese.setPlaceholderText("输入中文标签...")
        self.normal_tags_chinese.setStyleSheet("background-color: #e8f4f8; border: 1px solid #ccc; border-radius: 3px;")
        normal_chinese_layout.addWidget(self.normal_tags_chinese)
        normal_tags_layout.addLayout(normal_chinese_layout)
        
        tags_display_layout.addWidget(normal_tags_group)
        
        # 详细标签区域
        detailed_tags_group = QGroupBox("详细标签")
        detailed_tags_layout = QVBoxLayout(detailed_tags_group)
        detailed_tags_layout.setSpacing(5)
        
        # 详细标签英文区域
        detailed_english_layout = QHBoxLayout()
        detailed_english_layout.addWidget(QLabel("英文:"))
        self.detailed_tags_english = QTextEdit()
        self.detailed_tags_english.setMaximumHeight(100)
        self.detailed_tags_english.setPlaceholderText("输入英文标签...")
        self.detailed_tags_english.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px;")
        detailed_english_layout.addWidget(self.detailed_tags_english)
        detailed_tags_layout.addLayout(detailed_english_layout)
        
        # 详细标签中文区域
        detailed_chinese_layout = QHBoxLayout()
        detailed_chinese_layout.addWidget(QLabel("中文:"))
        self.detailed_tags_chinese = QTextEdit()
        self.detailed_tags_chinese.setMaximumHeight(100)
        self.detailed_tags_chinese.setPlaceholderText("输入中文标签...")
        self.detailed_tags_chinese.setStyleSheet("background-color: #e8f4f8; border: 1px solid #ccc; border-radius: 3px;")
        detailed_chinese_layout.addWidget(self.detailed_tags_chinese)
        detailed_tags_layout.addLayout(detailed_chinese_layout)
        
        tags_display_layout.addWidget(detailed_tags_group)
        
        layout.addLayout(tags_display_layout)
        
        # 标签备注
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel("标签备注:"))
        
        self.tags_notes = QTextEdit()
        self.tags_notes.setMaximumHeight(80)
        self.tags_notes.setPlaceholderText("添加标签备注...")
        notes_layout.addWidget(self.tags_notes)
        
        layout.addLayout(notes_layout)
        
        return panel
    

    
    def load_tags(self):
        """Load tags from database."""
        try:
            # In a real implementation, this would query the database
            # For now, we'll create some sample tags
            sample_tags = [
                {"id": 1, "name": "Family", "color": "#e74c3c", "usage_count": 56},
                {"id": 2, "name": "Vacation", "color": "#3498db", "usage_count": 24},
                {"id": 3, "name": "Nature", "color": "#2ecc71", "usage_count": 18},
                {"id": 4, "name": "Food", "color": "#f39c12", "usage_count": 12},
                {"id": 5, "name": "Architecture", "color": "#9b59b6", "usage_count": 8}
            ]
            
            # 由于我们已经将tag_list替换为AI信息面板，这里不再需要加载标签列表
            # 但保留日志记录
            self.logger.info("Tags loaded", count=len(sample_tags))
            
        except Exception as e:
            self.logger.error("Failed to load tags", error=str(e))
    
    def create_tag(self):
        """Create a new tag."""
        dialog = TagDialog(self)
        if dialog.exec():
            tag_data = dialog.get_tag_data()
            
            # In a real implementation, this would add to the database
            # For now, we'll just add to the list
            tag_data["id"] = len(self.tag_list.findItems("", Qt.MatchFlag.MatchContains)) + 1
            tag_data["usage_count"] = 0
            
            item = TagListItem(tag_data)
            self.tag_list.addItem(item)
            
            self.logger.info("Tag created", name=tag_data["name"])
            self.tags_updated.emit()
    
    def edit_tag(self, tag_id: int):
        """Edit an existing tag."""
        # Find the tag item
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if hasattr(item, 'tag_id') and item.tag_id == tag_id:
                dialog = TagDialog(self, item.tag_data)
                if dialog.exec():
                    tag_data = dialog.get_tag_data()
                    item.tag_data.update(tag_data)
                    item.setText(tag_data["name"])
                    
                    self.logger.info("Tag edited", tag_id=tag_id, name=tag_data["name"])
                    self.tags_updated.emit()
                break
    
    def delete_tag(self, tag_id: int):
        """Delete a tag."""
        # Find the tag item
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if hasattr(item, 'tag_id') and item.tag_id == tag_id:
                reply = QMessageBox.question(
                    self, "Delete Tag",
                    f"Are you sure you want to delete the tag '{item.text()}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.tag_list.takeItem(i)
                    self.logger.info("Tag deleted", tag_id=tag_id, name=item.text())
                    self.tags_updated.emit()
                break
    
    def on_tag_selected(self, item):
        """Handle tag selection."""
        if hasattr(item, 'tag_id'):
            self.tag_selected.emit(item.tag_id)
    
    def show_tag_context_menu(self, position):
        """Show context menu for tags."""
        item = self.tag_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.edit_tag(item.tag_id))
        menu.addAction(edit_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_tag(item.tag_id))
        menu.addAction(delete_action)
        
        menu.exec(self.tag_list.mapToGlobal(position))
    
    def highlight_photo_tags(self, photo_tags: List[str]):
        """Highlight tags that are used by the current photo."""
        try:
            # 由于我们已经将tag_list替换为AI信息面板，这里不再需要高亮标签
            # 但保留日志记录
            self.logger.info("Tags highlighted for photo", highlighted_count=0, photo_tags=photo_tags)
            
        except Exception as e:
            self.logger.error("Failed to highlight photo tags", error=str(e))
    
    def update_photo_tags_display(self, photo_data: dict):
        """更新照片标签显示"""
        try:
            self.current_photo = photo_data
            
            # 获取标签数据
            simple_tags = photo_data.get('simple_tags', [])
            normal_tags = photo_data.get('normal_tags', [])
            detailed_tags = photo_data.get('detailed_tags', [])
            tag_translations = photo_data.get('tag_translations', {})
            
            # 如果启用了全局翻译功能，尝试翻译英文标签
            if self.enable_global_translation.isChecked():
                try:
                    # 如果启用了Google翻译插件，使用插件翻译
                    if self.use_translation_plugin.isChecked():
                        # 修复导入路径问题
                        import sys
                        import os
                        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                        from plugins.google_translate_plugin import GoogleTranslatePlugin
                        
                        # 创建插件实例
                        plugin = GoogleTranslatePlugin()
                        plugin.initialize({})  # 传入空的app_context
                        
                        # 翻译简单标签
                        if simple_tags:
                            simple_translations = {}
                            for tag in simple_tags:
                                if self._is_english_text(tag):
                                    translation = plugin.translate_text(tag)
                                    if translation:
                                        simple_translations[tag] = translation
                            tag_translations.update(simple_translations)
                        
                        # 翻译普通标签
                        if normal_tags:
                            normal_translations = {}
                            for tag in normal_tags:
                                if self._is_english_text(tag):
                                    translation = plugin.translate_text(tag)
                                    if translation:
                                        normal_translations[tag] = translation
                            tag_translations.update(normal_translations)
                        
                        # 翻译详细标签
                        if detailed_tags:
                            detailed_translations = {}
                            for tag in detailed_tags:
                                if self._is_english_text(tag):
                                    translation = plugin.translate_text(tag)
                                    if translation:
                                        detailed_translations[tag] = translation
                            tag_translations.update(detailed_translations)
                        
                        plugin.shutdown()
                        
                    else:
                        # 使用内置的简单翻译词典
                        builtin_translations = self._get_builtin_translations()
                        
                        # 翻译简单标签
                        if simple_tags:
                            simple_translations = {}
                            for tag in simple_tags:
                                if self._is_english_text(tag):
                                    translation = builtin_translations.get(tag.lower(), tag)
                                    if translation != tag:
                                        simple_translations[tag] = translation
                            tag_translations.update(simple_translations)
                        
                        # 翻译普通标签
                        if normal_tags:
                            normal_translations = {}
                            for tag in normal_tags:
                                if self._is_english_text(tag):
                                    translation = builtin_translations.get(tag.lower(), tag)
                                    if translation != tag:
                                        normal_translations[tag] = translation
                            tag_translations.update(normal_translations)
                        
                        # 翻译详细标签
                        if detailed_tags:
                            detailed_translations = {}
                            for tag in detailed_tags:
                                if self._is_english_text(tag):
                                    translation = builtin_translations.get(tag.lower(), tag)
                                    if translation != tag:
                                        detailed_translations[tag] = translation
                            tag_translations.update(detailed_translations)
                    
                except Exception as e:
                    self.logger.error("Failed to use translation", error=str(e))
            
            # 更新简单标签
            if simple_tags:
                english_text = ', '.join(simple_tags)
                chinese_text = ', '.join([tag_translations.get(tag, tag) for tag in simple_tags])
                self.simple_tags_english.setPlainText(english_text)
                self.simple_tags_chinese.setPlainText(chinese_text)
            else:
                self.simple_tags_english.setPlainText("")
                self.simple_tags_chinese.setPlainText("")
            
            # 更新普通标签
            if normal_tags:
                english_text = ', '.join(normal_tags)
                chinese_text = ', '.join([tag_translations.get(tag, tag) for tag in normal_tags])
                self.normal_tags_english.setPlainText(english_text)
                self.normal_tags_chinese.setPlainText(chinese_text)
            else:
                self.normal_tags_english.setPlainText("")
                self.normal_tags_chinese.setPlainText("")
            
            # 更新详细标签
            if detailed_tags:
                english_text = ', '.join(detailed_tags)
                chinese_text = ', '.join([tag_translations.get(tag, tag) for tag in detailed_tags])
                self.detailed_tags_english.setPlainText(english_text)
                self.detailed_tags_chinese.setPlainText(chinese_text)
            else:
                self.detailed_tags_english.setPlainText("")
                self.detailed_tags_chinese.setPlainText("")
            
            # 更新标签备注
            notes = photo_data.get('tag_notes', '')
            if self.tags_notes.toPlainText() != notes:
                self.tags_notes.setPlainText(notes)
            
            # 高亮显示照片使用的标签
            all_tags = simple_tags + normal_tags + detailed_tags
            self.highlight_photo_tags(all_tags)
            
            self.logger.info("Photo tags display updated", photo_id=photo_data.get('id'))
            
        except Exception as e:
            self.logger.error("Failed to update photo tags display", error=str(e))
    
    def _is_english_text(self, text: str) -> bool:
        """检查文本是否为英文"""
        if not text:
            return False
        
        # 简单的英文检测：检查是否包含英文字母
        import re
        english_pattern = re.compile(r'[a-zA-Z]')
        return bool(english_pattern.search(text))
    
    def _get_builtin_translations(self) -> Dict[str, str]:
        """获取内置翻译词典"""
        return {
            # 常见摄影标签
            "portrait": "人像",
            "landscape": "风景",
            "nature": "自然",
            "architecture": "建筑",
            "street": "街拍",
            "macro": "微距",
            "black and white": "黑白",
            "color": "彩色",
            "sunset": "日落",
            "sunrise": "日出",
            "night": "夜景",
            "city": "城市",
            "countryside": "乡村",
            "mountain": "山",
            "sea": "海",
            "ocean": "海洋",
            "forest": "森林",
            "flower": "花",
            "tree": "树",
            "sky": "天空",
            "cloud": "云",
            "rain": "雨",
            "snow": "雪",
            "winter": "冬天",
            "summer": "夏天",
            "spring": "春天",
            "autumn": "秋天",
            "fall": "秋天",
            
            # 人物相关
            "man": "男人",
            "woman": "女人",
            "child": "孩子",
            "family": "家庭",
            "people": "人们",
            "crowd": "人群",
            "face": "脸",
            "smile": "微笑",
            "laugh": "笑",
            "happy": "快乐",
            "sad": "悲伤",
            
            # 动作相关
            "walking": "走路",
            "running": "跑步",
            "dancing": "跳舞",
            "singing": "唱歌",
            "playing": "玩耍",
            "working": "工作",
            "reading": "阅读",
            "writing": "写作",
            "cooking": "烹饪",
            "eating": "吃饭",
            "drinking": "喝水",
            
            # 物体相关
            "car": "汽车",
            "bike": "自行车",
            "bus": "公交车",
            "train": "火车",
            "plane": "飞机",
            "boat": "船",
            "house": "房子",
            "building": "建筑",
            "bridge": "桥",
            "road": "路",
            "street": "街道",
            "park": "公园",
            "garden": "花园",
            "school": "学校",
            "hospital": "医院",
            "shop": "商店",
            "market": "市场",
            "restaurant": "餐厅",
            "cafe": "咖啡厅",
            "hotel": "酒店",
            
            # 动物相关
            "dog": "狗",
            "cat": "猫",
            "bird": "鸟",
            "fish": "鱼",
            "horse": "马",
            "cow": "牛",
            "sheep": "羊",
            "pig": "猪",
            "chicken": "鸡",
            "duck": "鸭子",
            
            # 颜色相关
            "red": "红色",
            "blue": "蓝色",
            "green": "绿色",
            "yellow": "黄色",
            "orange": "橙色",
            "purple": "紫色",
            "pink": "粉色",
            "brown": "棕色",
            "black": "黑色",
            "white": "白色",
            "gray": "灰色",
            "grey": "灰色",
            
            # 其他常见词汇
            "beautiful": "美丽",
            "amazing": "令人惊叹",
            "wonderful": "精彩",
            "great": "很棒",
            "good": "好",
            "bad": "坏",
            "big": "大",
            "small": "小",
            "old": "老",
            "new": "新",
            "young": "年轻",
            "tall": "高",
            "short": "矮",
            "long": "长",
            "wide": "宽",
            "narrow": "窄",
            "fast": "快",
            "slow": "慢",
            "hot": "热",
            "cold": "冷",
            "warm": "温暖",
            "cool": "凉爽",
        }
    
    def translate_now(self):
        """立即翻译功能"""
        try:
            if not self.current_photo:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "请先选择一张照片")
                return
            
            # 获取当前标签内容
            simple_english = self.simple_tags_english.toPlainText().strip()
            simple_chinese = self.simple_tags_chinese.toPlainText().strip()
            normal_english = self.normal_tags_english.toPlainText().strip()
            normal_chinese = self.normal_tags_chinese.toPlainText().strip()
            detailed_english = self.detailed_tags_english.toPlainText().strip()
            detailed_chinese = self.detailed_tags_chinese.toPlainText().strip()
            
            # 检查是否有内容需要翻译
            if not any([simple_english, simple_chinese, normal_english, normal_chinese, detailed_english, detailed_chinese]):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "没有需要翻译的内容")
                return
            
            # 创建翻译插件实例
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from plugins.google_translate_plugin import GoogleTranslatePlugin
            
            plugin = GoogleTranslatePlugin()
            plugin.initialize({})
            
            # 智能翻译：根据内容判断翻译方向
            translations_made = False
            
            # 简单标签翻译
            if simple_english and not simple_chinese:
                # 英文翻译为中文
                translation = plugin.translate_text(simple_english)
                if translation:
                    self.simple_tags_chinese.setPlainText(translation)
                    translations_made = True
            elif simple_chinese and not simple_english:
                # 中文翻译为英文
                plugin.source_language = "zh-CN"
                plugin.target_language = "en"
                translation = plugin.translate_text(simple_chinese)
                if translation:
                    self.simple_tags_english.setPlainText(translation)
                    translations_made = True
            
            # 普通标签翻译
            if normal_english and not normal_chinese:
                # 英文翻译为中文
                plugin.source_language = "en"
                plugin.target_language = "zh-CN"
                translation = plugin.translate_text(normal_english)
                if translation:
                    self.normal_tags_chinese.setPlainText(translation)
                    translations_made = True
            elif normal_chinese and not normal_english:
                # 中文翻译为英文
                plugin.source_language = "zh-CN"
                plugin.target_language = "en"
                translation = plugin.translate_text(normal_chinese)
                if translation:
                    self.normal_tags_english.setPlainText(translation)
                    translations_made = True
            
            # 详细标签翻译
            if detailed_english and not detailed_chinese:
                # 英文翻译为中文
                plugin.source_language = "en"
                plugin.target_language = "zh-CN"
                translation = plugin.translate_text(detailed_english)
                if translation:
                    self.detailed_tags_chinese.setPlainText(translation)
                    translations_made = True
            elif detailed_chinese and not detailed_english:
                # 中文翻译为英文
                plugin.source_language = "zh-CN"
                plugin.target_language = "en"
                translation = plugin.translate_text(detailed_chinese)
                if translation:
                    self.detailed_tags_english.setPlainText(translation)
                    translations_made = True
            
            plugin.shutdown()
            
            if translations_made:
                # 保存到数据库
                self.save_tags_to_database()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "成功", "翻译完成并已保存到数据库")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "没有需要翻译的内容")
                
        except Exception as e:
            self.logger.error("Failed to translate now", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
    def save_tags_to_database(self):
        """保存标签到数据库"""
        try:
            if not self.current_photo:
                return
            
            # 获取当前标签内容
            simple_english = self.simple_tags_english.toPlainText().strip()
            simple_chinese = self.simple_tags_chinese.toPlainText().strip()
            normal_english = self.normal_tags_english.toPlainText().strip()
            normal_chinese = self.normal_tags_chinese.toPlainText().strip()
            detailed_english = self.detailed_tags_english.toPlainText().strip()
            detailed_chinese = self.detailed_tags_chinese.toPlainText().strip()
            
            # 更新照片数据
            photo_id = self.current_photo.get('id')
            if photo_id:
                # 这里应该调用数据库更新方法
                # 由于我们没有完整的数据库接口，这里只是记录日志
                self.logger.info("Tags saved to database", 
                               photo_id=photo_id,
                               simple_english=simple_english,
                               simple_chinese=simple_chinese,
                               normal_english=normal_english,
                               normal_chinese=normal_chinese,
                               detailed_english=detailed_english,
                               detailed_chinese=detailed_chinese)
                
        except Exception as e:
            self.logger.error("Failed to save tags to database", error=str(e))
    
    def show_plugin_config(self):
        """显示插件配置对话框"""
        try:
            from .plugin_config_dialog import PluginConfigDialog
            dialog = PluginConfigDialog(self)
            dialog.exec()
        except Exception as e:
            self.logger.error("Failed to show plugin config", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"无法打开插件配置：{str(e)}")