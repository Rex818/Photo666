"""
Janus插件图片选择对话框
"""

import logging
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox,
    QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon


class ImageSelectionDialog(QDialog):
    """Janus插件图片选择对话框"""
    
    # 信号定义
    images_selected = pyqtSignal(list)  # 图片选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.ui.image_selection_dialog")
        
        self.setWindowTitle("选择图片")
        self.setMinimumSize(600, 400)
        self.setModal(True)
        
        # 选择的图片列表
        self.selected_images = []
        
        self.setup_ui()
        
        self.logger.info("Janus图片选择对话框初始化完成")
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 选择模式组
        mode_group = QGroupBox("选择模式")
        mode_layout = QVBoxLayout(mode_group)
        
        self.single_file_radio = QCheckBox("单张图片")
        self.single_file_radio.setChecked(True)
        self.single_file_radio.toggled.connect(self.on_mode_changed)
        mode_layout.addWidget(self.single_file_radio)
        
        self.multiple_files_radio = QCheckBox("多张图片")
        self.multiple_files_radio.toggled.connect(self.on_mode_changed)
        mode_layout.addWidget(self.multiple_files_radio)
        
        self.directory_radio = QCheckBox("目录批量")
        self.directory_radio.toggled.connect(self.on_mode_changed)
        mode_layout.addWidget(self.directory_radio)
        
        layout.addWidget(mode_group)
        
        # 文件选择组
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)
        
        # 文件路径输入
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择图片文件或目录")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_files)
        path_layout.addWidget(self.browse_btn)
        
        file_layout.addLayout(path_layout)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(200)
        file_layout.addWidget(self.file_list)
        
        # 文件过滤设置
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("文件过滤:"))
        
        self.include_subdirs_check = QCheckBox("包含子目录")
        self.include_subdirs_check.setChecked(True)
        filter_layout.addWidget(self.include_subdirs_check)
        
        filter_layout.addStretch()
        file_layout.addLayout(filter_layout)
        
        layout.addWidget(file_group)
        
        # 预览组
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("预览区域")
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # 统计信息
        self.stats_label = QLabel("已选择: 0 个文件")
        layout.addWidget(self.stats_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("选择")
        self.select_btn.clicked.connect(self.on_select)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.on_clear)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def on_mode_changed(self):
        """选择模式改变"""
        try:
            # 清空当前选择
            self.selected_images.clear()
            self.file_list.clear()
            self.path_edit.clear()
            self.update_stats()
            
        except Exception as e:
            self.logger.error(f"选择模式改变失败: {str(e)}")
    
    def browse_files(self):
        """浏览文件"""
        try:
            if self.single_file_radio.isChecked():
                # 单文件选择
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "选择图片文件", "",
                    "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.webp);;所有文件 (*.*)"
                )
                if file_path:
                    self.path_edit.setText(file_path)
                    self.selected_images = [file_path]
                    self.update_file_list()
                    
            elif self.multiple_files_radio.isChecked():
                # 多文件选择
                file_paths, _ = QFileDialog.getOpenFileNames(
                    self, "选择图片文件", "",
                    "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.webp);;所有文件 (*.*)"
                )
                if file_paths:
                    self.path_edit.setText(";".join(file_paths))
                    self.selected_images = file_paths
                    self.update_file_list()
                    
            elif self.directory_radio.isChecked():
                # 目录选择
                dir_path = QFileDialog.getExistingDirectory(self, "选择图片目录")
                if dir_path:
                    self.path_edit.setText(dir_path)
                    self.selected_images = self.get_images_from_directory(dir_path)
                    self.update_file_list()
            
        except Exception as e:
            self.logger.error(f"浏览文件失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"浏览文件失败: {str(e)}")
    
    def get_images_from_directory(self, directory_path: str) -> List[str]:
        """从目录获取图片文件"""
        try:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                return []
            
            # 支持的图片格式
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            
            image_files = []
            if self.include_subdirs_check.isChecked():
                # 包含子目录
                for file_path in directory.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                        image_files.append(str(file_path))
            else:
                # 仅当前目录
                for file_path in directory.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                        image_files.append(str(file_path))
            
            return image_files
            
        except Exception as e:
            self.logger.error(f"从目录获取图片失败: {str(e)}")
            return []
    
    def update_file_list(self):
        """更新文件列表"""
        try:
            self.file_list.clear()
            
            for image_path in self.selected_images:
                item = QListWidgetItem(Path(image_path).name)
                item.setData(Qt.ItemDataRole.UserRole, image_path)
                self.file_list.addItem(item)
            
            self.update_stats()
            
        except Exception as e:
            self.logger.error(f"更新文件列表失败: {str(e)}")
    
    def update_stats(self):
        """更新统计信息"""
        try:
            count = len(self.selected_images)
            self.stats_label.setText(f"已选择: {count} 个文件")
            
            # 更新预览
            if count > 0:
                self.update_preview(self.selected_images[0])
            else:
                self.preview_label.setText("预览区域")
                
        except Exception as e:
            self.logger.error(f"更新统计信息失败: {str(e)}")
    
    def update_preview(self, image_path: str):
        """更新预览"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放预览
                scaled_pixmap = pixmap.scaled(
                    200, 150, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("无法加载预览")
                
        except Exception as e:
            self.logger.error(f"更新预览失败: {str(e)}")
            self.preview_label.setText("预览失败")
    
    def on_select(self):
        """确认选择"""
        try:
            if not self.selected_images:
                QMessageBox.warning(self, "警告", "请先选择图片文件")
                return
            
            # 验证文件
            valid_images = []
            for image_path in self.selected_images:
                if self.validate_image_file(image_path):
                    valid_images.append(image_path)
                else:
                    self.logger.warning(f"无效的图片文件: {image_path}")
            
            if not valid_images:
                QMessageBox.warning(self, "警告", "没有有效的图片文件")
                return
            
            # 发送选择信号
            self.images_selected.emit(valid_images)
            self.accept()
            
        except Exception as e:
            self.logger.error(f"确认选择失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"确认选择失败: {str(e)}")
    
    def on_clear(self):
        """清空选择"""
        try:
            self.selected_images.clear()
            self.file_list.clear()
            self.path_edit.clear()
            self.update_stats()
            
        except Exception as e:
            self.logger.error(f"清空选择失败: {str(e)}")
    
    def validate_image_file(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            image_path_obj = Path(image_path)
            
            # 检查文件是否存在
            if not image_path_obj.exists():
                return False
            
            # 检查文件扩展名
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            if image_path_obj.suffix.lower() not in valid_extensions:
                return False
            
            # 尝试打开图片
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    img.verify()
                return True
            except Exception:
                return False
                
        except Exception as e:
            self.logger.error(f"验证图片文件失败: {str(e)}")
            return False
