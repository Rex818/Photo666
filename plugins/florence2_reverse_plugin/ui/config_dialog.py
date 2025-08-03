"""
Florence2配置对话框
提供模型选择、自定义路径、描述级别等配置选项
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QLineEdit, QPushButton, QLabel, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox, QTextEdit, QCheckBox,
    QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from plugins.florence2_reverse_plugin.core.config_manager import ConfigManager
from plugins.florence2_reverse_plugin.ui.proxy_config_dialog import ProxyConfigDialog


class Florence2ConfigDialog(QDialog):
    """Florence2图片反推配置对话框"""
    
    # 信号定义
    config_confirmed = pyqtSignal(dict)  # 配置确认信号
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.selected_model = None
        self.custom_path = None
        self.description_level = "normal"
        self.selected_images = []  # 选中的图片路径
        
        self.setup_ui()
        self.load_config()
        self.setup_connections()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("Florence2图片反推配置")
        self.setModal(True)
        self.resize(800, 700)
        self.setMinimumWidth(600)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 模型选择组
        model_group = self.create_model_selection_group()
        main_layout.addWidget(model_group)
        
        # 自定义路径组
        custom_path_group = self.create_custom_path_group()
        main_layout.addWidget(custom_path_group)
        
        # 描述级别组
        level_group = self.create_description_level_group()
        main_layout.addWidget(level_group)
        
        # 模型信息显示
        self.model_info_text = QTextEdit()
        self.model_info_text.setMaximumHeight(100)
        self.model_info_text.setReadOnly(True)
        self.model_info_text.setPlaceholderText("选择模型后显示详细信息...")
        main_layout.addWidget(QLabel("模型信息:"))
        main_layout.addWidget(self.model_info_text)
        
        # 图片选择组
        image_group = self.create_image_selection_group()
        main_layout.addWidget(image_group)
        
        # 按钮组
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)
        
        # 代理配置按钮
        proxy_layout = QHBoxLayout()
        proxy_btn = QPushButton("代理服务器配置")
        proxy_btn.clicked.connect(self.show_proxy_config)
        proxy_layout.addWidget(proxy_btn)
        proxy_layout.addStretch()
        main_layout.addLayout(proxy_layout)
        
        self.setLayout(main_layout)
    
    def create_model_selection_group(self) -> QGroupBox:
        """创建模型选择组"""
        group = QGroupBox("模型选择")
        layout = QFormLayout()
        
        # 模型选择下拉框
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(300)
        layout.addRow("选择模型:", self.model_combo)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新模型列表")
        refresh_btn.clicked.connect(self.refresh_model_list)
        layout.addRow("", refresh_btn)
        
        group.setLayout(layout)
        return group
    
    def create_custom_path_group(self) -> QGroupBox:
        """创建自定义路径组"""
        group = QGroupBox("自定义模型路径")
        layout = QFormLayout()
        
        # 路径输入框
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择自定义模型目录...")
        self.path_edit.setMinimumWidth(300)
        layout.addRow("模型路径:", self.path_edit)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_custom_path)
        layout.addRow("", browse_btn)
        
        # 使用自定义路径复选框
        self.use_custom_path_cb = QCheckBox("使用自定义路径")
        self.use_custom_path_cb.toggled.connect(self.on_custom_path_toggled)
        layout.addRow("", self.use_custom_path_cb)
        
        group.setLayout(layout)
        return group
    
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
        
        group.setLayout(layout)
        return group
    
    def create_description_level_group(self) -> QGroupBox:
        """创建描述级别组"""
        group = QGroupBox("描述级别")
        layout = QVBoxLayout()
        
        # 描述级别说明
        level_info = QLabel(
            "• 简单描述：以词、词组组成的对图片内容的简单描述\n"
            "• 普通描述：用简单的自然语句，一般是几句话描述的图片内容\n"
            "• 详细描述：用很多句话组成的对图案细节详细描述的内容"
        )
        level_info.setWordWrap(True)
        level_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(level_info)
        
        # 单选按钮组
        self.level_group = QButtonGroup()
        
        self.simple_radio = QRadioButton("简单描述")
        self.normal_radio = QRadioButton("普通描述")
        self.detailed_radio = QRadioButton("详细描述")
        
        self.level_group.addButton(self.simple_radio, 1)
        self.level_group.addButton(self.normal_radio, 2)
        self.level_group.addButton(self.detailed_radio, 3)
        
        # 默认选择普通描述
        self.normal_radio.setChecked(True)
        
        layout.addWidget(self.simple_radio)
        layout.addWidget(self.normal_radio)
        layout.addWidget(self.detailed_radio)
        
        group.setLayout(layout)
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        
        # 左侧按钮
        self.test_btn = QPushButton("测试模型")
        self.test_btn.clicked.connect(self.test_model)
        layout.addWidget(self.test_btn)
        
        # 保存默认配置按钮
        self.save_default_btn = QPushButton("保存为默认配置")
        self.save_default_btn.clicked.connect(self.save_as_default_config)
        layout.addWidget(self.save_default_btn)
        
        layout.addStretch()
        
        # 右侧按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self.on_confirm_clicked)
        
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.confirm_btn)
        
        return layout
    
    def setup_connections(self):
        """设置信号连接"""
        self.model_combo.currentTextChanged.connect(self.on_model_selection_changed)
        self.path_edit.textChanged.connect(self.on_custom_path_changed)
        self.level_group.buttonClicked.connect(self.on_level_changed)
        
        # 图片选择相关连接
        self.select_images_btn.clicked.connect(self.select_images)
        self.clear_images_btn.clicked.connect(self.clear_images)
        self.preview_btn.clicked.connect(self.preview_selected_image)
        self.image_list.itemSelectionChanged.connect(self.on_image_selection_changed)
    
    def load_config(self):
        """加载配置"""
        try:
            # 加载可用模型列表
            self.refresh_model_list()
            
            # 设置默认模型
            default_model = self.config_manager.get_config("models.default_model")
            if default_model:
                # 尝试通过显示名称查找
                index = self.model_combo.findText(default_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    # 如果找不到显示名称，尝试通过模型名称查找
                    for i in range(self.model_combo.count()):
                        if self.model_combo.itemData(i) == default_model:
                            self.model_combo.setCurrentIndex(i)
                            break
            
            # 设置自定义路径
            custom_path = self.config_manager.get_config("models.custom_path")
            if custom_path:
                self.path_edit.setText(custom_path)
                self.use_custom_path_cb.setChecked(True)
                self.custom_path = custom_path  # 设置内部变量
            
            # 设置描述级别
            level = self.config_manager.get_config("inference.default_level", "normal")
            if level == "simple":
                self.simple_radio.setChecked(True)
            elif level == "detailed":
                self.detailed_radio.setChecked(True)
            else:
                self.normal_radio.setChecked(True)
                
        except Exception as e:
            QMessageBox.warning(self, "配置加载失败", f"加载配置时发生错误：{str(e)}")
    
    def refresh_model_list(self):
        """刷新模型列表"""
        try:
            self.model_combo.clear()
            
            # 获取可用模型
            available_models = self.config_manager.get_available_models()
            
            for model_name in available_models:
                # 获取模型信息
                model_info = self.config_manager.get_model_info(model_name)
                if model_info:
                    display_name = model_info.get("name", model_name)
                else:
                    display_name = model_name
                
                self.model_combo.addItem(display_name, model_name)
            
            # 如果没有模型，添加默认选项
            if self.model_combo.count() == 0:
                self.model_combo.addItem("microsoft/florence2-base-patch16-224", 
                                       "microsoft/florence2-base-patch16-224")
                self.model_combo.addItem("microsoft/florence2-large-patch16-224", 
                                       "microsoft/florence2-large-patch16-224")
            
        except Exception as e:
            QMessageBox.warning(self, "模型列表刷新失败", f"刷新模型列表时发生错误：{str(e)}")
    
    def on_model_selection_changed(self, display_name: str):
        """模型选择改变时的处理"""
        try:
            # 获取模型名称
            index = self.model_combo.currentIndex()
            if index >= 0:
                model_name = self.model_combo.itemData(index)
                self.selected_model = model_name
                
                # 更新模型信息显示
                self.update_model_info(model_name)
                
        except Exception as e:
            QMessageBox.warning(self, "模型信息更新失败", f"更新模型信息时发生错误：{str(e)}")
    
    def update_model_info(self, model_name: str):
        """更新模型信息显示"""
        try:
            # 获取模型信息
            model_info = self.config_manager.get_model_info(model_name)
            
            if model_info:
                info_text = f"模型名称: {model_info.get('name', model_name)}\n"
                info_text += f"描述: {model_info.get('description', '无描述')}\n"
                info_text += f"大小: {model_info.get('size', '未知')}\n"
                
                tasks = model_info.get('tasks', [])
                if tasks:
                    info_text += f"支持的任务: {', '.join(tasks)}"
                
                self.model_info_text.setText(info_text)
            else:
                self.model_info_text.setText(f"模型: {model_name}\n未找到详细信息")
                
        except Exception as e:
            self.model_info_text.setText(f"获取模型信息失败: {str(e)}")
    
    def on_custom_path_changed(self, path: str):
        """自定义路径改变时的处理"""
        self.custom_path = path if path.strip() else None
    
    def on_custom_path_toggled(self, checked: bool):
        """自定义路径复选框状态改变"""
        self.path_edit.setEnabled(checked)
        if not checked:
            self.custom_path = None
    
    def on_level_changed(self, button):
        """描述级别改变时的处理"""
        if button == self.simple_radio:
            self.description_level = "simple"
        elif button == self.detailed_radio:
            self.description_level = "detailed"
        else:
            self.description_level = "normal"
    
    def browse_custom_path(self):
        """浏览自定义路径"""
        try:
            path = QFileDialog.getExistingDirectory(
                self, 
                "选择模型目录",
                self.path_edit.text() or str(Path.home())
            )
            
            if path:
                self.path_edit.setText(path)
                self.custom_path = path
                
        except Exception as e:
            QMessageBox.warning(self, "路径选择失败", f"选择路径时发生错误：{str(e)}")
    
    def test_model(self):
        """测试模型"""
        try:
            # 获取当前配置
            config = self.get_current_config()
            
            if not config.get("model_name"):
                QMessageBox.warning(self, "测试失败", "请先选择一个模型")
                return
            
            # 这里可以添加模型测试逻辑
            QMessageBox.information(self, "测试", f"测试模型: {config['model_name']}\n"
                                                  f"路径: {config.get('custom_path', '默认路径')}\n"
                                                  f"描述级别: {config['description_level']}")
            
        except Exception as e:
            QMessageBox.warning(self, "测试失败", f"测试模型时发生错误：{str(e)}")
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = {
            "model_name": self.selected_model,
            "description_level": self.description_level,
            "image_paths": self.selected_images.copy(),  # 添加选中的图片路径
        }
        
        if self.use_custom_path_cb.isChecked() and self.custom_path:
            config["custom_path"] = self.custom_path
        
        return config
    
    def validate_config(self) -> bool:
        """验证配置"""
        try:
            config = self.get_current_config()
            
            # 检查是否选择了模型
            if not config.get("model_name"):
                QMessageBox.warning(self, "配置错误", "请选择一个模型")
                return False
            
            # 检查是否选择了图片
            if not config.get("image_paths"):
                QMessageBox.warning(self, "配置错误", "请至少选择一张图片")
                return False
            
            # 检查自定义路径 - 更智能的验证
            if self.use_custom_path_cb.isChecked():
                if not self.custom_path:
                    QMessageBox.warning(self, "配置错误", "请选择自定义模型路径")
                    return False
                
                custom_path = Path(self.custom_path)
                
                # 如果路径不存在，给出提示但不强制要求
                if not custom_path.exists():
                    reply = QMessageBox.question(
                        self, 
                        "路径不存在", 
                        f"自定义路径 '{self.custom_path}' 不存在，是否继续使用？\n\n"
                        "如果路径确实存在，请检查路径是否正确。",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return False
                else:
                    # 如果路径存在，检查是否为目录
                    if not custom_path.is_dir():
                        QMessageBox.warning(self, "配置错误", "自定义路径必须是目录")
                        return False
            
            return True
            
        except Exception as e:
            QMessageBox.warning(self, "配置验证失败", f"验证配置时发生错误：{str(e)}")
            return False
    
    def on_confirm_clicked(self):
        """确认按钮点击处理"""
        try:
            # 验证配置
            if not self.validate_config():
                return
            
            # 获取配置
            config = self.get_current_config()
            
            # 保存配置
            self.save_config(config)
            
            # 发送确认信号
            self.config_confirmed.emit(config)
            
            # 关闭对话框
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "确认失败", f"确认配置时发生错误：{str(e)}")
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置"""
        try:
            # 使用set_config方法更新配置
            self.config_manager.set_config("models.default_model", config["model_name"])
            
            if config.get("custom_path"):
                self.config_manager.set_config("models.custom_path", config["custom_path"])
            else:
                # 如果没有自定义路径，清除配置
                self.config_manager.set_config("models.custom_path", "")
            
            self.config_manager.set_config("inference.default_level", config["description_level"])
            
            # 强制保存配置到文件
            self.config_manager.save_config()
            
        except Exception as e:
            QMessageBox.warning(self, "配置保存失败", f"保存配置时发生错误：{str(e)}")
    
    def save_as_default_config(self):
        """保存为默认配置"""
        try:
            # 获取当前配置
            config = self.get_current_config()
            
            # 保存为默认配置
            success = self.config_manager.save_as_default_config(config)
            
            if success:
                QMessageBox.information(self, "保存成功", "当前配置已保存为默认配置")
            else:
                QMessageBox.warning(self, "保存失败", "保存默认配置失败")
                
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存默认配置时发生错误：{str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 清理资源
        self.custom_path = None
        self.selected_model = None
        super().closeEvent(event)
    
    # 图片选择相关方法
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
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
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
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
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
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
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
    
    def show_proxy_config(self):
        """显示代理配置对话框"""
        try:
            dialog = ProxyConfigDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开代理配置对话框失败: {str(e)}") 