"""
Tag management UI components.
"""

import time
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QColorDialog,
    QMessageBox, QInputDialog, QMenu, QFrame, QSplitter, QGroupBox,
    QCheckBox, QTextEdit, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QContextMenuEvent, QColor
import logging

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


class AIImageInfoPanel(QWidget):
    """AI图片信息面板"""
    
    def __init__(self, db_manager: DatabaseManager, album_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.album_manager = album_manager
        self.logger = logging.getLogger("picman.gui.ai_image_info_panel")
        
        # 当前选中的照片
        self.current_photo = None
        
        # 编辑状态标志
        self.is_editing = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建AI图片信息面板（带滚动条）
        scroll = QScrollArea()
        widget = self.create_ai_info_panel()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(scroll)
    
    def create_ai_info_panel(self) -> QWidget:
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
        
        # 模型名称
        model_name_layout = QHBoxLayout()
        model_name_layout.addWidget(QLabel("模型:"))
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("输入模型名称...")
        self.model_name_edit.setReadOnly(not self.is_editing)
        model_name_layout.addWidget(self.model_name_edit)
        model_layout.addLayout(model_name_layout)
        
        # 模型版本
        model_version_layout = QHBoxLayout()
        model_version_layout.addWidget(QLabel("版本:"))
        self.model_version_edit = QLineEdit()
        self.model_version_edit.setPlaceholderText("输入模型版本...")
        self.model_version_edit.setReadOnly(not self.is_editing)
        model_version_layout.addWidget(self.model_version_edit)
        model_layout.addLayout(model_version_layout)
        
        ai_display_layout.addWidget(model_group)
        
        # Lora信息区域
        lora_group = QGroupBox("Lora信息")
        lora_layout = QVBoxLayout(lora_group)
        
        # Lora名称
        lora_name_layout = QHBoxLayout()
        lora_name_layout.addWidget(QLabel("Lora:"))
        self.lora_name_edit = QLineEdit()
        self.lora_name_edit.setPlaceholderText("输入Lora名称...")
        self.lora_name_edit.setReadOnly(not self.is_editing)
        lora_name_layout.addWidget(self.lora_name_edit)
        lora_layout.addLayout(lora_name_layout)
        
        # Lora权重
        lora_weight_layout = QHBoxLayout()
        lora_weight_layout.addWidget(QLabel("权重:"))
        self.lora_weight_edit = QLineEdit()
        self.lora_weight_edit.setPlaceholderText("输入Lora权重...")
        self.lora_weight_edit.setReadOnly(not self.is_editing)
        lora_weight_layout.addWidget(self.lora_weight_edit)
        lora_layout.addLayout(lora_weight_layout)
        
        ai_display_layout.addWidget(lora_group)
        
        # Midjourney参数区域
        midjourney_group = QGroupBox("Midjourney参数")
        midjourney_layout = QVBoxLayout(midjourney_group)
        
        # 任务ID
        task_id_layout = QHBoxLayout()
        task_id_layout.addWidget(QLabel("任务ID:"))
        self.task_id_edit = QLineEdit()
        self.task_id_edit.setPlaceholderText("Midjourney任务ID...")
        self.task_id_edit.setReadOnly(not self.is_editing)
        task_id_layout.addWidget(self.task_id_edit)
        midjourney_layout.addLayout(task_id_layout)
        
        # 版本
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("版本:"))
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("Midjourney版本...")
        self.version_edit.setReadOnly(not self.is_editing)
        version_layout.addWidget(self.version_edit)
        midjourney_layout.addLayout(version_layout)
        
        # 风格化
        stylize_layout = QHBoxLayout()
        stylize_layout.addWidget(QLabel("风格化:"))
        self.stylize_edit = QLineEdit()
        self.stylize_edit.setPlaceholderText("风格化参数...")
        self.stylize_edit.setReadOnly(not self.is_editing)
        stylize_layout.addWidget(self.stylize_edit)
        midjourney_layout.addLayout(stylize_layout)
        
        # 质量
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("质量:"))
        self.quality_edit = QLineEdit()
        self.quality_edit.setPlaceholderText("质量参数...")
        self.quality_edit.setReadOnly(not self.is_editing)
        quality_layout.addWidget(self.quality_edit)
        midjourney_layout.addLayout(quality_layout)
        
        # 宽高比
        aspect_ratio_layout = QHBoxLayout()
        aspect_ratio_layout.addWidget(QLabel("宽高比:"))
        self.aspect_ratio_edit = QLineEdit()
        self.aspect_ratio_edit.setPlaceholderText("宽高比...")
        self.aspect_ratio_edit.setReadOnly(not self.is_editing)
        aspect_ratio_layout.addWidget(self.aspect_ratio_edit)
        midjourney_layout.addLayout(aspect_ratio_layout)
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        
        self.raw_mode_radio = QCheckBox("原始模式")
        self.raw_mode_radio.setChecked(True)
        self.raw_mode_radio.setEnabled(self.is_editing)
        mode_layout.addWidget(self.raw_mode_radio)
        
        self.tile_mode_radio = QCheckBox("平铺模式")
        self.tile_mode_radio.setEnabled(self.is_editing)
        mode_layout.addWidget(self.tile_mode_radio)
        
        self.niji_mode_radio = QCheckBox("Niji模式")
        self.niji_mode_radio.setEnabled(self.is_editing)
        mode_layout.addWidget(self.niji_mode_radio)
        
        mode_layout.addStretch()
        midjourney_layout.addLayout(mode_layout)
        
        # 混乱度
        chaos_layout = QHBoxLayout()
        chaos_layout.addWidget(QLabel("混乱度:"))
        self.chaos_edit = QLineEdit()
        self.chaos_edit.setPlaceholderText("混乱度...")
        self.chaos_edit.setReadOnly(not self.is_editing)
        chaos_layout.addWidget(self.chaos_edit)
        midjourney_layout.addLayout(chaos_layout)
        
        # 怪异度
        weirdness_layout = QHBoxLayout()
        weirdness_layout.addWidget(QLabel("怪异度:"))
        self.weirdness_edit = QLineEdit()
        self.weirdness_edit.setPlaceholderText("怪异度...")
        self.weirdness_edit.setReadOnly(not self.is_editing)
        weirdness_layout.addWidget(self.weirdness_edit)
        midjourney_layout.addLayout(weirdness_layout)
        
        ai_display_layout.addWidget(midjourney_group)
        
        # Prompt信息区域
        prompt_group = QGroupBox("提示词信息")
        prompt_layout = QVBoxLayout(prompt_group)
        
        # 正向提示词
        positive_layout = QVBoxLayout()
        positive_layout.addWidget(QLabel("正向提示词:"))
        self.positive_prompt_edit = QTextEdit()
        self.positive_prompt_edit.setMaximumHeight(100)
        self.positive_prompt_edit.setPlaceholderText("正向提示词...")
        self.positive_prompt_edit.setReadOnly(not self.is_editing)
        positive_layout.addWidget(self.positive_prompt_edit)
        prompt_layout.addLayout(positive_layout)
        
        # 负向提示词
        negative_layout = QVBoxLayout()
        negative_layout.addWidget(QLabel("负向提示词:"))
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setMaximumHeight(100)
        self.negative_prompt_edit.setPlaceholderText("负向提示词...")
        self.negative_prompt_edit.setReadOnly(not self.is_editing)
        negative_layout.addWidget(self.negative_prompt_edit)
        prompt_layout.addLayout(negative_layout)
        
        ai_display_layout.addWidget(prompt_group)
        
        # Stable Diffusion参数区域
        sd_group = QGroupBox("Stable Diffusion参数")
        sd_layout = QVBoxLayout(sd_group)
        
        # 第一行：采样器和步数
        sd_row1 = QHBoxLayout()
        sd_row1.addWidget(QLabel("采样器:"))
        self.sampler_edit = QLineEdit()
        self.sampler_edit.setPlaceholderText("采样器...")
        self.sampler_edit.setReadOnly(not self.is_editing)
        sd_row1.addWidget(self.sampler_edit)
        
        sd_row1.addWidget(QLabel("步数:"))
        self.steps_edit = QLineEdit()
        self.steps_edit.setPlaceholderText("步数...")
        self.steps_edit.setReadOnly(not self.is_editing)
        sd_row1.addWidget(self.steps_edit)
        sd_layout.addLayout(sd_row1)
        
        # 第二行：CFG和种子
        sd_row2 = QHBoxLayout()
        sd_row2.addWidget(QLabel("CFG Scale:"))
        self.cfg_edit = QLineEdit()
        self.cfg_edit.setPlaceholderText("CFG Scale...")
        self.cfg_edit.setReadOnly(not self.is_editing)
        sd_row2.addWidget(self.cfg_edit)
        
        sd_row2.addWidget(QLabel("种子:"))
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("种子...")
        self.seed_edit.setReadOnly(not self.is_editing)
        sd_row2.addWidget(self.seed_edit)
        sd_layout.addLayout(sd_row2)
        
        # 第三行：尺寸和软件
        sd_row3 = QHBoxLayout()
        sd_row3.addWidget(QLabel("尺寸:"))
        self.size_edit = QLineEdit()
        self.size_edit.setPlaceholderText("尺寸...")
        self.size_edit.setReadOnly(not self.is_editing)
        sd_row3.addWidget(self.size_edit)
        
        sd_row3.addWidget(QLabel("软件:"))
        self.software_edit = QLineEdit()
        self.software_edit.setPlaceholderText("生成软件...")
        self.software_edit.setReadOnly(not self.is_editing)
        sd_row3.addWidget(self.software_edit)
        sd_layout.addLayout(sd_row3)
        
        ai_display_layout.addWidget(sd_group)
        
        layout.addLayout(ai_display_layout)
        
        return panel
    
    def show_ai_config(self):
        """显示AI配置对话框"""
        try:
            QMessageBox.information(self, "AI配置", "AI配置功能正在开发中...")
        except Exception as e:
            self.logger.error("Failed to show AI config: %s", str(e))
    
    def analyze_now(self):
        """立即分析当前图片"""
        try:
            QMessageBox.information(self, "AI分析", "AI分析功能正在开发中...")
        except Exception as e:
            self.logger.error("Failed to analyze image: %s", str(e))
    
    def update_ai_info_display(self, photo_data: dict):
        """更新AI信息显示"""
        self.current_photo = photo_data
        
        if not photo_data:
            # 清空所有字段
            self.model_name_edit.clear()
            self.model_version_edit.clear()
            self.lora_name_edit.clear()
            self.lora_weight_edit.clear()
            self.task_id_edit.clear()
            self.version_edit.clear()
            self.stylize_edit.clear()
            self.quality_edit.clear()
            self.aspect_ratio_edit.clear()
            self.chaos_edit.clear()
            self.weirdness_edit.clear()
            return
        
        # 从照片数据中提取AI信息 - 使用ai_metadata而不是ai_info
        ai_metadata = photo_data.get("ai_metadata", {})
        is_ai_generated = photo_data.get("is_ai_generated", False)
        
        # 处理字符串格式的AI元数据
        if isinstance(ai_metadata, str):
            try:
                import json
                ai_metadata = json.loads(ai_metadata)
                self.logger.info("AI metadata JSON parsed successfully: photo_id=%s", photo_data.get("id"))
            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse AI metadata JSON: photo_id=%s", photo_data.get("id"), 
                                error=str(e))
                ai_metadata = {}
        
        self.logger.info("AI info display updated: photo_id=%s, is_ai_generated=%s, ai_metadata_type=%s, ai_metadata_keys=%s", 
                        photo_data.get("id"), is_ai_generated, type(ai_metadata), 
                        list(ai_metadata.keys()) if isinstance(ai_metadata, dict) else [])
        
        if not is_ai_generated or not ai_metadata:
            # 清空所有字段
            self.model_name_edit.clear()
            self.model_version_edit.clear()
            self.lora_name_edit.clear()
            self.lora_weight_edit.clear()
            self.task_id_edit.clear()
            self.version_edit.clear()
            self.stylize_edit.clear()
            self.quality_edit.clear()
            self.aspect_ratio_edit.clear()
            self.chaos_edit.clear()
            self.weirdness_edit.clear()
            # 清空新添加的字段
            self.positive_prompt_edit.clear()
            self.negative_prompt_edit.clear()
            self.sampler_edit.clear()
            self.steps_edit.clear()
            self.cfg_edit.clear()
            self.seed_edit.clear()
            self.size_edit.clear()
            self.software_edit.clear()
            return
        
        # 更新模型信息 - 使用正确的键名
        self.model_name_edit.setText(ai_metadata.get("model_name", ""))
        self.model_version_edit.setText(ai_metadata.get("model_version", ""))
        
        # 更新Lora信息
        self.lora_name_edit.setText(ai_metadata.get("lora", ""))
        lora_weight = ai_metadata.get("lora_weight", 0.0)
        if lora_weight > 0:
            self.lora_weight_edit.setText(str(lora_weight))
        else:
            self.lora_weight_edit.clear()
        
        # 更新Midjourney参数
        self.task_id_edit.setText(ai_metadata.get("mj_job_id", ""))
        self.version_edit.setText(ai_metadata.get("mj_version", ""))
        stylize = ai_metadata.get("mj_stylize", 0)
        if stylize > 0:
            self.stylize_edit.setText(str(stylize))
        else:
            self.stylize_edit.clear()
        
        quality = ai_metadata.get("mj_quality", 0)
        if quality > 0:
            self.quality_edit.setText(str(quality))
        else:
            self.quality_edit.clear()
            
        self.aspect_ratio_edit.setText(ai_metadata.get("mj_aspect_ratio", ""))
        
        chaos = ai_metadata.get("mj_chaos", 0)
        if chaos > 0:
            self.chaos_edit.setText(str(chaos))
        else:
            self.chaos_edit.clear()
            
        weird = ai_metadata.get("mj_weird", 0)
        if weird > 0:
            self.weirdness_edit.setText(str(weird))
        else:
            self.weirdness_edit.clear()
        
        # 更新模式选择
        raw_mode = ai_metadata.get("mj_raw_mode", False)
        tile_mode = ai_metadata.get("mj_tile", False)
        niji_mode = ai_metadata.get("mj_niji", False)
        
        self.raw_mode_radio.setChecked(raw_mode)
        self.tile_mode_radio.setChecked(tile_mode)
        self.niji_mode_radio.setChecked(niji_mode)
        
        # 更新Prompt信息
        self.positive_prompt_edit.setPlainText(ai_metadata.get("positive_prompt", ""))
        self.negative_prompt_edit.setPlainText(ai_metadata.get("negative_prompt", ""))
        
        # 更新Stable Diffusion参数
        self.sampler_edit.setText(ai_metadata.get("sampler", ""))
        
        steps = ai_metadata.get("steps", 0)
        if steps > 0:
            self.steps_edit.setText(str(steps))
        else:
            self.steps_edit.clear()
            
        cfg_scale = ai_metadata.get("cfg_scale", 0.0)
        if cfg_scale > 0:
            self.cfg_edit.setText(str(cfg_scale))
        else:
            self.cfg_edit.clear()
            
        seed = ai_metadata.get("seed", 0)
        if seed > 0:
            self.seed_edit.setText(str(seed))
        else:
            self.seed_edit.clear()
            
        self.size_edit.setText(ai_metadata.get("size", ""))
        self.software_edit.setText(ai_metadata.get("generation_software", ""))


class PhotoTagsPanel(QWidget):
    """照片标签信息面板"""
    
    def __init__(self, db_manager: DatabaseManager, album_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.album_manager = album_manager
        self.logger = logging.getLogger("picman.gui.photo_tags_panel")
        
        # 当前选中的照片
        self.current_photo = None
        
        # 编辑状态标志
        self.is_editing = False
        
        self.init_ui()
        self.load_tags()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建照片标签信息面板（带滚动条）
        scroll = QScrollArea()
        widget = self.create_photo_tags_panel()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(scroll)
    
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
        self.translate_now_btn.setToolTip("立即翻译当前照片的标签")
        plugin_layout.addWidget(self.translate_now_btn)
        
        # 添加编辑模式切换按钮
        self.edit_mode_btn = QPushButton("编辑模式")
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.setToolTip("点击进入/退出编辑模式")
        self.edit_mode_btn.clicked.connect(self.toggle_edit_mode)
        plugin_layout.addWidget(self.edit_mode_btn)
        
        # 添加保存按钮
        self.save_btn = QPushButton("保存标签")
        self.save_btn.clicked.connect(self.save_tags)
        self.save_btn.setToolTip("保存当前照片的标签")
        self.save_btn.setEnabled(False)  # 初始状态禁用
        plugin_layout.addWidget(self.save_btn)
        
        plugin_layout.addStretch()
        layout.addLayout(plugin_layout)
        
        # 使用QSplitter来控制两个区域的比例
        from PyQt6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 1区 - 标签信息区域（占主要空间）
        tags_info_widget = QWidget()
        tags_info_layout = QVBoxLayout(tags_info_widget)
        tags_info_layout.setSpacing(10)
        
        # 简单标签区域
        simple_tags_group = QGroupBox("简单标签")
        simple_tags_layout = QVBoxLayout(simple_tags_group)
        
        # 英文简单标签
        simple_en_layout = QVBoxLayout()
        simple_en_layout.addWidget(QLabel("英文:"))
        self.simple_en_edit = QTextEdit()
        self.simple_en_edit.setPlaceholderText("输入英文标签...")
        self.simple_en_edit.setReadOnly(True)  # 初始状态为只读
        self.simple_en_edit.setMaximumHeight(80)
        self.simple_en_edit.setMinimumHeight(60)
        simple_en_layout.addWidget(self.simple_en_edit)
        simple_tags_layout.addLayout(simple_en_layout)
        
        # 中文简单标签
        simple_cn_layout = QVBoxLayout()
        simple_cn_layout.addWidget(QLabel("中文:"))
        self.simple_cn_edit = QTextEdit()
        self.simple_cn_edit.setPlaceholderText("输入中文标签...")
        self.simple_cn_edit.setReadOnly(True)  # 初始状态为只读
        self.simple_cn_edit.setMaximumHeight(80)
        self.simple_cn_edit.setMinimumHeight(60)
        simple_cn_layout.addWidget(self.simple_cn_edit)
        simple_tags_layout.addLayout(simple_cn_layout)
        
        tags_info_layout.addWidget(simple_tags_group)
        
        # 普通标签区域
        general_tags_group = QGroupBox("普通标签")
        general_tags_layout = QVBoxLayout(general_tags_group)
        
        # 英文普通标签
        general_en_layout = QVBoxLayout()
        general_en_layout.addWidget(QLabel("英文:"))
        self.general_en_edit = QTextEdit()
        self.general_en_edit.setPlaceholderText("输入英文标签...")
        self.general_en_edit.setReadOnly(True)  # 初始状态为只读
        self.general_en_edit.setMaximumHeight(80)
        self.general_en_edit.setMinimumHeight(60)
        general_en_layout.addWidget(self.general_en_edit)
        general_tags_layout.addLayout(general_en_layout)
        
        # 中文普通标签
        general_cn_layout = QVBoxLayout()
        general_cn_layout.addWidget(QLabel("中文:"))
        self.general_cn_edit = QTextEdit()
        self.general_cn_edit.setPlaceholderText("输入中文标签...")
        self.general_cn_edit.setReadOnly(True)  # 初始状态为只读
        self.general_cn_edit.setMaximumHeight(80)
        self.general_cn_edit.setMinimumHeight(60)
        general_cn_layout.addWidget(self.general_cn_edit)
        general_tags_layout.addLayout(general_cn_layout)
        
        tags_info_layout.addWidget(general_tags_group)
        
        # 详细标签区域
        detailed_tags_group = QGroupBox("详细标签")
        detailed_tags_layout = QVBoxLayout(detailed_tags_group)
        
        # 英文详细标签
        detailed_en_layout = QVBoxLayout()
        detailed_en_layout.addWidget(QLabel("英文:"))
        self.detailed_en_edit = QTextEdit()
        self.detailed_en_edit.setPlaceholderText("输入英文标签...")
        self.detailed_en_edit.setReadOnly(True)  # 初始状态为只读
        self.detailed_en_edit.setMaximumHeight(80)
        self.detailed_en_edit.setMinimumHeight(60)
        detailed_en_layout.addWidget(self.detailed_en_edit)
        detailed_tags_layout.addLayout(detailed_en_layout)
        
        # 中文详细标签
        detailed_cn_edit_layout = QVBoxLayout()
        detailed_cn_edit_layout.addWidget(QLabel("中文:"))
        self.detailed_cn_edit = QTextEdit()
        self.detailed_cn_edit.setPlaceholderText("输入中文标签...")
        self.detailed_cn_edit.setReadOnly(True)  # 初始状态为只读
        self.detailed_cn_edit.setMaximumHeight(80)
        self.detailed_cn_edit.setMinimumHeight(60)
        detailed_cn_edit_layout.addWidget(self.detailed_cn_edit)
        detailed_tags_layout.addLayout(detailed_cn_edit_layout)
        
        tags_info_layout.addWidget(detailed_tags_group)
        
        # 2区 - 标签备注区域（占较小空间）
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        
        notes_group = QGroupBox("标签备注")
        notes_group_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("添加标签备注...")
        self.notes_edit.setReadOnly(True)  # 初始状态为只读
        self.notes_edit.setMaximumHeight(100)  # 设置最大高度
        self.notes_edit.setMinimumHeight(80)   # 设置最小高度
        notes_group_layout.addWidget(self.notes_edit)
        
        notes_layout.addWidget(notes_group)
        
        # 添加到分割器并设置比例
        splitter.addWidget(tags_info_widget)
        splitter.addWidget(notes_widget)
        
        # 设置分割器比例：标签信息占80%，备注占20%
        splitter.setSizes([800, 200])
        
        layout.addWidget(splitter)
        
        return panel
    
    def load_tags(self):
        """Load tags from database."""
        try:
            tags = self.db_manager.get_all_tags()
            self.logger.info("Tags loaded: count=%d", len(tags))
        except Exception as e:
            self.logger.error("Failed to load tags: %s", str(e))
    
    def update_photo_tags_display(self, photo_data: dict):
        """更新照片标签显示"""
        try:
            # 如果正在编辑，不要覆盖用户输入的内容
            if self.is_editing:
                self.logger.info("Skipping display update while editing: photo_id=%s", photo_data.get('id'))
                return
            
            self.current_photo = photo_data
            
            if not photo_data:
                # 清空所有标签字段
                self.simple_en_edit.clear()
                self.simple_cn_edit.clear()
                self.general_en_edit.clear()
                self.general_cn_edit.clear()
                self.detailed_en_edit.clear()
                self.detailed_cn_edit.clear()
                self.notes_edit.clear()
                return
            
            # 更新简单标签
            try:
                simple_en = photo_data.get('simple_tags_en', '')
                simple_cn = photo_data.get('simple_tags_cn', '')
                
                # 如果有正向提示词且没有简单标签，使用正向提示词
                positive_prompt = photo_data.get('positive_prompt', '')
                if positive_prompt and not simple_en:
                    prompt_tags = [tag.strip() for tag in positive_prompt.split(',') if tag.strip()]
                    # 分离中英文标签
                    english_tags = []
                    chinese_tags = []
                    
                    for tag in prompt_tags:
                        if self._is_chinese_text(tag):
                            chinese_tags.append(tag)
                        else:
                            english_tags.append(tag)
                    
                    self.simple_en_edit.setPlainText(', '.join(english_tags))
                    self.simple_cn_edit.setPlainText(', '.join(chinese_tags))
                    self.logger.info("Simple tags loaded from prompt: en=%s, cn=%s", english_tags, chinese_tags)
                else:
                    # 使用数据库中的标签
                    self.simple_en_edit.setPlainText(simple_en)
                    self.simple_cn_edit.setPlainText(simple_cn)
                    self.logger.info("Simple tags loaded: en=%s, cn=%s", simple_en, simple_cn)
            except Exception as e:
                self.simple_en_edit.clear()
                self.simple_cn_edit.clear()
                self.logger.error("Failed to load simple tags: %s", str(e))
            
            # 更新普通标签
            try:
                general_en = photo_data.get('general_tags_en', '')
                general_cn = photo_data.get('general_tags_cn', '')
                
                self.general_en_edit.setPlainText(general_en)
                self.general_cn_edit.setPlainText(general_cn)
                
                self.logger.info("General tags loaded: en=%s, cn=%s", general_en, general_cn)
            except Exception as e:
                self.general_en_edit.clear()
                self.general_cn_edit.clear()
                self.logger.error("Failed to load normal tags: %s", str(e))
            
            # 更新详细标签
            try:
                detailed_en = photo_data.get('detailed_tags_en', '')
                detailed_cn = photo_data.get('detailed_tags_cn', '')
                
                self.detailed_en_edit.setPlainText(detailed_en)
                self.detailed_cn_edit.setPlainText(detailed_cn)
                
                self.logger.info("Detailed tags loaded: en=%s, cn=%s", detailed_en, detailed_cn)
            except Exception as e:
                self.detailed_en_edit.clear()
                self.detailed_cn_edit.clear()
                self.logger.error("Failed to load detailed tags: %s", str(e))
            
            # 更新备注
            notes = photo_data.get('notes', '')
            self.notes_edit.setText(notes)
            self.logger.info("Notes loaded: notes=%s", notes)
                
        except Exception as e:
            self.logger.error("Failed to update photo tags display: %s", str(e))
    
    def _is_chinese_text(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        if not text:
            return False
        
        # 检查是否包含中文字符
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def show_plugin_config(self):
        """显示插件配置对话框"""
        try:
            # 创建配置对话框
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox
            
            config_dialog = QDialog(self)
            config_dialog.setWindowTitle("Google翻译插件配置")
            config_dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(config_dialog)
            
            # 源语言配置
            source_group = QGroupBox("源语言")
            source_layout = QVBoxLayout(source_group)
            source_layout.addWidget(QLabel("选择要翻译的源语言:"))
            
            self.source_lang_combo = QComboBox()
            self.source_lang_combo.addItems([
                "英语 (en)",
                "中文简体 (zh-CN)", 
                "中文繁体 (zh-TW)",
                "日语 (ja)",
                "韩语 (ko)",
                "法语 (fr)",
                "德语 (de)",
                "西班牙语 (es)",
                "俄语 (ru)",
                "自动检测 (auto)"
            ])
            source_layout.addWidget(self.source_lang_combo)
            layout.addWidget(source_group)
            
            # 目标语言配置
            target_group = QGroupBox("目标语言")
            target_layout = QVBoxLayout(target_group)
            target_layout.addWidget(QLabel("选择要翻译成的目标语言:"))
            
            self.target_lang_combo = QComboBox()
            self.target_lang_combo.addItems([
                "英语 (en)",
                "中文简体 (zh-CN)",
                "中文繁体 (zh-TW)", 
                "日语 (ja)",
                "韩语 (ko)",
                "法语 (fr)",
                "德语 (de)",
                "西班牙语 (es)",
                "俄语 (ru)"
            ])
            target_layout.addWidget(self.target_lang_combo)
            layout.addWidget(target_group)
            
            # 按钮
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(config_dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("保存")
            save_btn.clicked.connect(lambda: self._save_plugin_config(config_dialog))
            save_btn.setDefault(True)
            button_layout.addWidget(save_btn)
            
            layout.addLayout(button_layout)
            
            # 显示对话框
            config_dialog.exec()
            
        except Exception as e:
            self.logger.error("Failed to show plugin config: %s", str(e))
            QMessageBox.critical(self, "错误", f"显示插件配置失败: {str(e)}")
    
    def _save_plugin_config(self, dialog):
        """保存插件配置"""
        try:
            # 获取选择的语言
            source_lang = self.source_lang_combo.currentText().split("(")[1].rstrip(")")
            target_lang = self.target_lang_combo.currentText().split("(")[1].rstrip(")")
            
            # 保存到配置文件
            import json
            from pathlib import Path
            
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "plugins" / "google_translate_plugin.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "config": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "max_retries": 3,
                    "base_delay": 0.5,
                    "max_delay": 2.0,
                    "request_interval": 1.0
                }
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("Plugin config saved: source_lang=%s, target_lang=%s", source_lang, target_lang)
            
            # 关闭对话框
            dialog.accept()
            
            # 显示成功消息
            QMessageBox.information(self, "配置保存", f"配置已保存\n源语言: {source_lang}\n目标语言: {target_lang}")
            
        except Exception as e:
            self.logger.error("Failed to save plugin config: %s", str(e))
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def translate_now(self):
        """立即翻译功能"""
        try:
            print("翻译按钮被点击了！")  # 调试信息
            
            # 检查是否启用了Google翻译插件
            if not self.use_translation_plugin.isChecked():
                QMessageBox.warning(self, "提示", "请先勾选'使用Google翻译插件'")
                return
            
            # 检查是否启用了全局翻译
            is_global_translation = self.enable_global_translation.isChecked()
            print(f"全局翻译状态: {is_global_translation}")  # 调试信息
            
            if is_global_translation:
                # 全局翻译：翻译当前相册内所有图片的所有标签
                print("执行全局翻译")  # 调试信息
                self._translate_album_tags()
            else:
                # 单张图片翻译：翻译当前选中图片的所有标签
                print("执行单张图片翻译")  # 调试信息
                self._translate_current_photo_tags()
                
        except Exception as e:
            print(f"翻译出错: {e}")  # 调试信息
            self.logger.error("Failed to translate now: %s", str(e))
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
    def _translate_current_photo_tags(self):
        """翻译当前选中图片的标签"""
        try:
            print("开始翻译当前照片标签")  # 调试信息
            
            if not self.current_photo:
                print("没有选中照片")  # 调试信息
                QMessageBox.information(self, "提示", "请先选择一张照片")
                return
            
            # 创建翻译插件实例
            plugin = self._get_translation_plugin()
            if not plugin:
                return
            
            # 根据插件设置决定翻译方向
            source_lang = getattr(plugin, 'source_language', 'en')
            target_lang = getattr(plugin, 'target_language', 'zh-CN')
            
            print(f"插件翻译设置: {source_lang} → {target_lang}")  # 调试信息
            
            # 获取当前界面上的标签内容
            simple_english_text = self.simple_en_edit.toPlainText().strip()
            simple_chinese_text = self.simple_cn_edit.toPlainText().strip()
            normal_english_text = self.general_en_edit.toPlainText().strip()
            normal_chinese_text = self.general_cn_edit.toPlainText().strip()
            detailed_english_text = self.detailed_en_edit.toPlainText().strip()
            detailed_chinese_text = self.detailed_cn_edit.toPlainText().strip()
            
            # 根据Google翻译设置确定翻译方向
            translation_direction = f"{source_lang} → {target_lang}"
            print(f"开始{translation_direction}翻译")
            
            translated_any = False
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                
                # 智能处理不同类型的标签内容
                def process_tag_content(text, field_name):
                    """智能处理标签内容，支持逗号分隔和长文本两种格式"""
                    if not text:
                        return [], "empty"
                    
                    # 如果文本很长且包含句号，认为是长文本描述
                    if len(text) > 100 and '.' in text:
                        print(f"{field_name}: 检测到长文本描述，直接翻译")
                        return [text], "long_text"
                    else:
                        # 短文本按逗号分隔处理
                        tags = [tag.strip() for tag in text.split(',') if tag.strip()]
                        print(f"{field_name}: 检测到标签列表，标签数量: {len(tags)}")
                        return tags, "tag_list"
                
                # 处理各类标签
                simple_english_tags, simple_type = process_tag_content(simple_english_text, "简单标签")
                normal_english_tags, normal_type = process_tag_content(normal_english_text, "普通标签") 
                detailed_english_tags, detailed_type = process_tag_content(detailed_english_text, "详细标签")
                
                print(f"待翻译内容:")
                print(f"  简单标签({simple_type}): {simple_english_tags[:50] if simple_english_tags else []}")
                print(f"  普通标签({normal_type}): {normal_english_tags[0][:100] + '...' if normal_english_tags and len(str(normal_english_tags[0])) > 100 else normal_english_tags}")
                print(f"  详细标签({detailed_type}): {detailed_english_tags[:50] if detailed_english_tags else []}")
                
                # 分别翻译各标签栏的内容
                if simple_english_tags:
                    print(f"开始翻译简单标签...")
                    if simple_type == "long_text":
                        # 长文本直接翻译
                        translation = plugin.translate_text(simple_english_tags[0])
                        if translation and translation != simple_english_tags[0]:
                            existing_simple_cn = self.simple_cn_edit.toPlainText().strip()
                            if existing_simple_cn:
                                combined_simple_cn = existing_simple_cn + '\n\n' + translation
                            else:
                                combined_simple_cn = translation
                            self.simple_cn_edit.setPlainText(combined_simple_cn)
                            print(f"简单标签长文本翻译成功")
                            translated_any = True
                    else:
                        # 标签列表逐个翻译
                        simple_translations = plugin.translate_tags(simple_english_tags)
                        simple_chinese_results = [simple_translations.get(tag, tag) for tag in simple_english_tags]
                        existing_simple_cn = self.simple_cn_edit.toPlainText().strip()
                        if existing_simple_cn:
                            combined_simple_cn = existing_simple_cn + ', ' + ', '.join(simple_chinese_results)
                        else:
                            combined_simple_cn = ', '.join(simple_chinese_results)
                        self.simple_cn_edit.setPlainText(combined_simple_cn)
                        print(f"简单标签翻译结果: {simple_chinese_results}")
                        translated_any = True
                
                if normal_english_tags:
                    print(f"开始翻译普通标签...")
                    if normal_type == "long_text":
                        # 长文本直接翻译
                        translation = plugin.translate_text(normal_english_tags[0])
                        if translation and translation != normal_english_tags[0]:
                            existing_general_cn = self.general_cn_edit.toPlainText().strip()
                            if existing_general_cn:
                                combined_general_cn = existing_general_cn + '\n\n' + translation
                            else:
                                combined_general_cn = translation
                            self.general_cn_edit.setPlainText(combined_general_cn)
                            print(f"普通标签长文本翻译成功")
                            translated_any = True
                    else:
                        # 标签列表逐个翻译
                        normal_translations = plugin.translate_tags(normal_english_tags)
                        normal_chinese_results = [normal_translations.get(tag, tag) for tag in normal_english_tags]
                        existing_general_cn = self.general_cn_edit.toPlainText().strip()
                        if existing_general_cn:
                            combined_general_cn = existing_general_cn + ', ' + ', '.join(normal_chinese_results)
                        else:
                            combined_general_cn = ', '.join(normal_chinese_results)
                        self.general_cn_edit.setPlainText(combined_general_cn)
                        print(f"普通标签翻译结果: {normal_chinese_results}")
                        translated_any = True
                
                if detailed_english_tags:
                    print(f"开始翻译详细标签...")
                    if detailed_type == "long_text":
                        # 长文本直接翻译
                        translation = plugin.translate_text(detailed_english_tags[0])
                        if translation and translation != detailed_english_tags[0]:
                            existing_detailed_cn = self.detailed_cn_edit.toPlainText().strip()
                            if existing_detailed_cn:
                                combined_detailed_cn = existing_detailed_cn + '\n\n' + translation
                            else:
                                combined_detailed_cn = translation
                            self.detailed_cn_edit.setPlainText(combined_detailed_cn)
                            print(f"详细标签长文本翻译成功")
                            translated_any = True
                    else:
                        # 标签列表逐个翻译
                        detailed_translations = plugin.translate_tags(detailed_english_tags)
                        detailed_chinese_results = [detailed_translations.get(tag, tag) for tag in detailed_english_tags]
                        existing_detailed_cn = self.detailed_cn_edit.toPlainText().strip()
                        if existing_detailed_cn:
                            combined_detailed_cn = existing_detailed_cn + ', ' + ', '.join(detailed_chinese_results)
                        else:
                            combined_detailed_cn = ', '.join(detailed_chinese_results)
                        self.detailed_cn_edit.setPlainText(combined_detailed_cn)
                        print(f"详细标签翻译结果: {detailed_chinese_results}")
                        translated_any = True
                    
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译
                # 分别检查各标签栏的中文内容
                simple_chinese_tags = [tag.strip() for tag in simple_chinese_text.split(',') if tag.strip()] if simple_chinese_text else []
                normal_chinese_tags = [tag.strip() for tag in normal_chinese_text.split(',') if tag.strip()] if normal_chinese_text else []
                detailed_chinese_tags = [tag.strip() for tag in detailed_chinese_text.split(',') if tag.strip()] if detailed_chinese_text else []
                
                print(f"简单标签中文: {simple_chinese_tags}")
                print(f"普通标签中文: {normal_chinese_tags}")
                print(f"详细标签中文: {detailed_chinese_tags}")
                
                # 分别翻译各标签栏的内容
                if simple_chinese_tags:
                    simple_translations = plugin.translate_tags(simple_chinese_tags)
                    simple_english_results = [simple_translations.get(tag, tag) for tag in simple_chinese_tags]
                    # 保留原有英文标签，追加翻译结果
                    existing_simple_en = self.simple_en_edit.toPlainText().strip()
                    if existing_simple_en:
                        combined_simple_en = existing_simple_en + ', ' + ', '.join(simple_english_results)
                    else:
                        combined_simple_en = ', '.join(simple_english_results)
                    self.simple_en_edit.setPlainText(combined_simple_en)
                    print(f"简单标签翻译结果: {simple_english_results}")
                    translated_any = True
                
                if normal_chinese_tags:
                    normal_translations = plugin.translate_tags(normal_chinese_tags)
                    normal_english_results = [normal_translations.get(tag, tag) for tag in normal_chinese_tags]
                    # 保留原有英文标签，追加翻译结果
                    existing_general_en = self.general_en_edit.toPlainText().strip()
                    if existing_general_en:
                        combined_general_en = existing_general_en + ', ' + ', '.join(normal_english_results)
                    else:
                        combined_general_en = ', '.join(normal_english_results)
                    self.general_en_edit.setPlainText(combined_general_en)
                    print(f"普通标签翻译结果: {normal_english_results}")
                    translated_any = True
                
                if detailed_chinese_tags:
                    detailed_translations = plugin.translate_tags(detailed_chinese_tags)
                    detailed_english_results = [detailed_translations.get(tag, tag) for tag in detailed_chinese_tags]
                    # 保留原有英文标签，追加翻译结果
                    existing_detailed_en = self.detailed_en_edit.toPlainText().strip()
                    if existing_detailed_en:
                        combined_detailed_en = existing_detailed_en + ', ' + ', '.join(detailed_english_results)
                    else:
                        combined_detailed_en = ', '.join(detailed_english_results)
                    self.detailed_en_edit.setPlainText(combined_detailed_en)
                    print(f"详细标签翻译结果: {detailed_english_results}")
                    translated_any = True
            else:
                # 其他语言组合，暂时不支持
                print(f"不支持的翻译方向: {source_lang} → {target_lang}")
                QMessageBox.warning(self, "提示", f"不支持的翻译方向: {source_lang} → {target_lang}")
                return
            
            # 关闭翻译插件
            plugin.shutdown()
            
            # 如果有翻译内容，自动保存标签
            if translated_any:
                print("翻译完成，自动保存标签到数据库")
                
                # 临时禁用编辑模式检查，确保UI能刷新
                original_editing_state = self.is_editing
                self.is_editing = False
                
                try:
                    self.save_tags()
                    
                    # 刷新UI显示以确保翻译结果正确显示
                    if self.current_photo:
                        updated_photo = self.db_manager.get_photo(self.current_photo.get('id'))
                        if updated_photo:
                            self.current_photo = updated_photo
                            self.update_photo_tags_display(updated_photo)
                            print("✅ UI显示已刷新，翻译结果应该可见")
                finally:
                    # 恢复编辑状态
                    self.is_editing = original_editing_state
                
                # 显示翻译完成消息
                QMessageBox.information(self, "翻译完成", f"标签翻译完成并已保存！\n翻译方向: {translation_direction}")
            else:
                QMessageBox.information(self, "提示", "没有找到需要翻译的标签内容")
            
        except Exception as e:
            self.logger.error("Failed to translate current photo tags: %s", str(e))
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
    def _translate_album_tags(self):
        """翻译当前相册内所有图片的标签"""
        try:
            print("开始翻译相册内所有图片标签")  # 调试信息
            
            # 获取当前相册ID
            current_album_id = self._get_current_album_id()
            if not current_album_id:
                QMessageBox.warning(self, "提示", "请先选择一个相册")
                return
            
            # 获取相册内所有图片
            album_photos = self.db_manager.get_album_photos(current_album_id)
            if not album_photos:
                QMessageBox.information(self, "提示", "当前相册内没有图片")
                return
            
            print(f"相册内图片数量: {len(album_photos)}")  # 调试信息
            
            # 创建翻译插件实例
            plugin = self._get_translation_plugin()
            if not plugin:
                return
            
            # 显示进度对话框
            from PyQt6.QtWidgets import QProgressDialog, QApplication
            progress = QProgressDialog("正在翻译相册标签...", "取消", 0, len(album_photos), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setMinimumDuration(0)  # 立即显示
            
            translated_count = 0
            failed_count = 0
            total_photos = len(album_photos)
            
            # 根据插件设置决定翻译方向
            source_lang = getattr(plugin, 'source_language', 'en')
            target_lang = getattr(plugin, 'target_language', 'zh-CN')
            translation_direction = f"{source_lang} → {target_lang}"
            
            print(f"相册翻译方向: {translation_direction}")
            
            # 挨个翻译每张图片
            for i, photo in enumerate(album_photos):
                if progress.wasCanceled():
                    print("用户取消了翻译操作")
                    break
                
                photo_id = photo.get('id')
                progress.setValue(i)
                progress.setLabelText(f"正在翻译第 {i+1}/{total_photos} 张图片 (ID: {photo_id})...")
                QApplication.processEvents()
                
                try:
                    print(f"开始翻译图片 {i+1}/{total_photos} (ID: {photo_id})")
                    
                    # 翻译单张图片的标签
                    success = self._translate_single_photo_tags_for_album(photo, plugin, source_lang, target_lang)
                    if success:
                        translated_count += 1
                        print(f"图片 {photo_id} 翻译成功")
                    else:
                        failed_count += 1
                        print(f"图片 {photo_id} 翻译失败或无需翻译的标签")
                    
                    # 强制更新进度显示
                    QApplication.processEvents()
                    
                except Exception as e:
                    failed_count += 1
                    self.logger.error("翻译图片标签失败: %s, error: %s", photo.get('id'), str(e))
                    continue
            
            # 完成进度
            progress.setValue(total_photos)
            progress.close()
            
            # 关闭翻译插件
            try:
                plugin.shutdown()
            except Exception as e:
                print(f"插件关闭时发生异常: {e}")
            
            # 显示详细结果
            result_message = (f"相册翻译完成！\n\n"
                            f"翻译方向: {translation_direction}\n"
                            f"总共处理了 {total_photos} 张图片\n"
                            f"成功翻译了 {translated_count} 张图片\n"
                            f"翻译失败 {failed_count} 张图片\n"
                            f"成功率: {translated_count/total_photos*100:.1f}%")
            
            print(f"批量翻译完成: {result_message}")
            
            # 显示翻译完成消息
            QMessageBox.information(self, "翻译完成", result_message)
            
            # 刷新当前照片的显示，以显示翻译结果
            if hasattr(self, 'current_photo') and self.current_photo:
                self.update_photo_tags_display(self.current_photo)
            
        except Exception as e:
            self.logger.error("Failed to translate album tags: %s", str(e))
            QMessageBox.critical(self, "错误", f"相册翻译失败：{str(e)}")
    
    def _translate_single_photo_tags_for_album(self, photo: dict, plugin, source_lang: str, target_lang: str) -> bool:
        """为相册翻译功能翻译单张图片的标签"""
        try:
            photo_id = photo.get('id')
            if not photo_id:
                return False
            
            print(f"翻译图片 {photo_id} 的标签")  # 调试信息
            
            # 从数据库获取图片的完整标签信息
            photo_data = self.db_manager.get_photo_by_id(photo_id)
            if not photo_data:
                print(f"无法获取图片 {photo_id} 的数据")
                return False
            
            # 获取标签数据
            simple_tags_en = photo_data.get("simple_tags_en", "")
            simple_tags_cn = photo_data.get("simple_tags_cn", "")
            general_tags_en = photo_data.get("general_tags_en", "")
            general_tags_cn = photo_data.get("general_tags_cn", "")
            detailed_tags_en = photo_data.get("detailed_tags_en", "")
            detailed_tags_cn = photo_data.get("detailed_tags_cn", "")
            
            # 如果没有分离式标签字段，尝试从传统字段获取
            if not simple_tags_en and not simple_tags_cn:
                simple_tags = photo_data.get("simple_tags", "")
                if simple_tags:
                    try:
                        import json
                        simple_tags_list = json.loads(simple_tags) if isinstance(simple_tags, str) else simple_tags
                        if isinstance(simple_tags_list, list):
                            # 分离英文和中文标签
                            english_tags = [tag for tag in simple_tags_list if not self._is_chinese_text(tag)]
                            chinese_tags = [tag for tag in simple_tags_list if self._is_chinese_text(tag)]
                            simple_tags_en = ', '.join(english_tags)
                            simple_tags_cn = ', '.join(chinese_tags)
                    except:
                        pass
            
            if not general_tags_en and not general_tags_cn:
                normal_tags = photo_data.get("normal_tags", "")
                if normal_tags:
                    try:
                        import json
                        normal_tags_list = json.loads(normal_tags) if isinstance(normal_tags, str) else normal_tags
                        if isinstance(normal_tags_list, list):
                            english_tags = [tag for tag in normal_tags_list if not self._is_chinese_text(tag)]
                            chinese_tags = [tag for tag in normal_tags_list if self._is_chinese_text(tag)]
                            general_tags_en = ', '.join(english_tags)
                            general_tags_cn = ', '.join(chinese_tags)
                    except:
                        pass
            
            if not detailed_tags_en and not detailed_tags_cn:
                detailed_tags = photo_data.get("detailed_tags", "")
                if detailed_tags:
                    try:
                        import json
                        detailed_tags_list = json.loads(detailed_tags) if isinstance(detailed_tags, str) else detailed_tags
                        if isinstance(detailed_tags_list, list):
                            english_tags = [tag for tag in detailed_tags_list if not self._is_chinese_text(tag)]
                            chinese_tags = [tag for tag in detailed_tags_list if self._is_chinese_text(tag)]
                            detailed_tags_en = ', '.join(english_tags)
                            detailed_tags_cn = ', '.join(chinese_tags)
                    except:
                        pass
            
            translated_any = False
            updates = {}
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                print(f"图片 {photo_id}: 英文→中文翻译")
                
                # 翻译简单标签
                if simple_tags_en.strip():
                    simple_english_tags = [tag.strip() for tag in simple_tags_en.split(',') if tag.strip()]
                    if simple_english_tags:
                        simple_translations = plugin.translate_tags(simple_english_tags)
                        simple_chinese_results = [simple_translations.get(tag, tag) for tag in simple_english_tags]
                        
                        # 保留原有中文标签，追加翻译结果
                        if simple_tags_cn.strip():
                            new_simple_cn = simple_tags_cn + ', ' + ', '.join(simple_chinese_results)
                        else:
                            new_simple_cn = ', '.join(simple_chinese_results)
                        
                        # 准备更新数据
                        updates['simple_tags_cn'] = new_simple_cn
                        print(f"简单标签翻译: {simple_english_tags} → {simple_chinese_results}")
                        translated_any = True
                
                # 翻译普通标签
                if general_tags_en.strip():
                    general_english_tags = [tag.strip() for tag in general_tags_en.split(',') if tag.strip()]
                    if general_english_tags:
                        general_translations = plugin.translate_tags(general_english_tags)
                        general_chinese_results = [general_translations.get(tag, tag) for tag in general_english_tags]
                        
                        # 保留原有中文标签，追加翻译结果
                        if general_tags_cn.strip():
                            new_general_cn = general_tags_cn + ', ' + ', '.join(general_chinese_results)
                        else:
                            new_general_cn = ', '.join(general_chinese_results)
                        
                        # 准备更新数据
                        updates['general_tags_cn'] = new_general_cn
                        print(f"普通标签翻译: {general_english_tags} → {general_chinese_results}")
                        translated_any = True
                
                # 翻译详细标签
                if detailed_tags_en.strip():
                    detailed_english_tags = [tag.strip() for tag in detailed_tags_en.split(',') if tag.strip()]
                    if detailed_english_tags:
                        detailed_translations = plugin.translate_tags(detailed_english_tags)
                        detailed_chinese_results = [detailed_translations.get(tag, tag) for tag in detailed_english_tags]
                        
                        # 保留原有中文标签，追加翻译结果
                        if detailed_tags_cn.strip():
                            new_detailed_cn = detailed_tags_cn + ', ' + ', '.join(detailed_chinese_results)
                        else:
                            new_detailed_cn = ', '.join(detailed_chinese_results)
                        
                        # 准备更新数据
                        updates['detailed_tags_cn'] = new_detailed_cn
                        print(f"详细标签翻译: {detailed_english_tags} → {detailed_chinese_results}")
                        translated_any = True
                
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译
                print(f"图片 {photo_id}: 中文→英文翻译")
                
                # 翻译简单标签
                if simple_tags_cn.strip():
                    simple_chinese_tags = [tag.strip() for tag in simple_tags_cn.split(',') if tag.strip()]
                    if simple_chinese_tags:
                        simple_translations = plugin.translate_tags(simple_chinese_tags)
                        simple_english_results = [simple_translations.get(tag, tag) for tag in simple_chinese_tags]
                        
                        # 保留原有英文标签，追加翻译结果
                        if simple_tags_en.strip():
                            new_simple_en = simple_tags_en + ', ' + ', '.join(simple_english_results)
                        else:
                            new_simple_en = ', '.join(simple_english_results)
                        
                        # 准备更新数据
                        updates['simple_tags_en'] = new_simple_en
                        print(f"简单标签翻译: {simple_chinese_tags} → {simple_english_results}")
                        translated_any = True
                
                # 翻译普通标签
                if general_tags_cn.strip():
                    general_chinese_tags = [tag.strip() for tag in general_tags_cn.split(',') if tag.strip()]
                    if general_chinese_tags:
                        general_translations = plugin.translate_tags(general_chinese_tags)
                        general_english_results = [general_translations.get(tag, tag) for tag in general_chinese_tags]
                        
                        # 保留原有英文标签，追加翻译结果
                        if general_tags_en.strip():
                            new_general_en = general_tags_en + ', ' + ', '.join(general_english_results)
                        else:
                            new_general_en = ', '.join(general_english_results)
                        
                        # 准备更新数据
                        updates['general_tags_en'] = new_general_en
                        print(f"普通标签翻译: {general_chinese_tags} → {general_english_results}")
                        translated_any = True
                
                # 翻译详细标签
                if detailed_tags_cn.strip():
                    detailed_chinese_tags = [tag.strip() for tag in detailed_tags_cn.split(',') if tag.strip()]
                    if detailed_chinese_tags:
                        detailed_translations = plugin.translate_tags(detailed_chinese_tags)
                        detailed_english_results = [detailed_translations.get(tag, tag) for tag in detailed_chinese_tags]
                        
                        # 保留原有英文标签，追加翻译结果
                        if detailed_tags_en.strip():
                            new_detailed_en = detailed_tags_en + ', ' + ', '.join(detailed_english_results)
                        else:
                            new_detailed_en = ', '.join(detailed_english_results)
                        
                        # 准备更新数据
                        updates['detailed_tags_en'] = new_detailed_en
                        print(f"详细标签翻译: {detailed_chinese_tags} → {detailed_english_results}")
                        translated_any = True
            
            # 批量更新数据库
            if translated_any and updates:
                try:
                    success = self.db_manager.update_photo(photo_id, updates)
                    if success:
                        print(f"图片 {photo_id} 翻译结果保存成功")
                    else:
                        print(f"图片 {photo_id} 翻译结果保存失败")
                        # 如果批量更新失败，尝试逐个字段更新
                        for field, value in updates.items():
                            field_success = self.db_manager.update_photo_field(photo_id, field, value)
                            if field_success:
                                print(f"字段 {field} 更新成功")
                            else:
                                print(f"字段 {field} 更新失败")
                except Exception as e:
                    print(f"保存翻译结果时发生错误: {e}")
                    # 尝试逐个字段更新作为备选方案
                    for field, value in updates.items():
                        try:
                            self.db_manager.update_photo_field(photo_id, field, value)
                        except Exception as field_e:
                            print(f"字段 {field} 更新失败: {field_e}")
            
            if translated_any:
                print(f"图片 {photo_id} 翻译完成")
            else:
                print(f"图片 {photo_id} 没有需要翻译的标签")
            
            return translated_any
            
        except Exception as e:
            self.logger.error("翻译图片标签失败: %s, error: %s", photo.get('id'), str(e))
            return False
    
    def _translate_single_photo_tags(self, photo: dict, plugin) -> bool:
        """翻译单张图片的标签 - 使用统一标签系统"""
        try:
            photo_id = photo.get('id')
            if not photo_id:
                return False
            
            print(f"翻译图片 {photo_id} 的标签")  # 调试信息
            
            # 从数据库获取图片的完整数据
            photo_data = self.db_manager.get_photo(photo_id)
            if not photo_data:
                return False
            
            # 使用统一标签系统读取标签数据
            from src.picman.database.manager import UnifiedTagsAccessor
            unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_data)
            
            # 从统一标签中提取标签数据
            simple_tags = []
            normal_tags = []
            detailed_tags = []
            
            # 将英文和中文标签合并为列表格式
            if unified_tags.get("simple", {}).get("en"):
                simple_tags.extend([tag.strip() for tag in unified_tags["simple"]["en"].split(',') if tag.strip()])
            if unified_tags.get("simple", {}).get("zh"):
                simple_tags.extend([tag.strip() for tag in unified_tags["simple"]["zh"].split(',') if tag.strip()])
                
            if unified_tags.get("normal", {}).get("en"):
                normal_tags.extend([tag.strip() for tag in unified_tags["normal"]["en"].split(',') if tag.strip()])
            if unified_tags.get("normal", {}).get("zh"):
                normal_tags.extend([tag.strip() for tag in unified_tags["normal"]["zh"].split(',') if tag.strip()])
                
            if unified_tags.get("detailed", {}).get("en"):
                detailed_tags.extend([tag.strip() for tag in unified_tags["detailed"]["en"].split(',') if tag.strip()])
            if unified_tags.get("detailed", {}).get("zh"):
                detailed_tags.extend([tag.strip() for tag in unified_tags["detailed"]["zh"].split(',') if tag.strip()])
            
            # 根据插件设置决定翻译方向
            source_lang = getattr(plugin, 'source_language', 'en')
            target_lang = getattr(plugin, 'target_language', 'zh-CN')
            
            translated = False
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                translated |= self._translate_english_to_chinese(photo_id, simple_tags, normal_tags, detailed_tags, plugin)
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译
                translated |= self._translate_chinese_to_english(photo_id, simple_tags, normal_tags, detailed_tags, plugin)
            
            return translated
            
        except Exception as e:
            self.logger.error("翻译图片标签失败: %s, error: %s", photo.get('id'), str(e))
            return False
    
    def _translate_english_to_chinese(self, photo_id: int, simple_tags: list, normal_tags: list, detailed_tags: list, plugin) -> bool:
        """英文标签翻译为中文"""
        try:
            translated = False
            
            # 翻译简单标签
            if simple_tags:
                english_simple = [tag for tag in simple_tags if not self._is_chinese_text(tag)]
                if english_simple:
                    translations = plugin.translate_tags(english_simple)
                    for tag in english_simple:
                        if tag in translations and translations[tag] != tag:
                            simple_tags.append(translations[tag])
                            translated = True
            
            # 翻译普通标签
            if normal_tags:
                english_normal = [tag for tag in normal_tags if not self._is_chinese_text(tag)]
                if english_normal:
                    translations = plugin.translate_tags(english_normal)
                    for tag in english_normal:
                        if tag in translations and translations[tag] != tag:
                            normal_tags.append(translations[tag])
                            translated = True
            
            # 翻译详细标签
            if detailed_tags:
                english_detailed = [tag for tag in detailed_tags if not self._is_chinese_text(tag)]
                if english_detailed:
                    translations = plugin.translate_tags(english_detailed)
                    for tag in english_detailed:
                        if tag in translations and translations[tag] != tag:
                            detailed_tags.append(translations[tag])
                            translated = True
            
            # 如果翻译了标签，更新数据库
            if translated:
                self._update_photo_tags_in_database(photo_id, simple_tags, normal_tags, detailed_tags)
            
            return translated
            
        except Exception as e:
            self.logger.error("英文翻译中文失败: %s, error: %s", photo_id, str(e))
            return False
    
    def _translate_chinese_to_english(self, photo_id: int, simple_tags: list, normal_tags: list, detailed_tags: list, plugin) -> bool:
        """中文标签翻译为英文"""
        try:
            translated = False
            
            # 翻译简单标签
            if simple_tags:
                chinese_simple = [tag for tag in simple_tags if self._is_chinese_text(tag)]
                if chinese_simple:
                    translations = plugin.translate_tags(chinese_simple)
                    for tag in chinese_simple:
                        if tag in translations and translations[tag] != tag:
                            simple_tags.append(translations[tag])
                            translated = True
            
            # 翻译普通标签
            if normal_tags:
                chinese_normal = [tag for tag in normal_tags if self._is_chinese_text(tag)]
                if chinese_normal:
                    translations = plugin.translate_tags(chinese_normal)
                    for tag in chinese_normal:
                        if tag in translations and translations[tag] != tag:
                            normal_tags.append(translations[tag])
                            translated = True
            
            # 翻译详细标签
            if detailed_tags:
                chinese_detailed = [tag for tag in detailed_tags if self._is_chinese_text(tag)]
                if chinese_detailed:
                    translations = plugin.translate_tags(chinese_detailed)
                    for tag in chinese_detailed:
                        if tag in translations and translations[tag] != tag:
                            detailed_tags.append(translations[tag])
                            translated = True
            
            # 如果翻译了标签，更新数据库
            if translated:
                self._update_photo_tags_in_database(photo_id, simple_tags, normal_tags, detailed_tags)
            
            return translated
            
        except Exception as e:
            self.logger.error("中文翻译英文失败: %s, error: %s", photo_id, str(e))
            return False
    
    def _update_photo_tags_in_database(self, photo_id: int, simple_tags: list, normal_tags: list, detailed_tags: list):
        """更新数据库中的图片标签 - 使用统一标签系统"""
        try:
            from src.picman.database.manager import UnifiedTagsAccessor
            from datetime import datetime
            
            # 获取当前照片数据
            photo_data = self.db_manager.get_photo(photo_id)
            if not photo_data:
                self.logger.error(f"无法获取照片数据: {photo_id}")
                return False
            
            # 读取现有的统一标签数据
            unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_data)
            
            # 将翻译结果分离为英文和中文，并更新到统一标签结构
            simple_en, simple_cn = self._separate_tags_by_language(simple_tags)
            normal_en, normal_cn = self._separate_tags_by_language(normal_tags)
            detailed_en, detailed_cn = self._separate_tags_by_language(detailed_tags)
            
            # 更新统一标签结构
            unified_tags["simple"]["en"] = ', '.join(simple_en) if simple_en else unified_tags["simple"]["en"]
            unified_tags["simple"]["zh"] = ', '.join(simple_cn) if simple_cn else unified_tags["simple"]["zh"]
            unified_tags["normal"]["en"] = ', '.join(normal_en) if normal_en else unified_tags["normal"]["en"]
            unified_tags["normal"]["zh"] = ', '.join(normal_cn) if normal_cn else unified_tags["normal"]["zh"]
            unified_tags["detailed"]["en"] = ', '.join(detailed_en) if detailed_en else unified_tags["detailed"]["en"]
            unified_tags["detailed"]["zh"] = ', '.join(detailed_cn) if detailed_cn else unified_tags["detailed"]["zh"]
            
            # 更新元数据
            unified_tags["metadata"] = {
                "last_updated": datetime.now().isoformat(),
                "source": "translation_result"
            }
            
            # 使用统一标签系统保存（会自动双写）
            success = self.db_manager.update_photo(photo_id, {
                "unified_tags_data": unified_tags
            })
            
            if success:
                self.logger.info(f"翻译结果保存成功: photo_id={photo_id}")
                
                # 如果是当前显示的照片，更新UI显示
                if self.current_photo and self.current_photo.get('id') == photo_id:
                    self.current_photo = self.db_manager.get_photo(photo_id)
                    self.update_photo_tags_display(self.current_photo)
                    
                return True
            else:
                self.logger.error(f"翻译结果保存失败: photo_id={photo_id}")
                return False
                
        except Exception as e:
            self.logger.error("更新数据库标签失败: photo_id=%s, error=%s", photo_id, str(e))
    
    def _separate_tags_by_language(self, tags_list: list) -> tuple:
        """将标签按语言分离"""
        chinese_tags = []
        english_tags = []
        
        for tag in tags_list:
            if isinstance(tag, str):
                if self._is_chinese_text(tag):
                    chinese_tags.append(tag)
                else:
                    english_tags.append(tag)
        
        return english_tags, chinese_tags
    
    def _get_translation_plugin(self):
        """获取翻译插件实例"""
        try:
            # 检查是否使用Google翻译插件
            if self.use_translation_plugin.isChecked():
                import sys
                import os
                from pathlib import Path
                
                # 添加插件路径
                plugin_path = Path(__file__).parent.parent.parent.parent / "plugins" / "google_translate_plugin"
                if plugin_path.exists():
                    sys.path.insert(0, str(plugin_path))
                    
                    try:
                        from plugin import GoogleTranslatePlugin
                        
                        plugin = GoogleTranslatePlugin()
                        
                        # 获取插件配置
                        config_path = Path(__file__).parent.parent.parent.parent / "config" / "plugins" / "google_translate_plugin.json"
                        if config_path.exists():
                            import json
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                plugin_config = config.get('config', {})
                        else:
                            plugin_config = {
                                'source_language': 'en',
                                'target_language': 'zh-CN'
                            }
                        
                        # 初始化插件
                        if plugin.initialize({'config': plugin_config}):
                            # 确保插件实例有正确的语言设置
                            plugin.source_language = plugin_config.get('source_language', 'en')
                            plugin.target_language = plugin_config.get('target_language', 'zh-CN')
                            self.logger.info(f"Google翻译插件初始化成功，翻译方向: {plugin.source_language} → {plugin.target_language}")
                            return plugin
                        else:
                            self.logger.warning("Google翻译插件初始化失败，使用内置翻译")
                            return self._get_builtin_translator()
                            
                    except ImportError as e:
                        self.logger.warning(f"无法导入Google翻译插件: {e}，使用内置翻译")
                        return self._get_builtin_translator()
                else:
                    self.logger.warning("Google翻译插件路径不存在，使用内置翻译")
                    return self._get_builtin_translator()
            else:
                # 使用内置翻译词典
                return self._get_builtin_translator()
                
        except Exception as e:
            self.logger.error("Failed to get translation plugin: %s", str(e))
            QMessageBox.critical(self, "错误", f"无法初始化翻译插件：{str(e)}")
            return self._get_builtin_translator()
    
    def _get_builtin_translator(self):
        """获取内置翻译器"""
        class BuiltinTranslator:
            def __init__(self, translations_dict):
                self.translations = translations_dict
                # 内置翻译器默认英文→中文，但可以通过配置修改
                self.source_language = "en"
                self.target_language = "zh-CN"
                
                # 尝试从配置文件读取语言设置
                try:
                    import json
                    from pathlib import Path
                    config_path = Path(__file__).parent.parent.parent.parent / "config" / "plugins" / "google_translate_plugin.json"
                    if config_path.exists():
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            plugin_config = config.get('config', {})
                            self.source_language = plugin_config.get('source_language', 'en')
                            self.target_language = plugin_config.get('target_language', 'zh-CN')
                except Exception:
                    pass  # 如果读取失败，使用默认设置
            
            def translate_text(self, text):
                return self.translations.get(text, text)
            
            def translate_tags(self, tags):
                return {tag: self.translations.get(tag, tag) for tag in tags}
            
            def shutdown(self):
                pass
        
        translations = self._get_builtin_translations()
        return BuiltinTranslator(translations)
    
    def _get_builtin_translations(self) -> Dict[str, str]:
        """获取内置翻译词典"""
        return {
            "beautiful": "美丽",
            "landscape": "风景",
            "portrait": "肖像",
            "nature": "自然",
            "city": "城市",
            "building": "建筑",
            "flower": "花",
            "tree": "树",
            "mountain": "山",
            "sea": "海",
            "sky": "天空",
            "sunset": "日落",
            "sunrise": "日出",
            "night": "夜晚",
            "day": "白天",
            "winter": "冬天",
            "summer": "夏天",
            "spring": "春天",
            "autumn": "秋天",
            "hot": "热",
            "cold": "冷",
            "warm": "温暖",
            "cool": "凉爽",
        }
    
    def _get_current_album_id(self) -> Optional[int]:
        """获取当前相册ID"""
        try:
            # 方法1：从主窗口获取当前相册ID
            if hasattr(self, 'parent') and self.parent():
                main_window = self.parent()
                while main_window and not hasattr(main_window, 'current_album_id'):
                    main_window = main_window.parent()
                
                if main_window and hasattr(main_window, 'current_album_id'):
                    current_album_id = main_window.current_album_id
                    if current_album_id:
                        self.logger.info(f"从主窗口获取到当前相册ID: {current_album_id}")
                        return current_album_id
            
            # 方法2：从相册管理器获取当前相册ID
            if hasattr(self, 'album_manager') and self.album_manager:
                if hasattr(self.album_manager, 'current_album_id'):
                    current_album_id = self.album_manager.current_album_id
                    if current_album_id:
                        self.logger.info(f"从相册管理器获取到当前相册ID: {current_album_id}")
                        return current_album_id
            
            # 方法3：从当前照片信息推断相册ID
            if self.current_photo:
                photo_id = self.current_photo.get('id')
                if photo_id:
                    # 查询照片所属的相册
                    album_photos = self.db_manager.get_photo_albums(photo_id)
                    if album_photos:
                        current_album_id = album_photos[0].get('album_id')
                        if current_album_id:
                            self.logger.info(f"从当前照片推断相册ID: {current_album_id}")
                            return current_album_id
            
            # 方法4：从数据库获取最近使用的相册
            try:
                recent_albums = self.db_manager.get_recent_albums(limit=1)
                if recent_albums:
                    current_album_id = recent_albums[0].get('id')
                    if current_album_id:
                        self.logger.info(f"使用最近使用的相册ID: {current_album_id}")
                        return current_album_id
            except Exception as e:
                self.logger.debug(f"获取最近相册失败: {e}")
            
            self.logger.warning("无法获取当前相册ID")
            return None
            
        except Exception as e:
            self.logger.error("Failed to get current album ID: %s", str(e))
            return None
    
    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def save_tags(self):
        """保存当前照片的标签"""
        try:
            if not self.current_photo:
                QMessageBox.warning(self, "提示", "请先选择一张照片")
                return
            
            photo_id = self.current_photo.get('id')
            if not photo_id:
                QMessageBox.warning(self, "提示", "无效的照片ID")
                return
            
            # 获取界面上的标签内容
            simple_en = self.simple_en_edit.toPlainText().strip()
            simple_cn = self.simple_cn_edit.toPlainText().strip()
            general_en = self.general_en_edit.toPlainText().strip()
            general_cn = self.general_cn_edit.toPlainText().strip()
            detailed_en = self.detailed_en_edit.toPlainText().strip()
            detailed_cn = self.detailed_cn_edit.toPlainText().strip()
            notes = self.notes_edit.toPlainText().strip()
            
            # 使用统一标签系统保存
            from src.picman.database.manager import UnifiedTagsAccessor
            from datetime import datetime
            
            # 获取当前照片的统一标签数据
            photo_data = self.db_manager.get_photo(photo_id)
            if not photo_data:
                QMessageBox.warning(self, "保存失败", "无法获取照片数据")
                return
            
            # 读取现有的统一标签数据
            unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_data)
            
            # 更新统一标签结构
            unified_tags["simple"]["en"] = simple_en
            unified_tags["simple"]["zh"] = simple_cn
            unified_tags["normal"]["en"] = general_en
            unified_tags["normal"]["zh"] = general_cn
            unified_tags["detailed"]["en"] = detailed_en
            unified_tags["detailed"]["zh"] = detailed_cn
            unified_tags["notes"] = notes
            
            # 更新元数据
            unified_tags["metadata"] = {
                "last_updated": datetime.now().isoformat(),
                "source": "tag_manager_manual_edit"
            }
            
            # 使用统一标签系统保存（会自动双写）
            print(f"🔍 尝试保存统一标签: {unified_tags}")
            success = self.db_manager.update_photo(photo_id, {
                "unified_tags_data": unified_tags
            })
            print(f"🔍 统一标签保存结果: {success}")
            
            # 如果统一标签保存失败，尝试直接保存分离字段
            if not success:
                self.logger.warning("Unified tags save failed, trying direct field save")
                print(f"🔍 尝试直接保存分离字段")
                success = self.db_manager.update_photo(photo_id, {
                    "simple_tags_en": simple_en,
                    "simple_tags_cn": simple_cn,
                    "general_tags_en": general_en,
                    "general_tags_cn": general_cn,
                    "detailed_tags_en": detailed_en,
                    "detailed_tags_cn": detailed_cn,
                    "notes": notes
                })
                print(f"🔍 分离字段保存结果: {success}")
            
            if success:
                QMessageBox.information(self, "保存成功", "标签已成功保存")
                self.logger.info("Tags saved successfully: photo_id=%s", photo_id)
                
                # 重新获取最新的照片数据并刷新UI显示
                self.current_photo = self.db_manager.get_photo(photo_id)
                if self.current_photo:
                    self.update_photo_tags_display(self.current_photo)
                    print("✅ 标签保存成功，UI显示已刷新")
            else:
                QMessageBox.warning(self, "保存失败", "标签保存失败，请重试")
                self.logger.error("Failed to save tags: photo_id=%s", photo_id)
            
        except Exception as e:
            self.logger.error("Failed to save tags: %s", str(e))
            QMessageBox.critical(self, "错误", f"保存标签时发生错误: {str(e)}")
    

    def _is_chinese_text(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        if not text:
            return False
        
        # 检查是否包含中文字符
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def toggle_edit_mode(self):
        """切换编辑模式"""
        self.is_editing = not self.is_editing
        self.edit_mode_btn.setChecked(self.is_editing)
        
        # 更新UI状态
        self._update_ui_editing_state()
        
        # 更新按钮状态
        self.save_btn.setEnabled(self.is_editing)
        
        # 显示状态信息
        if self.is_editing:
            self.logger.info("Entered edit mode")
        else:
            self.logger.info("Exited edit mode")
    
    def _update_ui_editing_state(self):
        """更新UI编辑状态"""
        # 更新所有标签输入框的只读状态
        self.simple_en_edit.setReadOnly(not self.is_editing)
        self.simple_cn_edit.setReadOnly(not self.is_editing)
        self.general_en_edit.setReadOnly(not self.is_editing)
        self.general_cn_edit.setReadOnly(not self.is_editing)
        self.detailed_en_edit.setReadOnly(not self.is_editing)
        self.detailed_cn_edit.setReadOnly(not self.is_editing)
        self.notes_edit.setReadOnly(not self.is_editing)
        
        # 更新按钮文本
        if self.is_editing:
            self.edit_mode_btn.setText("退出编辑")
            self.edit_mode_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        else:
            self.edit_mode_btn.setText("编辑模式")
            self.edit_mode_btn.setStyleSheet("")
        
        self.logger.info("UI editing state updated: is_editing=%s", self.is_editing)


class TagManager(QWidget):
    """Tag management widget with tabbed interface."""
    
    tag_selected = pyqtSignal(int)  # tag_id
    tags_updated = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager, album_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.album_manager = album_manager
        self.logger = logging.getLogger("picman.gui.tag_manager")
        
        # 当前选中的照片
        self.current_photo = None
        
        # 编辑状态标志
        self.is_editing = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        
        # 创建AI图片信息面板
        self.ai_panel = AIImageInfoPanel(self.db_manager, self.album_manager)
        self.tab_widget.addTab(self.ai_panel, "AI图片信息")
        
        # 创建照片标签信息面板
        self.photo_tags_panel = PhotoTagsPanel(self.db_manager, self.album_manager)
        self.tab_widget.addTab(self.photo_tags_panel, "照片标签信息")
        
        layout.addWidget(self.tab_widget)
    
    def update_photo_display(self, photo_data: dict):
        """更新照片显示"""
        self.current_photo = photo_data
        
        # 更新两个面板的显示
        self.ai_panel.update_ai_info_display(photo_data)
        self.photo_tags_panel.update_photo_tags_display(photo_data)
    
    def set_editing_mode(self, editing: bool):
        """设置编辑模式"""
        self.is_editing = editing
        
        # 更新两个面板的编辑模式
        self.ai_panel.is_editing = editing
        self.photo_tags_panel.is_editing = editing
        
        # 更新UI状态
        self._update_ui_editing_state()
    
    def _update_ui_editing_state(self):
        """更新UI编辑状态"""
        # 更新AI面板的编辑状态
        self.ai_panel.model_name_edit.setReadOnly(not self.is_editing)
        self.ai_panel.model_version_edit.setReadOnly(not self.is_editing)
        self.ai_panel.lora_name_edit.setReadOnly(not self.is_editing)
        self.ai_panel.lora_weight_edit.setReadOnly(not self.is_editing)
        self.ai_panel.task_id_edit.setReadOnly(not self.is_editing)
        self.ai_panel.version_edit.setReadOnly(not self.is_editing)
        self.ai_panel.stylize_edit.setReadOnly(not self.is_editing)
        self.ai_panel.quality_edit.setReadOnly(not self.is_editing)
        self.ai_panel.aspect_ratio_edit.setReadOnly(not self.is_editing)
        self.ai_panel.chaos_edit.setReadOnly(not self.is_editing)
        self.ai_panel.weirdness_edit.setReadOnly(not self.is_editing)
        
        self.ai_panel.raw_mode_radio.setEnabled(self.is_editing)
        self.ai_panel.tile_mode_radio.setEnabled(self.is_editing)
        self.ai_panel.niji_mode_radio.setEnabled(self.is_editing)
        
        # 更新新添加字段的编辑状态
        self.ai_panel.positive_prompt_edit.setReadOnly(not self.is_editing)
        self.ai_panel.negative_prompt_edit.setReadOnly(not self.is_editing)
        self.ai_panel.sampler_edit.setReadOnly(not self.is_editing)
        self.ai_panel.steps_edit.setReadOnly(not self.is_editing)
        self.ai_panel.cfg_edit.setReadOnly(not self.is_editing)
        self.ai_panel.seed_edit.setReadOnly(not self.is_editing)
        self.ai_panel.size_edit.setReadOnly(not self.is_editing)
        self.ai_panel.software_edit.setReadOnly(not self.is_editing)
        
        # 更新照片标签面板的编辑状态
        self.photo_tags_panel.simple_en_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.simple_cn_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.general_en_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.general_cn_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.detailed_en_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.detailed_cn_edit.setReadOnly(not self.is_editing)
        self.photo_tags_panel.notes_edit.setReadOnly(not self.is_editing)
    
    # 保持原有的公共接口，确保兼容性
    def update_photo_tags_display(self, photo_data: dict):
        """更新照片标签显示（兼容性方法）"""
        self.update_photo_display(photo_data)
    
    def _update_ai_info_display(self, photo_data: dict):
        """更新AI信息显示（兼容性方法）"""
        self.update_photo_display(photo_data)
    
    def refresh_current_photo_display(self):
        """刷新当前照片显示（兼容性方法）"""
        if self.current_photo:
            self.update_photo_display(self.current_photo)
    
    def save_tags_to_database(self):
        """保存标签到数据库（兼容性方法）"""
        # 这里可以添加保存逻辑
        pass
    
    def _is_chinese_text(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        if not text:
            return False
        
        # 检查是否包含中文字符
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    

    
    
    def update_photo_tags_display(self, photo_data: dict):
        """更新照片标签显示"""
        try:
            # 如果正在编辑，不要覆盖用户输入的内容
            if self.is_editing:
                self.logger.info("Skipping display update while editing: photo_id=%s", photo_data.get('id'))
                return
            
            self.current_photo = photo_data
            
            if not photo_data:
                # 清空所有标签字段
                self.simple_en_edit.clear()
                self.simple_cn_edit.clear()
                self.general_en_edit.clear()
                self.general_cn_edit.clear()
                self.detailed_en_edit.clear()
                self.detailed_cn_edit.clear()
                self.notes_edit.clear()
                return
            
            # 更新简单标签
            try:
                simple_en = photo_data.get('simple_tags_en', '')
                simple_cn = photo_data.get('simple_tags_cn', '')
                
                # 如果有正向提示词且没有简单标签，使用正向提示词
                positive_prompt = photo_data.get('positive_prompt', '')
                if positive_prompt and not simple_en:
                    prompt_tags = [tag.strip() for tag in positive_prompt.split(',') if tag.strip()]
                    # 分离中英文标签
                    english_tags = []
                    chinese_tags = []
                    
                    for tag in prompt_tags:
                        if self._is_chinese_text(tag):
                            chinese_tags.append(tag)
                        else:
                            english_tags.append(tag)
                    
                    self.simple_en_edit.setPlainText(', '.join(english_tags))
                    self.simple_cn_edit.setPlainText(', '.join(chinese_tags))
                    self.logger.info("Simple tags loaded from prompt: en=%s, cn=%s", english_tags, chinese_tags)
                else:
                    # 使用数据库中的标签
                    self.simple_en_edit.setPlainText(simple_en)
                    self.simple_cn_edit.setPlainText(simple_cn)
                    self.logger.info("Simple tags loaded: en=%s, cn=%s", simple_en, simple_cn)
            except Exception as e:
                self.simple_en_edit.clear()
                self.simple_cn_edit.clear()
                self.logger.error("Failed to load simple tags: %s", str(e))
            
            # 更新普通标签
            try:
                general_en = photo_data.get('general_tags_en', '')
                general_cn = photo_data.get('general_tags_cn', '')
                
                self.general_en_edit.setPlainText(general_en)
                self.general_cn_edit.setPlainText(general_cn)
                
                self.logger.info("General tags loaded: en=%s, cn=%s", general_en, general_cn)
            except Exception as e:
                self.general_en_edit.clear()
                self.general_cn_edit.clear()
                self.logger.error("Failed to load normal tags: %s", str(e))
            
            # 更新详细标签
            try:
                detailed_en = photo_data.get('detailed_tags_en', '')
                detailed_cn = photo_data.get('detailed_tags_cn', '')
                
                self.detailed_en_edit.setPlainText(detailed_en)
                self.detailed_cn_edit.setPlainText(detailed_cn)
                
                self.logger.info("Detailed tags loaded: en=%s, cn=%s", detailed_en, detailed_cn)
            except Exception as e:
                self.detailed_en_edit.clear()
                self.detailed_cn_edit.clear()
                self.logger.error("Failed to load detailed tags: %s", str(e))
            
            # 更新备注
            notes = photo_data.get('notes', '')
            self.notes_edit.setText(notes)
            self.logger.info("Notes loaded: notes=%s", notes)
                
        except Exception as e:
            self.logger.error("Failed to update photo tags display: %s", str(e))


class TagManager(QWidget):
    """标签管理器主类"""
    
    photo_selected = pyqtSignal(int)  # 照片选择信号
    tag_selected = pyqtSignal(int)    # 标签选择信号
    
    def __init__(self, db_manager: DatabaseManager, album_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.album_manager = album_manager
        self.logger = logging.getLogger("picman.gui.tag_manager")
        
        # 当前选中的照片
        self.current_photo = None
        
        # 编辑状态标志
        self.is_editing = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # AI图片信息标签页
        self.ai_info_panel = AIImageInfoPanel(self.db_manager, self.album_manager)
        self.tab_widget.addTab(self.ai_info_panel, "AI信息")
        
        # 照片标签信息标签页
        self.photo_tags_panel = PhotoTagsPanel(self.db_manager, self.album_manager)
        self.tab_widget.addTab(self.photo_tags_panel, "标签信息")
        
        layout.addWidget(self.tab_widget)
    
    def update_photo_display(self, photo_data: dict):
        """更新照片显示"""
        self.current_photo = photo_data
        
        # 更新AI信息面板
        self.ai_info_panel.update_ai_info_display(photo_data)
        
        # 更新标签信息面板
        self.photo_tags_panel.current_photo = photo_data
        self.photo_tags_panel.update_photo_tags_display(photo_data)
    
    def set_editing_mode(self, editing: bool):
        """设置编辑模式"""
        self.is_editing = editing
        self.ai_info_panel.is_editing = editing
        self.photo_tags_panel.is_editing = editing
        
        # 更新UI控件的只读状态
        # 这里可以添加更多的UI状态更新逻辑