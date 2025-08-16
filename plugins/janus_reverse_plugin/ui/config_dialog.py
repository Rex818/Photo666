"""
Janus插件配置对话框
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTextEdit, QPushButton, QGroupBox, QCheckBox, QFileDialog,
    QMessageBox, QProgressBar, QSlider, QWidget, QRadioButton,
    QButtonGroup, QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap


class JanusConfigDialog(QDialog):
    """Janus插件配置对话框"""
    
    # 信号定义
    config_confirmed = pyqtSignal(dict)  # 配置确认信号
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.ui.config_dialog")
        self.config_manager = config_manager
        
        # 当前配置
        self.current_config = {}
        
        # 图片选择相关
        self.selected_images = []  # 选中的图片路径
        
        self.setup_ui()
        self.load_config()
        
        self.logger.info("Janus配置对话框初始化完成")
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("Janus图片反推配置")
        self.setMinimumSize(800, 600)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 模型配置标签页
        model_tab = self.create_model_tab()
        tab_widget.addTab(model_tab, "模型配置")
        
        # 反推配置标签页
        reverse_tab = self.create_reverse_tab()
        tab_widget.addTab(reverse_tab, "反推配置")
        
        # 系统配置标签页
        system_tab = self.create_system_tab()
        tab_widget.addTab(system_tab, "系统配置")
        
        # 图片选择标签页
        image_tab = self.create_image_selection_tab()
        tab_widget.addTab(image_tab, "图片选择")
        
        layout.addWidget(tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.save_default_btn = QPushButton("保存为默认配置")
        self.save_default_btn.clicked.connect(self.save_as_default_config)
        
        self.confirm_btn = QPushButton("开始处理")
        self.confirm_btn.clicked.connect(self.on_confirm)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_default_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_model_tab(self):
        """创建模型配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 模型选择组
        model_group = QGroupBox("模型选择")
        model_layout = QGridLayout(model_group)
        
        # 模型选择
        model_layout.addWidget(QLabel("选择模型:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo, 0, 1)
        
        # 模型路径
        model_layout.addWidget(QLabel("模型路径:"), 1, 0)
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("留空使用默认路径，或指定本地模型路径")
        model_layout.addWidget(self.model_path_edit, 1, 1)
        
        self.browse_model_btn = QPushButton("浏览...")
        self.browse_model_btn.clicked.connect(self.browse_model_path)
        model_layout.addWidget(self.browse_model_btn, 1, 2)
        
        # 模型信息
        self.model_info_label = QLabel("模型信息将在这里显示")
        self.model_info_label.setWordWrap(True)
        model_layout.addWidget(self.model_info_label, 2, 0, 1, 3)
        
        # 系统要求检查
        self.system_check_label = QLabel("系统要求检查将在这里显示")
        self.system_check_label.setWordWrap(True)
        model_layout.addWidget(self.system_check_label, 3, 0, 1, 3)
        
        layout.addWidget(model_group)
        
        # 下载控制组
        download_group = QGroupBox("模型下载")
        download_layout = QVBoxLayout(download_group)
        
        self.auto_download_check = QCheckBox("自动下载缺失的模型")
        self.auto_download_check.setChecked(True)
        download_layout.addWidget(self.auto_download_check)
        
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        download_layout.addWidget(self.download_progress)
        
        self.download_btn = QPushButton("下载选中模型")
        self.download_btn.clicked.connect(self.download_selected_model)
        download_layout.addWidget(self.download_btn)
        
        layout.addWidget(download_group)
        layout.addStretch()
        
        return widget
    
    def create_reverse_tab(self):
        """创建反推配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 反推参数组
        reverse_group = QGroupBox("反推参数")
        reverse_layout = QGridLayout(reverse_group)
        
        # 问题提示词
        reverse_layout.addWidget(QLabel("问题提示词:"), 0, 0)
        self.question_edit = QTextEdit()
        self.question_edit.setMaximumHeight(80)
        self.question_edit.setPlaceholderText("输入反推问题，例如：Describe this image in detail.")
        reverse_layout.addWidget(self.question_edit, 0, 1)
        
        # Temperature
        reverse_layout.addWidget(QLabel("Temperature:"), 1, 0)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.1)
        self.temperature_spin.setToolTip("控制生成的随机性，值越大越随机")
        reverse_layout.addWidget(self.temperature_spin, 1, 1)
        
        # Top P
        reverse_layout.addWidget(QLabel("Top P:"), 2, 0)
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        self.top_p_spin.setToolTip("控制词汇选择的多样性")
        reverse_layout.addWidget(self.top_p_spin, 2, 1)
        
        # Max Tokens
        reverse_layout.addWidget(QLabel("Max Tokens:"), 3, 0)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2048)
        self.max_tokens_spin.setValue(512)
        self.max_tokens_spin.setToolTip("最大生成token数量")
        reverse_layout.addWidget(self.max_tokens_spin, 3, 1)
        
        # Seed
        reverse_layout.addWidget(QLabel("Seed:"), 4, 0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2147483647)  # 使用32位整数的最大值
        self.seed_spin.setValue(12345)  # 使用更小的数值避免溢出
        self.seed_spin.setToolTip("随机种子，用于结果复现")
        reverse_layout.addWidget(self.seed_spin, 4, 1)
        
        layout.addWidget(reverse_group)
        
        # 结果保存组
        save_group = QGroupBox("结果保存")
        save_layout = QVBoxLayout(save_group)
        
        self.save_results_check = QCheckBox("保存反推结果到文件")
        self.save_results_check.setChecked(True)
        save_layout.addWidget(self.save_results_check)
        
        save_layout.addWidget(QLabel("结果文件后缀:"))
        self.result_suffix_edit = QLineEdit(".txt")
        save_layout.addWidget(self.result_suffix_edit)
        
        layout.addWidget(save_group)
        layout.addStretch()
        
        return widget
    
    def create_system_tab(self):
        """创建系统配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 设备配置组
        device_group = QGroupBox("设备配置")
        device_layout = QVBoxLayout(device_group)
        
        self.use_gpu_check = QCheckBox("使用GPU")
        self.use_gpu_check.setChecked(True)
        device_layout.addWidget(self.use_gpu_check)
        
        device_layout.addWidget(QLabel("最大内存使用率:"))
        self.memory_usage_slider = QSlider(Qt.Orientation.Horizontal)
        self.memory_usage_slider.setRange(10, 100)
        self.memory_usage_slider.setValue(80)
        self.memory_usage_label = QLabel("80%")
        self.memory_usage_slider.valueChanged.connect(
            lambda v: self.memory_usage_label.setText(f"{v}%")
        )
        
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(self.memory_usage_slider)
        memory_layout.addWidget(self.memory_usage_label)
        device_layout.addLayout(memory_layout)
        
        layout.addWidget(device_group)
        
        # 缓存配置组
        cache_group = QGroupBox("缓存配置")
        cache_layout = QVBoxLayout(cache_group)
        
        self.cache_enabled_check = QCheckBox("启用缓存")
        self.cache_enabled_check.setChecked(True)
        cache_layout.addWidget(self.cache_enabled_check)
        
        cache_layout.addWidget(QLabel("缓存大小:"))
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        cache_layout.addWidget(self.cache_size_spin)
        
        cache_layout.addWidget(QLabel("缓存超时:"))
        self.cache_timeout_spin = QSpinBox()
        self.cache_timeout_spin.setRange(300, 86400)
        self.cache_timeout_spin.setValue(3600)
        self.cache_timeout_spin.setSuffix(" 秒")
        cache_layout.addWidget(self.cache_timeout_spin)
        
        layout.addWidget(cache_group)
        layout.addStretch()
        
        return widget
    
    def create_image_selection_tab(self):
        """创建图片选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
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
            # 加载可用模型
            available_models = self.config_manager.get_available_models()
            self.model_combo.clear()
            for model in available_models:
                self.model_combo.addItem(model["name"], model["id"])
            
            # 设置默认模型
            default_model = self.config_manager.get_default_model()
            index = self.model_combo.findData(default_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            # 加载用户设置
            user_settings = self.config_manager.get_user_settings()
            if user_settings:
                # 加载反推设置
                reverse_settings = user_settings.get("reverse_inference_settings", {})
                self.question_edit.setPlainText(reverse_settings.get("last_question", "Describe this image in detail."))
                self.temperature_spin.setValue(reverse_settings.get("last_temperature", 0.1))
                self.top_p_spin.setValue(reverse_settings.get("last_top_p", 0.95))
                self.max_tokens_spin.setValue(reverse_settings.get("last_max_new_tokens", 512))
                # 确保种子值在有效范围内
                seed_value = reverse_settings.get("last_seed", 12345)
                if seed_value > 2147483647:
                    seed_value = 12345
                self.seed_spin.setValue(seed_value)
                
                # 加载系统设置
                system_settings = user_settings.get("user_settings", {})
                self.use_gpu_check.setChecked(system_settings.get("use_gpu", True))
                memory_usage = system_settings.get("max_memory_usage", 0.8)
                self.memory_usage_slider.setValue(int(memory_usage * 100))
                self.cache_enabled_check.setChecked(system_settings.get("cache_enabled", True))
                self.cache_size_spin.setValue(system_settings.get("cache_size", 100))
                self.cache_timeout_spin.setValue(system_settings.get("cache_timeout", 3600))
            
            # 更新模型信息
            self.update_model_info()
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
    
    def on_model_changed(self):
        """模型选择改变"""
        self.update_model_info()
    
    def update_model_info(self):
        """更新模型信息"""
        try:
            current_model_id = self.model_combo.currentData()
            if not current_model_id:
                return
            
            model_info = self.config_manager.get_model_by_id(current_model_id)
            if not model_info:
                return
            
            # 更新模型信息显示
            info_text = f"模型: {model_info['name']}\n"
            info_text += f"描述: {model_info['description']}\n"
            info_text += f"大小: {model_info['size']}\n"
            info_text += f"下载大小: {model_info.get('download_size', '未知')}"
            
            self.model_info_label.setText(info_text)
            
            # 检查系统要求
            from ..core.download_manager import DownloadManager
            download_manager = DownloadManager(self.config_manager)
            requirements = download_manager.check_system_requirements(current_model_id)
            
            check_text = "系统要求检查:\n"
            check_text += f"GPU可用: {'✓' if requirements['gpu_available'] else '✗'}\n"
            check_text += f"GPU内存充足: {'✓' if requirements['gpu_memory_sufficient'] else '✗'}\n"
            check_text += f"系统内存充足: {'✓' if requirements['system_memory_sufficient'] else '✗'}"
            
            self.system_check_label.setText(check_text)
            
        except Exception as e:
            self.logger.error(f"更新模型信息失败: {str(e)}")
    
    def browse_model_path(self):
        """浏览模型路径"""
        path = QFileDialog.getExistingDirectory(self, "选择模型目录")
        if path:
            self.model_path_edit.setText(path)
    
    def download_selected_model(self):
        """下载选中的模型"""
        current_model_id = self.model_combo.currentData()
        if not current_model_id:
            QMessageBox.warning(self, "警告", "请先选择一个模型")
            return
        
        # 这里应该调用下载管理器，但为了简化，先显示消息
        QMessageBox.information(self, "信息", f"开始下载模型: {current_model_id}")
    
    def select_images(self):
        """选择图片"""
        if self.single_radio.isChecked():
            self._select_single_image()
        elif self.multiple_radio.isChecked():
            self._select_multiple_images()
        elif self.directory_radio.isChecked():
            self._select_directory()
    
    def _select_single_image(self):
        """选择单张图片"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择单张图片", "", 
            "Images (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp);;All Files (*)"
        )
        if file_name:
            self.image_list.clear()
            self.image_list.addItem(file_name)
            self.selected_images = [file_name]
    
    def _select_multiple_images(self):
        """选择多张图片"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "选择多张图片", "", 
            "Images (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp);;All Files (*)"
        )
        if file_names:
            self.image_list.clear()
            for file_name in file_names:
                self.image_list.addItem(file_name)
            self.selected_images = file_names
    
    def _select_directory(self):
        """选择目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择图片目录", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            # 查找目录中的图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
            image_files = []
            
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(str(file_path))
            
            if image_files:
                self.image_list.clear()
                for file_path in image_files:
                    self.image_list.addItem(file_path)
                self.selected_images = image_files
                QMessageBox.information(self, "信息", f"找到 {len(image_files)} 张图片")
            else:
                QMessageBox.warning(self, "警告", "所选目录中没有找到图片文件")
    
    def clear_images(self):
        """清空图片列表"""
        self.image_list.clear()
        self.selected_images = []
        self.preview_label.clear()
        self.preview_label.setText("预览区域")
    
    def preview_selected_image(self):
        """预览选中的图片"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.text()
            self._show_preview(image_path)
    
    def on_image_selection_changed(self):
        """图片选择改变时的处理"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.text()
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
                self.preview_label.setText(f"无法加载图片:\n{Path(image_path).name}")
        except Exception as e:
            self.preview_label.setText(f"预览失败:\n{str(e)}")
    
    def save_as_default_config(self):
        """保存为默认配置"""
        try:
            config = self.get_config()
            self.config_manager.save_default_config(config)
            QMessageBox.information(self, "成功", "配置已保存为默认配置")
        except Exception as e:
            self.logger.error(f"保存默认配置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存默认配置失败: {str(e)}")
    
    def on_confirm(self):
        """确认配置并开始处理"""
        try:
            # 获取当前配置
            config = self.get_config()
            
            # 检查是否选择了图片
            if not self.selected_images:
                QMessageBox.warning(self, "警告", "请先选择要处理的图片")
                return
            
            # 检查Janus库是否可用 - 移除这个检查，让插件主类来处理
            # 配置对话框不应该检查Janus库可用性，这个检查应该在插件主类中进行
            
            # 添加图片路径到配置
            config["image_paths"] = self.selected_images
            
            # 发送配置确认信号
            self.config_confirmed.emit(config)
            
            # 关闭对话框
            self.accept()
            
        except Exception as e:
            self.logger.error(f"确认配置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"确认配置失败: {str(e)}")
    
    def save_user_settings(self, config: Dict[str, Any]):
        """保存用户设置"""
        try:
            user_settings = self.config_manager.get_user_settings()
            if not user_settings:
                user_settings = {}
            
            # 保存反推设置
            if "reverse_inference_settings" not in user_settings:
                user_settings["reverse_inference_settings"] = {}
            
            reverse_settings = user_settings["reverse_inference_settings"]
            reverse_config = config.get("reverse_inference", {})
            reverse_settings["last_question"] = reverse_config.get("question", "Describe this image in detail.")
            reverse_settings["last_temperature"] = reverse_config.get("temperature", 0.1)
            reverse_settings["last_top_p"] = reverse_config.get("top_p", 0.95)
            reverse_settings["last_max_new_tokens"] = reverse_config.get("max_new_tokens", 512)
            reverse_settings["last_seed"] = reverse_config.get("seed", 12345)
            
            # 保存系统设置
            if "user_settings" not in user_settings:
                user_settings["user_settings"] = {}
            
            system_settings = user_settings["user_settings"]
            system_config = config.get("system", {})
            system_settings["use_gpu"] = system_config.get("use_gpu", True)
            system_settings["max_memory_usage"] = system_config.get("max_memory_usage", 0.8)
            system_settings["cache_enabled"] = system_config.get("cache_enabled", True)
            system_settings["cache_size"] = system_config.get("cache_size", 100)
            system_settings["cache_timeout"] = system_config.get("cache_timeout", 3600)
            
            # 保存图片选择设置
            if "image_selection_settings" not in user_settings:
                user_settings["image_selection_settings"] = {}
            
            image_selection_settings = user_settings["image_selection_settings"]
            image_selection_config = config.get("image_selection", {})
            image_selection_settings["last_selected_images"] = image_selection_config.get("selected_images", [])
            
            # 保存设置
            self.config_manager._save_user_settings()
            
        except Exception as e:
            self.logger.error(f"保存用户设置失败: {str(e)}")

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = {
            "model": {
                "model_id": self.model_combo.currentData(),
                "model_path": self.model_path_edit.text().strip() or None,
                "auto_download": self.auto_download_check.isChecked()
            },
            "reverse_inference": {
                "question": self.question_edit.toPlainText().strip(),
                "temperature": self.temperature_spin.value(),
                "top_p": self.top_p_spin.value(),
                "max_new_tokens": self.max_tokens_spin.value(),
                "seed": self.seed_spin.value(),
                "save_results": self.save_results_check.isChecked(),
                "result_file_suffix": self.result_suffix_edit.text().strip()
            },
            "system": {
                "use_gpu": self.use_gpu_check.isChecked(),
                "max_memory_usage": self.memory_usage_slider.value() / 100.0,
                "cache_enabled": self.cache_enabled_check.isChecked(),
                "cache_size": self.cache_size_spin.value(),
                "cache_timeout": self.cache_timeout_spin.value()
            },
            "image_selection": {
                "selected_images": self.selected_images
            }
        }
        
        # 保存用户设置
        self.save_user_settings(config)
        
        return config
