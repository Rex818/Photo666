"""
图片选择对话框
让用户选择单张图片、多张图片或目录进行反推处理
"""

import os
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QGroupBox, QRadioButton, QButtonGroup, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap


class ImageSelectionDialog(QDialog):
    """图片选择对话框"""
    
    # 信号定义
    images_selected = pyqtSignal(list)  # 选中的图片路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择图片进行反推")
        self.setModal(True)
        self.resize(800, 600)
        
        # 选中的图片路径
        self.selected_images = []
        
        # 初始化UI
        self._init_ui()
        self._setup_connections()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 选择模式组
        mode_group = QGroupBox("选择模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.single_radio = QRadioButton("单张图片")
        self.multiple_radio = QRadioButton("多张图片")
        self.directory_radio = QRadioButton("目录")
        
        self.single_radio.setChecked(True)
        
        mode_layout.addWidget(self.single_radio)
        mode_layout.addWidget(self.multiple_radio)
        mode_layout.addWidget(self.directory_radio)
        mode_layout.addStretch()
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("选择")
        self.clear_button = QPushButton("清空")
        self.preview_button = QPushButton("预览")
        
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片列表
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        
        left_layout.addWidget(QLabel("已选择的图片:"))
        left_layout.addWidget(self.image_list)
        
        # 右侧：预览区域
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        
        right_layout.addWidget(QLabel("图片预览:"))
        right_layout.addWidget(self.preview_label)
        
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([400, 400])
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.setDefault(True)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.ok_button)
        bottom_layout.addWidget(self.cancel_button)
        
        # 组装布局
        layout.addWidget(mode_group)
        layout.addLayout(button_layout)
        layout.addWidget(splitter)
        layout.addLayout(bottom_layout)
    
    def _setup_connections(self):
        """设置信号连接"""
        self.select_button.clicked.connect(self._select_images)
        self.clear_button.clicked.connect(self._clear_selection)
        self.preview_button.clicked.connect(self._preview_selected)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.cancel_button.clicked.connect(self.reject)
    
    def _select_images(self):
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
    
    def _clear_selection(self):
        """清空选择"""
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
    
    def _preview_selected(self):
        """预览选中的图片"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.data(Qt.ItemDataRole.UserRole)
            self._show_preview(image_path)
    
    def _on_selection_changed(self):
        """选择改变时自动预览"""
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
    
    def _on_ok_clicked(self):
        """确定按钮点击"""
        if not self.selected_images:
            QMessageBox.warning(self, "警告", "请至少选择一张图片")
            return
        
        self.images_selected.emit(self.selected_images)
        self.accept()
    
    def get_selected_images(self) -> List[str]:
        """获取选中的图片路径"""
        return self.selected_images.copy() 