"""
Thumbnail grid widget for displaying photo thumbnails.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QScrollArea, 
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QMenu, QMessageBox, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, QUrl, QMimeData, QTimer, QThreadPool, QRunnable
from PyQt6.QtGui import QPixmap, QContextMenuEvent, QAction, QPainter, QFont, QDrag
import logging
import time


class ThumbnailLoader(QRunnable):
    """异步缩略图加载器"""
    
    def __init__(self, photo_data: Dict[str, Any], callback):
        super().__init__()
        self.photo_data = photo_data
        self.callback = callback
        self.photo_id = photo_data.get("id", 0)
        
    def run(self):
        """在后台线程中加载缩略图"""
        try:
            thumbnail_path = self.photo_data.get("thumbnail_path", "")
            filepath = self.photo_data.get("filepath", "")
            
            pixmap = None
            
            # 优先加载缩略图
            if thumbnail_path and Path(thumbnail_path).exists():
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        180, 135,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
            
            # 如果没有缩略图，加载原图
            if not pixmap or pixmap.isNull():
                if filepath and Path(filepath).exists():
                    pixmap = QPixmap(filepath)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(
                            180, 135,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
            
            # 回调到主线程更新UI
            if pixmap and not pixmap.isNull():
                self.callback.emit(self.photo_id, pixmap)
            else:
                # 创建一个空的QPixmap而不是None
                empty_pixmap = QPixmap(180, 135)
                empty_pixmap.fill(Qt.GlobalColor.transparent)
                self.callback.emit(self.photo_id, empty_pixmap)
            
        except Exception as e:
            # 加载失败时发送空QPixmap
            empty_pixmap = QPixmap(180, 135)
            empty_pixmap.fill(Qt.GlobalColor.transparent)
            self.callback.emit(self.photo_id, empty_pixmap)


class ThumbnailItem(QFrame):
    """Individual thumbnail item widget."""
    
    clicked = pyqtSignal(int)  # photo_id
    context_menu_requested = pyqtSignal(int, object)  # photo_id, position
    thumbnail_loaded = pyqtSignal(int, QPixmap)  # photo_id, pixmap
    
    def __init__(self, photo_data: Dict[str, Any]):
        super().__init__()
        self.photo_data = photo_data
        self.photo_id = photo_data.get("id", 0)
        self.logger = logging.getLogger("picman.gui.thumbnail_item")
        self.is_selected = False
        self.thumbnail_loaded = False
        
        # 延迟初始化UI，避免频繁创建时的性能开销
        self._ui_initialized = False
        self.init_ui()
        self.show_loading_placeholder()
    
    def init_ui(self):
        """Initialize the thumbnail item UI."""
        if self._ui_initialized:
            return
            
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedSize(200, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 135)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        layout.addWidget(self.image_label)
        
        # Photo info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Filename
        filename = self.photo_data.get("filename", "Unknown")
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        self.filename_label = QLabel(filename)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.filename_label.font()
        font.setPointSize(8)
        self.filename_label.setFont(font)
        info_layout.addWidget(self.filename_label)
        
        # Rating and favorite indicator
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # Rating stars
        rating = self.photo_data.get("rating", 0)
        rating_text = "★" * rating + "☆" * (5 - rating)
        self.rating_label = QLabel(rating_text)
        self.rating_label.setStyleSheet("color: gold;")
        font = self.rating_label.font()
        font.setPointSize(8)
        self.rating_label.setFont(font)
        status_layout.addWidget(self.rating_label)
        
        # Favorite indicator
        if self.photo_data.get("is_favorite", False):
            favorite_label = QLabel("♥")
            favorite_label.setStyleSheet("color: red;")
            font = favorite_label.font()
            font.setPointSize(10)
            favorite_label.setFont(font)
            status_layout.addWidget(favorite_label)
        
        status_layout.addStretch()
        info_layout.addLayout(status_layout)
        
        layout.addLayout(info_layout)
    
        self._ui_initialized = True
    
    def show_loading_placeholder(self):
        """显示加载占位符"""
        self.image_label.setText("加载中...")
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc; 
                background-color: #f5f5f5;
                color: #999;
                font-size: 10px;
            }
        """)
    
    def set_thumbnail(self, pixmap: QPixmap):
        """设置缩略图"""
        try:
            if pixmap and not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
                self.thumbnail_loaded = True
            else:
                self.image_label.setText("无图片")
                self.image_label.setStyleSheet("""
                    QLabel {
                        border: 1px solid #ccc; 
                        background-color: #f5f5f5;
                        color: #999;
                        font-size: 10px;
                    }
                """)
        except RuntimeError as e:
            # 如果image_label已被删除，忽略错误
            self.logger.warning("Image label deleted when setting thumbnail: %s", str(e))

    def set_selected(self, selected: bool):
        """Set the selection state of the thumbnail."""
        self.is_selected = selected
        
        if selected:
            # Highlight the thumbnail and show checkmark
            self.setStyleSheet("""
                QFrame {
                    border: 3px solid #0078d4 !important;
                    background-color: #e3f2fd !important;
                    border-radius: 5px;
                }
                QLabel {
                    background-color: transparent;
                }
            """)

            self.show_checkmark()
            # 强制刷新显示
            self.update()
            self.repaint()
        else:
            # Remove highlight and hide checkmark
            self.setStyleSheet("")
            self.hide_checkmark()
            # 强制刷新显示
            self.update()
            self.repaint()
    
    def show_checkmark(self):
        """Show selection checkmark."""
        if not hasattr(self, 'checkmark_label'):
            self.checkmark_label = QLabel("✓")
            self.checkmark_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: #0078d4;
                    border-radius: 10px;
                    padding: 2px 6px;
                    font-weight: bold;
                }
            """)
            self.checkmark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.checkmark_label.setFixedSize(20, 20)
            self.checkmark_label.setParent(self)
            
            # Position checkmark in top-right corner using absolute positioning
            self.checkmark_label.move(self.width() - 25, 5)
        
        self.checkmark_label.show()
        self.checkmark_label.raise_()  # 确保显示在最顶层
    
    def hide_checkmark(self):
        """Hide selection checkmark."""
        if hasattr(self, 'checkmark_label'):
            self.checkmark_label.hide()
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:

            
            # Get the thumbnail widget
            thumbnail_widget = None
            parent = self.parent()
            while parent:
                if hasattr(parent, 'multi_select_mode'):
                    thumbnail_widget = parent
                    break
                parent = parent.parent()
            
            if thumbnail_widget and thumbnail_widget.multi_select_mode:
                # Toggle selection in multi-select mode

                thumbnail_widget.toggle_item_selection(self.photo_id)
            else:
                # Normal single selection
    
                self.clicked.emit(self.photo_id)
        super().mousePressEvent(event)
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle context menu events."""
        self.context_menu_requested.emit(self.photo_id, event.globalPos())


class ThumbnailWidget(QScrollArea):
    """Widget for displaying a grid of photo thumbnails."""
    
    photo_selected = pyqtSignal(int)  # photo_id
    photos_updated = pyqtSignal()
    selection_changed = pyqtSignal(list)  # list of photo_ids
    thumbnail_loaded = pyqtSignal(int, QPixmap)  # photo_id, pixmap
    
    def __init__(self):
        super().__init__()
        self.photos = []
        self.thumbnail_items = []
        self.columns = 3
        self.selected_items = []
        self.logger = logging.getLogger("picman.gui.thumbnail_widget")
        self.drag_start_position = None
        self.multi_select_mode = False
        self._displaying_photos = False
        
        # 性能优化相关
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制并发线程数
        self.loading_queue = []  # 待加载队列
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.process_loading_queue)
        self.loading_timer.setInterval(50)  # 50ms间隔处理队列
        
        # 虚拟化相关
        self.visible_range = (0, 0)  # 当前可见范围
        self.page_size = 50  # 每页显示数量
        self.current_page = 0
        self.max_visible_items = 150  # 最大可见项数量，超过时回收
        
        # 滚动优化相关
        self.scroll_throttle_timer = QTimer()
        self.scroll_throttle_timer.setSingleShot(True)
        self.scroll_throttle_timer.timeout.connect(self.process_scroll_event)
        self.pending_scroll_event = False
        self.last_scroll_value = 0
        
        # 缩略图项缓存（暂时禁用，避免UI组件删除问题）
        self.thumbnail_item_cache = []  # 缓存未使用的缩略图项
        self.max_cache_size = 0  # 暂时禁用缓存
        
        # 可见性检测
        self.visibility_timer = QTimer()
        self.visibility_timer.timeout.connect(self.check_visibility_and_optimize)
        self.visibility_timer.setInterval(500)  # 500ms检查一次可见性
        
        self.init_ui()
        self.thumbnail_loaded.connect(self.on_thumbnail_loaded)
    
    def init_ui(self):
        """Initialize the thumbnail widget UI."""
        # Create main widget
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)
        
        # 启用拖放
        self.setAcceptDrops(True)
        
        # Create grid layout
        self.grid_layout = QGridLayout(self.main_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        # 连接滚动条信号
        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        
        # Show placeholder initially
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder when no photos are available."""
        placeholder = QLabel("没有照片")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 16px;")
        self.grid_layout.addWidget(placeholder, 0, 0)
    
    def display_photos(self, photos: List[Dict[str, Any]]):
        """Display a list of photos as thumbnails with virtualization."""
        try:
            # Prevent recursive calls
            if hasattr(self, '_displaying_photos') and self._displaying_photos:
                return
            self._displaying_photos = True
            
            # 停止之前的可见性监控
            self.stop_visibility_monitoring()
            
            # Clear existing thumbnails
            self.clear_thumbnails()
            
            self.photos = photos
            self.selected_items = []
            self.current_page = 0
            
            if not photos:
                self.show_placeholder()
                return
            
            # Calculate columns based on widget width
            self.update_columns()
            
            # 计算总页数
            total_pages = (len(photos) + self.page_size - 1) // self.page_size
            
            # 只显示第一页的缩略图
            self.display_page(0)
            
            # 开始异步加载
            self.start_async_loading()
            
            # 启动可见性监控
            self.start_visibility_monitoring()
            
            self.logger.info("Displayed thumbnails with virtualization: count=%d, total_pages=%d, page_size=%d, multi_select_mode=%s", 
                           len(photos), total_pages, self.page_size, self.multi_select_mode)
            
        except Exception as e:
            self.logger.error("Failed to display photos: %s", str(e))
        finally:
            self._displaying_photos = False
    
    def display_page(self, page: int):
        """显示指定页的缩略图（使用缓存优化）"""
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.photos))
        
        # 回收当前显示的缩略图项到缓存
        for item in self.thumbnail_items:
            self.recycle_thumbnail_item(item)
        
        # 清空当前项列表
        self.thumbnail_items.clear()
        
        # 创建当前页的缩略图项（使用缓存）
        for i in range(start_idx, end_idx):
            photo = self.photos[i]
            row = (i - start_idx) // self.columns
            col = (i - start_idx) % self.columns
            
            # 使用缓存创建缩略图项
            thumbnail_item = self.create_thumbnail_item(photo)
            thumbnail_item.clicked.connect(self.on_thumbnail_clicked)
            thumbnail_item.context_menu_requested.connect(self.show_context_menu)
            
            self.grid_layout.addWidget(thumbnail_item, row, col)
            self.thumbnail_items.append(thumbnail_item)
        
        self.current_page = page
        self.visible_range = (start_idx, end_idx)
    
    def start_async_loading(self):
        """开始异步加载缩略图"""
        # 清空加载队列
        self.loading_queue.clear()
        
        # 将当前可见的缩略图加入加载队列
        for i in range(self.visible_range[0], self.visible_range[1]):
            if i < len(self.photos):
                self.loading_queue.append(i)
        
        # 启动加载定时器
        if not self.loading_timer.isActive():
            self.loading_timer.start()
    
    def process_loading_queue(self):
        """处理加载队列"""
        if not self.loading_queue:
            self.loading_timer.stop()
            return
        
        # 每次处理几个缩略图
        batch_size = 3
        for _ in range(min(batch_size, len(self.loading_queue))):
            if self.loading_queue:
                photo_idx = self.loading_queue.pop(0)
                if photo_idx < len(self.photos):
                    self.load_thumbnail_async(photo_idx)
    
    def load_thumbnail_async(self, photo_idx: int):
        """异步加载单个缩略图"""
        photo = self.photos[photo_idx]
        loader = ThumbnailLoader(photo, self.thumbnail_loaded)
        self.thread_pool.start(loader)
    
    def on_thumbnail_loaded(self, photo_id: int, pixmap: QPixmap):
        """缩略图加载完成回调"""
        # 找到对应的缩略图项并更新
        for item in self.thumbnail_items:
            if item.photo_id == photo_id:
                try:
                    # 检查item是否仍然有效
                    if item and not item.isHidden() and hasattr(item, 'image_label'):
                        item.set_thumbnail(pixmap)
                except RuntimeError as e:
                    # 如果QLabel已被删除，忽略错误
                    self.logger.warning("Thumbnail item UI component deleted: photo_id=%s, error=%s", photo_id, str(e))
                break
    
    def clear_thumbnails(self):
        """Clear all thumbnail items (使用缓存回收)."""
        # 回收所有缩略图项到缓存
        for item in self.thumbnail_items:
            self.recycle_thumbnail_item(item)
        
        # Remove all widgets from layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.thumbnail_items.clear()
    
    def clear_thumbnail_items(self):
        """只清除缩略图项，保留布局"""
        for item in self.thumbnail_items:
            self.grid_layout.removeWidget(item)
            item.deleteLater()
        self.thumbnail_items.clear()
    
    def update_columns(self):
        """Update number of columns based on widget width."""
        widget_width = self.width()
        item_width = 220  # thumbnail width + margins
        
        new_columns = max(1, widget_width // item_width)
        
        if new_columns != self.columns:
            self.columns = new_columns
            # Redisplay current page with new column count
            if self.photos and hasattr(self, '_displaying_photos') and not self._displaying_photos:
                self._displaying_photos = True
                self.display_page(self.current_page)
                self._displaying_photos = False
    
    def on_thumbnail_clicked(self, photo_id: int):
        """Handle thumbnail click events."""
        self.logger.info("Thumbnail clicked: photo_id=%d, multi_select_mode=%s", photo_id, self.multi_select_mode)

        
        # 注意：这个方法只在单选模式下被调用
        # 多选模式的处理在mousePressEvent中直接调用toggle_item_selection
        if not self.multi_select_mode:
            # In single-select mode, clear previous selections and select this item
            self.clear_selection()
            # Select the clicked item (this will emit selection_changed signal)
            self.select_item(photo_id)
            # Emit selection signal
            self.logger.info("Emitting photo_selected signal: photo_id=%d", photo_id)
            self.photo_selected.emit(photo_id)
    
    def toggle_item_selection(self, photo_id: int):
        """Toggle selection state of an item."""
        for item in self.thumbnail_items:
            if item.photo_id == photo_id:
                if photo_id in self.selected_items:
                    # Deselect
                    item.set_selected(False)
                    self.selected_items.remove(photo_id)
                else:
                    # Select
                    item.set_selected(True)
                    self.selected_items.append(photo_id)
                break
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_items.copy())
    
    def select_item(self, photo_id: int):
        """Select a specific item."""
        for item in self.thumbnail_items:
            if item.photo_id == photo_id:
                item.set_selected(True)
                if photo_id not in self.selected_items:
                    self.selected_items.append(photo_id)
                break
        
        # Log for debugging
        self.logger.info("Item selected: photo_id=%d, selected_items=%s", photo_id, self.selected_items.copy())
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_items.copy())
    
    def clear_selection(self):
        """Clear all selections."""
        for item in self.thumbnail_items:
            item.set_selected(False)
        self.selected_items.clear()
        self.selection_changed.emit([])
    
    def select_all(self):
        """Select all visible items."""
        for item in self.thumbnail_items:
            item.set_selected(True)
            if item.photo_id not in self.selected_items:
                self.selected_items.append(item.photo_id)
        self.selection_changed.emit(self.selected_items.copy())
    
    def deselect_all(self):
        """Deselect all items."""
        for item in self.thumbnail_items:
            item.set_selected(False)
        self.selected_items.clear()
        self.selection_changed.emit([])
    
    def set_multi_select_mode(self, enabled: bool):
        """Enable or disable multi-select mode."""
        self.multi_select_mode = enabled
        if not enabled:
            # Clear selection when exiting multi-select mode
            self.clear_selection()
    
    def on_thumbnail_selection_changed(self, photo_id: int, selected: bool):
        """Handle thumbnail selection change."""
        if selected and photo_id not in self.selected_items:
            self.selected_items.append(photo_id)
        elif not selected and photo_id in self.selected_items:
            self.selected_items.remove(photo_id)
        
        self.selection_changed.emit(self.selected_items.copy())
    
    def get_selected_photos(self) -> List[Dict[str, Any]]:
        """Get list of selected photo data."""
        selected_photos = []
        for photo in self.photos:
            if photo.get("id") in self.selected_items:
                selected_photos.append(photo)
        return selected_photos
    
    def show_context_menu(self, photo_id: int, position):
        """Show context menu for a photo."""
        menu = QMenu(self)
        
        # Get photo data
        photo_data = None
        for photo in self.photos:
            if photo.get("id") == photo_id:
                photo_data = photo
                break
        
        if not photo_data:
            return
        
        # Add actions
        rating_menu = menu.addMenu("评分")
        for i in range(1, 6):
            action = rating_menu.addAction("★" * i + "☆" * (5 - i))
            action.triggered.connect(lambda checked, rating=i: self.set_rating(photo_id, rating))
        
        # Favorite action
        is_favorite = photo_data.get("is_favorite", False)
        favorite_action = menu.addAction("取消收藏" if is_favorite else "收藏")
        favorite_action.triggered.connect(lambda: self.toggle_favorite(photo_id))
        
        menu.addSeparator()
        
        # Album actions
        album_action = menu.addAction("添加到相册...")
        album_action.triggered.connect(lambda: self.add_to_album(photo_id))
        
        # Tag actions
        tag_action = menu.addAction("添加标签...")
        tag_action.triggered.connect(lambda: self.add_tags(photo_id))
        
        menu.addSeparator()
        
        # Delete actions
        delete_action = menu.addAction("删除缩略图")
        delete_action.triggered.connect(lambda: self.delete_photo(photo_id))
        
        delete_original_action = menu.addAction("删除原图")
        delete_original_action.triggered.connect(lambda: self.delete_single_photo(photo_id))
        
        # Show menu
        menu.exec(position)
    
    def set_rating(self, photo_id: int, rating: int):
        """Set rating for a photo."""
        # This would typically update the database
        self.logger.info("Setting rating: photo_id=%d, rating=%d", photo_id, rating)
    
    def toggle_favorite(self, photo_id: int):
        """Toggle favorite status for a photo."""
        # This would typically update the database
        self.logger.info("Toggling favorite: photo_id=%d", photo_id)
    
    def add_to_album(self, photo_id: int):
        """Add photo to album."""
        # This would typically show an album selector
        self.logger.info("Adding to album: photo_id=%d", photo_id)
    
    def add_tags(self, photo_id: int):
        """Add tags to photo."""
        # This would typically show a tag editor
        self.logger.info("Adding tags: photo_id=%d", photo_id)
    
    def delete_photo(self, photo_id: int):
        """Delete photo thumbnail."""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这张照片的缩略图吗？\n原图文件将保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # This would typically delete from database and remove thumbnail file
            self.logger.info("Deleting photo thumbnail: photo_id=%d", photo_id)
            self.photos_updated.emit()
    
    def delete_single_photo(self, photo_id: int):
        """Delete single photo (thumbnail and original)."""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这张照片吗？\n这将删除缩略图和原图文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # This would typically delete from database and remove files
            self.logger.info("Deleting single photo: photo_id=%d", photo_id)
            self.photos_updated.emit()
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.update_columns()
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for drag and drop."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if not self.drag_start_position:
            return
        
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        # Get selected photos
        selected_photos = self.get_selected_photos()
        if not selected_photos:
            return
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Add file paths to mime data
        file_paths = []
        for photo in selected_photos:
            filepath = photo.get("filepath", "")
            if filepath and Path(filepath).exists():
                file_paths.append(filepath)
        
        if file_paths:
            mime_data.setUrls([QUrl.fromLocalFile(path) for path in file_paths])
        drag.setMimeData(mime_data)
        
            # Start drag
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events."""
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls]
        
        # This would typically handle file import
        self.logger.info("Files dropped: count=%d", len(file_paths))
        event.acceptProposedAction()

    def on_scroll(self, value):
        """处理滚动事件，实现无限滚动加载（带节流）"""
        # 节流处理：避免频繁触发
        if abs(value - self.last_scroll_value) < 50:  # 滚动距离小于50像素时不处理
            return
        
        self.last_scroll_value = value
        
        # 如果已经有待处理的滚动事件，不重复设置
        if self.pending_scroll_event:
            return
        
        self.pending_scroll_event = True
        self.scroll_throttle_timer.start(100)  # 100ms节流
    
    def process_scroll_event(self):
        """处理节流后的滚动事件"""
        self.pending_scroll_event = False
        
        scrollbar = self.verticalScrollBar()
        if not scrollbar:
            return
        
        # 检查是否滚动到底部
        if scrollbar.value() >= scrollbar.maximum() - 200:  # 距离底部200像素时开始加载
            self.load_next_page()
        
        # 检查是否需要优化可见项
        if len(self.thumbnail_items) > self.max_visible_items:
            # 立即优化，不等待定时器
            self.optimize_visible_items()
    
    def load_next_page(self):
        """加载下一页照片"""
        if not self.photos:
            return
        
        total_pages = (len(self.photos) + self.page_size - 1) // self.page_size
        
        if self.current_page < total_pages - 1:
            next_page = self.current_page + 1
            self.append_page(next_page)
            self.current_page = next_page
            
            # 开始异步加载新页的缩略图
            self.load_page_thumbnails_async(next_page)
    
    def append_page(self, page: int):
        """追加显示指定页的缩略图（使用缓存优化）"""
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.photos))
        
        # 计算当前网格的行数
        current_rows = len(self.thumbnail_items) // self.columns
        if len(self.thumbnail_items) % self.columns != 0:
            current_rows += 1
        
        # 创建新页的缩略图项（使用缓存）
        for i in range(start_idx, end_idx):
            photo = self.photos[i]
            row = current_rows + (i - start_idx) // self.columns
            col = (i - start_idx) % self.columns
            
            # 使用缓存创建缩略图项
            thumbnail_item = self.create_thumbnail_item(photo)
            thumbnail_item.clicked.connect(self.on_thumbnail_clicked)
            thumbnail_item.context_menu_requested.connect(self.show_context_menu)
            
            self.grid_layout.addWidget(thumbnail_item, row, col)
            self.thumbnail_items.append(thumbnail_item)
        
        # 更新可见范围
        self.visible_range = (0, len(self.thumbnail_items))
    
    def load_page_thumbnails_async(self, page: int):
        """异步加载指定页的缩略图"""
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.photos))
        
        # 将新页的缩略图加入加载队列
        for i in range(start_idx, end_idx):
            if i < len(self.photos):
                self.loading_queue.append(i)
        
        # 启动加载定时器
        if not self.loading_timer.isActive():
            self.loading_timer.start()
    
    def create_thumbnail_item(self, photo: Dict[str, Any]) -> ThumbnailItem:
        """创建缩略图项（使用缓存优化）"""
        # 尝试从缓存中获取
        if self.thumbnail_item_cache:
            try:
                item = self.thumbnail_item_cache.pop()
                # 重新初始化项
                item.photo_data = photo
                item.photo_id = photo.get("id", 0)
                item.is_selected = False
                item.thumbnail_loaded = False
                item._ui_initialized = False  # 重置UI初始化状态
                item.show()  # 显示项
                item.show_loading_placeholder()
                return item
            except RuntimeError as e:
                # 如果缓存项已被删除，创建新项
                self.logger.warning("Cached thumbnail item deleted, creating new one: %s", str(e))
                return ThumbnailItem(photo)
        
        # 缓存为空，创建新项
        return ThumbnailItem(photo)
    
    def recycle_thumbnail_item(self, item: ThumbnailItem):
        """回收缩略图项到缓存"""
        try:
            if len(self.thumbnail_item_cache) < self.max_cache_size:
                # 清理项的状态
                item.photo_data = {}
                item.photo_id = 0
                item.is_selected = False
                item.thumbnail_loaded = False
                item.hide()
                self.thumbnail_item_cache.append(item)
            else:
                # 缓存已满，直接删除
                item.deleteLater()
        except RuntimeError as e:
            # 如果item已经被删除，忽略错误
            self.logger.warning("Failed to recycle thumbnail item: %s", str(e))

    def check_visibility_and_optimize(self):
        """检查可见性并优化内存使用"""
        if not self.photos or not self.thumbnail_items:
            return
        
        # 如果可见项数量超过限制，回收不可见的项
        if len(self.thumbnail_items) > self.max_visible_items:
            self.optimize_visible_items()
    
    def optimize_visible_items(self):
        """优化可见项，回收不可见的项"""
        if not self.thumbnail_items:
            return
        
        # 计算当前可见区域
        scrollbar = self.verticalScrollBar()
        if not scrollbar:
            return
        
        viewport_height = self.viewport().height()
        scroll_value = scrollbar.value()
        
        # 计算可见范围（扩大一些以提供缓冲）
        buffer_height = 200  # 缓冲区高度
        visible_start = max(0, scroll_value - buffer_height)
        visible_end = scroll_value + viewport_height + buffer_height
        
        # 计算每个项的大概位置
        item_height = 200  # 缩略图项高度（包含间距）
        items_per_row = self.columns
        
        # 回收不可见的项
        items_to_remove = []
        for i, item in enumerate(self.thumbnail_items):
            row = i // items_per_row
            item_top = row * item_height
            item_bottom = item_top + item_height
            
            # 如果项完全不可见，标记为回收
            if item_bottom < visible_start or item_top > visible_end:
                items_to_remove.append((i, item))
        
        # 从后往前移除，避免索引变化
        for i, item in reversed(items_to_remove):
            self.grid_layout.removeWidget(item)
            self.thumbnail_items.pop(i)
            self.recycle_thumbnail_item(item)
        
        if items_to_remove:
            self.logger.info("Optimized visible items: removed_count=%s", len(items_to_remove),
                           remaining_count=len(self.thumbnail_items))
    
    def start_visibility_monitoring(self):
        """开始可见性监控"""
        if not self.visibility_timer.isActive():
            self.visibility_timer.start()
    
    def stop_visibility_monitoring(self):
        """停止可见性监控"""
        if self.visibility_timer.isActive():
            self.visibility_timer.stop()