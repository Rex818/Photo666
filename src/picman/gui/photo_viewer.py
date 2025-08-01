"""
Photo viewer widget for displaying individual photos.
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QSpinBox,
    QCheckBox, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QFont, QTransform
from PyQt6.QtWidgets import QApplication
import structlog


class PhotoViewer(QWidget):
    """Widget for viewing and editing individual photos."""
    
    photo_updated = pyqtSignal(int)  # photo_id
    previous_photo_requested = pyqtSignal()  # 请求上一张图片
    next_photo_requested = pyqtSignal()  # 请求下一张图片
    
    def __init__(self, plugin_manager=None):
        super().__init__()
        self.current_photo = None
        self.current_pixmap = None
        self.original_pixmap = None
        self.logger = structlog.get_logger("picman.gui.photo_viewer")
        self.plugin_manager = plugin_manager
        
        # Zoom and rotation settings
        self.zoom_factor = 1.0
        self.rotation_angle = 0  # 用户旋转角度（相对于当前显示状态）
        self.is_fullscreen = False
        
        # 鼠标拖动浏览相关变量
        self.is_dragging = False
        self.drag_start_pos = None
        self.scroll_offset = QPoint(0, 0)  # 滚动偏移量
        
        # 初始化旋转角度显示
        self.update_rotation_label()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Image display area (4区上方 - 图片显示)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setText("未选择照片")
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area, 1)
        
        # Toolbar for image controls (4区下方 - 图片控制工具栏)
        toolbar_layout = QHBoxLayout()
        
        # Zoom controls - 进一步缩小按钮尺寸
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setToolTip("缩小")
        zoom_out_btn.setFixedWidth(20)  # 进一步缩小宽度
        zoom_out_btn.setFixedHeight(25)  # 固定高度
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setFixedWidth(35)  # 进一步缩小宽度
        toolbar_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setToolTip("放大")
        zoom_in_btn.setFixedWidth(20)  # 进一步缩小宽度
        zoom_in_btn.setFixedHeight(25)  # 固定高度
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(zoom_in_btn)
        
        fit_btn = QPushButton("适应窗口")
        fit_btn.setToolTip("适应窗口大小")
        fit_btn.setFixedWidth(50)  # 进一步缩小宽度
        fit_btn.setFixedHeight(25)  # 固定高度
        fit_btn.clicked.connect(self.fit_to_window)
        toolbar_layout.addWidget(fit_btn)
        
        toolbar_layout.addStretch()
        
        # 添加分隔符确保空间
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; margin: 0 5px;")
        toolbar_layout.addWidget(separator)
        
        # Rotation controls - 3个旋转按钮：左90°、右90°、180°
        # 直接在主工具栏中添加旋转按钮，不使用容器
        
        # 1. 逆时针90度旋转按钮（向左）
        rotate_left_btn = QPushButton("↺")
        rotate_left_btn.setToolTip("逆时针旋转90度")
        rotate_left_btn.setFixedSize(35, 30)  # 固定尺寸
        rotate_left_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #999;
                border-radius: 5px;
                background-color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        rotate_left_btn.clicked.connect(self.rotate_left)
        toolbar_layout.addWidget(rotate_left_btn)
        
        # 添加间距
        toolbar_layout.addSpacing(5)
        
        # 2. 顺时针90度旋转按钮（向右）
        rotate_right_btn = QPushButton("↻")
        rotate_right_btn.setToolTip("顺时针旋转90度")
        rotate_right_btn.setFixedSize(35, 30)  # 固定尺寸
        rotate_right_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #999;
                border-radius: 5px;
                background-color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        rotate_right_btn.clicked.connect(self.rotate_right)
        toolbar_layout.addWidget(rotate_right_btn)
        
        # 添加间距
        toolbar_layout.addSpacing(5)
        
        # 3. 旋转180度按钮
        rotate_180_btn = QPushButton("↻↻")
        rotate_180_btn.setToolTip("旋转180度")
        rotate_180_btn.setFixedSize(40, 30)  # 固定尺寸
        rotate_180_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #999;
                border-radius: 5px;
                background-color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        rotate_180_btn.clicked.connect(self.rotate_180)
        toolbar_layout.addWidget(rotate_180_btn)
        
        # 旋转角度显示
        self.rotation_label = QLabel("0°")
        self.rotation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotation_label.setFixedWidth(40)
        self.rotation_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f8f8f8;
                padding: 2px;
                font-size: 12px;
            }
        """)
        toolbar_layout.addWidget(self.rotation_label)
        
        # Save rotation button
        self.save_rotation_btn = QPushButton("保存旋转")
        self.save_rotation_btn.setToolTip("保存旋转后的图片")
        self.save_rotation_btn.clicked.connect(self.save_rotated_image)
        self.save_rotation_btn.setEnabled(False)  # 初始禁用
        toolbar_layout.addWidget(self.save_rotation_btn)
        
        # Edit button
        edit_btn = QPushButton("编辑")
        edit_btn.setToolTip("打开照片编辑器")
        edit_btn.clicked.connect(self.open_photo_editor)
        toolbar_layout.addWidget(edit_btn)
        
        toolbar_layout.addStretch()
        
        # Navigation controls
        prev_btn = QPushButton("◀")
        prev_btn.setToolTip("上一张图片")
        prev_btn.clicked.connect(self.show_previous_photo)
        toolbar_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("▶")
        next_btn.setToolTip("下一张图片")
        next_btn.clicked.connect(self.show_next_photo)
        toolbar_layout.addWidget(next_btn)
        
        toolbar_layout.addStretch()
        
        # Fullscreen button
        fullscreen_btn = QPushButton("⛶")
        fullscreen_btn.setToolTip("切换全屏")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        toolbar_layout.addWidget(fullscreen_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Photo information and controls
        self.info_panel = self.create_info_panel()
        layout.addWidget(self.info_panel)
        
        # Install event filter for mouse wheel zoom
        self.scroll_area.viewport().installEventFilter(self)
    
    def create_info_panel(self) -> QWidget:
        """Create the photo information and controls panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        # 不再限制最大高度，让QScrollArea自适应
        layout = QHBoxLayout(panel)
        
        # 5区 - 基本信息 (左侧) - 调整宽度和行间距
        basic_info_group = QGroupBox("基本信息")
        basic_info_group.setFixedWidth(220)  # 固定宽度
        basic_info_layout = QVBoxLayout(basic_info_group)
        basic_info_layout.setSpacing(2)  # 缩小行间距
        basic_info_layout.setContentsMargins(5, 5, 5, 5)  # 缩小边距
        
        # 基本信息
        self.filename_label = QLabel("文件名: -")
        self.filename_label.setWordWrap(True)
        basic_info_layout.addWidget(self.filename_label)
        
        self.size_label = QLabel("文件大小: -")
        basic_info_layout.addWidget(self.size_label)
        
        self.dimensions_label = QLabel("分辨率: -")
        basic_info_layout.addWidget(self.dimensions_label)
        
        self.format_label = QLabel("格式: -")
        basic_info_layout.addWidget(self.format_label)
        
        self.date_taken_label = QLabel("拍摄日期: -")
        basic_info_layout.addWidget(self.date_taken_label)
        
        self.date_added_label = QLabel("添加日期: -")
        basic_info_layout.addWidget(self.date_added_label)
        
        # 文件路径（可点击）
        self.filepath_label = QLabel("文件路径: -")
        self.filepath_label.setWordWrap(True)
        self.filepath_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.filepath_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filepath_label.mousePressEvent = self.open_file_location
        basic_info_layout.addWidget(self.filepath_label)
        
        layout.addWidget(basic_info_group)
        
        # 6区 - 补充信息 (中间) - 调整宽度和行间距
        # 用滚动区域包裹补充信息分组
        detailed_info_group = QGroupBox("补充信息")
        detailed_info_group.setMinimumWidth(320)
        detailed_info_layout = QVBoxLayout(detailed_info_group)
        detailed_info_layout.setSpacing(2)
        detailed_info_layout.setContentsMargins(5, 5, 5, 5)
        
        # 相机信息
        self.camera_make_label = QLabel("相机品牌: -")
        detailed_info_layout.addWidget(self.camera_make_label)
        
        self.camera_model_label = QLabel("相机型号: -")
        detailed_info_layout.addWidget(self.camera_model_label)
        
        self.lens_label = QLabel("镜头: -")
        detailed_info_layout.addWidget(self.lens_label)
        
        # 拍摄参数
        self.focal_length_label = QLabel("焦距: -")
        detailed_info_layout.addWidget(self.focal_length_label)
        
        self.aperture_label = QLabel("光圈: -")
        detailed_info_layout.addWidget(self.aperture_label)
        
        self.shutter_speed_label = QLabel("快门速度: -")
        detailed_info_layout.addWidget(self.shutter_speed_label)
        
        self.iso_label = QLabel("ISO: -")
        detailed_info_layout.addWidget(self.iso_label)
        
        # 恢复并优化GPS信息显示
        self.gps_latitude_label = QLabel("纬度: -")
        detailed_info_layout.addWidget(self.gps_latitude_label)
        self.gps_longitude_label = QLabel("经度: -")
        detailed_info_layout.addWidget(self.gps_longitude_label)
        self.gps_altitude_label = QLabel("高度: -")
        detailed_info_layout.addWidget(self.gps_altitude_label)
        self.gps_label = QLabel("GPS坐标: -")
        detailed_info_layout.addWidget(self.gps_label)
        self.location_label = QLabel("地理位置: -")
        detailed_info_layout.addWidget(self.location_label)
        # 刷新地理位置按钮（上下排列）
        self.refresh_location_btn = QPushButton("刷新当前图片地理位置")
        self.refresh_location_btn.setToolTip("重新查询并刷新当前图片地理位置信息")
        self.refresh_location_btn.clicked.connect(self.refresh_location)
        detailed_info_layout.addWidget(self.refresh_location_btn)
        self.refresh_all_location_btn = QPushButton("刷新全部图片地理位置")
        self.refresh_all_location_btn.setToolTip("批量刷新所有图片的地理位置信息")
        self.refresh_all_location_btn.clicked.connect(self.refresh_all_locations)
        detailed_info_layout.addWidget(self.refresh_all_location_btn)
        
        # 其他EXIF信息
        self.flash_label = QLabel("闪光灯: -")
        detailed_info_layout.addWidget(self.flash_label)
        
        self.white_balance_label = QLabel("白平衡: -")
        detailed_info_layout.addWidget(self.white_balance_label)
        
        self.exposure_mode_label = QLabel("曝光模式: -")
        detailed_info_layout.addWidget(self.exposure_mode_label)
        
        layout.addWidget(detailed_info_group)
        
        # 添加间距
        layout.addSpacing(10)
        
        # 评分和收藏 (右侧) - 设置最小宽度
        rating_group = QGroupBox("评分与收藏")
        rating_group.setFixedWidth(200)  # 固定宽度
        rating_layout = QVBoxLayout(rating_group)
        rating_layout.setSpacing(2)  # 缩小行间距
        rating_layout.setContentsMargins(5, 5, 5, 5)  # 缩小边距
        
        # Rating
        rating_row = QHBoxLayout()
        rating_row.addWidget(QLabel("评分:"))
        
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(0, 5)
        self.rating_spinbox.setSuffix(" 星")
        self.rating_spinbox.valueChanged.connect(self.update_rating)
        rating_row.addWidget(self.rating_spinbox)
        
        rating_layout.addLayout(rating_row)
        
        # Favorite checkbox
        self.favorite_checkbox = QCheckBox("收藏")
        self.favorite_checkbox.stateChanged.connect(self.toggle_favorite)
        rating_layout.addWidget(self.favorite_checkbox)
        
        # 分类标签显示
        self.category_tags_label = QLabel("分类标签: 无")
        self.category_tags_label.setWordWrap(True)
        rating_layout.addWidget(self.category_tags_label)
        
        # 分类标签编辑按钮
        self.edit_category_tags_btn = QPushButton("编辑分类标签")
        self.edit_category_tags_btn.clicked.connect(self.edit_category_tags)
        rating_layout.addWidget(self.edit_category_tags_btn)
        
        # 备注
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText("添加照片备注...")
        self.notes_text.textChanged.connect(self.update_notes)
        rating_layout.addWidget(self.notes_text)
        
        layout.addWidget(rating_group)
        
        return panel
    
    def display_photo(self, photo_data: dict):
        """显示照片大图和详细信息。"""
        # 检查是否是同一张照片，如果是则跳过重新加载
        if (self.current_photo and 
            self.current_photo.get("filepath") == photo_data.get("filepath") and
            self.original_pixmap and not self.original_pixmap.isNull()):
            # 同一张照片，只更新信息面板
            self.current_photo = photo_data
            self.logger.info("同一张照片，跳过重新加载", path=photo_data.get("filepath"))
            # 更新信息面板
            self.update_info_panel()
            return
        
        # 新照片，重新加载
        self.current_photo = photo_data
        self.zoom_factor = 1.0
        # 不重置旋转角度，保持用户的旋转设置
        # self.rotation_angle = 0  # 注释掉这行，保持旋转角度
        self.update_zoom_label()
        self.update_rotation_label()

        # 尝试显示原图
        file_path = photo_data.get("filepath")
        original_found = False
        
        if file_path and Path(file_path).exists():
            # 加载并处理EXIF方向的图片
            pixmap = self.load_image_with_exif_orientation(file_path)
            if not pixmap.isNull():
                self.original_pixmap = pixmap
                self.current_pixmap = pixmap
                self.image_label.setPixmap(self.scale_pixmap(pixmap))
                self.image_label.setText("")
                original_found = True
                self.logger.info("Original image displayed with EXIF orientation", path=file_path)
        
        # 如果原图不存在，尝试显示缩略图
        if not original_found:
            thumbnail_path = photo_data.get("thumbnail_path", "")
            if thumbnail_path and Path(thumbnail_path).exists():
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    # 放大缩略图以更好地显示
                    scaled_pixmap = pixmap.scaled(
                        800, 600,  # 更大的显示尺寸
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.original_pixmap = scaled_pixmap
                    self.current_pixmap = scaled_pixmap
                    self.image_label.setPixmap(scaled_pixmap)
                    
                    # 显示提示信息
                    self.image_label.setStyleSheet("border: 2px solid orange;")
                    self.logger.warning("Original image not found, displaying thumbnail", 
                                      photo_id=photo_data.get('id'))
                else:
                    self.image_label.setText("原图查找不到\n缩略图也无法加载")
                    self.image_label.setStyleSheet("border: 2px solid red; color: red; font-size: 16px;")
                    self.original_pixmap = None
                    self.current_pixmap = None
            else:
                self.image_label.setText("原图查找不到\n缩略图文件不存在")
                self.image_label.setStyleSheet("border: 2px solid red; color: red; font-size: 16px;")
                self.original_pixmap = None
                self.current_pixmap = None

        # 更新信息面板
        self.filename_label.setText(f"文件名: {photo_data.get('filename', '-')}")
        self.size_label.setText(f"文件大小: {self.format_file_size(photo_data.get('file_size', 0))}")
        self.dimensions_label.setText(f"分辨率: {photo_data.get('width', 0)} x {photo_data.get('height', 0)}")
        self.date_taken_label.setText(f"拍摄日期: {photo_data.get('date_taken', '-')}")
        self.format_label.setText(f"格式: {photo_data.get('format', '-')}")
        self.date_added_label.setText(f"添加日期: {photo_data.get('date_added', '-')}")
        self.filepath_label.setText(f"文件路径: {photo_data.get('filepath', '-')}")
        self.rating_spinbox.setValue(photo_data.get('rating', 0))
        self.favorite_checkbox.setChecked(photo_data.get('is_favorite', False))
        self.notes_text.setText(photo_data.get('notes', ''))
        
        # 更新详细信息面板
        self.update_detailed_info_panel(photo_data)
        
        # 更新标签显示
        self.update_tags_display(photo_data)
        
        # 如果原图不存在，在信息面板中显示提示
        if not original_found:
            self.filename_label.setText(f"文件名: {photo_data.get('filename', '-')} (原图已删除)")
            self.filename_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.filename_label.setStyleSheet("")
    
    def display_photo_info_only(self, photo_data: dict):
        """显示照片信息但不显示图片（当原图不存在时）。"""
        self.current_photo = photo_data
        self.zoom_factor = 1.0
        # 不重置旋转角度，保持用户的旋转设置
        # self.rotation_angle = 0  # 注释掉这行，保持旋转角度
        self.update_zoom_label()

        # 显示占位符
        self.image_label.setText("原图文件不存在\n仅显示照片信息")
        self.original_pixmap = None
        self.current_pixmap = None

        # 更新信息面板
        self.filename_label.setText(f"文件名: {photo_data.get('filename', '-')}")
        self.size_label.setText(f"文件大小: {self.format_file_size(photo_data.get('file_size', 0))}")
        self.dimensions_label.setText(f"分辨率: {photo_data.get('width', 0)} x {photo_data.get('height', 0)}")
        self.date_taken_label.setText(f"拍摄日期: {photo_data.get('date_taken', '-')}")
        self.format_label.setText(f"格式: {photo_data.get('format', '-')}")
        self.date_added_label.setText(f"添加日期: {photo_data.get('date_added', '-')}")
        self.filepath_label.setText(f"文件路径: {photo_data.get('filepath', '-')}")
        self.rating_spinbox.setValue(photo_data.get('rating', 0))
        self.favorite_checkbox.setChecked(photo_data.get('is_favorite', False))
        self.notes_text.setText(photo_data.get('notes', ''))
        
        # 更新详细信息面板
        self.update_detailed_info_panel(photo_data)
        
        # 更新标签显示
        self.update_tags_display(photo_data)
        
        self.logger.info("Displayed photo info only", photo_id=photo_data.get('id'))
    
    def display_photo_by_path(self, file_path: str):
        """Display a photo by file path."""
        try:
            path = Path(file_path)
            if not path.exists():
                self.image_label.setText("File not found")
                return
            
            # Load image
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self.image_label.setText("Cannot load image")
                return
            
            # Store original pixmap
            self.original_pixmap = pixmap
            self.current_pixmap = pixmap
            
            # Reset zoom but keep rotation
            self.zoom_factor = 1.0
            # self.rotation_angle = 0  # 注释掉这行，保持旋转角度
            self.update_zoom_label()
            
            # Scale image to fit display
            scaled_pixmap = self.scale_pixmap(pixmap)
            self.image_label.setPixmap(scaled_pixmap)
            
            # Update current photo info
            self.current_photo = {
                "filepath": str(path),
                "filename": path.name,
                "width": pixmap.width(),
                "height": pixmap.height(),
                "format": path.suffix.upper()[1:] if path.suffix else "Unknown"
            }
            
            self.update_info_panel()
            
        except Exception as e:
            self.logger.error("Failed to display photo", path=file_path, error=str(e))
            self.image_label.setText("Error loading image")
    
    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """Scale pixmap based on zoom factor and rotation."""
        if pixmap.isNull():
            return pixmap
        
        # 注意：旋转现在由apply_rotation方法处理，这里不再处理旋转
        # 避免双重旋转问题
        
        # Get available size
        available_size = self.scroll_area.size()
        max_width = available_size.width() - 20
        max_height = available_size.height() - 20
        
        # Calculate target size based on zoom factor
        if self.zoom_factor == 1.0:
            # Fit to window
            target_width = max_width
            target_height = max_height
            keep_aspect_ratio = True
        else:
            # Apply zoom
            target_width = int(pixmap.width() * self.zoom_factor)
            target_height = int(pixmap.height() * self.zoom_factor)
            keep_aspect_ratio = False
        
        # Scale the image
        if keep_aspect_ratio:
            scaled = pixmap.scaled(
                target_width, target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            scaled = pixmap.scaled(
                target_width, target_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        return scaled
    
    def open_file_location(self, event):
        """Open file location in file explorer."""
        if self.current_photo and self.current_photo.get("filepath"):
            file_path = Path(self.current_photo["filepath"])
            if file_path.exists():
                import subprocess
                import platform
                
                try:
                    if platform.system() == "Windows":
                        subprocess.run(["explorer", "/select,", str(file_path)])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", "-R", str(file_path)])
                    else:  # Linux
                        subprocess.run(["xdg-open", str(file_path.parent)])
                except Exception as e:
                    self.logger.error("Failed to open file location", error=str(e))

    def update_info_panel(self):
        """Update the photo information panel."""
        if not self.current_photo:
            self.filename_label.setText("文件名: -")
            self.size_label.setText("文件大小: -")
            self.dimensions_label.setText("分辨率: -")
            self.date_taken_label.setText("拍摄日期: -")
            self.format_label.setText("格式: -")
            self.date_added_label.setText("添加日期: -")
            self.filepath_label.setText("文件路径: -")
            self.category_tags_label.setText("分类标签: 无")
            # 清空详细信息面板
            self.update_detailed_info_panel({})
            return
        
        # Update labels
        filename = self.current_photo.get("filename", "Unknown")
        self.filename_label.setText(f"文件名: {filename}")
        
        # 格式化文件大小
        file_size = self.current_photo.get("file_size", 0)
        if file_size > 0:
            size_str = self.format_file_size(file_size)
            self.size_label.setText(f"文件大小: {size_str}")
        else:
            self.size_label.setText("文件大小: 未知")
        
        # 分辨率信息
        width = self.current_photo.get("width", 0)
        height = self.current_photo.get("height", 0)
        if width > 0 and height > 0:
            self.dimensions_label.setText(f"分辨率: {width} × {height}")
        else:
            self.dimensions_label.setText("分辨率: 未知")
        
        # 日期信息
        date_taken = self.current_photo.get("date_taken", "")
        if date_taken:
            # 格式化日期显示
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_taken.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%Y年%m月%d日 %H:%M:%S")
                self.date_taken_label.setText(f"拍摄日期: {formatted_date}")
            except:
                self.date_taken_label.setText(f"拍摄日期: {date_taken}")
        else:
            self.date_taken_label.setText("拍摄日期: 未知")
        
        date_added = self.current_photo.get("date_added", "")
        if date_added:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%Y年%m月%d日 %H:%M:%S")
                self.date_added_label.setText(f"添加日期: {formatted_date}")
            except:
                self.date_added_label.setText(f"添加日期: {date_added}")
        else:
            self.date_added_label.setText("添加日期: 未知")
        
        format_info = self.current_photo.get("format", "Unknown")
        self.format_label.setText(f"格式: {format_info.upper() if format_info else '未知'}")
        
        filepath = self.current_photo.get("filepath", "")
        if filepath:
            # 缩短路径显示
            path = Path(filepath)
            if len(str(path)) > 50:
                display_path = f"...{str(path)[-47:]}"
            else:
                display_path = str(path)
            self.filepath_label.setText(f"文件路径: {display_path}")
        else:
            self.filepath_label.setText("文件路径: 未知")
        
        # 标签信息
        tags = self.current_photo.get("tags", [])
        if tags and len(tags) > 0:
            tags_text = ", ".join(tags[:5])  # 最多显示5个标签
            if len(tags) > 5:
                tags_text += f" 等{len(tags)}个标签"
            self.category_tags_label.setText(f"分类标签: {tags_text}")
        else:
            self.category_tags_label.setText("分类标签: 无")
        
        # 更新详细信息面板
        self.update_detailed_info_panel(self.current_photo)
        
        # Update rating and favorite
        self.rating_spinbox.setValue(self.current_photo.get("rating", 0))
        self.favorite_checkbox.setChecked(self.current_photo.get("is_favorite", False))
        
        # Update notes
        notes = self.current_photo.get("notes", "")
        if self.notes_text.toPlainText() != notes:
            self.notes_text.setPlainText(notes)
    
    def update_rating(self, rating: int):
        """Update photo rating."""
        if self.current_photo and "id" in self.current_photo:
            # In a real implementation, update the database
            self.current_photo["rating"] = rating
            self.photo_updated.emit(self.current_photo["id"])
    
    def toggle_favorite(self, state: int):
        """Toggle photo favorite status."""
        if self.current_photo and "id" in self.current_photo:
            # In a real implementation, update the database
            is_favorite = state == Qt.CheckState.Checked.value
            self.current_photo["is_favorite"] = is_favorite
            self.photo_updated.emit(self.current_photo["id"])
    
    def update_notes(self):
        """Update photo notes."""
        if self.current_photo and self.current_photo.get("id"):
            notes = self.notes_text.toPlainText()
            
            # 更新内存中的数据
            self.current_photo["notes"] = notes
            
            # 更新数据库
            try:
                # 获取主窗口的photo_manager
                main_window = self.window()
                if main_window and hasattr(main_window, 'photo_manager'):
                    # 使用photo_manager更新数据库
                    success = main_window.photo_manager.db.update_photo(
                        self.current_photo['id'], 
                        {"notes": notes}
                    )
                    if success:
                        self.logger.info("Notes saved to database", 
                                       photo_id=self.current_photo.get('id'), 
                                       notes_length=len(notes))
                        # 发送更新信号
                        self.photo_updated.emit(self.current_photo["id"])
                    else:
                        self.logger.error("Failed to save notes to database", 
                                        photo_id=self.current_photo.get('id'))
                else:
                    self.logger.error("Photo manager not available")
            except Exception as e:
                self.logger.error("Failed to save notes", error=str(e))
    
    def zoom_in(self):
        """Zoom in on the image."""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        self.zoom_factor *= 1.25
        self.update_zoom_label()
        self.update_display()
    
    def zoom_out(self):
        """Zoom out from the image."""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        self.zoom_factor /= 1.25
        self.update_zoom_label()
        self.update_display()
    
    def fit_to_window(self):
        """Fit image to window size."""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        self.zoom_factor = 1.0
        self.update_zoom_label()
        self.update_display()
    
    def update_zoom_label(self):
        """Update the zoom percentage label."""
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_label.setText(f"{zoom_percent}%")
    
    def update_rotation_label(self):
        """Update the rotation angle label."""
        if hasattr(self, 'rotation_label'):
            self.rotation_label.setText(f"{self.rotation_angle}°")
    
    def apply_rotation(self):
        """应用旋转 - 使用Qt的QTransform方法
        
        关键逻辑：
        1. 从已经处理过EXIF的原图开始
        2. 直接应用用户旋转角度
        3. 使用Qt的QTransform进行旋转，更可靠
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        
        try:
            # 使用Qt的QTransform进行旋转
            if self.rotation_angle != 0:
                transform = QTransform().rotate(self.rotation_angle)
                rotated = self.original_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                self.current_pixmap = rotated
                self.logger.info("应用用户旋转", 
                               rotation_angle=self.rotation_angle,
                               original_size=f"{self.original_pixmap.width()}x{self.original_pixmap.height()}",
                               rotated_size=f"{rotated.width()}x{rotated.height()}")
            else:
                self.current_pixmap = self.original_pixmap
                self.logger.info("无旋转，使用原图")
            
            # 应用缩放并显示
            self.apply_zoom_and_display()
            
        except Exception as e:
            self.logger.error("应用旋转失败", error=str(e))
            # 如果失败，回退到原来的方法
            self.fallback_rotation_display()
    
    def fallback_rotation_display(self):
        """回退的旋转显示方法（当apply_rotation失败时使用）"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        
        # 使用Qt的QTransform进行旋转
        if self.rotation_angle != 0:
            transform = QTransform().rotate(self.rotation_angle)
            rotated = self.original_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
            self.current_pixmap = rotated
            self.logger.info("使用回退方法应用旋转", 
                            rotation_angle=self.rotation_angle,
                            rotated_size=f"{rotated.width()}x{rotated.height()}")
        else:
            self.current_pixmap = self.original_pixmap
            self.logger.info("使用回退方法，无旋转")
        
        # 应用缩放并显示
        self.apply_zoom_and_display()
    
    def rotate_left(self):
        """Rotate image 90 degrees counter-clockwise (逆时针).
        
        参照照片编辑器的实现：直接累加角度，从原图重新应用旋转
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.logger.warning("无法旋转：没有有效的图片")
            return
        
        old_angle = self.rotation_angle
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.logger.info("逆时针旋转90度", old_angle=old_angle, new_angle=self.rotation_angle)
        self.apply_rotation()
        self.update_rotation_label()
        # 启用保存按钮
        self.save_rotation_btn.setEnabled(True)
    
    def rotate_right(self):
        """Rotate image 90 degrees clockwise (顺时针).
        
        参照照片编辑器的实现：直接累加角度，从原图重新应用旋转
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.logger.warning("无法旋转：没有有效的图片")
            return
        
        old_angle = self.rotation_angle
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.logger.info("顺时针旋转90度", old_angle=old_angle, new_angle=self.rotation_angle)
        self.apply_rotation()
        self.update_rotation_label()
        # 启用保存按钮
        self.save_rotation_btn.setEnabled(True)
    
    def rotate_180(self):
        """Rotate image by 180 degrees.
        
        参照照片编辑器的实现：直接累加角度，从原图重新应用旋转
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.logger.warning("无法旋转：没有有效的图片")
            return
        
        old_angle = self.rotation_angle
        self.rotation_angle = (self.rotation_angle + 180) % 360
        self.logger.info("旋转180度", old_angle=old_angle, new_angle=self.rotation_angle)
        self.apply_rotation()
        self.update_rotation_label()
        # 启用保存按钮
        self.save_rotation_btn.setEnabled(True)
    

    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.is_fullscreen:
            # Exit fullscreen
            self.is_fullscreen = False
            self.info_panel.setVisible(True)
            self.parentWidget().showNormal()
        else:
            # Enter fullscreen
            self.is_fullscreen = True
            self.info_panel.setVisible(False)
            self.parentWidget().showFullScreen()
    
    def update_display(self):
        """Update the displayed image with current zoom and rotation.
        
        简化版本：旋转由apply_rotation方法处理，这里只处理缩放
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.logger.warning("无法更新显示：没有有效的图片")
            return
        
        self.logger.info("开始更新显示", 
                        rotation_angle=self.rotation_angle,
                        original_size=f"{self.original_pixmap.width()}x{self.original_pixmap.height()}")
        
        # 应用旋转（如果有的话）
        if self.rotation_angle != 0:
            self.apply_rotation()
        else:
            # 无旋转，直接使用原图
            self.current_pixmap = self.original_pixmap
            self.logger.info("无用户旋转，使用已处理EXIF的图片")
            
            # 应用缩放并显示
            self.apply_zoom_and_display()
    
    def apply_zoom_and_display(self):
        """应用缩放并显示图片"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        if self.zoom_factor != 1.0:
            # Calculate new size
            new_width = int(self.current_pixmap.width() * self.zoom_factor)
            new_height = int(self.current_pixmap.height() * self.zoom_factor)
            
            # Scale pixmap
            scaled = self.current_pixmap.scaled(
                new_width, new_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled)
        else:
            # Fit to window
            scaled = self.scale_pixmap(self.current_pixmap)
            self.image_label.setPixmap(scaled)
    
    def eventFilter(self, obj, event):
        """Handle mouse events for zooming and dragging."""
        if obj is self.scroll_area.viewport():
            if event.type() == QEvent.Type.Wheel:
                modifiers = QApplication.keyboardModifiers()
                
                # 支持Ctrl+滚轮缩放，也支持直接滚轮缩放
                if modifiers & Qt.KeyboardModifier.ControlModifier or True:  # 允许直接滚轮缩放
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    return True
            
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # 开始拖动
                    self.is_dragging = True
                    self.drag_start_pos = event.pos()
                    self.scroll_area.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return True
            
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    # 结束拖动
                    self.is_dragging = False
                    self.drag_start_pos = None
                    self.scroll_area.setCursor(Qt.CursorShape.ArrowCursor)
                    return True
            
            elif event.type() == QEvent.Type.MouseMove:
                if self.is_dragging and self.drag_start_pos:
                    # 计算拖动距离
                    delta = event.pos() - self.drag_start_pos
                    self.drag_start_pos = event.pos()
                    
                    # 更新滚动位置
                    self.scroll_area.horizontalScrollBar().setValue(
                        self.scroll_area.horizontalScrollBar().value() - delta.x()
                    )
                    self.scroll_area.verticalScrollBar().setValue(
                        self.scroll_area.verticalScrollBar().value() - delta.y()
                    )
                    return True
        
        return super().eventFilter(obj, event)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self.zoom_in()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key.Key_0:
            self.fit_to_window()
        elif event.key() == Qt.Key.Key_Left:
            self.rotate_left()
        elif event.key() == Qt.Key.Key_Right:
            self.rotate_right()
        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        
        # Rescale current image if available
        if self.current_pixmap and not self.current_pixmap.isNull():
            self.update_display()
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def update_detailed_info_panel(self, photo_data: dict):
        """
        更新详细信息面板，包括地理位置显示。
        """
        try:
            exif_data = photo_data.get("exif_data", {})
            
            # 相机信息
            self.camera_make_label.setText(f"相机品牌: {exif_data.get('Make', '-')}")
            self.camera_model_label.setText(f"相机型号: {exif_data.get('Model', '-')}")
            self.lens_label.setText(f"镜头: {exif_data.get('LensModel', '-')}")
            
            # 拍摄参数
            focal_length = exif_data.get('FocalLength')
            if focal_length:
                if isinstance(focal_length, str) and '/' in focal_length:
                    # 处理分数格式
                    try:
                        num, den = map(float, focal_length.split('/'))
                        focal_length = f"{num/den:.1f}mm"
                    except:
                        focal_length = f"{focal_length}mm"
                else:
                    focal_length = f"{focal_length}mm"
            self.focal_length_label.setText(f"焦距: {focal_length or '-'}")
            
            # 光圈
            aperture = exif_data.get('FNumber')
            if aperture:
                if isinstance(aperture, str) and '/' in aperture:
                    try:
                        num, den = map(float, aperture.split('/'))
                        aperture = f"f/{num/den:.1f}"
                    except:
                        aperture = f"f/{aperture}"
                else:
                    aperture = f"f/{aperture}"
            self.aperture_label.setText(f"光圈: {aperture or '-'}")
            
            # 快门速度
            shutter_speed = exif_data.get('ExposureTime')
            if shutter_speed:
                if isinstance(shutter_speed, str) and '/' in shutter_speed:
                    try:
                        num, den = map(float, shutter_speed.split('/'))
                        if num/den >= 1:
                            shutter_speed = f"{num/den:.1f}秒"
                        else:
                            shutter_speed = f"1/{den/num:.0f}秒"
                    except:
                        shutter_speed = f"{shutter_speed}秒"
                else:
                    shutter_speed = f"{shutter_speed}秒"
            self.shutter_speed_label.setText(f"快门速度: {shutter_speed or '-'}")
            
            # ISO
            iso = exif_data.get('ISOSpeedRatings')
            self.iso_label.setText(f"ISO: {iso or '-'}")
            
            # GPS信息
            # 优先直接用photo_data中的gps字段
            lat = photo_data.get("gps_latitude")
            lon = photo_data.get("gps_longitude")
            alt = photo_data.get("gps_altitude")
            # 如果没有，尝试从exif_data中解析
            if (lat is None or lon is None) and photo_data.get("exif_data"):
                exif_data = photo_data["exif_data"]
                gps_info = exif_data.get("GPSInfo")
                if gps_info:
                    try:
                        gps_lat = gps_info.get(2) or gps_info.get('GPSLatitude')
                        gps_lat_ref = gps_info.get(1) or gps_info.get('GPSLatitudeRef')
                        gps_lon = gps_info.get(4) or gps_info.get('GPSLongitude')
                        gps_lon_ref = gps_info.get(3) or gps_info.get('GPSLongitudeRef')
                        def _val(x):
                            if isinstance(x, tuple) and len(x) == 2:
                                return x[0] / x[1] if x[1] else 0
                            try:
                                return float(x)
                            except Exception:
                                return 0
                        if gps_lat and gps_lat_ref and gps_lon and gps_lon_ref:
                            d, m, s = gps_lat if isinstance(gps_lat, (list, tuple)) else (0, 0, 0)
                            lat = _val(d) + _val(m) / 60 + _val(s) / 3600
                            if gps_lat_ref in ['S', 'W']:
                                lat = -lat
                            d, m, s = gps_lon if isinstance(gps_lon, (list, tuple)) else (0, 0, 0)
                            lon = _val(d) + _val(m) / 60 + _val(s) / 3600
                            if gps_lon_ref in ['S', 'W']:
                                lon = -lon
                        gps_alt = gps_info.get(6) or gps_info.get('GPSAltitude')
                        if gps_alt:
                            if isinstance(gps_alt, tuple):
                                alt = gps_alt[0] / gps_alt[1] if gps_alt[1] else 0
                            else:
                                alt = float(gps_alt)
                    except Exception:
                        pass
            # 显示
            if lat is not None:
                self.gps_latitude_label.setText(f"纬度: {lat:.6f}")
            else:
                self.gps_latitude_label.setText("纬度: -")
            if lon is not None:
                self.gps_longitude_label.setText(f"经度: {lon:.6f}")
            else:
                self.gps_longitude_label.setText("经度: -")
            if alt is not None:
                try:
                    self.gps_altitude_label.setText(f"高度: {float(alt):.2f}")
                except Exception:
                    self.gps_altitude_label.setText(f"高度: {alt}")
            else:
                self.gps_altitude_label.setText("高度: -")
            if lat is not None and lon is not None:
                self.gps_label.setText(f"GPS坐标: {lat:.6f}, {lon:.6f}")
                # 优先用数据库缓存
                location_text = photo_data.get("location_text")
                if location_text:
                    self.location_label.setText(f"地理位置: {location_text}")
                else:
                    self.location_label.setText("地理位置: 查询中...")
            else:
                self.gps_label.setText("GPS坐标: -")
                self.location_label.setText("地理位置: 无GPS信息")
                
        except Exception as e:
            self.logger.error("Failed to update detailed info panel", error=str(e))
    
    def update_tags_display(self, photo_data: dict):
        """更新分类标签显示"""
        try:
            # 获取照片的分类标签
            tags = photo_data.get('tags', [])
            if isinstance(tags, str):
                # 如果是字符串，尝试解析为列表
                try:
                    import json
                    tags = json.loads(tags)
                except:
                    tags = [tags] if tags else []
            
            if tags:
                # 显示分类标签
                tags_text = ", ".join(tags)
                self.category_tags_label.setText(f"分类标签: {tags_text}")
            else:
                self.category_tags_label.setText("分类标签: 无")
                
        except Exception as e:
            self.logger.error("Failed to update category tags display", error=str(e))
            self.category_tags_label.setText("分类标签: 显示错误")
    
    def edit_category_tags(self):
        """编辑分类标签"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem
            
            # 创建分类标签编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑分类标签")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(300)
            
            layout = QVBoxLayout(dialog)
            
            # 当前标签显示
            current_tags = self.current_photo.get('tags', []) if self.current_photo else []
            if isinstance(current_tags, str):
                try:
                    import json
                    current_tags = json.loads(current_tags)
                except:
                    current_tags = [current_tags] if current_tags else []
            
            # 标签输入框
            layout.addWidget(QLabel("分类标签（用逗号分隔）:"))
            self.tags_input = QLineEdit()
            self.tags_input.setText(", ".join(current_tags))
            layout.addWidget(self.tags_input)
            
            # 常用标签列表
            layout.addWidget(QLabel("常用标签:"))
            common_tags = ["Nature", "Food", "Architecture", "People", "Travel", "Art", "Technology", "Sports"]
            self.common_tags_list = QListWidget()
            for tag in common_tags:
                item = QListWidgetItem(tag)
                self.common_tags_list.addItem(item)
            self.common_tags_list.itemDoubleClicked.connect(self.add_common_tag)
            layout.addWidget(self.common_tags_list)
            
            # 按钮
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("保存")
            save_btn.clicked.connect(dialog.accept)
            save_btn.setDefault(True)
            button_layout.addWidget(save_btn)
            
            layout.addLayout(button_layout)
            
            # 显示对话框
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 保存标签
                tags_text = self.tags_input.text().strip()
                if tags_text:
                    new_tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
                else:
                    new_tags = []
                
                # 更新照片数据
                if self.current_photo and self.current_photo.get('id'):
                    # 更新内存中的数据
                    self.current_photo['tags'] = new_tags
                    
                    # 更新数据库
                    try:
                        # 获取主窗口的photo_manager
                        main_window = self.window()
                        if main_window and hasattr(main_window, 'photo_manager'):
                            # 使用photo_manager更新数据库
                            success = main_window.photo_manager.db.update_photo(
                                self.current_photo['id'], 
                                {"tags": new_tags}
                            )
                            if success:
                                self.logger.info("Category tags saved to database", 
                                               photo_id=self.current_photo.get('id'), 
                                               tags=new_tags)
                                # 发送更新信号
                                self.photo_updated.emit(self.current_photo['id'])
                            else:
                                self.logger.error("Failed to save category tags to database", 
                                                photo_id=self.current_photo.get('id'))
                        else:
                            self.logger.error("Photo manager not available")
                    except Exception as e:
                        self.logger.error("Failed to save category tags", error=str(e))
                    
                    # 更新显示
                    self.update_tags_display(self.current_photo)
                    
        except Exception as e:
            self.logger.error("Failed to edit category tags", error=str(e))
    
    def add_common_tag(self, item):
        """添加常用标签到输入框"""
        try:
            tag = item.text()
            current_text = self.tags_input.text()
            if current_text:
                new_text = f"{current_text}, {tag}"
            else:
                new_text = tag
            self.tags_input.setText(new_text)
        except Exception as e:
            self.logger.error("Failed to add common tag", error=str(e))
    
    def _query_location_info(self, photo_data: dict):
        """查询位置信息"""
        try:
            # 检查是否有GPS坐标
            exif_data = photo_data.get("exif_data", {})
            gps_lat = exif_data.get('GPSLatitude')
            gps_lon = exif_data.get('GPSLongitude')
            
            if not gps_lat or not gps_lon:
                self.location_label.setText("位置: 无GPS信息")
                return
            
            # 尝试从主窗口获取GPS插件
            main_window = self.window()
            if not main_window or not hasattr(main_window, 'plugin_manager'):
                self.location_label.setText("位置: 插件管理器不可用")
                return
            
            # 查找GPS位置查询插件
            gps_plugin = None
            for plugin in main_window.plugin_manager.get_plugins():
                if hasattr(plugin, 'get_info') and plugin.get_info().name == "GPS位置查询插件":
                    gps_plugin = plugin
                    break
            
            if not gps_plugin or not gps_plugin.is_available():
                self.location_label.setText("位置: GPS插件不可用")
                return
            
            # 查询位置信息
            location_info = gps_plugin.query_location_from_photo_data(photo_data)
            
            if location_info:
                # 显示位置信息
                location_text = location_info.to_display_string("short")
                self.location_label.setText(f"位置: {location_text}")
                self.location_label.setToolTip(f"完整地址: {location_info.to_display_string('full')}")
            else:
                self.location_label.setText("位置: 查询失败")
                
        except Exception as e:
            self.logger.error("Failed to query location info", error=str(e))
            self.location_label.setText("位置: 查询出错")

    def _convert_gps_coordinate(self, coord, ref):
        """转换GPS坐标为度分秒格式"""
        try:
            if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                degrees, minutes, seconds = coord[:3]
                if isinstance(degrees, str) and '/' in degrees:
                    num, den = map(float, degrees.split('/'))
                    degrees = num / den
                if isinstance(minutes, str) and '/' in minutes:
                    num, den = map(float, minutes.split('/'))
                    minutes = num / den
                if isinstance(seconds, str) and '/' in seconds:
                    num, den = map(float, seconds.split('/'))
                    seconds = num / den
                
                result = f"{degrees:.0f}°{minutes:.0f}'{seconds:.1f}\""
                if ref in ['S', 'W']:
                    result = f"-{result}"
                return result
            else:
                return str(coord)
        except:
            return str(coord)
    
    def save_rotated_image(self):
        """保存旋转后的图片
        
        参照照片编辑器的实现：
        1. 从原图开始
        2. 处理EXIF方向
        3. 应用用户旋转角度
        4. 保存结果
        """
        if not self.current_photo or not self.current_pixmap:
            return
        
        try:
            from PyQt6.QtWidgets import QMessageBox, QFileDialog
            from PIL import Image
            import os
            
            # 获取原图路径
            original_path = self.current_photo.get("filepath")
            if not original_path or not os.path.exists(original_path):
                QMessageBox.warning(self, "警告", "原图文件不存在，无法保存旋转")
                return
            
            # 询问用户是否要覆盖原图
            reply = QMessageBox.question(
                self, "保存旋转", 
                "是否要覆盖原图文件？\n建议先备份原图。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 保存到原图路径
                save_path = original_path
            else:
                # 选择保存路径
                save_path, _ = QFileDialog.getSaveFileName(
                    self, "保存旋转后的图片", 
                    original_path,
                    "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)"
                )
                if not save_path:
                    return
            
            # 重新加载原图并处理EXIF方向（与load_image_with_exif_orientation保持一致）
            pil_image = Image.open(original_path)
            
            # 处理EXIF方向
            exif = pil_image.getexif()
            orientation = exif.get(274)
            
            if orientation and orientation != 1:
                orientation_rotations = {
                    1: 0, 2: 0, 3: 180, 4: 0, 5: 0, 6: 270, 7: 0, 8: 90
                }
                rotation_angle = orientation_rotations.get(orientation, 0)
                if rotation_angle != 0:
                    pil_image = pil_image.rotate(rotation_angle, expand=True)
                    self.logger.info("保存时处理EXIF方向", 
                                   original_orientation=orientation,
                                   rotation_angle=rotation_angle)
            
            # 应用用户旋转角度（参照照片编辑器的实现）
            if self.rotation_angle != 0:
                pil_image = pil_image.rotate(self.rotation_angle, expand=True)
                self.logger.info("保存时应用用户旋转", 
                               user_rotation_angle=self.rotation_angle)
            
            # 保存图片
            pil_image.save(save_path, quality=95)
            
            # 更新数据库中的图片信息
            if hasattr(self, 'photo_updated'):
                self.photo_updated.emit(self.current_photo.get('id'))
            
            # 重置旋转角度
            self.rotation_angle = 0
            self.save_rotation_btn.setEnabled(False)
            self.update_rotation_label()
            
            # 重新加载图片
            self.display_photo(self.current_photo)
            
            QMessageBox.information(self, "成功", "图片旋转已保存")
            
        except Exception as e:
            self.logger.error("Failed to save rotated image", error=str(e))
            QMessageBox.critical(self, "错误", f"保存旋转图片失败：{str(e)}")
    
    def show_previous_photo(self):
        """显示上一张图片"""
        self.previous_photo_requested.emit()
    
    def show_next_photo(self):
        """显示下一张图片"""
        self.next_photo_requested.emit()
    
    def open_photo_editor(self):
        """打开照片编辑器对话框"""
        if not self.current_photo or not self.current_photo.get('filepath'):
            return
        
        try:
            from .photo_editor import PhotoEditorDialog
            editor = PhotoEditorDialog(self.current_photo['filepath'], self)
            if editor.exec() == PhotoEditorDialog.DialogCode.Accepted:
                # 重新加载图片
                self.display_photo(self.current_photo)
                self.photo_updated.emit(self.current_photo['id'])
                self.logger.info("Photo edited and saved", photo_id=self.current_photo['id'])
        except ImportError as e:
            self.logger.error("Failed to import photo editor", error=str(e))
        except Exception as e:
            self.logger.error("Failed to open photo editor", error=str(e))
    
    def load_image_with_exif_orientation(self, file_path: str) -> QPixmap:
        """加载图片并处理EXIF方向信息 - 重新设计版本
        
        这个方法的职责：
        1. 加载原始图片
        2. 处理EXIF方向信息，确保图片以正确方向显示
        3. 返回处理后的图片作为新的"标准方向"
        
        注意：处理完成后，这个图片就是新的参考系，用户的所有旋转都基于这个方向
        """
        try:
            # 检查缓存
            if hasattr(self, '_image_cache') and file_path in self._image_cache:
                self.logger.info("使用缓存的图片", path=file_path)
                return self._image_cache[file_path]
            
            from PIL import Image, ImageOps
            import io
            
            # 使用PIL加载图片
            pil_image = Image.open(file_path)
            
            # 获取EXIF方向信息
            exif = pil_image.getexif()
            orientation = exif.get(274)  # 274 是 Orientation 标签
            
            self.logger.info("加载图片EXIF信息", 
                           path=file_path, 
                           orientation=orientation,
                           original_size=f"{pil_image.width}x{pil_image.height}")
            
            # 根据EXIF方向信息旋转图片到标准方向
            if orientation and orientation != 1:  # 1是正常方向，不需要处理
                # EXIF方向值对应的旋转角度（PIL的rotate是逆时针）
                orientation_rotations = {
                    1: 0,    # 正常
                    2: 0,    # 水平翻转
                    3: 180,  # 旋转180度
                    4: 0,    # 垂直翻转
                    5: 0,    # 水平翻转+旋转90度
                    6: 270,  # 旋转90度（顺时针90度，PIL需要逆时针270度）
                    7: 0,    # 水平翻转+旋转270度
                    8: 90,   # 旋转270度（逆时针90度，PIL需要顺时针90度）
                }
                
                rotation_angle = orientation_rotations.get(orientation, 0)
                
                if rotation_angle != 0:
                    # 旋转图片到标准方向
                    pil_image = pil_image.rotate(rotation_angle, expand=True)
                    self.logger.info("应用EXIF方向旋转到标准方向", 
                                   original_orientation=orientation,
                                   rotation_angle=rotation_angle,
                                   final_size=f"{pil_image.width}x{pil_image.height}")
                
                # 处理翻转
                if orientation in [2, 4, 5, 7]:
                    if orientation in [2, 4]:  # 水平或垂直翻转
                        pil_image = ImageOps.mirror(pil_image)
                    elif orientation in [5, 7]:  # 需要先旋转再翻转
                        pil_image = ImageOps.mirror(pil_image)
                    self.logger.info("应用EXIF翻转", orientation=orientation)
            
            # 优化：对于大图片，先压缩以提高性能
            max_size = 2048
            if pil_image.width > max_size or pil_image.height > max_size:
                # 计算缩放比例
                ratio = min(max_size / pil_image.width, max_size / pil_image.height)
                new_width = int(pil_image.width * ratio)
                new_height = int(pil_image.height * ratio)
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.logger.info("压缩大图片以提高性能", 
                               original_size=f"{pil_image.width}x{pil_image.height}",
                               compressed_size=f"{new_width}x{new_height}")
            
            # 转换回QPixmap
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            # 缓存结果
            if not hasattr(self, '_image_cache'):
                self._image_cache = {}
            self._image_cache[file_path] = pixmap
            
            # 限制缓存大小，避免内存泄漏
            if len(self._image_cache) > 10:
                # 删除最旧的缓存项
                oldest_key = next(iter(self._image_cache))
                del self._image_cache[oldest_key]
            
            self.logger.info("图片加载完成，已处理EXIF方向", 
                           final_size=f"{pixmap.width()}x{pixmap.height()}")
            
            return pixmap
            
        except Exception as e:
            self.logger.error("处理EXIF方向失败，使用原始加载方式", 
                            path=file_path, error=str(e))
            # 如果处理失败，回退到原始加载方式
            return QPixmap(file_path)

    def refresh_location(self):
        """刷新当前照片的地理位置信息，并写入数据库缓存。"""
        if not self.current_photo:
            return
        lat = self.current_photo.get("gps_latitude")
        lon = self.current_photo.get("gps_longitude")
        alt = self.current_photo.get("gps_altitude")
        if lat is not None and lon is not None and self.plugin_manager:
            gps_plugin = self.plugin_manager.get_plugin("GPS位置查询插件")
            if gps_plugin and hasattr(gps_plugin, "query_location"):
                from PyQt6.QtCore import QThread, pyqtSignal
                class LocationWorker(QThread):
                    location_ready = pyqtSignal(object)
                    def __init__(self, plugin, lat, lon, alt):
                        super().__init__()
                        self.plugin = plugin
                        self.lat = lat
                        self.lon = lon
                        self.alt = alt
                    def run(self):
                        from types import SimpleNamespace
                        try:
                            coord = SimpleNamespace(latitude=self.lat, longitude=self.lon, altitude=self.alt)
                            location = self.plugin.query_location(coord)
                            self.location_ready.emit(location)
                        except Exception as e:
                            self.location_ready.emit(None)
                def on_location_ready(location):
                    if location and hasattr(location, 'full_address') and location.full_address:
                        self.location_label.setText(f"地理位置: {location.full_address}")
                        # 写入数据库缓存
                        main_win = self.parentWidget()
                        while main_win and not hasattr(main_win, 'photo_manager'):
                            main_win = main_win.parentWidget() if hasattr(main_win, 'parentWidget') else None
                        if main_win and hasattr(main_win, 'photo_manager') and self.current_photo.get('id'):
                            main_win.photo_manager.db.update_photo(self.current_photo['id'], {"location_text": location.full_address})
                            self.current_photo["location_text"] = location.full_address
                    elif location:
                        # 拼接简要地理位置
                        parts = []
                        for k in ["country", "state_province", "city", "district", "street"]:
                            v = getattr(location, k, None)
                            if v:
                                parts.append(str(v))
                        if parts:
                            loc_str = "_".join(parts)
                            self.location_label.setText(f"地理位置: {loc_str}")
                            main_win = self.parentWidget()
                            while main_win and not hasattr(main_win, 'photo_manager'):
                                main_win = main_win.parentWidget() if hasattr(main_win, 'parentWidget') else None
                            if main_win and hasattr(main_win, 'photo_manager') and self.current_photo.get('id'):
                                main_win.photo_manager.db.update_photo(self.current_photo['id'], {"location_text": loc_str})
                                self.current_photo["location_text"] = loc_str
                        else:
                            self.location_label.setText("地理位置: 查询失败")
                    else:
                        self.location_label.setText("地理位置: 查询失败")
                self.location_label.setText("地理位置: 查询中...")
                worker = LocationWorker(gps_plugin, lat, lon, alt)
                self._location_worker = worker  # 保存引用，防止被回收
                worker.location_ready.connect(on_location_ready)
                worker.finished.connect(lambda: setattr(self, "_location_worker", None))  # 线程结束后释放
                worker.start()
        else:
            self.location_label.setText("地理位置: 无GPS信息")

    def refresh_all_locations(self):
        """批量刷新所有图片的地理位置信息。"""
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from PyQt6.QtCore import QCoreApplication
        # 获取photo_manager实例
        main_win = self.parentWidget()
        while main_win and not hasattr(main_win, 'photo_manager'):
            main_win = main_win.parentWidget() if hasattr(main_win, 'parentWidget') else None
        if not main_win or not hasattr(main_win, 'photo_manager'):
            QMessageBox.warning(self, "错误", "无法获取PhotoManager实例，无法批量刷新！")
            return
        photo_manager = main_win.photo_manager
        # 获取所有图片
        all_photos = photo_manager.db.search_photos(limit=100000)
        photos_to_update = [p for p in all_photos if p.get("gps_latitude") and not p.get("location_text")]
        if not photos_to_update:
            QMessageBox.information(self, "批量刷新地理位置", "没有需要刷新的图片（所有图片都已缓存地理位置）")
            return
        progress = QProgressDialog("正在批量刷新地理位置信息...", "取消", 0, len(photos_to_update), self)
        progress.setWindowTitle("批量刷新地理位置")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        updated = 0
        for idx, photo in enumerate(photos_to_update, 1):
            if progress.wasCanceled():
                break
            lat = photo.get("gps_latitude")
            lon = photo.get("gps_longitude")
            if lat is not None and lon is not None:
                # 查询地理位置（用插件）
                location_text = self._query_location_text(photo_manager, lat, lon)
                if location_text:
                    photo_manager.db.update_photo(photo["id"], {"location_text": location_text})
                    updated += 1
            progress.setValue(idx)
            QCoreApplication.processEvents()
        progress.close()
        QMessageBox.information(self, "批量刷新完成", f"已成功刷新 {updated} 张图片的地理位置信息。")

    def _query_location_text(self, photo_manager, lat, lon):
        """调用GPS插件查询地理位置文本，返回如'北京市_朝阳区'"""
        plugin = None
        if hasattr(photo_manager, 'plugin_manager'):
            plugin = photo_manager.plugin_manager.get_plugin("GPS位置查询插件")
        if not plugin or not hasattr(plugin, "query_location"):
            return None
        from types import SimpleNamespace
        coord = SimpleNamespace(latitude=lat, longitude=lon, altitude=None)
        try:
            location = plugin.query_location(coord)
            # 优先用详细地址或城市、区县
            if location:
                # 兼容多种插件返回结构
                if hasattr(location, 'full_address') and location.full_address:
                    return location.full_address
                parts = []
                for k in ["country", "state_province", "city", "district", "street"]:
                    v = getattr(location, k, None)
                    if v:
                        parts.append(str(v))
                if parts:
                    return "_".join(parts)
            return None
        except Exception:
            return None