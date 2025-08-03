"""
Tag management UI components.
"""

import time
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QColorDialog,
    QMessageBox, QInputDialog, QMenu, QFrame, QSplitter, QGroupBox,
    QCheckBox, QTextEdit, QScrollArea
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
    
    def __init__(self, db_manager: DatabaseManager, album_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.album_manager = album_manager
        self.logger = structlog.get_logger("picman.gui.tag_manager")
        
        # 当前选中的照片
        self.current_photo = None
        
        # 编辑状态标志
        self.is_editing = False
        
        self.init_ui()
        self.load_tags()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部分：AI图片信息（带滚动条）
        top_scroll = QScrollArea()
        top_widget = self.create_tag_management_panel()
        top_scroll.setWidget(top_widget)
        top_scroll.setWidgetResizable(True)
        top_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        splitter.addWidget(top_scroll)
        
        # 下半部分：照片标签信息（带滚动条）
        bottom_scroll = QScrollArea()
        bottom_widget = self.create_photo_tags_panel()
        bottom_scroll.setWidget(bottom_widget)
        bottom_scroll.setWidgetResizable(True)
        bottom_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        bottom_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        splitter.addWidget(bottom_scroll)
        
        # 设置分割器比例 - 调整AI图片信息和照片标签信息的比例
        splitter.setSizes([200, 300])  # AI图片信息占200，照片标签信息占300
        
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
        
        # Midjourney特有参数区域
        mj_group = QGroupBox("Midjourney参数")
        mj_layout = QVBoxLayout(mj_group)
        mj_layout.setSpacing(5)
        
        # 第一行：任务ID、版本
        mj_row1_layout = QHBoxLayout()
        
        # 任务ID
        mj_job_id_layout = QVBoxLayout()
        mj_job_id_layout.addWidget(QLabel("任务ID:"))
        self.mj_job_id_edit = QLineEdit()
        self.mj_job_id_edit.setPlaceholderText("Midjourney任务ID...")
        mj_job_id_layout.addWidget(self.mj_job_id_edit)
        mj_row1_layout.addLayout(mj_job_id_layout)
        
        # 版本
        mj_version_layout = QVBoxLayout()
        mj_version_layout.addWidget(QLabel("版本:"))
        self.mj_version_edit = QLineEdit()
        self.mj_version_edit.setPlaceholderText("Midjourney版本...")
        mj_version_layout.addWidget(self.mj_version_edit)
        mj_row1_layout.addLayout(mj_version_layout)
        
        mj_layout.addLayout(mj_row1_layout)
        
        # 第二行：风格化、质量、宽高比
        mj_row2_layout = QHBoxLayout()
        
        # 风格化
        mj_stylize_layout = QVBoxLayout()
        mj_stylize_layout.addWidget(QLabel("风格化:"))
        self.mj_stylize_edit = QLineEdit()
        self.mj_stylize_edit.setPlaceholderText("风格化参数...")
        mj_stylize_layout.addWidget(self.mj_stylize_edit)
        mj_row2_layout.addLayout(mj_stylize_layout)
        
        # 质量
        mj_quality_layout = QVBoxLayout()
        mj_quality_layout.addWidget(QLabel("质量:"))
        self.mj_quality_edit = QLineEdit()
        self.mj_quality_edit.setPlaceholderText("质量参数...")
        mj_quality_layout.addWidget(self.mj_quality_edit)
        mj_row2_layout.addLayout(mj_quality_layout)
        
        # 宽高比
        mj_ar_layout = QVBoxLayout()
        mj_ar_layout.addWidget(QLabel("宽高比:"))
        self.mj_ar_edit = QLineEdit()
        self.mj_ar_edit.setPlaceholderText("宽高比...")
        mj_ar_layout.addWidget(self.mj_ar_edit)
        mj_row2_layout.addLayout(mj_ar_layout)
        
        mj_layout.addLayout(mj_row2_layout)
        
        # 第三行：特殊模式
        mj_row3_layout = QHBoxLayout()
        
        # 原始模式
        self.mj_raw_mode_checkbox = QCheckBox("原始模式")
        mj_row3_layout.addWidget(self.mj_raw_mode_checkbox)
        
        # 平铺模式
        self.mj_tile_checkbox = QCheckBox("平铺模式")
        mj_row3_layout.addWidget(self.mj_tile_checkbox)
        
        # Niji模式
        self.mj_niji_checkbox = QCheckBox("Niji模式")
        mj_row3_layout.addWidget(self.mj_niji_checkbox)
        
        mj_row3_layout.addStretch()
        mj_layout.addLayout(mj_row3_layout)
        
        # 第四行：混乱度、怪异度
        mj_row4_layout = QHBoxLayout()
        
        # 混乱度
        mj_chaos_layout = QVBoxLayout()
        mj_chaos_layout.addWidget(QLabel("混乱度:"))
        self.mj_chaos_edit = QLineEdit()
        self.mj_chaos_edit.setPlaceholderText("混乱度参数...")
        mj_chaos_layout.addWidget(self.mj_chaos_edit)
        mj_row4_layout.addLayout(mj_chaos_layout)
        
        # 怪异度
        mj_weird_layout = QVBoxLayout()
        mj_weird_layout.addWidget(QLabel("怪异度:"))
        self.mj_weird_edit = QLineEdit()
        self.mj_weird_edit.setPlaceholderText("怪异度参数...")
        mj_weird_layout.addWidget(self.mj_weird_edit)
        mj_row4_layout.addLayout(mj_weird_layout)
        
        mj_row4_layout.addStretch()
        mj_layout.addLayout(mj_row4_layout)
        
        ai_display_layout.addWidget(mj_group)
        
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
        
        # 第一行：采样器、步数、CFG
        row1_layout = QHBoxLayout()
        
        # 采样器
        sampler_layout = QVBoxLayout()
        sampler_layout.addWidget(QLabel("采样器:"))
        self.sampler_edit = QLineEdit()
        self.sampler_edit.setPlaceholderText("输入采样器...")
        sampler_layout.addWidget(self.sampler_edit)
        row1_layout.addLayout(sampler_layout)
        
        # 步数
        steps_layout = QVBoxLayout()
        steps_layout.addWidget(QLabel("步数:"))
        self.steps_edit = QLineEdit()
        self.steps_edit.setPlaceholderText("输入步数...")
        steps_layout.addWidget(self.steps_edit)
        row1_layout.addLayout(steps_layout)
        
        # CFG Scale
        cfg_layout = QVBoxLayout()
        cfg_layout.addWidget(QLabel("CFG:"))
        self.cfg_edit = QLineEdit()
        self.cfg_edit.setPlaceholderText("输入CFG Scale...")
        cfg_layout.addWidget(self.cfg_edit)
        row1_layout.addLayout(cfg_layout)
        
        params_layout.addLayout(row1_layout)
        
        # 第二行：种子、尺寸、Clip Skip
        row2_layout = QHBoxLayout()
        
        # 种子
        seed_layout = QVBoxLayout()
        seed_layout.addWidget(QLabel("种子:"))
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("输入种子值...")
        seed_layout.addWidget(self.seed_edit)
        row2_layout.addLayout(seed_layout)
        
        # 尺寸
        size_layout = QVBoxLayout()
        size_layout.addWidget(QLabel("尺寸:"))
        self.size_edit = QLineEdit()
        self.size_edit.setPlaceholderText("输入图片尺寸...")
        size_layout.addWidget(self.size_edit)
        row2_layout.addLayout(size_layout)
        
        # Clip Skip
        clip_skip_layout = QVBoxLayout()
        clip_skip_layout.addWidget(QLabel("Clip Skip:"))
        self.clip_skip_edit = QLineEdit()
        self.clip_skip_edit.setPlaceholderText("输入Clip Skip...")
        clip_skip_layout.addWidget(self.clip_skip_edit)
        row2_layout.addLayout(clip_skip_layout)
        
        params_layout.addLayout(row2_layout)
        
        # 第三行：去噪强度、Lora权重、模型版本
        row3_layout = QHBoxLayout()
        
        # 去噪强度
        denoising_layout = QVBoxLayout()
        denoising_layout.addWidget(QLabel("去噪强度:"))
        self.denoising_edit = QLineEdit()
        self.denoising_edit.setPlaceholderText("输入去噪强度...")
        denoising_layout.addWidget(self.denoising_edit)
        row3_layout.addLayout(denoising_layout)
        
        # Lora权重
        lora_weight_layout = QVBoxLayout()
        lora_weight_layout.addWidget(QLabel("Lora权重:"))
        self.lora_weight_edit = QLineEdit()
        self.lora_weight_edit.setPlaceholderText("输入Lora权重...")
        lora_weight_layout.addWidget(self.lora_weight_edit)
        row3_layout.addLayout(lora_weight_layout)
        
        # 模型版本
        model_version_layout = QVBoxLayout()
        model_version_layout.addWidget(QLabel("模型版本:"))
        self.model_version_edit = QLineEdit()
        self.model_version_edit.setPlaceholderText("输入模型版本...")
        model_version_layout.addWidget(self.model_version_edit)
        row3_layout.addLayout(model_version_layout)
        
        params_layout.addLayout(row3_layout)
        
        # 第四行：生成软件、生成日期
        row4_layout = QHBoxLayout()
        
        # 生成软件
        software_layout = QVBoxLayout()
        software_layout.addWidget(QLabel("生成软件:"))
        self.software_edit = QLineEdit()
        self.software_edit.setPlaceholderText("输入生成软件...")
        software_layout.addWidget(self.software_edit)
        row4_layout.addLayout(software_layout)
        
        # 生成日期
        date_layout = QVBoxLayout()
        date_layout.addWidget(QLabel("生成日期:"))
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("输入生成日期...")
        date_layout.addWidget(self.date_edit)
        row4_layout.addLayout(date_layout)
        
        params_layout.addLayout(row4_layout)
        
        # 工作流信息区域
        workflow_group = QGroupBox("工作流信息")
        workflow_layout = QVBoxLayout(workflow_group)
        workflow_layout.setSpacing(5)
        
        # 工作流摘要
        workflow_summary_layout = QVBoxLayout()
        workflow_summary_layout.addWidget(QLabel("工作流摘要:"))
        self.workflow_summary_edit = QTextEdit()
        self.workflow_summary_edit.setMaximumHeight(60)
        self.workflow_summary_edit.setPlaceholderText("工作流摘要信息...")
        workflow_summary_layout.addWidget(self.workflow_summary_edit)
        workflow_layout.addLayout(workflow_summary_layout)
        
        # 工作流统计信息
        workflow_stats_layout = QHBoxLayout()
        
        # 节点数量
        node_count_layout = QVBoxLayout()
        node_count_layout.addWidget(QLabel("节点数量:"))
        self.node_count_edit = QLineEdit()
        self.node_count_edit.setPlaceholderText("节点数量...")
        node_count_layout.addWidget(self.node_count_edit)
        workflow_stats_layout.addLayout(node_count_layout)
        
        # 连接数量
        connection_count_layout = QVBoxLayout()
        connection_count_layout.addWidget(QLabel("连接数量:"))
        self.connection_count_edit = QLineEdit()
        self.connection_count_edit.setPlaceholderText("连接数量...")
        connection_count_layout.addWidget(self.connection_count_edit)
        workflow_stats_layout.addLayout(connection_count_layout)
        
        # 工作流版本
        workflow_version_layout = QVBoxLayout()
        workflow_version_layout.addWidget(QLabel("工作流版本:"))
        self.workflow_version_edit = QLineEdit()
        self.workflow_version_edit.setPlaceholderText("工作流版本...")
        workflow_version_layout.addWidget(self.workflow_version_edit)
        workflow_stats_layout.addLayout(workflow_version_layout)
        
        workflow_layout.addLayout(workflow_stats_layout)
        
        ai_display_layout.addWidget(workflow_group)
        
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
        
        # 添加保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_tags_btn = QPushButton("保存标签")
        self.save_tags_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.save_tags_btn.clicked.connect(self.save_tags_to_database)
        self.save_tags_btn.setToolTip("保存当前标签和备注到数据库")
        save_layout.addWidget(self.save_tags_btn)
        
        layout.addLayout(save_layout)
        
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
            # 如果正在编辑，不要覆盖用户输入的内容
            if self.is_editing:
                self.logger.info("Skipping display update while editing", photo_id=photo_data.get('id'))
                return
                
            self.current_photo = photo_data
            
            # 获取标签数据
            simple_tags = photo_data.get('simple_tags', [])
            normal_tags = photo_data.get('normal_tags', [])
            detailed_tags = photo_data.get('detailed_tags', [])
            tag_translations = photo_data.get('tag_translations', {})
            
            # 解析标签数据（可能是JSON字符串或列表/字典）
            import json
            if isinstance(simple_tags, str):
                try:
                    simple_tags = json.loads(simple_tags) if simple_tags else []
                except json.JSONDecodeError:
                    simple_tags = []
            
            if isinstance(normal_tags, str):
                try:
                    normal_tags = json.loads(normal_tags) if normal_tags else []
                except json.JSONDecodeError:
                    normal_tags = []
            
            if isinstance(detailed_tags, str):
                try:
                    detailed_tags = json.loads(detailed_tags) if detailed_tags else []
                except json.JSONDecodeError:
                    detailed_tags = []
            
            if isinstance(tag_translations, str):
                try:
                    tag_translations = json.loads(tag_translations) if tag_translations else {}
                except json.JSONDecodeError:
                    tag_translations = {}
            
            # 分离中英文标签的函数
            def separate_tags_by_language(tags_list):
                chinese_tags = []
                english_tags = []
                
                for tag in tags_list:
                    if self._is_chinese_text(tag):
                        chinese_tags.append(tag)
                    else:
                        english_tags.append(tag)
                
                return english_tags, chinese_tags
            
            # 更新简单标签
            if simple_tags:
                english_tags, chinese_tags = separate_tags_by_language(simple_tags)
                english_text = ', '.join(english_tags)
                chinese_text = ', '.join(chinese_tags)  # 直接显示中文标签
                self.simple_tags_english.setPlainText(english_text)
                self.simple_tags_chinese.setPlainText(chinese_text)
            else:
                self.simple_tags_english.setPlainText("")
                self.simple_tags_chinese.setPlainText("")
            
            # 更新普通标签
            if normal_tags:
                english_tags, chinese_tags = separate_tags_by_language(normal_tags)
                english_text = ', '.join(english_tags)
                chinese_text = ', '.join(chinese_tags)  # 直接显示中文标签
                self.normal_tags_english.setPlainText(english_text)
                self.normal_tags_chinese.setPlainText(chinese_text)
            else:
                self.normal_tags_english.setPlainText("")
                self.normal_tags_chinese.setPlainText("")
            
            # 更新详细标签
            if detailed_tags:
                english_tags, chinese_tags = separate_tags_by_language(detailed_tags)
                english_text = ', '.join(english_tags)
                chinese_text = ', '.join(chinese_tags)  # 直接显示中文标签
                self.detailed_tags_english.setPlainText(english_text)
                self.detailed_tags_chinese.setPlainText(chinese_text)
            else:
                self.detailed_tags_english.setPlainText("")
                self.detailed_tags_chinese.setPlainText("")
            
            # 更新标签备注
            notes = photo_data.get('notes', '')  # 使用数据库中的 'notes' 字段
            if self.tags_notes.toPlainText() != notes:
                self.tags_notes.setPlainText(notes)
            
            # 高亮显示照片使用的标签
            all_tags = simple_tags + normal_tags + detailed_tags
            self.highlight_photo_tags(all_tags)
            
            # 更新AI信息显示
            self._update_ai_info_display(photo_data)
            
            self.logger.info("Photo tags display updated", photo_id=photo_data.get('id'))
            
        except Exception as e:
            self.logger.error("Failed to update photo tags display", error=str(e))
    
    def _update_ai_info_display(self, photo_data: dict):
        """更新AI信息显示"""
        try:
            # 获取AI元数据
            ai_metadata = photo_data.get('ai_metadata', {})
            is_ai_generated = photo_data.get('is_ai_generated', False)
            
            if not is_ai_generated or not ai_metadata:
                # 清空所有AI信息字段
                self.model_name_edit.setText("")
                self.sampler_edit.setText("")
                self.steps_edit.setText("")
                self.cfg_edit.setText("")
                self.seed_edit.setText("")
                self.size_edit.setText("")
                self.clip_skip_edit.setText("")
                self.denoising_edit.setText("")
                self.lora_weight_edit.setText("")
                self.model_version_edit.setText("")
                self.software_edit.setText("")
                self.date_edit.setText("")
                self.workflow_summary_edit.setPlainText("")
                self.node_count_edit.setText("")
                self.connection_count_edit.setText("")
                self.workflow_version_edit.setText("")
                self.positive_prompt_edit.setPlainText("")
                self.negative_prompt_edit.setPlainText("")
                
                # 清空Midjourney特有参数
                self.mj_job_id_edit.setText("")
                self.mj_version_edit.setText("")
                self.mj_stylize_edit.setText("")
                self.mj_quality_edit.setText("")
                self.mj_ar_edit.setText("")
                self.mj_raw_mode_checkbox.setChecked(False)
                self.mj_tile_checkbox.setChecked(False)
                self.mj_niji_checkbox.setChecked(False)
                self.mj_chaos_edit.setText("")
                self.mj_weird_edit.setText("")
                return
            
            # 更新模型信息
            model_name = ai_metadata.get('model_name', '')
            if model_name:
                self.model_name_edit.setText(model_name)
            else:
                self.model_name_edit.setText("")
            
            # 更新生成参数
            sampler = ai_metadata.get('sampler', '')
            if sampler:
                self.sampler_edit.setText(sampler)
            else:
                self.sampler_edit.setText("")
            
            steps = ai_metadata.get('steps', 0)
            if steps > 0:
                self.steps_edit.setText(str(steps))
            else:
                self.steps_edit.setText("")
            
            cfg_scale = ai_metadata.get('cfg_scale', 0.0)
            if cfg_scale > 0:
                self.cfg_edit.setText(str(cfg_scale))
            else:
                self.cfg_edit.setText("")
            
            # 更新其他参数
            seed = ai_metadata.get('seed', 0)
            if seed > 0:
                self.seed_edit.setText(str(seed))
            else:
                self.seed_edit.setText("")
            
            size = ai_metadata.get('size', '')
            if size:
                self.size_edit.setText(size)
            else:
                self.size_edit.setText("")
            
            clip_skip = ai_metadata.get('clip_skip', 0)
            if clip_skip > 0:
                self.clip_skip_edit.setText(str(clip_skip))
            else:
                self.clip_skip_edit.setText("")
            
            denoising_strength = ai_metadata.get('denoising_strength', 0.0)
            if denoising_strength > 0:
                self.denoising_edit.setText(str(denoising_strength))
            else:
                self.denoising_edit.setText("")
            
            lora_weight = ai_metadata.get('lora_weight', 0.0)
            if lora_weight > 0:
                self.lora_weight_edit.setText(str(lora_weight))
            else:
                self.lora_weight_edit.setText("")
            
            model_version = ai_metadata.get('model_version', '')
            if model_version:
                self.model_version_edit.setText(model_version)
            else:
                self.model_version_edit.setText("")
            
            generation_software = ai_metadata.get('generation_software', '')
            if generation_software:
                self.software_edit.setText(generation_software)
            else:
                self.software_edit.setText("")
            
            generation_date = ai_metadata.get('generation_date', '')
            if generation_date:
                self.date_edit.setText(generation_date)
            else:
                self.date_edit.setText("")
            
            # 更新工作流信息
            raw_metadata = ai_metadata.get('raw_metadata', {})
            if isinstance(raw_metadata, dict):
                # 工作流摘要
                workflow_summary = raw_metadata.get('workflow_summary', '')
                if workflow_summary:
                    self.workflow_summary_edit.setPlainText(workflow_summary)
                else:
                    self.workflow_summary_edit.setPlainText("")
                
                # 工作流统计信息
                workflow_info = raw_metadata.get('workflow_info', {})
                if isinstance(workflow_info, dict):
                    node_count = workflow_info.get('node_count', 0)
                    if node_count > 0:
                        self.node_count_edit.setText(str(node_count))
                    else:
                        self.node_count_edit.setText("")
                    
                    connection_count = workflow_info.get('connection_count', 0)
                    if connection_count > 0:
                        self.connection_count_edit.setText(str(connection_count))
                    else:
                        self.connection_count_edit.setText("")
                    
                    workflow_version = workflow_info.get('workflow_version', '')
                    if workflow_version:
                        self.workflow_version_edit.setText(workflow_version)
                    else:
                        self.workflow_version_edit.setText("")
                else:
                    self.node_count_edit.setText("")
                    self.connection_count_edit.setText("")
                    self.workflow_version_edit.setText("")
            else:
                self.workflow_summary_edit.setPlainText("")
                self.node_count_edit.setText("")
                self.connection_count_edit.setText("")
                self.workflow_version_edit.setText("")
            
            # 更新提示词
            positive_prompt = ai_metadata.get('positive_prompt', '')
            if positive_prompt:
                self.positive_prompt_edit.setPlainText(positive_prompt)
            else:
                self.positive_prompt_edit.setPlainText("")
            
            negative_prompt = ai_metadata.get('negative_prompt', '')
            if negative_prompt:
                self.negative_prompt_edit.setPlainText(negative_prompt)
            else:
                self.negative_prompt_edit.setPlainText("")
            
            # 更新Midjourney特有参数
            mj_job_id = ai_metadata.get('mj_job_id', '')
            if mj_job_id:
                self.mj_job_id_edit.setText(mj_job_id)
            else:
                self.mj_job_id_edit.setText("")
            
            mj_version = ai_metadata.get('mj_version', '')
            if mj_version:
                self.mj_version_edit.setText(mj_version)
            else:
                self.mj_version_edit.setText("")
            
            mj_stylize = ai_metadata.get('mj_stylize', 0)
            if mj_stylize > 0:
                self.mj_stylize_edit.setText(str(mj_stylize))
            else:
                self.mj_stylize_edit.setText("")
            
            mj_quality = ai_metadata.get('mj_quality', 0)
            if mj_quality > 0:
                self.mj_quality_edit.setText(str(mj_quality))
            else:
                self.mj_quality_edit.setText("")
            
            mj_aspect_ratio = ai_metadata.get('mj_aspect_ratio', '')
            if mj_aspect_ratio:
                self.mj_ar_edit.setText(mj_aspect_ratio)
            else:
                self.mj_ar_edit.setText("")
            
            mj_raw_mode = ai_metadata.get('mj_raw_mode', False)
            self.mj_raw_mode_checkbox.setChecked(mj_raw_mode)
            
            mj_tile = ai_metadata.get('mj_tile', False)
            self.mj_tile_checkbox.setChecked(mj_tile)
            
            mj_niji = ai_metadata.get('mj_niji', False)
            self.mj_niji_checkbox.setChecked(mj_niji)
            
            mj_chaos = ai_metadata.get('mj_chaos', 0)
            if mj_chaos > 0:
                self.mj_chaos_edit.setText(str(mj_chaos))
            else:
                self.mj_chaos_edit.setText("")
            
            mj_weird = ai_metadata.get('mj_weird', 0)
            if mj_weird > 0:
                self.mj_weird_edit.setText(str(mj_weird))
            else:
                self.mj_weird_edit.setText("")
            
            self.logger.info("AI info display updated", 
                           is_ai_generated=is_ai_generated,
                           software=generation_software,
                           model=model_name)
            
        except Exception as e:
            self.logger.error("Failed to update AI info display", error=str(e))
    
    def _is_chinese_text(self, text: str) -> bool:
        """检查文本是否为中文"""
        if not text:
            return False
        
        # 检查是否包含中文字符
        import re
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        return bool(chinese_pattern.search(text))
    
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
            print("翻译按钮被点击了！")  # 调试信息
            
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
            self.logger.error("Failed to translate now", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
    def _translate_current_photo_tags(self):
        """翻译当前选中图片的标签"""
        try:
            print("开始翻译当前照片标签")  # 调试信息
            
            if not self.current_photo:
                print("没有选中照片")  # 调试信息
                from PyQt6.QtWidgets import QMessageBox
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
            simple_english_text = self.simple_tags_english.toPlainText().strip()
            simple_chinese_text = self.simple_tags_chinese.toPlainText().strip()
            normal_english_text = self.normal_tags_english.toPlainText().strip()
            normal_chinese_text = self.normal_tags_chinese.toPlainText().strip()
            detailed_english_text = self.detailed_tags_english.toPlainText().strip()
            detailed_chinese_text = self.detailed_tags_chinese.toPlainText().strip()
            
            # 根据Google翻译设置确定翻译方向
            translation_direction = f"{source_lang} → {target_lang}"
            print(f"开始{translation_direction}翻译")
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                # 分别检查各标签栏的英文内容
                simple_english_tags = [tag.strip() for tag in simple_english_text.split(',') if tag.strip()] if simple_english_text else []
                normal_english_tags = [tag.strip() for tag in normal_english_text.split(',') if tag.strip()] if normal_english_text else []
                detailed_english_tags = [tag.strip() for tag in detailed_english_text.split(',') if tag.strip()] if detailed_english_text else []
                
                print(f"简单标签英文: {simple_english_tags}")
                print(f"普通标签英文: {normal_english_tags}")
                print(f"详细标签英文: {detailed_english_tags}")
                
                # 分别翻译各标签栏的内容
                if simple_english_tags:
                    simple_translations = plugin.translate_tags(simple_english_tags)
                    simple_chinese_results = [simple_translations.get(tag, tag) for tag in simple_english_tags]
                    self.simple_tags_chinese.setPlainText(', '.join(simple_chinese_results))
                    print(f"简单标签翻译结果: {simple_chinese_results}")
                
                if normal_english_tags:
                    normal_translations = plugin.translate_tags(normal_english_tags)
                    normal_chinese_results = [normal_translations.get(tag, tag) for tag in normal_english_tags]
                    self.normal_tags_chinese.setPlainText(', '.join(normal_chinese_results))
                    print(f"普通标签翻译结果: {normal_chinese_results}")
                
                if detailed_english_tags:
                    detailed_translations = plugin.translate_tags(detailed_english_tags)
                    detailed_chinese_results = [detailed_translations.get(tag, tag) for tag in detailed_english_tags]
                    self.detailed_tags_chinese.setPlainText(', '.join(detailed_chinese_results))
                    print(f"详细标签翻译结果: {detailed_chinese_results}")
                    
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
                    self.simple_tags_english.setPlainText(', '.join(simple_english_results))
                    print(f"简单标签翻译结果: {simple_english_results}")
                
                if normal_chinese_tags:
                    normal_translations = plugin.translate_tags(normal_chinese_tags)
                    normal_english_results = [normal_translations.get(tag, tag) for tag in normal_chinese_tags]
                    self.normal_tags_english.setPlainText(', '.join(normal_english_results))
                    print(f"普通标签翻译结果: {normal_english_results}")
                
                if detailed_chinese_tags:
                    detailed_translations = plugin.translate_tags(detailed_chinese_tags)
                    detailed_english_results = [detailed_translations.get(tag, tag) for tag in detailed_chinese_tags]
                    self.detailed_tags_english.setPlainText(', '.join(detailed_english_results))
                    print(f"详细标签翻译结果: {detailed_english_results}")
                    
            else:
                # 其他语言组合，暂时不支持
                print(f"不支持的翻译方向: {source_lang} → {target_lang}")  # 调试信息
                return
            
            # 显示成功消息
            print(f"翻译完成！翻译方向: {translation_direction}")  # 调试信息
            
            # 关闭翻译插件
            plugin.shutdown()
            
        except Exception as e:
            self.logger.error("Failed to translate current photo tags", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
    def refresh_current_photo_display(self):
        """刷新当前照片的显示"""
        try:
            if hasattr(self, 'current_photo') and self.current_photo:
                # 重新从数据库获取最新的照片数据
                photo_id = self.current_photo.get('id')
                if photo_id:
                    updated_photo = self.db_manager.get_photo(photo_id)
                    if updated_photo:
                        self.update_photo_tags_display(updated_photo)
                        self.logger.info(f"刷新了照片 {photo_id} 的显示")
        except Exception as e:
            self.logger.error(f"刷新当前照片显示失败: {e}")

    def _translate_album_tags(self):
        """翻译当前相册内所有图片的标签（挨个检查，挨个翻译）"""
        try:
            # 获取当前相册ID
            current_album_id = self._get_current_album_id()
            if not current_album_id:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "请先选择一个相册，或者确保当前有选中的照片")
                return
            
            # 获取相册内所有图片
            album_photos = self.db_manager.get_album_photos(current_album_id)
            if not album_photos:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", f"相册ID {current_album_id} 中没有图片")
                return
            
            # 创建翻译插件实例
            plugin = self._get_translation_plugin()
            if not plugin:
                return
            
            # 显示进度对话框
            from PyQt6.QtWidgets import QProgressDialog, QApplication
            from PyQt6.QtCore import Qt
            progress = QProgressDialog("正在翻译相册标签...", "取消", 0, len(album_photos), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setMinimumDuration(0)  # 立即显示
            
            translated_count = 0
            failed_count = 0
            total_photos = len(album_photos)
            
            self.logger.info(f"开始翻译相册 {current_album_id}，共 {total_photos} 张图片")
            
            # 挨个检查，挨个翻译每张图片
            for i, photo in enumerate(album_photos):
                if progress.wasCanceled():
                    self.logger.info("用户取消了翻译操作")
                    break
                
                photo_id = photo.get('id')
                progress.setValue(i)
                progress.setLabelText(f"正在翻译第 {i+1}/{total_photos} 张图片 (ID: {photo_id})...")
                QApplication.processEvents()
                
                try:
                    self.logger.info(f"开始翻译图片 {i+1}/{total_photos} (ID: {photo_id})")
                    
                    # 挨个翻译每张图片的标签
                    success = self._translate_single_photo_tags(photo, plugin)
                    if success:
                        translated_count += 1
                        self.logger.info(f"图片 {photo_id} 翻译成功")
                    else:
                        failed_count += 1
                        self.logger.warning(f"图片 {photo_id} 翻译失败或无需要翻译的标签")
                    
                    # 强制更新进度显示
                    QApplication.processEvents()
                    
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"翻译图片 {photo_id} 时发生异常", error=str(e))
                    continue
            
            # 确保进度对话框正确关闭
            progress.setValue(total_photos)
            progress.close()
            
            # 确保插件正确关闭
            try:
                plugin.shutdown()
            except Exception as e:
                self.logger.warning(f"插件关闭时发生异常: {e}")
            
            # 显示详细结果
            result_message = (f"相册翻译完成！\n\n"
                            f"总共处理了 {total_photos} 张图片\n"
                            f"成功翻译了 {translated_count} 张图片\n"
                            f"翻译失败 {failed_count} 张图片\n"
                            f"成功率: {translated_count/total_photos*100:.1f}%")
            
            print(f"批量翻译完成: {result_message}")
            
            # 刷新当前照片的显示，以显示翻译结果
            self.refresh_current_photo_display()
            
        except Exception as e:
            self.logger.error("Failed to translate album tags", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"相册翻译失败：{str(e)}")
    
    def _translate_single_photo_tags(self, photo: dict, plugin) -> bool:
        """挨个翻译单张图片的标签"""
        try:
            photo_id = photo.get('id')
            if not photo_id:
                self.logger.warning(f"图片ID为空，跳过翻译")
                return False
            
            # 获取图片的标签数据
            simple_tags = photo.get('simple_tags', '[]')
            normal_tags = photo.get('normal_tags', '[]')
            detailed_tags = photo.get('detailed_tags', '[]')
            tag_translations = photo.get('tag_translations', '{}')
            
            # 解析JSON数据
            import json
            try:
                # 处理可能已经是列表/字典的情况
                if isinstance(simple_tags, str):
                    simple_tags_list = json.loads(simple_tags) if simple_tags else []
                else:
                    simple_tags_list = simple_tags or []
                    
                if isinstance(normal_tags, str):
                    normal_tags_list = json.loads(normal_tags) if normal_tags else []
                else:
                    normal_tags_list = normal_tags or []
                    
                if isinstance(detailed_tags, str):
                    detailed_tags_list = json.loads(detailed_tags) if detailed_tags else []
                else:
                    detailed_tags_list = detailed_tags or []
                    
                if isinstance(tag_translations, str):
                    translations_dict = json.loads(tag_translations) if tag_translations else {}
                else:
                    translations_dict = tag_translations or {}
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"解析图片 {photo_id} 标签JSON失败", error=str(e))
                return False
            
            # 分离中英文标签
            def separate_tags_by_language(tags_list):
                chinese_tags = []
                english_tags = []
                for tag in tags_list:
                    if self._is_chinese_text(tag):
                        chinese_tags.append(tag)
                    else:
                        english_tags.append(tag)
                return english_tags, chinese_tags
            
            # 分离各类型标签的中英文
            simple_english, simple_chinese = separate_tags_by_language(simple_tags_list)
            normal_english, normal_chinese = separate_tags_by_language(normal_tags_list)
            detailed_english, detailed_chinese = separate_tags_by_language(detailed_tags_list)
            
            # 根据插件设置决定翻译方向
            source_lang = getattr(plugin, 'source_language', 'en')
            target_lang = getattr(plugin, 'target_language', 'zh-CN')
            
            print(f"图片 {photo_id} 翻译设置: {source_lang} → {target_lang}")  # 调试信息
            
            # 分别处理各标签类型的翻译
            successful_translations = {}
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                translation_direction = "英文→中文"
                
                # 分别翻译各标签类型
                if simple_english:
                    simple_translations = plugin.translate_tags(simple_english)
                    for original_tag, translated_tag in simple_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if normal_english:
                    normal_translations = plugin.translate_tags(normal_english)
                    for original_tag, translated_tag in normal_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if detailed_english:
                    detailed_translations = plugin.translate_tags(detailed_english)
                    for original_tag, translated_tag in detailed_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                            
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译
                translation_direction = "中文→英文"
                
                # 分别翻译各标签类型
                if simple_chinese:
                    simple_translations = plugin.translate_tags(simple_chinese)
                    for original_tag, translated_tag in simple_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if normal_chinese:
                    normal_translations = plugin.translate_tags(normal_chinese)
                    for original_tag, translated_tag in normal_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if detailed_chinese:
                    detailed_translations = plugin.translate_tags(detailed_chinese)
                    for original_tag, translated_tag in detailed_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                            
            else:
                # 其他语言组合，暂时不支持
                self.logger.warning(f"不支持的翻译方向: {source_lang} → {target_lang}")
                return False
            
            # 检查是否有需要翻译的内容
            if not successful_translations:
                self.logger.info(f"图片 {photo_id} 没有需要翻译的标签 ({translation_direction})")
                return True
            
            self.logger.info(f"图片 {photo_id} {translation_direction}翻译完成: {len(successful_translations)} 个")
            
            # 根据翻译方向，将翻译结果添加到正确的语言区域
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译：将翻译结果添加到中文区域
                print(f"开始分配翻译结果到对应标签区域...")
                print(f"简单标签英文: {simple_english}")
                print(f"普通标签英文: {normal_english}")
                print(f"详细标签英文: {detailed_english}")
                
                # 分别处理每种标签类型的翻译结果
                # 简单标签翻译结果
                simple_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in simple_english:
                        simple_translations[original_tag] = translated_tag
                
                # 普通标签翻译结果
                normal_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in normal_english:
                        normal_translations[original_tag] = translated_tag
                
                # 详细标签翻译结果
                detailed_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in detailed_english:
                        detailed_translations[original_tag] = translated_tag
                
                # 将翻译结果添加到对应的中文区域
                for original_tag, translated_tag in simple_translations.items():
                    if translated_tag not in simple_chinese:
                        simple_chinese.append(translated_tag)
                        print(f"将简单标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到简单标签中文区域")
                
                for original_tag, translated_tag in normal_translations.items():
                    if translated_tag not in normal_chinese:
                        normal_chinese.append(translated_tag)
                        print(f"将普通标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到普通标签中文区域")
                
                for original_tag, translated_tag in detailed_translations.items():
                    if translated_tag not in detailed_chinese:
                        detailed_chinese.append(translated_tag)
                        print(f"将详细标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到详细标签中文区域")
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译：将翻译结果添加到英文区域
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in simple_chinese:
                        if translated_tag not in simple_english:
                            simple_english.append(translated_tag)
                    elif original_tag in normal_chinese:
                        if translated_tag not in normal_english:
                            normal_english.append(translated_tag)
                    elif original_tag in detailed_chinese:
                        if translated_tag not in detailed_english:
                            detailed_english.append(translated_tag)
            
            # 重新组合标签列表
            updated_simple_tags = simple_english + simple_chinese
            updated_normal_tags = normal_english + normal_chinese
            updated_detailed_tags = detailed_english + detailed_chinese
            
            # 添加调试日志
            self.logger.info(f"图片 {photo_id} 翻译后标签分类 - 简单: 英文{len(simple_english)}个, 中文{len(simple_chinese)}个")
            self.logger.info(f"图片 {photo_id} 翻译后标签分类 - 普通: 英文{len(normal_english)}个, 中文{len(normal_chinese)}个")
            self.logger.info(f"图片 {photo_id} 翻译后标签分类 - 详细: 英文{len(detailed_english)}个, 中文{len(detailed_chinese)}个")
            
            # 保存到数据库
            updates = {
                'simple_tags': json.dumps(updated_simple_tags, ensure_ascii=False),
                'normal_tags': json.dumps(updated_normal_tags, ensure_ascii=False),
                'detailed_tags': json.dumps(updated_detailed_tags, ensure_ascii=False),
                'tag_translations': json.dumps(translations_dict, ensure_ascii=False)
            }
            
            success = self.db_manager.update_photo(photo_id, updates)
            if success:
                print(f"图片 {photo_id} 翻译完成: 成功翻译了 {len(successful_translations)} 个标签！翻译方向: {translation_direction}")
                return True
            else:
                self.logger.warning(f"图片 {photo_id} 保存翻译结果到数据库失败")
                return False
            
        except Exception as e:
            self.logger.error(f"翻译图片 {photo_id} 时发生异常", error=str(e))
            return False

    def _translate_photo_tags_in_database(self, photo: dict, plugin) -> bool:
        """翻译数据库中单张图片的标签（逐张处理）"""
        try:
            photo_id = photo.get('id')
            if not photo_id:
                self.logger.warning(f"图片ID为空，跳过翻译")
                return False
            
            # 获取图片的标签数据
            simple_tags = photo.get('simple_tags', '[]')
            normal_tags = photo.get('normal_tags', '[]')
            detailed_tags = photo.get('detailed_tags', '[]')
            tag_translations = photo.get('tag_translations', '{}')
            
            # 解析JSON数据
            import json
            try:
                # 处理可能已经是列表/字典的情况
                if isinstance(simple_tags, str):
                    simple_tags_list = json.loads(simple_tags) if simple_tags else []
                else:
                    simple_tags_list = simple_tags or []
                    
                if isinstance(normal_tags, str):
                    normal_tags_list = json.loads(normal_tags) if normal_tags else []
                else:
                    normal_tags_list = normal_tags or []
                    
                if isinstance(detailed_tags, str):
                    detailed_tags_list = json.loads(detailed_tags) if detailed_tags else []
                else:
                    detailed_tags_list = detailed_tags or []
                    
                if isinstance(tag_translations, str):
                    translations_dict = json.loads(tag_translations) if tag_translations else {}
                else:
                    translations_dict = tag_translations or {}
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"解析图片 {photo_id} 标签JSON失败", error=str(e))
                return False
            
            # 分离中英文标签
            def separate_tags_by_language(tags_list):
                chinese_tags = []
                english_tags = []
                for tag in tags_list:
                    if self._is_chinese_text(tag):
                        chinese_tags.append(tag)
                    else:
                        english_tags.append(tag)
                return english_tags, chinese_tags
            
            # 分离各类型标签的中英文
            simple_english, simple_chinese = separate_tags_by_language(simple_tags_list)
            normal_english, normal_chinese = separate_tags_by_language(normal_tags_list)
            detailed_english, detailed_chinese = separate_tags_by_language(detailed_tags_list)
            
            # 根据插件设置决定翻译方向
            source_lang = getattr(plugin, 'source_language', 'en')
            target_lang = getattr(plugin, 'target_language', 'zh-CN')
            
            print(f"批量翻译插件设置: {source_lang} → {target_lang}")  # 调试信息
            
            # 分别处理各标签类型的翻译
            successful_translations = {}
            
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译
                translation_direction = "英文→中文"
                
                # 分别翻译各标签类型
                if simple_english:
                    simple_translations = plugin.translate_tags(simple_english)
                    for original_tag, translated_tag in simple_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if normal_english:
                    normal_translations = plugin.translate_tags(normal_english)
                    for original_tag, translated_tag in normal_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if detailed_english:
                    detailed_translations = plugin.translate_tags(detailed_english)
                    for original_tag, translated_tag in detailed_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                            
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译
                translation_direction = "中文→英文"
                
                # 分别翻译各标签类型
                if simple_chinese:
                    simple_translations = plugin.translate_tags(simple_chinese)
                    for original_tag, translated_tag in simple_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if normal_chinese:
                    normal_translations = plugin.translate_tags(normal_chinese)
                    for original_tag, translated_tag in normal_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                
                if detailed_chinese:
                    detailed_translations = plugin.translate_tags(detailed_chinese)
                    for original_tag, translated_tag in detailed_translations.items():
                        if original_tag != translated_tag:
                            successful_translations[original_tag] = translated_tag
                            translations_dict[original_tag] = translated_tag
                            
            else:
                # 其他语言组合，暂时不支持
                self.logger.warning(f"不支持的翻译方向: {source_lang} → {target_lang}")
                return False
            
            # 检查是否有需要翻译的内容
            if not successful_translations:
                self.logger.info(f"图片 {photo_id} 没有需要翻译的标签 ({translation_direction})")
                return True
            
            self.logger.info(f"图片 {photo_id} {translation_direction}翻译完成: {len(successful_translations)} 个")
            
            # 根据翻译方向，将翻译结果添加到正确的语言区域
            if source_lang == 'en' and target_lang == 'zh-CN':
                # 英文→中文翻译：将翻译结果添加到中文区域
                print(f"开始分配翻译结果到对应标签区域...")
                print(f"简单标签英文: {simple_english}")
                print(f"普通标签英文: {normal_english}")
                print(f"详细标签英文: {detailed_english}")
                
                # 分别处理每种标签类型的翻译结果
                # 简单标签翻译结果
                simple_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in simple_english:
                        simple_translations[original_tag] = translated_tag
                
                # 普通标签翻译结果
                normal_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in normal_english:
                        normal_translations[original_tag] = translated_tag
                
                # 详细标签翻译结果
                detailed_translations = {}
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in detailed_english:
                        detailed_translations[original_tag] = translated_tag
                
                # 将翻译结果添加到对应的中文区域
                for original_tag, translated_tag in simple_translations.items():
                    if translated_tag not in simple_chinese:
                        simple_chinese.append(translated_tag)
                        print(f"将简单标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到简单标签中文区域")
                
                for original_tag, translated_tag in normal_translations.items():
                    if translated_tag not in normal_chinese:
                        normal_chinese.append(translated_tag)
                        print(f"将普通标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到普通标签中文区域")
                
                for original_tag, translated_tag in detailed_translations.items():
                    if translated_tag not in detailed_chinese:
                        detailed_chinese.append(translated_tag)
                        print(f"将详细标签 '{original_tag}' 的翻译 '{translated_tag}' 添加到详细标签中文区域")
            elif source_lang == 'zh-CN' and target_lang == 'en':
                # 中文→英文翻译：将翻译结果添加到英文区域
                for original_tag, translated_tag in successful_translations.items():
                    if original_tag in simple_chinese:
                        if translated_tag not in simple_english:
                            simple_english.append(translated_tag)
                    elif original_tag in normal_chinese:
                        if translated_tag not in normal_english:
                            normal_english.append(translated_tag)
                    elif original_tag in detailed_chinese:
                        if translated_tag not in detailed_english:
                            detailed_english.append(translated_tag)
            
            # 重新组合标签列表
            updated_simple_tags = simple_english + simple_chinese
            updated_normal_tags = normal_english + normal_chinese
            updated_detailed_tags = detailed_english + detailed_chinese
            
            # 添加调试日志
            self.logger.info(f"翻译后标签分类 - 简单: 英文{len(simple_english)}个, 中文{len(simple_chinese)}个")
            self.logger.info(f"翻译后标签分类 - 普通: 英文{len(normal_english)}个, 中文{len(normal_chinese)}个")
            self.logger.info(f"翻译后标签分类 - 详细: 英文{len(detailed_english)}个, 中文{len(detailed_chinese)}个")
            
            # 保存到数据库
            updates = {
                'simple_tags': json.dumps(updated_simple_tags, ensure_ascii=False),
                'normal_tags': json.dumps(updated_normal_tags, ensure_ascii=False),
                'detailed_tags': json.dumps(updated_detailed_tags, ensure_ascii=False),
                'tag_translations': json.dumps(translations_dict, ensure_ascii=False)
            }
            
            success = self.db_manager.update_photo(photo_id, updates)
            if success:
                # 直接更新界面显示，绕过编辑保护
                self.is_editing = False  # 临时关闭编辑保护
                
                # 直接更新界面显示翻译结果
                if source_lang == 'en' and target_lang == 'zh-CN':
                    # 英文→中文翻译：更新中文标签栏
                    simple_chinese_text = ', '.join(simple_chinese)
                    normal_chinese_text = ', '.join(normal_chinese)
                    detailed_chinese_text = ', '.join(detailed_chinese)
                    
                    self.simple_tags_chinese.setPlainText(simple_chinese_text)
                    self.normal_tags_chinese.setPlainText(normal_chinese_text)
                    self.detailed_tags_chinese.setPlainText(detailed_chinese_text)
                    
                elif source_lang == 'zh-CN' and target_lang == 'en':
                    # 中文→英文翻译：更新英文标签栏
                    simple_english_text = ', '.join(simple_english)
                    normal_english_text = ', '.join(normal_english)
                    detailed_english_text = ', '.join(detailed_english)
                    
                    self.simple_tags_english.setPlainText(simple_english_text)
                    self.normal_tags_english.setPlainText(normal_english_text)
                    self.detailed_tags_english.setPlainText(detailed_english_text)
                
                self.is_editing = True   # 重新开启编辑保护
                
                # 显示成功消息
                from PyQt6.QtWidgets import QMessageBox
                print(f"翻译完成: 成功翻译了 {len(successful_translations)} 个标签！翻译方向: {translation_direction}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", "保存翻译结果到数据库失败")
            
            # 关闭翻译插件
            plugin.shutdown()
            
        except Exception as e:
            self.logger.error("Failed to translate current photo tags", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"翻译失败：{str(e)}")
    
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
            self.logger.error("Failed to get translation plugin", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
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
    
    def _get_current_album_id(self) -> Optional[int]:
        """获取当前相册ID"""
        try:
            # 尝试从主窗口获取当前相册ID
            if hasattr(self, 'parent') and self.parent():
                main_window = self.parent()
                if hasattr(main_window, 'current_album_id') and main_window.current_album_id:
                    return main_window.current_album_id
                elif hasattr(main_window, 'get_current_album_id'):
                    return main_window.get_current_album_id()
            
            # 尝试从相册管理器获取
            if hasattr(self, 'album_manager') and self.album_manager:
                if hasattr(self.album_manager, 'current_album_id') and self.album_manager.current_album_id:
                    return self.album_manager.current_album_id
                elif hasattr(self.album_manager, 'get_current_album_id'):
                    return self.album_manager.get_current_album_id()
            
            # 尝试从当前照片获取相册信息
            if hasattr(self, 'current_photo') and self.current_photo:
                # 如果当前有选中的照片，尝试获取其所属相册
                photo_id = self.current_photo.get('id')
                if photo_id:
                    # 查询照片所属的相册
                    with self.db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT album_id FROM album_photos 
                            WHERE photo_id = ? 
                            LIMIT 1
                        """, (photo_id,))
                        result = cursor.fetchone()
                        if result:
                            return result[0]
            
            # 如果无法获取，返回None而不是默认值
            self.logger.warning("无法获取当前相册ID")
            return None
            
        except Exception as e:
            self.logger.error("Failed to get current album ID", error=str(e))
            return None
    
    def save_tags_to_database(self):
        """保存标签到数据库"""
        try:
            if not self.current_photo:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "请先选择一张照片")
                return
            
            # 设置编辑状态，防止显示更新覆盖用户输入
            self.is_editing = True
            
            # 获取当前标签内容
            simple_english = self.simple_tags_english.toPlainText().strip()
            simple_chinese = self.simple_tags_chinese.toPlainText().strip()
            normal_english = self.normal_tags_english.toPlainText().strip()
            normal_chinese = self.normal_tags_chinese.toPlainText().strip()
            detailed_english = self.detailed_tags_english.toPlainText().strip()
            detailed_chinese = self.detailed_tags_chinese.toPlainText().strip()
            tags_notes = self.tags_notes.toPlainText().strip()
            
            # 解析标签为列表
            import json
            
            # 简单标签 - 分别保存英文和中文
            simple_english_list = []
            simple_chinese_list = []
            if simple_english:
                simple_english_list = [tag.strip() for tag in simple_english.split(',') if tag.strip()]
            if simple_chinese:
                simple_chinese_list = [tag.strip() for tag in simple_chinese.split(',') if tag.strip()]
            
            # 普通标签 - 分别保存英文和中文
            normal_english_list = []
            normal_chinese_list = []
            if normal_english:
                normal_english_list = [tag.strip() for tag in normal_english.split(',') if tag.strip()]
            if normal_chinese:
                normal_chinese_list = [tag.strip() for tag in normal_chinese.split(',') if tag.strip()]
            
            # 详细标签 - 分别保存英文和中文
            detailed_english_list = []
            detailed_chinese_list = []
            if detailed_english:
                detailed_english_list = [tag.strip() for tag in detailed_english.split(',') if tag.strip()]
            if detailed_chinese:
                detailed_chinese_list = [tag.strip() for tag in detailed_chinese.split(',') if tag.strip()]
            
            # 构建翻译字典 - 从英文标签到中文标签的映射
            translations_dict = {}
            
            # 简单标签翻译映射
            for i, eng_tag in enumerate(simple_english_list):
                if i < len(simple_chinese_list):
                    translations_dict[eng_tag] = simple_chinese_list[i]
            
            # 普通标签翻译映射
            for i, eng_tag in enumerate(normal_english_list):
                if i < len(normal_chinese_list):
                    translations_dict[eng_tag] = normal_chinese_list[i]
            
            # 详细标签翻译映射
            for i, eng_tag in enumerate(detailed_english_list):
                if i < len(detailed_chinese_list):
                    translations_dict[eng_tag] = detailed_chinese_list[i]
            
            # 更新照片数据
            photo_id = self.current_photo.get('id')
            if photo_id:
                # 合并英文和中文标签到原有字段，保持翻译功能
                simple_tags_list = simple_english_list + simple_chinese_list
                normal_tags_list = normal_english_list + normal_chinese_list
                detailed_tags_list = detailed_english_list + detailed_chinese_list
                
                updates = {
                    'simple_tags': json.dumps(simple_tags_list, ensure_ascii=False),
                    'normal_tags': json.dumps(normal_tags_list, ensure_ascii=False),
                    'detailed_tags': json.dumps(detailed_tags_list, ensure_ascii=False),
                    'tag_translations': json.dumps(translations_dict, ensure_ascii=False),
                    'notes': tags_notes  # 保存标签备注
                }
                
                # 调用数据库更新方法
                success = self.db_manager.update_photo(photo_id, updates)
                
                if success:
                    self.logger.info("Tags saved to database successfully", 
                                   photo_id=photo_id,
                                   simple_tags_count=len(simple_tags_list),
                                   normal_tags_count=len(normal_tags_list),
                                   detailed_tags_count=len(detailed_tags_list),
                                   translations_count=len(translations_dict),
                                   has_notes=bool(tags_notes))
                    
                    # 显示成功消息
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "成功", "标签和备注已成功保存到数据库")
                    
                    # 更新内存中的照片数据
                    self.current_photo.update(updates)
                    
                    # 不要重新加载显示，保持用户当前的编辑状态
                    # 这样可以避免翻译逻辑覆盖用户刚输入的内容
                    
                else:
                    self.logger.error("Failed to save tags to database", photo_id=photo_id)
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "警告", "保存标签到数据库失败")
            
            # 保存完成后，重置编辑状态
            self.is_editing = False
            
        except Exception as e:
            self.logger.error("Failed to save tags to database", error=str(e))
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"保存标签失败：{str(e)}")
        finally:
            # 确保编辑状态被重置
            self.is_editing = False
    
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