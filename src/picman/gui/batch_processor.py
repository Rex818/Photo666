"""
Batch processing functionality for photos.
"""

from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QFileDialog, QProgressDialog,
    QMessageBox, QGroupBox, QFormLayout, QTabWidget, QWidget, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import logging

from ..core.image_processor import ImageProcessor
from ..core.photo_manager import PhotoManager
from ..config.manager import ConfigManager


class BatchWorker(QThread):
    """Worker thread for batch processing."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(dict)  # result
    error = pyqtSignal(str)
    
    def __init__(self, processor: ImageProcessor, operation: str, 
                photos: List[Dict[str, Any]], params: Dict[str, Any]):
        super().__init__()
        self.processor = processor
        self.operation = operation
        self.photos = photos
        self.params = params
    
    def run(self):
        """Run the batch operation."""
        try:
            total = len(self.photos)
            success_count = 0
            error_count = 0
            
            for i, photo in enumerate(self.photos):
                self.progress.emit(i + 1, total)
                
                try:
                    # Get file path
                    file_path = photo.get("filepath", "")
                    if not file_path or not Path(file_path).exists():
                        error_count += 1
                        continue
                    
                    # Generate output path
                    output_dir = self.params.get("output_dir", "data/processed")
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    
                    filename = Path(file_path).name
                    output_path = str(Path(output_dir) / filename)
                    
                    # Apply operation
                    result = False
                    
                    if self.operation == "resize":
                        width = self.params.get("width", 800)
                        height = self.params.get("height", 600)
                        maintain_aspect = self.params.get("maintain_aspect", True)
                        result = self.processor.resize_image(
                            file_path, output_path, (width, height), maintain_aspect
                        )
                    
                    elif self.operation == "rotate":
                        angle = self.params.get("angle", 0)
                        result = self.processor.rotate_image(file_path, output_path, angle)
                    
                    elif self.operation == "brightness":
                        factor = self.params.get("factor", 1.0)
                        result = self.processor.adjust_brightness(file_path, output_path, factor)
                    
                    elif self.operation == "contrast":
                        factor = self.params.get("factor", 1.0)
                        result = self.processor.adjust_contrast(file_path, output_path, factor)
                    
                    elif self.operation == "convert":
                        format_name = self.params.get("format", "JPEG")
                        quality = self.params.get("quality", 95)
                        
                        # Adjust output path for format change
                        output_path = str(Path(output_path).with_suffix(f".{format_name.lower()}"))
                        
                        result = self.processor.convert_format(
                            file_path, output_path, format_name, quality
                        )
                    
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
            
            result = {
                "success": True,
                "total": total,
                "success_count": success_count,
                "error_count": error_count
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class ResizeTab(QWidget):
    """Tab for resize operations."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Width
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(1280)
        form_layout.addRow("宽度:", self.width_spin)
        
        # Height
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(720)
        form_layout.addRow("高度:", self.height_spin)
        
        # Maintain aspect ratio
        self.maintain_aspect = QCheckBox("保持宽高比")
        self.maintain_aspect.setChecked(True)
        form_layout.addRow("", self.maintain_aspect)
        
        layout.addLayout(form_layout)
        layout.addStretch()
    
    def get_params(self) -> Dict[str, Any]:
        """Get parameters for the operation."""
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "maintain_aspect": self.maintain_aspect.isChecked()
        }


class RotateTab(QWidget):
    """Tab for rotate operations."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Angle
        self.angle_combo = QComboBox()
        self.angle_combo.addItems(["顺时针90°", "180°", "逆时针90°", "自定义"])
        self.angle_combo.currentIndexChanged.connect(self.on_angle_changed)
        form_layout.addRow("旋转:", self.angle_combo)
        
        # Custom angle
        self.custom_angle = QSpinBox()
        self.custom_angle.setRange(-360, 360)
        self.custom_angle.setValue(0)
        self.custom_angle.setEnabled(False)
        form_layout.addRow("自定义角度:", self.custom_angle)
        
        layout.addLayout(form_layout)
        layout.addStretch()
    
    def on_angle_changed(self, index):
        """Handle angle selection change."""
        self.custom_angle.setEnabled(index == 3)  # Enable for "Custom"
    
    def get_params(self) -> Dict[str, Any]:
        """Get parameters for the operation."""
        angle = 0
        if self.angle_combo.currentIndex() == 0:
            angle = -90  # 90° Clockwise
        elif self.angle_combo.currentIndex() == 1:
            angle = 180  # 180°
        elif self.angle_combo.currentIndex() == 2:
            angle = 90  # 90° Counter-clockwise
        else:
            angle = self.custom_angle.value()
        
        return {"angle": angle}


class AdjustTab(QWidget):
    """Tab for brightness/contrast adjustments."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Brightness factor
        self.brightness_factor = QDoubleSpinBox()
        self.brightness_factor.setRange(0.1, 3.0)
        self.brightness_factor.setValue(1.0)
        self.brightness_factor.setSingleStep(0.1)
        form_layout.addRow("亮度因子:", self.brightness_factor)
        
        # Contrast factor
        self.contrast_factor = QDoubleSpinBox()
        self.contrast_factor.setRange(0.1, 3.0)
        self.contrast_factor.setValue(1.0)
        self.contrast_factor.setSingleStep(0.1)
        form_layout.addRow("对比度因子:", self.contrast_factor)
        
        layout.addLayout(form_layout)
        layout.addStretch()
    
    def get_params(self) -> Dict[str, Any]:
        """Get parameters for the operation."""
        return {
            "brightness_factor": self.brightness_factor.value(),
            "contrast_factor": self.contrast_factor.value()
        }


class ConvertTab(QWidget):
    """Tab for format conversion."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "BMP", "TIFF", "WEBP"])
        form_layout.addRow("格式:", self.format_combo)
        
        # Quality
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        form_layout.addRow("质量:", self.quality_spin)
        
        layout.addLayout(form_layout)
        layout.addStretch()
    
    def get_params(self) -> Dict[str, Any]:
        """Get parameters for the operation."""
        return {
            "format": self.format_combo.currentText(),
            "quality": self.quality_spin.value()
        }


class BatchProcessorDialog(QDialog):
    """Dialog for batch processing photos."""
    
    def __init__(self, config_manager: ConfigManager, 
                photo_manager: PhotoManager, 
                image_processor: ImageProcessor,
                selected_photos: List[Dict[str, Any]] = None,
                parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.photo_manager = photo_manager
        self.image_processor = image_processor
        self.selected_photos = selected_photos or []
        # 配置标准logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("picman.gui.batch_processor")
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("批量处理器")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Operation selection
        operation_group = QGroupBox("操作类型")
        operation_layout = QVBoxLayout(operation_group)
        
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            "调整大小",
            "旋转",
            "亮度调整",
            "对比度调整",
            "格式转换"
        ])
        self.operation_combo.currentIndexChanged.connect(self.on_operation_changed)
        operation_layout.addWidget(self.operation_combo)
        
        layout.addWidget(operation_group)
        
        # Operation parameters
        self.param_tabs = QTabWidget()
        
        self.resize_tab = ResizeTab()
        self.rotate_tab = RotateTab()
        self.adjust_tab = AdjustTab()
        self.convert_tab = ConvertTab()
        
        self.param_tabs.addTab(self.resize_tab, "调整大小")
        self.param_tabs.addTab(self.rotate_tab, "旋转")
        self.param_tabs.addTab(self.adjust_tab, "调整")
        self.param_tabs.addTab(self.convert_tab, "转换")
        
        layout.addWidget(self.param_tabs)
        
        # Output directory
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)
        
        self.output_dir = QLineEdit()
        self.output_dir.setText("data/processed")
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_dir)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir)
        dir_layout.addWidget(browse_btn)
        
        output_layout.addRow("输出目录:", dir_layout)
        
        layout.addWidget(output_group)
        
        # Photo list
        photo_group = QGroupBox(f"选中的照片 ({len(self.selected_photos)})")
        photo_layout = QVBoxLayout(photo_group)
        
        self.photo_list = QListWidget()
        for photo in self.selected_photos:
            filename = Path(photo.get("filepath", "")).name
            item = QListWidgetItem(filename)
            self.photo_list.addItem(item)
        
        photo_layout.addWidget(self.photo_list)
        
        layout.addWidget(photo_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setDefault(True)
        button_layout.addWidget(self.process_btn)
        
        layout.addLayout(button_layout)
    
    def on_operation_changed(self, index):
        """Handle operation selection change."""
        self.param_tabs.setCurrentIndex(index)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir.text()
        )
        if directory:
            self.output_dir.setText(directory)
    
    def get_operation_params(self) -> Dict[str, Any]:
        """Get parameters for the selected operation."""
        params = {
            "output_dir": self.output_dir.text()
        }
        
        operation = self.operation_combo.currentIndex()
        
        if operation == 0:  # Resize
            params.update(self.resize_tab.get_params())
        elif operation == 1:  # Rotate
            params.update(self.rotate_tab.get_params())
        elif operation == 2:  # Brightness
            params.update(self.adjust_tab.get_params())
            params["operation"] = "brightness"
        elif operation == 3:  # Contrast
            params.update(self.adjust_tab.get_params())
            params["operation"] = "contrast"
        elif operation == 4:  # Convert
            params.update(self.convert_tab.get_params())
        
        return params
    
    def get_operation_name(self) -> str:
        """Get the name of the selected operation."""
        operations = [
            "resize",
            "rotate", 
            "brightness",
            "contrast",
            "convert"
        ]
        return operations[self.operation_combo.currentIndex()]
    
    def start_processing(self):
        """Start the batch processing operation."""
        if not self.selected_photos:
            QMessageBox.warning(self, "无照片", "未选择照片进行处理。")
            return
        
        # Get operation parameters
        operation = self.get_operation_name()
        params = self.get_operation_params()
        
        # Create and start worker
        self.batch_worker = BatchWorker(
            self.image_processor, operation, self.selected_photos, params
        )
        
        # Create progress dialog
        progress = QProgressDialog("正在处理照片...", "取消", 0, len(self.selected_photos), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Connect signals
        self.batch_worker.progress.connect(progress.setValue)
        self.batch_worker.finished.connect(lambda result: self.on_processing_finished(result, progress))
        self.batch_worker.error.connect(lambda error: self.on_processing_error(error, progress))
        
        # Start processing
        self.batch_worker.start()
        progress.show()
    
    def on_processing_finished(self, result: dict, progress: QProgressDialog):
        """Handle processing completion."""
        progress.close()
        
        if result.get("success", False):
            message = f"处理完成！\n成功: {result['success_count']}\n错误: {result['error_count']}"
            QMessageBox.information(self, "处理完成", message)
        else:
            QMessageBox.critical(self, "处理错误", "批量处理失败。")
    
    def on_processing_error(self, error: str, progress: QProgressDialog):
        """Handle processing error."""
        progress.close()
        QMessageBox.critical(self, "处理错误", f"处理过程中发生错误: {error}")