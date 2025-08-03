"""
JoyCaption插件主对话框
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QTextEdit, QProgressBar, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QScrollArea, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from ..core.config_manager import ConfigManager
from ..utils.logger import setup_logger


class InferenceWorker(QThread):
    """推理工作线程"""
    
    progress_updated = pyqtSignal(str, int, str)  # 阶段, 进度, 消息
    inference_completed = pyqtSignal(str, str)  # 图片路径, 结果
    error_occurred = pyqtSignal(str)  # 错误信息
    finished = pyqtSignal(dict)  # 完成信号，返回结果字典
    
    def __init__(self, plugin, image_paths: List[str], detail_level: str):
        super().__init__()
        self.plugin = plugin
        self.image_paths = image_paths
        self.detail_level = detail_level
    
    def run(self):
        """执行推理任务"""
        try:
            # 连接信号
            self.plugin.progress_updated.connect(self.progress_updated.emit)
            self.plugin.inference_completed.connect(self.inference_completed.emit)
            self.plugin.error_occurred.connect(self.error_occurred.emit)
            
            # 执行推理
            results = self.plugin.perform_inference(self.image_paths, self.detail_level)
            
            # 断开信号连接
            self.plugin.progress_updated.disconnect()
            self.plugin.inference_completed.disconnect()
            self.plugin.error_occurred.disconnect()
            
            self.finished.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(f"推理任务异常: {e}")


class JoyCaptionDialog(QDialog):
    """JoyCaption反推对话框"""
    
    def __init__(self, parent=None, plugin=None):
        super().__init__(parent)
        self.plugin = plugin
        self.logger = setup_logger("joycaption_dialog")
        
        # 初始化UI
        self.init_ui()
        self.load_config()
        self.setup_connections()
        
        self.logger.info("JoyCaption反推对话框初始化完成")
    
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("JoyCaption图片反推信息")
        self.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个标签页
        self.create_model_tab()
        self.create_settings_tab()
        self.create_inference_tab()
        self.create_results_tab()
        
        # 底部按钮
        self.create_bottom_buttons(main_layout)
        
        self.setLayout(main_layout)
    
    def create_model_tab(self):
        """创建模型配置标签页"""
        model_widget = QWidget()
        layout = QVBoxLayout()
        
        # 模型选择组
        model_group = QGroupBox("模型配置")
        model_layout = QGridLayout()
        
        # 模型选择
        model_layout.addWidget(QLabel("选择模型:"), 0, 0)
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo, 0, 1)
        
        # 内存模式
        model_layout.addWidget(QLabel("内存模式:"), 1, 0)
        self.memory_combo = QComboBox()
        self.memory_combo.addItems([
            "Balanced (8-bit)",
            "Full Precision (bf16)",
            "Maximum Savings (4-bit)"
        ])
        model_layout.addWidget(self.memory_combo, 1, 1)
        
        # 模型信息
        self.model_info_label = QLabel("请选择模型")
        self.model_info_label.setWordWrap(True)
        model_layout.addWidget(self.model_info_label, 2, 0, 1, 2)
        
        # 加载按钮
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.setEnabled(False)
        model_layout.addWidget(self.load_model_btn, 3, 0, 1, 2)
        
        # 进度条
        self.model_progress = QProgressBar()
        self.model_progress.setVisible(False)
        model_layout.addWidget(self.model_progress, 4, 0, 1, 2)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 代理设置组
        proxy_group = QGroupBox("网络代理")
        proxy_layout = QGridLayout()
        
        proxy_layout.addWidget(QLabel("代理设置:"), 0, 0)
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItems(["自动检测", "无代理", "自定义"])
        proxy_layout.addWidget(self.proxy_combo, 0, 1)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        layout.addStretch()
        model_widget.setLayout(layout)
        self.tab_widget.addTab(model_widget, "模型配置")
    
    def create_settings_tab(self):
        """创建设置标签页"""
        settings_widget = QWidget()
        layout = QVBoxLayout()
        
        # 推理设置组
        inference_group = QGroupBox("推理设置")
        inference_layout = QGridLayout()
        
        # 详细程度
        inference_layout.addWidget(QLabel("详细程度:"), 0, 0)
        self.detail_combo = QComboBox()
        self.detail_combo.addItems(["简单描述", "普通描述", "详细描述"])
        inference_layout.addWidget(self.detail_combo, 0, 1)
        
        # 描述类型
        inference_layout.addWidget(QLabel("描述类型:"), 1, 0)
        self.caption_combo = QComboBox()
        self.caption_combo.addItems([
            "Descriptive",
            "Descriptive (Casual)",
            "Straightforward",
            "Stable Diffusion Prompt",
            "MidJourney",
            "Danbooru tag list"
        ])
        inference_layout.addWidget(self.caption_combo, 1, 1)
        
        # 温度
        inference_layout.addWidget(QLabel("Temperature:"), 2, 0)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setSingleStep(0.1)
        inference_layout.addWidget(self.temperature_spin, 2, 1)
        
        # Top P
        inference_layout.addWidget(QLabel("Top P:"), 3, 0)
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setValue(0.9)
        self.top_p_spin.setSingleStep(0.1)
        inference_layout.addWidget(self.top_p_spin, 3, 1)
        
        # Max Tokens
        inference_layout.addWidget(QLabel("Max Tokens:"), 4, 0)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2048)
        self.max_tokens_spin.setValue(512)
        inference_layout.addWidget(self.max_tokens_spin, 4, 1)
        
        inference_group.setLayout(inference_layout)
        layout.addWidget(inference_group)
        
        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_layout = QGridLayout()
        
        # 自动保存
        self.auto_save_check = QCheckBox("自动保存结果")
        self.auto_save_check.setChecked(True)
        output_layout.addWidget(self.auto_save_check, 0, 0)
        
        # 保存格式
        output_layout.addWidget(QLabel("保存格式:"), 1, 0)
        self.save_format_combo = QComboBox()
        self.save_format_combo.addItems(["txt", "json"])
        output_layout.addWidget(self.save_format_combo, 1, 1)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        settings_widget.setLayout(layout)
        self.tab_widget.addTab(settings_widget, "推理设置")
    
    def create_inference_tab(self):
        """创建推理标签页"""
        inference_widget = QWidget()
        layout = QVBoxLayout()
        
        # 图片选择组
        image_group = QGroupBox("图片选择")
        image_layout = QVBoxLayout()
        
        # 选择按钮
        button_layout = QHBoxLayout()
        self.select_single_btn = QPushButton("选择单张图片")
        self.select_multiple_btn = QPushButton("选择多张图片")
        self.select_folder_btn = QPushButton("选择文件夹")
        self.clear_selection_btn = QPushButton("清除选择")
        
        button_layout.addWidget(self.select_single_btn)
        button_layout.addWidget(self.select_multiple_btn)
        button_layout.addWidget(self.select_folder_btn)
        button_layout.addWidget(self.clear_selection_btn)
        button_layout.addStretch()
        
        image_layout.addLayout(button_layout)
        
        # 图片列表
        self.image_list = QTextEdit()
        self.image_list.setMaximumHeight(150)
        self.image_list.setPlaceholderText("请选择要处理的图片...")
        image_layout.addWidget(self.image_list)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        # 推理控制组
        control_group = QGroupBox("推理控制")
        control_layout = QVBoxLayout()
        
        # 开始推理按钮
        self.start_inference_btn = QPushButton("开始推理")
        self.start_inference_btn.setEnabled(False)
        control_layout.addWidget(self.start_inference_btn)
        
        # 进度条
        self.inference_progress = QProgressBar()
        self.inference_progress.setVisible(False)
        control_layout.addWidget(self.inference_progress)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        control_layout.addWidget(self.status_label)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        inference_widget.setLayout(layout)
        self.tab_widget.addTab(inference_widget, "图片推理")
    
    def create_results_tab(self):
        """创建结果标签页"""
        results_widget = QWidget()
        layout = QVBoxLayout()
        
        # 结果显示
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("推理结果将在这里显示...")
        layout.addWidget(self.results_text)
        
        # 结果操作按钮
        button_layout = QHBoxLayout()
        self.save_results_btn = QPushButton("保存结果")
        self.clear_results_btn = QPushButton("清除结果")
        self.copy_results_btn = QPushButton("复制结果")
        
        button_layout.addWidget(self.save_results_btn)
        button_layout.addWidget(self.clear_results_btn)
        button_layout.addWidget(self.copy_results_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        results_widget.setLayout(layout)
        self.tab_widget.addTab(results_widget, "推理结果")
    
    def create_bottom_buttons(self, main_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("关闭")
        self.reset_btn = QPushButton("重置设置")
        
        button_layout.addStretch()
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
    
    def load_config(self):
        """加载配置"""
        try:
            if not self.plugin or not self.plugin.config_manager:
                return
            
            config_manager = self.plugin.config_manager
            
            # 加载可用模型
            available_models = config_manager.get_available_models()
            self.model_combo.addItems(available_models)
            
            # 设置默认值
            default_model = config_manager.get("selected_model", "joycaption-v1.5")
            index = self.model_combo.findText(default_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            # 更新模型信息
            self.update_model_info()
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
    
    def setup_connections(self):
        """设置信号连接"""
        # 模型相关
        self.model_combo.currentTextChanged.connect(self.update_model_info)
        self.load_model_btn.clicked.connect(self.load_model)
        
        # 图片选择
        self.select_single_btn.clicked.connect(self.select_single_image)
        self.select_multiple_btn.clicked.connect(self.select_multiple_images)
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        
        # 推理控制
        self.start_inference_btn.clicked.connect(self.start_inference)
        
        # 结果操作
        self.save_results_btn.clicked.connect(self.save_results)
        self.clear_results_btn.clicked.connect(self.clear_results)
        self.copy_results_btn.clicked.connect(self.copy_results)
        
        # 底部按钮
        self.close_btn.clicked.connect(self.close)
        self.reset_btn.clicked.connect(self.reset_settings)
    
    def update_model_info(self):
        """更新模型信息显示"""
        try:
            model_name = self.model_combo.currentText()
            if not model_name:
                self.model_info_label.setText("请选择模型")
                self.load_model_btn.setEnabled(False)
                return
            
            if not self.plugin or not self.plugin.config_manager:
                return
            
            config_manager = self.plugin.config_manager
            model_config = config_manager.get_model_config(model_name)
            
            if model_config:
                info_text = f"模型: {model_config.get('name', model_name)}\n"
                info_text += f"描述: {model_config.get('description', '无描述')}\n"
                info_text += f"大小: {model_config.get('size', '未知')}\n"
                info_text += f"任务: {', '.join(model_config.get('tasks', []))}"
                
                self.model_info_label.setText(info_text)
                self.load_model_btn.setEnabled(True)
            else:
                self.model_info_label.setText(f"未找到模型配置: {model_name}")
                self.load_model_btn.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"更新模型信息失败: {e}")
    
    def load_model(self):
        """加载模型"""
        try:
            model_name = self.model_combo.currentText()
            if not model_name:
                QMessageBox.warning(self, "警告", "请先选择模型")
                return
            
            # 构建配置
            config = {
                "selected_model": model_name,
                "memory_mode": self.memory_combo.currentText(),
                "detail_level": self.detail_combo.currentText(),
                "caption_type": self.caption_combo.currentText(),
                "temperature": self.temperature_spin.value(),
                "top_p": self.top_p_spin.value(),
                "max_tokens": self.max_tokens_spin.value(),
                "top_k": 0,
                "auto_download": True,
                "custom_model_path": "",
                "extra_options": []
            }
            
            # 显示进度
            self.model_progress.setVisible(True)
            self.load_model_btn.setEnabled(False)
            self.status_label.setText("正在加载模型...")
            
            # 加载模型
            success = self.plugin.load_model(model_name, config)
            
            if success:
                self.status_label.setText(f"模型加载成功: {model_name}")
                self.start_inference_btn.setEnabled(True)
                QMessageBox.information(self, "成功", f"模型 {model_name} 加载成功")
            else:
                self.status_label.setText("模型加载失败")
                QMessageBox.critical(self, "错误", f"模型 {model_name} 加载失败")
            
            self.model_progress.setVisible(False)
            self.load_model_btn.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            self.model_progress.setVisible(False)
            self.load_model_btn.setEnabled(True)
            self.status_label.setText("模型加载异常")
            QMessageBox.critical(self, "错误", f"加载模型异常: {e}")
    
    def select_single_image(self):
        """选择单张图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp)"
        )
        if file_path:
            self.image_list.setText(file_path)
            self.update_inference_button()
    
    def select_multiple_images(self):
        """选择多张图片"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp)"
        )
        if file_paths:
            self.image_list.setText("\n".join(file_paths))
            self.update_inference_button()
    
    def select_folder(self):
        """选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder_path:
            # 扫描文件夹中的图片
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
            image_paths = []
            
            for file_path in Path(folder_path).rglob("*"):
                if file_path.suffix.lower() in image_extensions:
                    image_paths.append(str(file_path))
            
            if image_paths:
                self.image_list.setText("\n".join(image_paths))
                self.update_inference_button()
                QMessageBox.information(self, "信息", f"找到 {len(image_paths)} 张图片")
            else:
                QMessageBox.warning(self, "警告", "所选文件夹中没有找到图片文件")
    
    def clear_selection(self):
        """清除选择"""
        self.image_list.clear()
        self.update_inference_button()
    
    def update_inference_button(self):
        """更新推理按钮状态"""
        has_images = bool(self.image_list.toPlainText().strip())
        model_loaded = self.plugin and self.plugin.is_initialized
        self.start_inference_btn.setEnabled(has_images and model_loaded)
    
    def start_inference(self):
        """开始推理"""
        try:
            # 获取图片路径列表
            image_text = self.image_list.toPlainText().strip()
            if not image_text:
                QMessageBox.warning(self, "警告", "请先选择图片")
                return
            
            image_paths = [path.strip() for path in image_text.split('\n') if path.strip()]
            
            # 验证图片文件
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    self.logger.warning(f"图片文件不存在: {path}")
            
            if not valid_paths:
                QMessageBox.warning(self, "警告", "没有找到有效的图片文件")
                return
            
            # 获取详细程度
            detail_level_map = {
                "简单描述": "simple",
                "普通描述": "normal", 
                "详细描述": "detailed"
            }
            detail_level = detail_level_map.get(self.detail_combo.currentText(), "normal")
            
            # 显示进度
            self.inference_progress.setVisible(True)
            self.start_inference_btn.setEnabled(False)
            self.status_label.setText("正在执行推理...")
            
            # 创建并启动工作线程
            self.inference_worker = InferenceWorker(self.plugin, valid_paths, detail_level)
            self.inference_worker.progress_updated.connect(self.update_inference_progress)
            self.inference_worker.inference_completed.connect(self.add_inference_result)
            self.inference_worker.error_occurred.connect(self.handle_inference_error)
            self.inference_worker.finished.connect(self.inference_finished)
            self.inference_worker.start()
            
        except Exception as e:
            self.logger.error(f"开始推理失败: {e}")
            self.inference_progress.setVisible(False)
            self.start_inference_btn.setEnabled(True)
            self.status_label.setText("推理启动失败")
            QMessageBox.critical(self, "错误", f"开始推理失败: {e}")
    
    def update_inference_progress(self, stage: str, progress: int, message: str):
        """更新推理进度"""
        self.inference_progress.setValue(progress)
        self.status_label.setText(message)
    
    def add_inference_result(self, image_path: str, result: str):
        """添加推理结果"""
        try:
            current_text = self.results_text.toPlainText()
            image_name = Path(image_path).name
            
            new_result = f"=== {image_name} ===\n{result}\n\n"
            
            self.results_text.append(new_result)
            
        except Exception as e:
            self.logger.error(f"添加推理结果失败: {e}")
    
    def handle_inference_error(self, error: str):
        """处理推理错误"""
        self.logger.error(f"推理错误: {error}")
        QMessageBox.warning(self, "推理错误", error)
    
    def inference_finished(self, results: Dict[str, str]):
        """推理完成"""
        try:
            self.inference_progress.setVisible(False)
            self.start_inference_btn.setEnabled(True)
            
            success_count = len([r for r in results.values() if r and not r.startswith("错误:")])
            total_count = len(results)
            
            self.status_label.setText(f"推理完成，成功处理 {success_count}/{total_count} 张图片")
            
            if success_count < total_count:
                QMessageBox.warning(self, "推理完成", 
                                  f"推理完成，成功处理 {success_count}/{total_count} 张图片")
            else:
                QMessageBox.information(self, "推理完成", 
                                      f"推理完成，成功处理 {success_count} 张图片")
            
        except Exception as e:
            self.logger.error(f"处理推理完成失败: {e}")
    
    def save_results(self):
        """保存结果"""
        try:
            results_text = self.results_text.toPlainText()
            if not results_text.strip():
                QMessageBox.warning(self, "警告", "没有结果可保存")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存结果", "", 
                "文本文件 (*.txt);;JSON文件 (*.json)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(results_text)
                
                QMessageBox.information(self, "成功", f"结果已保存到: {file_path}")
                
        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")
            QMessageBox.critical(self, "错误", f"保存结果失败: {e}")
    
    def clear_results(self):
        """清除结果"""
        self.results_text.clear()
    
    def copy_results(self):
        """复制结果"""
        try:
            results_text = self.results_text.toPlainText()
            if results_text.strip():
                clipboard = QApplication.clipboard()
                clipboard.setText(results_text)
                QMessageBox.information(self, "成功", "结果已复制到剪贴板")
            else:
                QMessageBox.warning(self, "警告", "没有结果可复制")
                
        except Exception as e:
            self.logger.error(f"复制结果失败: {e}")
            QMessageBox.critical(self, "错误", f"复制结果失败: {e}")
    
    def reset_settings(self):
        """重置设置"""
        try:
            reply = QMessageBox.question(
                self, "确认重置", 
                "确定要重置所有设置到默认值吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 重置设置
                self.detail_combo.setCurrentIndex(1)  # 普通描述
                self.caption_combo.setCurrentIndex(0)  # Descriptive
                self.temperature_spin.setValue(0.7)
                self.top_p_spin.setValue(0.9)
                self.max_tokens_spin.setValue(512)
                self.memory_combo.setCurrentIndex(0)  # Balanced (8-bit)
                
                QMessageBox.information(self, "成功", "设置已重置")
                
        except Exception as e:
            self.logger.error(f"重置设置失败: {e}")
            QMessageBox.critical(self, "错误", f"重置设置失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止推理线程
            if hasattr(self, 'inference_worker') and self.inference_worker.isRunning():
                self.inference_worker.terminate()
                self.inference_worker.wait()
            
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭对话框异常: {e}")
            event.accept() 