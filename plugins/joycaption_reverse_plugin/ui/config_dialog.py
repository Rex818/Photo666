"""
JoyCaption插件配置对话框
"""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QGroupBox, QScrollArea, QWidget, QTextEdit,
    QLineEdit, QProgressBar, QMessageBox, QFileDialog,
    QRadioButton, QButtonGroup, QListWidget, QListWidgetItem,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
import os
from pathlib import Path


class ModelDownloadThread(QThread):
    """模型下载线程"""
    progress_updated = pyqtSignal(str, int, str)  # stage, progress, message
    download_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, model_manager, model_id):
        super().__init__()
        self.model_manager = model_manager
        self.model_id = model_id
    
    def run(self):
        try:
            success = self.model_manager.download_model(
                self.model_id, 
                self.progress_updated.emit
            )
            if success:
                self.download_finished.emit(True, "模型下载完成")
            else:
                self.download_finished.emit(False, "模型下载失败")
        except Exception as e:
            self.download_finished.emit(False, f"下载异常: {str(e)}")


class JoyCaptionConfigDialog(QDialog):
    """JoyCaption配置对话框"""
    
    def __init__(self, config_manager, model_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.model_manager = model_manager
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.ui.config_dialog")
        
        # 配置数据
        self.config = {}
        self.download_thread = None
        
        # 图片选择相关
        self.selected_images = []  # 选中的图片路径
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("JoyCaption图片反推信息插件配置")
        self.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 基本配置标签页
        basic_tab = self.create_basic_tab()
        tab_widget.addTab(basic_tab, "基本配置")
        
        # 模型配置标签页
        model_tab = self.create_model_tab()
        tab_widget.addTab(model_tab, "模型配置")
        
        # 高级配置标签页
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "高级配置")
        
        # 额外选项标签页
        options_tab = self.create_options_tab()
        tab_widget.addTab(options_tab, "额外选项")
        
        # 图片选择标签页
        image_tab = self.create_image_selection_tab()
        tab_widget.addTab(image_tab, "图片选择")
        
        main_layout.addWidget(tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_config)
        
        self.save_default_button = QPushButton("保存为默认配置")
        self.save_default_button.clicked.connect(self.save_as_default_config)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_default_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def create_basic_tab(self) -> QWidget:
        """创建基本配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 描述级别配置
        level_group = QGroupBox("描述级别")
        level_layout = QGridLayout()
        
        self.level_combo = QComboBox()
        description_levels = self.config_manager.get_description_levels()
        for level_id, level_info in description_levels.items():
            self.level_combo.addItem(level_info["name"], level_id)
        
        level_layout.addWidget(QLabel("描述级别:"), 0, 0)
        level_layout.addWidget(self.level_combo, 0, 1)
        
        # 描述级别说明
        self.level_description = QLabel()
        self.level_combo.currentIndexChanged.connect(self.update_level_description)
        level_layout.addWidget(self.level_description, 1, 0, 1, 2)
        
        level_group.setLayout(level_layout)
        layout.addWidget(level_group)
        
        # 描述类型配置
        type_group = QGroupBox("描述类型")
        type_layout = QGridLayout()
        
        self.type_combo = QComboBox()
        caption_types = self.config_manager.get_caption_types()
        for caption_type in caption_types.keys():
            self.type_combo.addItem(caption_type)
        
        type_layout.addWidget(QLabel("描述类型:"), 0, 0)
        type_layout.addWidget(self.type_combo, 0, 1)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 描述长度配置
        length_group = QGroupBox("描述长度")
        length_layout = QGridLayout()
        
        self.length_combo = QComboBox()
        length_choices = self.config_manager.get_caption_length_choices()
        for length_choice in length_choices:
            self.length_combo.addItem(length_choice)
        
        length_layout.addWidget(QLabel("描述长度:"), 0, 0)
        length_layout.addWidget(self.length_combo, 0, 1)
        
        length_group.setLayout(length_layout)
        layout.addWidget(length_group)
        
        # 角色名称配置
        name_group = QGroupBox("角色名称")
        name_layout = QGridLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入角色名称（可选）")
        
        name_layout.addWidget(QLabel("角色名称:"), 0, 0)
        name_layout.addWidget(self.name_input, 0, 1)
        
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_model_tab(self) -> QWidget:
        """创建模型配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 模型选择
        model_group = QGroupBox("模型选择")
        model_layout = QGridLayout()
        
        self.model_combo = QComboBox()
        available_models = self.config_manager.get_available_models()
        for model_id, model_info in available_models.items():
            display_name = model_info.get("name", model_id)
            self.model_combo.addItem(display_name, model_id)
        
        self.model_combo.currentIndexChanged.connect(self.update_model_info)
        model_layout.addWidget(QLabel("选择模型:"), 0, 0)
        model_layout.addWidget(self.model_combo, 0, 1)
        
        # 模型信息显示
        self.model_info_label = QLabel()
        self.model_info_label.setWordWrap(True)
        model_layout.addWidget(self.model_info_label, 1, 0, 1, 2)
        
        # 模型状态
        self.model_status_label = QLabel()
        model_layout.addWidget(self.model_status_label, 2, 0, 1, 2)
        
        # 本地模型信息
        self.local_model_label = QLabel()
        self.local_model_label.setWordWrap(True)
        model_layout.addWidget(self.local_model_label, 3, 0, 1, 2)
        
        # 下载按钮
        self.download_button = QPushButton("下载模型")
        self.download_button.clicked.connect(self.download_model)
        model_layout.addWidget(self.download_button, 4, 0, 1, 2)
        
        # 下载进度
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        model_layout.addWidget(self.download_progress, 5, 0, 1, 2)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 模型文件结构信息
        file_structure_group = QGroupBox("模型文件结构")
        file_layout = QVBoxLayout()
        
        self.file_structure_text = QTextEdit()
        self.file_structure_text.setMaximumHeight(150)
        self.file_structure_text.setReadOnly(True)
        file_layout.addWidget(self.file_structure_text)
        
        file_structure_group.setLayout(file_layout)
        layout.addWidget(file_structure_group)
        
        # 本地模型目录管理
        local_paths_group = QGroupBox("本地模型目录管理")
        local_paths_layout = QVBoxLayout()
        
        # 当前搜索路径显示
        self.local_paths_label = QLabel("当前搜索路径:")
        self.local_paths_label.setWordWrap(True)
        local_paths_layout.addWidget(self.local_paths_label)
        
        # 添加自定义路径
        add_path_layout = QHBoxLayout()
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("输入本地模型目录路径")
        add_path_layout.addWidget(self.custom_path_edit)
        
        self.add_path_button = QPushButton("添加路径")
        self.add_path_button.clicked.connect(self.add_custom_path)
        add_path_layout.addWidget(self.add_path_button)
        
        self.browse_path_button = QPushButton("浏览")
        self.browse_path_button.clicked.connect(self.browse_custom_path)
        add_path_layout.addWidget(self.browse_path_button)
        
        local_paths_layout.addLayout(add_path_layout)
        
        # 自定义路径列表
        self.custom_paths_list = QListWidget()
        self.custom_paths_list.setMaximumHeight(100)
        local_paths_layout.addWidget(QLabel("自定义路径列表:"))
        local_paths_layout.addWidget(self.custom_paths_list)
        
        # 删除路径按钮
        self.remove_path_button = QPushButton("删除选中路径")
        self.remove_path_button.clicked.connect(self.remove_custom_path)
        local_paths_layout.addWidget(self.remove_path_button)
        
        local_paths_group.setLayout(local_paths_layout)
        layout.addWidget(local_paths_group)
        
        # 精度配置
        precision_group = QGroupBox("精度配置")
        precision_layout = QGridLayout()
        
        self.precision_combo = QComboBox()
        memory_configs = self.config_manager.get_memory_configs()
        for precision_name, precision_config in memory_configs.items():
            description = precision_config.get("description", precision_name)
            self.precision_combo.addItem(f"{precision_name} - {description}")
        
        precision_layout.addWidget(QLabel("精度模式:"), 0, 0)
        precision_layout.addWidget(self.precision_combo, 0, 1)
        
        precision_group.setLayout(precision_layout)
        layout.addWidget(precision_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """创建高级配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 推理参数配置
        params_group = QGroupBox("推理参数")
        params_layout = QGridLayout()
        
        # 最大token数
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2048)
        self.max_tokens_spin.setValue(512)
        params_layout.addWidget(QLabel("最大Token数:"), 0, 0)
        params_layout.addWidget(self.max_tokens_spin, 0, 1)
        
        # 温度
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.6)
        params_layout.addWidget(QLabel("温度:"), 1, 0)
        params_layout.addWidget(self.temperature_spin, 1, 1)
        
        # Top-p
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.01)
        self.top_p_spin.setValue(0.9)
        params_layout.addWidget(QLabel("Top-p:"), 2, 0)
        params_layout.addWidget(self.top_p_spin, 2, 1)
        
        # Top-k
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(0, 100)
        self.top_k_spin.setValue(0)
        params_layout.addWidget(QLabel("Top-k:"), 3, 0)
        params_layout.addWidget(self.top_k_spin, 3, 1)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 输出配置
        output_group = QGroupBox("输出配置")
        output_layout = QGridLayout()
        
        self.save_to_file_check = QCheckBox("保存到文件")
        self.save_to_file_check.setChecked(True)
        output_layout.addWidget(self.save_to_file_check, 0, 0)
        
        self.save_to_db_check = QCheckBox("保存到数据库")
        self.save_to_db_check.setChecked(True)
        output_layout.addWidget(self.save_to_db_check, 0, 1)
        
        self.auto_display_check = QCheckBox("自动显示结果")
        self.auto_display_check.setChecked(True)
        output_layout.addWidget(self.auto_display_check, 1, 0)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_options_tab(self) -> QWidget:
        """创建额外选项标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # 获取额外选项
        extra_options = self.config_manager.get_extra_options()
        self.option_checkboxes = {}
        
        for option_id, option_info in extra_options.items():
            checkbox = QCheckBox(option_info["name"])
            checkbox.setToolTip(option_info["description"])
            checkbox.setChecked(option_info.get("default", False))
            self.option_checkboxes[option_id] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        widget.setLayout(layout)
        return widget
    
    def create_image_selection_tab(self) -> QWidget:
        """创建图片选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 选择模式
        mode_group = QGroupBox("选择模式")
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("选择模式:"))
        
        self.single_radio = QRadioButton("单张图片")
        self.multiple_radio = QRadioButton("多张图片")
        self.directory_radio = QRadioButton("目录")
        
        self.single_radio.setChecked(True)
        
        mode_layout.addWidget(self.single_radio)
        mode_layout.addWidget(self.multiple_radio)
        mode_layout.addWidget(self.directory_radio)
        mode_layout.addStretch()
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.select_images_btn = QPushButton("选择图片")
        self.select_images_btn.clicked.connect(self.select_images)
        self.clear_images_btn = QPushButton("清空")
        self.clear_images_btn.clicked.connect(self.clear_images)
        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self.preview_selected_image)
        
        button_layout.addWidget(self.select_images_btn)
        button_layout.addWidget(self.clear_images_btn)
        button_layout.addWidget(self.preview_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片列表
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setMaximumHeight(200)
        self.image_list.currentItemChanged.connect(self.on_image_selection_changed)
        
        left_layout.addWidget(QLabel("已选择的图片:"))
        left_layout.addWidget(self.image_list)
        
        # 右侧：预览区域
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setMaximumSize(200, 200)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        
        right_layout.addWidget(QLabel("图片预览:"))
        right_layout.addWidget(self.preview_label)
        
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([300, 200])
        
        layout.addWidget(splitter)
        
        widget.setLayout(layout)
        return widget
    
    def load_config(self):
        """加载配置"""
        try:
            # 获取当前配置
            current_config = self.config_manager.config
            inference_config = current_config.get('inference', {})
            
            # 设置描述级别
            saved_level = inference_config.get("default_level", "normal")
            level_index = self.level_combo.findData(saved_level)
            if level_index >= 0:
                self.level_combo.setCurrentIndex(level_index)
            
            # 设置描述类型
            saved_type = inference_config.get("default_caption_type", "Descriptive")
            type_index = self.type_combo.findText(saved_type)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            
            # 设置精度模式
            saved_precision = inference_config.get("precision", "Balanced (8-bit)")
            precision_index = self.precision_combo.findText(saved_precision, Qt.MatchFlag.MatchStartsWith)
            if precision_index >= 0:
                self.precision_combo.setCurrentIndex(precision_index)
            
            # 设置推理参数
            self.max_tokens_spin.setValue(inference_config.get("max_new_tokens", 512))
            self.temperature_spin.setValue(inference_config.get("temperature", 0.6))
            self.top_p_spin.setValue(inference_config.get("top_p", 0.9))
            self.top_k_spin.setValue(inference_config.get("top_k", 0))
            
            # 设置输出配置
            self.save_to_file_check.setChecked(inference_config.get("save_to_file", True))
            self.save_to_db_check.setChecked(inference_config.get("save_to_database", True))
            self.auto_display_check.setChecked(inference_config.get("auto_display", True))
            
            # 设置模型选择
            saved_model = current_config.get('models', {}).get('default_model', '')
            if saved_model:
                model_index = self.model_combo.findData(saved_model)
                if model_index >= 0:
                    self.model_combo.setCurrentIndex(model_index)
            
            # 加载额外选项状态
            self.load_extra_options()
            
            # 更新模型信息
            self.update_model_info()
            
            # 初始化本地路径显示
            self.update_local_paths_display()
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
    
    def load_extra_options(self):
        """加载额外选项状态"""
        try:
            # 获取用户保存的额外选项
            current_config = self.config_manager.config
            saved_options = current_config.get('inference', {}).get('extra_options', [])
            
            # 设置复选框状态
            for option_id, checkbox in self.option_checkboxes.items():
                if option_id in saved_options:
                    checkbox.setChecked(True)
                else:
                    # 使用默认值
                    extra_options = self.config_manager.get_extra_options()
                    default_value = extra_options.get(option_id, {}).get("default", False)
                    checkbox.setChecked(default_value)
                    
        except Exception as e:
            self.logger.error(f"加载额外选项失败: {str(e)}")
    
    def update_level_description(self):
        """更新描述级别说明"""
        try:
            current_level = self.level_combo.currentData()
            description_levels = self.config_manager.get_description_levels()
            
            if current_level in description_levels:
                description = description_levels[current_level]["description"]
                self.level_description.setText(f"说明: {description}")
            else:
                self.level_description.setText("")
                
        except Exception as e:
            self.logger.error(f"更新描述级别说明失败: {str(e)}")
    
    def update_model_info(self):
        """更新模型信息"""
        try:
            current_model_id = self.model_combo.currentData()
            if not current_model_id:
                return
            
            # 获取模型信息
            model_info = self.config_manager.get_model_config(current_model_id)
            if model_info:
                info_text = f"名称: {model_info.get('name', current_model_id)}\n"
                info_text += f"描述: {model_info.get('description', '无描述')}\n"
                info_text += f"大小: {model_info.get('size', '未知')}\n"
                info_text += f"推荐: {'是' if model_info.get('recommended', False) else '否'}"
                self.model_info_label.setText(info_text)
                
                # 显示文件结构信息
                file_structure = model_info.get('file_structure', {})
                if file_structure:
                    file_text = "模型文件结构:\n"
                    for file_name, description in file_structure.items():
                        file_text += f"• {file_name}: {description}\n"
                    self.file_structure_text.setText(file_text)
                else:
                    self.file_structure_text.setText("无文件结构信息")
            
            # 检查模型状态
            status = self.model_manager.check_model_status(current_model_id)
            
            # 更新状态显示
            if status["downloaded"]:
                self.model_status_label.setText("✅ 模型已下载")
                self.download_button.setEnabled(False)
            else:
                self.model_status_label.setText("❌ 模型未下载")
                self.download_button.setEnabled(True)
            
            # 更新本地模型信息
            if status.get("local_found", False):
                local_path = status.get("local_path", "")
                self.local_model_label.setText(f"🔍 发现本地模型: {local_path}")
                self.local_model_label.setStyleSheet("color: green;")
            else:
                # 显示本地搜索路径
                local_paths = status.get("local_search_paths", [])
                if local_paths:
                    paths_text = "本地搜索路径:\n" + "\n".join([f"• {path}" for path in local_paths])
                    self.local_model_label.setText(paths_text)
                    self.local_model_label.setStyleSheet("color: blue;")
                else:
                    self.local_model_label.setText("")
                    self.local_model_label.setStyleSheet("")
            
            # 更新本地路径显示
            self.update_local_paths_display()
                
        except Exception as e:
            self.logger.error(f"更新模型信息失败: {str(e)}")
    
    def download_model(self):
        """下载模型"""
        try:
            current_model_id = self.model_combo.currentData()
            if not current_model_id:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return
            
            # 检查是否已在下载
            if self.download_thread and self.download_thread.isRunning():
                QMessageBox.information(self, "提示", "模型正在下载中，请稍候")
                return
            
            # 开始下载
            self.download_button.setEnabled(False)
            self.download_progress.setVisible(True)
            self.download_progress.setValue(0)
            
            self.download_thread = ModelDownloadThread(self.model_manager, current_model_id)
            self.download_thread.progress_updated.connect(self.update_download_progress)
            self.download_thread.download_finished.connect(self.download_finished)
            self.download_thread.start()
            
        except Exception as e:
            self.logger.error(f"下载模型失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"下载模型失败: {str(e)}")
            self.download_button.setEnabled(True)
            self.download_progress.setVisible(False)
    
    def update_download_progress(self, stage: str, progress: int, message: str):
        """更新下载进度"""
        try:
            self.download_progress.setValue(progress)
            self.model_status_label.setText(f"下载中: {message}")
        except Exception as e:
            self.logger.error(f"更新下载进度失败: {str(e)}")
    
    def download_finished(self, success: bool, message: str):
        """下载完成"""
        try:
            self.download_button.setEnabled(True)
            self.download_progress.setVisible(False)
            
            if success:
                self.model_status_label.setText("✅ 模型下载完成")
                QMessageBox.information(self, "成功", message)
            else:
                self.model_status_label.setText("❌ 模型下载失败")
                QMessageBox.critical(self, "错误", message)
            
            # 更新模型信息
            self.update_model_info()
            
        except Exception as e:
            self.logger.error(f"处理下载完成失败: {str(e)}")
    
    def update_local_paths_display(self):
        """更新本地路径显示"""
        try:
            # 获取当前配置
            config = self.config_manager.config
            global_search_paths = config.get('models', {}).get('local_search_paths', [])
            custom_paths = config.get('models', {}).get('custom_local_paths', [])
            
            # 显示所有搜索路径
            all_paths = global_search_paths + custom_paths
            paths_text = "当前搜索路径:\n" + "\n".join([f"• {path}" for path in all_paths])
            self.local_paths_label.setText(paths_text)
            
            # 更新自定义路径列表
            self.custom_paths_list.clear()
            for path in custom_paths:
                self.custom_paths_list.addItem(path)
                
        except Exception as e:
            self.logger.error(f"更新本地路径显示失败: {str(e)}")
    
    def add_custom_path(self):
        """添加自定义路径"""
        try:
            path = self.custom_path_edit.text().strip()
            if not path:
                QMessageBox.warning(self, "警告", "请输入路径")
                return
            
            # 验证路径
            path_obj = Path(path)
            if not path_obj.exists():
                QMessageBox.warning(self, "警告", "路径不存在")
                return
            
            if not path_obj.is_dir():
                QMessageBox.warning(self, "警告", "路径必须是目录")
                return
            
            # 获取当前配置
            config = self.config_manager.config
            custom_paths = config.get('models', {}).get('custom_local_paths', [])
            
            # 检查是否已存在
            if path in custom_paths:
                QMessageBox.information(self, "提示", "路径已存在")
                return
            
            # 添加路径
            custom_paths.append(path)
            config['models']['custom_local_paths'] = custom_paths
            
            # 保存配置
            self.config_manager.update_config(config)
            
            # 更新显示
            self.update_local_paths_display()
            self.custom_path_edit.clear()
            
            QMessageBox.information(self, "成功", "自定义路径添加成功")
            
        except Exception as e:
            self.logger.error(f"添加自定义路径失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"添加自定义路径失败: {str(e)}")
    
    def browse_custom_path(self):
        """浏览选择自定义路径"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            path = QFileDialog.getExistingDirectory(
                self, 
                "选择本地模型目录",
                str(Path.home())
            )
            
            if path:
                self.custom_path_edit.setText(path)
                
        except Exception as e:
            self.logger.error(f"浏览路径失败: {str(e)}")
    
    def remove_custom_path(self):
        """删除自定义路径"""
        try:
            current_item = self.custom_paths_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "警告", "请选择要删除的路径")
                return
            
            path = current_item.text()
            
            # 获取当前配置
            config = self.config_manager.config
            custom_paths = config.get('models', {}).get('custom_local_paths', [])
            
            # 删除路径
            if path in custom_paths:
                custom_paths.remove(path)
                config['models']['custom_local_paths'] = custom_paths
                
                # 保存配置
                self.config_manager.update_config(config)
                
                # 更新显示
                self.update_local_paths_display()
                
                QMessageBox.information(self, "成功", "自定义路径删除成功")
            
        except Exception as e:
            self.logger.error(f"删除自定义路径失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除自定义路径失败: {str(e)}")
    
    def reset_config(self):
        """重置配置"""
        try:
            reply = QMessageBox.question(
                self, "确认", "确定要重置所有配置吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.load_config()
                
        except Exception as e:
            self.logger.error(f"重置配置失败: {str(e)}")
    
    def save_as_default_config(self):
        """保存当前配置为默认配置"""
        try:
            # 获取当前配置
            current_config = self.get_config()
            
            # 移除图片路径，只保存处理参数
            config_to_save = {k: v for k, v in current_config.items() if k != "image_paths"}
            
            # 保存为默认配置
            self.config_manager.save_as_default_config(config_to_save)
            
            QMessageBox.information(
                self, 
                "成功", 
                "当前配置已保存为默认配置！\n\n现在可以使用快速处理功能了。"
            )
            
        except Exception as e:
            self.logger.error(f"保存默认配置失败: {str(e)}")
            QMessageBox.critical(
                self, 
                "错误", 
                f"保存默认配置失败：{str(e)}"
            )
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        try:
            config = {}
            
            # 基本配置
            config["description_level"] = self.level_combo.currentData()
            config["caption_type"] = self.type_combo.currentText()
            config["caption_length"] = self.length_combo.currentText()
            config["name_input"] = self.name_input.text()
            
            # 模型配置
            config["model_id"] = self.model_combo.currentData()
            precision_text = self.precision_combo.currentText()
            config["precision"] = precision_text.split(" - ")[0]
            
            # 推理参数
            config["max_new_tokens"] = self.max_tokens_spin.value()
            config["temperature"] = self.temperature_spin.value()
            config["top_p"] = self.top_p_spin.value()
            config["top_k"] = self.top_k_spin.value()
            
            # 输出配置
            config["save_to_file"] = self.save_to_file_check.isChecked()
            config["save_to_database"] = self.save_to_db_check.isChecked()
            config["auto_display"] = self.auto_display_check.isChecked()
            
            # 额外选项
            config["extra_options"] = []
            for option_id, checkbox in self.option_checkboxes.items():
                if checkbox.isChecked():
                    config["extra_options"].append(option_id)
            
            # 图片路径
            config["image_paths"] = self.selected_images.copy()
            
            # 添加自定义路径信息
            current_config = self.config_manager.config
            custom_paths = current_config.get('models', {}).get('custom_local_paths', [])
            config["custom_local_paths"] = custom_paths
            
            # 保存配置到配置文件
            self.save_config_to_file(config)
            
            return config
        except Exception as e:
            self.logger.error(f"获取配置失败: {str(e)}")
            return {}
    
    def save_config_to_file(self, config: Dict[str, Any]):
         """保存配置到配置文件"""
         try:
             # 获取当前配置
             current_config = self.config_manager.config
             
             # 更新推理配置
             if 'inference' not in current_config:
                 current_config['inference'] = {}
             
             # 保存基本配置
             current_config['inference']['default_level'] = config.get("description_level", "normal")
             current_config['inference']['default_caption_type'] = config.get("caption_type", "Descriptive")
             current_config['inference']['precision'] = config.get("precision", "Balanced (8-bit)")
             current_config['inference']['max_new_tokens'] = config.get("max_new_tokens", 512)
             current_config['inference']['temperature'] = config.get("temperature", 0.6)
             current_config['inference']['top_p'] = config.get("top_p", 0.9)
             current_config['inference']['top_k'] = config.get("top_k", 0)
             
             # 保存额外选项
             current_config['inference']['extra_options'] = config.get("extra_options", [])
             
             # 保存输出配置
             current_config['inference']['save_to_file'] = config.get("save_to_file", True)
             current_config['inference']['save_to_database'] = config.get("save_to_database", True)
             current_config['inference']['auto_display'] = config.get("auto_display", True)
             
             # 更新模型配置
             if 'models' not in current_config:
                 current_config['models'] = {}
             
             # 保存默认模型
             current_config['models']['default_model'] = config.get("model_id", "")
             
             # 保存自定义路径
             current_config['models']['custom_local_paths'] = config.get("custom_local_paths", [])
             
             # 保存到配置文件
             self.config_manager.update_config(current_config)
             
         except Exception as e:
             self.logger.error(f"保存配置到文件失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止下载线程
            if self.download_thread and self.download_thread.isRunning():
                self.download_thread.terminate()
                self.download_thread.wait()
            
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭对话框失败: {str(e)}")
            event.accept()
    
    def create_image_selection_group(self) -> QGroupBox:
        """创建图片选择组"""
        group = QGroupBox("图片选择")
        layout = QVBoxLayout()
        
        # 选择模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("选择模式:"))
        
        self.single_radio = QRadioButton("单张图片")
        self.multiple_radio = QRadioButton("多张图片")
        self.directory_radio = QRadioButton("目录")
        
        self.single_radio.setChecked(True)
        
        mode_layout.addWidget(self.single_radio)
        mode_layout.addWidget(self.multiple_radio)
        mode_layout.addWidget(self.directory_radio)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.select_images_btn = QPushButton("选择图片")
        self.clear_images_btn = QPushButton("清空")
        self.preview_btn = QPushButton("预览")
        
        button_layout.addWidget(self.select_images_btn)
        button_layout.addWidget(self.clear_images_btn)
        button_layout.addWidget(self.preview_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片列表
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setMaximumHeight(150)
        
        left_layout.addWidget(QLabel("已选择的图片:"))
        left_layout.addWidget(self.image_list)
        
        # 右侧：预览区域
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(200, 150)
        self.preview_label.setMaximumSize(200, 150)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        
        right_layout.addWidget(QLabel("图片预览:"))
        right_layout.addWidget(self.preview_label)
        
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([300, 200])
        
        layout.addWidget(splitter)
        
        # 初始化图片列表
        self.selected_images = []
        
        # 连接信号
        self.select_images_btn.clicked.connect(self.select_images)
        self.clear_images_btn.clicked.connect(self.clear_images)
        self.preview_btn.clicked.connect(self.preview_selected_image)
        self.image_list.itemSelectionChanged.connect(self.on_image_selection_changed)
        
        group.setLayout(layout)
        return group
    
    def select_images(self):
        """选择图片"""
        try:
            if self.single_radio.isChecked():
                self._select_single_image()
            elif self.multiple_radio.isChecked():
                self._select_multiple_images()
            elif self.directory_radio.isChecked():
                self._select_directory()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择图片失败：{str(e)}")
    
    def _select_single_image(self):
        """选择单张图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择单张图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp)"
        )
        
        if file_path:
            self.selected_images = [file_path]
            self._update_image_list()
    
    def _select_multiple_images(self):
        """选择多张图片"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择多张图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp)"
        )
        
        if file_paths:
            self.selected_images.extend(file_paths)
            self._update_image_list()
    
    def _select_directory(self):
        """选择目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择包含图片的目录"
        )
        
        if dir_path:
            # 扫描目录中的图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            image_files = []
            
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        image_files.append(os.path.join(root, file))
            
            if image_files:
                self.selected_images.extend(image_files)
                self._update_image_list()
                QMessageBox.information(
                    self, 
                    "扫描完成", 
                    f"在目录中找到 {len(image_files)} 张图片"
                )
            else:
                QMessageBox.warning(self, "未找到图片", "所选目录中没有找到图片文件")
    
    def clear_images(self):
        """清空图片选择"""
        self.selected_images.clear()
        self.image_list.clear()
        self.preview_label.clear()
        self.preview_label.setText("预览区域")
    
    def _update_image_list(self):
        """更新图片列表"""
        self.image_list.clear()
        
        for image_path in self.selected_images:
            item = QListWidgetItem()
            item.setText(os.path.basename(image_path))
            item.setData(Qt.ItemDataRole.UserRole, image_path)
            self.image_list.addItem(item)
    
    def preview_selected_image(self):
        """预览选中的图片"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.data(Qt.ItemDataRole.UserRole)
            self._show_preview(image_path)
    
    def on_image_selection_changed(self):
        """图片选择改变时自动预览"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.data(Qt.ItemDataRole.UserRole)
            self._show_preview(image_path)
    
    def _show_preview(self, image_path: str):
        """显示图片预览"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放图片以适应预览区域
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("无法加载图片")
        except Exception as e:
            self.preview_label.setText(f"预览失败: {str(e)}") 