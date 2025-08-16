"""
Photo editor dialog for basic image editing operations.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QSpinBox, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QSplitter, QFrame, QCheckBox,
    QComboBox, QTabWidget, QGridLayout, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QTransform, QImage
import logging
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np


class CropWidget(QWidget):
    """Widget for image cropping with visual selection."""
    
    crop_changed = pyqtSignal(QRect)  # 裁剪区域改变信号
    
    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.original_pixmap = pixmap
        self.crop_rect = QRect(0, 0, pixmap.width(), pixmap.height())
        self.is_dragging = False
        self.drag_start = QPoint()
        self.drag_corner = None
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制原图
        painter.drawPixmap(0, 0, self.original_pixmap)
        
        # 绘制半透明遮罩
        overlay = QColor(0, 0, 0, 128)
        painter.fillRect(self.rect(), overlay)
        
        # 清除裁剪区域的遮罩
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.crop_rect, Qt.GlobalColor.transparent)
        
        # 绘制裁剪框
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pen = QPen(Qt.GlobalColor.white, 2)
        painter.setPen(pen)
        painter.drawRect(self.crop_rect)
        
        # 绘制角落控制点
        corner_size = 8
        corners = [
            self.crop_rect.topLeft(),
            self.crop_rect.topRight(),
            self.crop_rect.bottomLeft(),
            self.crop_rect.bottomRight()
        ]
        
        for corner in corners:
            painter.fillRect(
                corner.x() - corner_size//2,
                corner.y() - corner_size//2,
                corner_size, corner_size,
                Qt.GlobalColor.white
            )
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start = event.pos()
            self.drag_corner = self.get_corner_at(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.is_dragging:
            if self.drag_corner:
                # 调整角落
                self.resize_crop_rect(event.pos())
            else:
                # 移动整个裁剪框
                self.move_crop_rect(event.pos())
        else:
            # 更新鼠标样式
            corner = self.get_corner_at(event.pos())
            if corner:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self.crop_rect.contains(event.pos()):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_corner = None
    
    def get_corner_at(self, pos: QPoint) -> Optional[str]:
        """获取指定位置的角落类型"""
        corner_size = 8
        corners = {
            'tl': self.crop_rect.topLeft(),
            'tr': self.crop_rect.topRight(),
            'bl': self.crop_rect.bottomLeft(),
            'br': self.crop_rect.bottomRight()
        }
        
        for name, corner in corners.items():
            if abs(pos.x() - corner.x()) <= corner_size//2 and \
               abs(pos.y() - corner.y()) <= corner_size//2:
                return name
        return None
    
    def resize_crop_rect(self, pos: QPoint):
        """调整裁剪框大小"""
        if not self.drag_corner:
            return
            
        new_rect = QRect(self.crop_rect)
        
        if 't' in self.drag_corner:
            new_rect.setTop(pos.y())
        if 'b' in self.drag_corner:
            new_rect.setBottom(pos.y())
        if 'l' in self.drag_corner:
            new_rect.setLeft(pos.x())
        if 'r' in self.drag_corner:
            new_rect.setRight(pos.x())
        
        # 确保最小尺寸
        if new_rect.width() >= 50 and new_rect.height() >= 50:
            self.crop_rect = new_rect
            self.crop_changed.emit(self.crop_rect)
            self.update()
    
    def move_crop_rect(self, pos: QPoint):
        """移动裁剪框"""
        delta = pos - self.drag_start
        new_rect = self.crop_rect.translated(delta)
        
        # 确保不超出边界
        if new_rect.left() >= 0 and new_rect.top() >= 0 and \
           new_rect.right() <= self.width() and new_rect.bottom() <= self.height():
            self.crop_rect = new_rect
            self.drag_start = pos
            self.crop_changed.emit(self.crop_rect)
            self.update()
    
    def set_crop_rect(self, rect: QRect):
        """设置裁剪框"""
        self.crop_rect = rect
        self.update()


class PhotoEditorDialog(QDialog):
    """Photo editor dialog with basic editing tools."""
    
    def __init__(self, photo_path: str, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.original_image = None
        self.current_image = None
        # 配置标准logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("picman.gui.photo_editor")
        
        # 编辑参数
        self.brightness = 1.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0
        self.rotation_angle = 0
        
        self.init_ui()
        self.load_image()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("照片编辑器")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：图片显示和编辑区域
        self.create_image_area(splitter)
        
        # 右侧：编辑工具面板
        self.create_tools_panel(splitter)
        
        # 设置分割器比例
        splitter.setSizes([700, 300])
        
        # 底部按钮
        self.create_bottom_buttons(layout)
    
    def create_image_area(self, parent):
        """创建图片显示区域"""
        image_widget = QWidget()
        layout = QVBoxLayout(image_widget)
        
        # 图片显示区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setText("加载中...")
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        parent.addWidget(image_widget)
    
    def create_tools_panel(self, parent):
        """创建编辑工具面板"""
        tools_widget = QWidget()
        layout = QVBoxLayout(tools_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 基础调整标签页
        self.create_basic_adjustments_tab(tab_widget)
        
        # 裁剪标签页
        self.create_crop_tab(tab_widget)
        
        # 滤镜标签页
        self.create_filter_tab(tab_widget)
        
        parent.addWidget(tools_widget)
    
    def create_basic_adjustments_tab(self, tab_widget):
        """创建基础调整标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 亮度调整
        brightness_group = QGroupBox("亮度")
        brightness_layout = QVBoxLayout(brightness_group)
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 200)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        
        self.brightness_spinbox = QSpinBox()
        self.brightness_spinbox.setRange(0, 200)
        self.brightness_spinbox.setValue(100)
        self.brightness_spinbox.valueChanged.connect(self.brightness_slider.setValue)
        
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_spinbox)
        layout.addWidget(brightness_group)
        
        # 对比度调整
        contrast_group = QGroupBox("对比度")
        contrast_layout = QVBoxLayout(contrast_group)
        
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        
        self.contrast_spinbox = QSpinBox()
        self.contrast_spinbox.setRange(0, 200)
        self.contrast_spinbox.setValue(100)
        self.contrast_spinbox.valueChanged.connect(self.contrast_slider.setValue)
        
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_spinbox)
        layout.addWidget(contrast_group)
        
        # 饱和度调整
        saturation_group = QGroupBox("饱和度")
        saturation_layout = QVBoxLayout(saturation_group)
        
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(100)
        self.saturation_slider.valueChanged.connect(self.on_saturation_changed)
        
        self.saturation_spinbox = QSpinBox()
        self.saturation_spinbox.setRange(0, 200)
        self.saturation_spinbox.setValue(100)
        self.saturation_spinbox.valueChanged.connect(self.saturation_slider.setValue)
        
        saturation_layout.addWidget(self.saturation_slider)
        saturation_layout.addWidget(self.saturation_spinbox)
        layout.addWidget(saturation_group)
        
        # 锐化调整
        sharpness_group = QGroupBox("锐化")
        sharpness_layout = QVBoxLayout(sharpness_group)
        
        self.sharpness_slider = QSlider(Qt.Orientation.Horizontal)
        self.sharpness_slider.setRange(0, 200)
        self.sharpness_slider.setValue(100)
        self.sharpness_slider.valueChanged.connect(self.on_sharpness_changed)
        
        self.sharpness_spinbox = QSpinBox()
        self.sharpness_spinbox.setRange(0, 200)
        self.sharpness_spinbox.setValue(100)
        self.sharpness_spinbox.valueChanged.connect(self.sharpness_slider.setValue)
        
        sharpness_layout.addWidget(self.sharpness_slider)
        sharpness_layout.addWidget(self.sharpness_spinbox)
        layout.addWidget(sharpness_group)
        
        # 重置按钮
        reset_btn = QPushButton("重置调整")
        reset_btn.clicked.connect(self.reset_adjustments)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        tab_widget.addTab(tab, "基础调整")
    
    def create_crop_tab(self, tab_widget):
        """创建裁剪标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 裁剪模式选择
        crop_mode_group = QGroupBox("裁剪模式")
        crop_mode_layout = QVBoxLayout(crop_mode_group)
        
        self.crop_mode_group = QButtonGroup()
        
        free_crop_radio = QRadioButton("自由裁剪")
        free_crop_radio.setChecked(True)
        self.crop_mode_group.addButton(free_crop_radio, 0)
        crop_mode_layout.addWidget(free_crop_radio)
        
        aspect_ratios = [
            ("1:1 (正方形)", 1, 1),
            ("4:3", 4, 3),
            ("3:4", 3, 4),
            ("16:9", 16, 9),
            ("9:16", 9, 16)
        ]
        
        for name, w, h in aspect_ratios:
            radio = QRadioButton(name)
            self.crop_mode_group.addButton(radio, w * 1000 + h)
            crop_mode_layout.addWidget(radio)
        
        layout.addWidget(crop_mode_group)
        
        # 裁剪按钮
        crop_btn = QPushButton("应用裁剪")
        crop_btn.clicked.connect(self.apply_crop)
        layout.addWidget(crop_btn)
        
        layout.addStretch()
        tab_widget.addTab(tab, "裁剪")
    
    def create_filter_tab(self, tab_widget):
        """创建滤镜标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 滤镜选择
        filter_group = QGroupBox("滤镜效果")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "无滤镜",
            "黑白",
            "复古",
            "冷色调",
            "暖色调",
            "模糊",
            "锐化"
        ])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        
        layout.addWidget(filter_group)
        
        # 旋转控制
        rotation_group = QGroupBox("旋转")
        rotation_layout = QHBoxLayout(rotation_group)
        
        rotate_left_btn = QPushButton("↺ 左转90°")
        rotate_left_btn.clicked.connect(lambda: self.rotate_image(-90))
        rotation_layout.addWidget(rotate_left_btn)
        
        rotate_right_btn = QPushButton("↻ 右转90°")
        rotate_right_btn.clicked.connect(lambda: self.rotate_image(90))
        rotation_layout.addWidget(rotate_right_btn)
        
        rotate_180_btn = QPushButton("↻↻ 180°")
        rotate_180_btn.clicked.connect(lambda: self.rotate_image(180))
        rotation_layout.addWidget(rotate_180_btn)
        
        layout.addWidget(rotation_group)
        
        layout.addStretch()
        tab_widget.addTab(tab, "滤镜")
    
    def create_bottom_buttons(self, layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        # 撤销按钮
        self.undo_btn = QPushButton("撤销")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo)
        button_layout.addWidget(self.undo_btn)
        
        # 重做按钮
        self.redo_btn = QPushButton("重做")
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self.redo)
        button_layout.addWidget(self.redo_btn)
        
        button_layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_image)
        button_layout.addWidget(save_btn)
        
        # 另存为按钮
        save_as_btn = QPushButton("另存为")
        save_as_btn.clicked.connect(self.save_as_image)
        button_layout.addWidget(save_as_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_image(self):
        """加载图片"""
        try:
            self.original_image = Image.open(self.photo_path)
            self.current_image = self.original_image.copy()
            self.update_display()
            self.logger.info("Image loaded successfully: %s", self.photo_path)
        except Exception as e:
            self.logger.error("Failed to load image: %s", str(e))
            QMessageBox.critical(self, "错误", f"无法加载图片: {str(e)}")
    
    def update_display(self):
        """更新显示"""
        if self.current_image:
            # 转换为QPixmap
            qimage = self.pil_to_qimage(self.current_image)
            pixmap = QPixmap.fromImage(qimage)
            
            # 缩放以适应显示区域
            scaled_pixmap = self.scale_pixmap(pixmap)
            self.image_label.setPixmap(scaled_pixmap)
    
    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """缩放图片以适应显示区域"""
        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return pixmap
        
        return pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    def pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """将PIL图像转换为QImage"""
        if pil_image.mode == "RGB":
            r, g, b = pil_image.split()
            pil_image = Image.merge("RGB", (b, g, r))
        elif pil_image.mode == "RGBA":
            r, g, b, a = pil_image.split()
            pil_image = Image.merge("RGBA", (b, g, r, a))
        
        im_data = pil_image.tobytes("raw", pil_image.mode)
        qimage = QImage(im_data, pil_image.size[0], pil_image.size[1], 
                       QImage.Format.Format_RGB888)
        return qimage
    
    def on_brightness_changed(self, value):
        """亮度改变"""
        self.brightness = value / 100.0
        self.brightness_spinbox.setValue(value)
        self.apply_adjustments()
    
    def on_contrast_changed(self, value):
        """对比度改变"""
        self.contrast = value / 100.0
        self.contrast_spinbox.setValue(value)
        self.apply_adjustments()
    
    def on_saturation_changed(self, value):
        """饱和度改变"""
        self.saturation = value / 100.0
        self.saturation_spinbox.setValue(value)
        self.apply_adjustments()
    
    def on_sharpness_changed(self, value):
        """锐化改变"""
        self.sharpness = value / 100.0
        self.sharpness_spinbox.setValue(value)
        self.apply_adjustments()
    
    def apply_adjustments(self):
        """应用调整"""
        if not self.original_image:
            return
        
        try:
            # 从原图开始应用调整
            image = self.original_image.copy()
            
            # 应用亮度
            if self.brightness != 1.0:
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(self.brightness)
            
            # 应用对比度
            if self.contrast != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(self.contrast)
            
            # 应用饱和度
            if self.saturation != 1.0:
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(self.saturation)
            
            # 应用锐化
            if self.sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(self.sharpness)
            
            # 应用旋转
            if self.rotation_angle != 0:
                image = image.rotate(self.rotation_angle, expand=True)
            
            self.current_image = image
            self.update_display()
            
        except Exception as e:
            self.logger.error("Failed to apply adjustments: %s", str(e))
    
    def reset_adjustments(self):
        """重置调整"""
        self.brightness = 1.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0
        self.rotation_angle = 0
        
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.saturation_slider.setValue(100)
        self.sharpness_slider.setValue(100)
        
        self.apply_adjustments()
    
    def apply_crop(self):
        """应用裁剪"""
        # TODO: 实现裁剪功能
        pass
    
    def apply_filter(self, filter_name: str):
        """应用滤镜"""
        if not self.current_image:
            return
        
        try:
            image = self.current_image.copy()
            
            if filter_name == "黑白":
                image = image.convert("L").convert("RGB")
            elif filter_name == "复古":
                # 简单的复古效果
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(0.8)
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)
            elif filter_name == "冷色调":
                # 简单的冷色调效果
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(0.7)
            elif filter_name == "暖色调":
                # 简单的暖色调效果
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(1.3)
            elif filter_name == "模糊":
                image = image.filter(ImageFilter.BLUR)
            elif filter_name == "锐化":
                image = image.filter(ImageFilter.SHARPEN)
            
            self.current_image = image
            self.update_display()
            
        except Exception as e:
            self.logger.error("Failed to apply filter: %s", str(e))
    
    def rotate_image(self, angle: int):
        """旋转图片"""
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.apply_adjustments()
    
    def undo(self):
        """撤销操作"""
        # TODO: 实现撤销功能
        pass
    
    def redo(self):
        """重做操作"""
        # TODO: 实现重做功能
        pass
    
    def save_image(self):
        """保存图片"""
        if not self.current_image:
            return
        
        try:
            self.current_image.save(self.photo_path)
            QMessageBox.information(self, "成功", "图片保存成功！")
            self.accept()
        except Exception as e:
            self.logger.error("Failed to save image: %s", str(e))
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def save_as_image(self):
        """另存为图片"""
        if not self.current_image:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        
        if file_path:
            try:
                self.current_image.save(file_path)
                QMessageBox.information(self, "成功", "图片保存成功！")
            except Exception as e:
                self.logger.error("Failed to save image as: %s", str(e))
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}") 