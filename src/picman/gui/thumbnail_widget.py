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
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, QUrl, QMimeData
from PyQt6.QtGui import QPixmap, QContextMenuEvent, QAction, QPainter, QFont, QDrag
import structlog


class ThumbnailItem(QFrame):
    """Individual thumbnail item widget."""
    
    clicked = pyqtSignal(int)  # photo_id
    context_menu_requested = pyqtSignal(int, object)  # photo_id, position
    
    def __init__(self, photo_data: Dict[str, Any]):
        super().__init__()
        self.photo_data = photo_data
        self.photo_id = photo_data.get("id", 0)
        self.logger = structlog.get_logger("picman.gui.thumbnail_item")
        self.is_selected = False
        
        self.init_ui()
        self.load_thumbnail()
    
    def init_ui(self):
        """Initialize the thumbnail item UI."""
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
    


    def set_selected(self, selected: bool):
        """Set the selection state of the thumbnail."""
        self.is_selected = selected
        
        if selected:
            # Highlight the thumbnail and show checkmark
            self.setStyleSheet("QFrame { border: 3px solid #3498db; background-color: #e8f4fc; }")
            # Show checkmark in bottom-right corner
            self.show_checkmark()
        else:
            # Reset to normal style and hide checkmark
            self.setStyleSheet("")
            self.hide_checkmark()
    
    def show_checkmark(self):
        """Show checkmark in bottom-right corner."""
        if not hasattr(self, 'checkmark_label'):
            self.checkmark_label = QLabel("✓", self)
            self.checkmark_label.setStyleSheet("""
                QLabel {
                    background-color: #27ae60;
                    color: white;
                    border-radius: 10px;
                    padding: 2px 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            self.checkmark_label.setFixedSize(20, 20)
            self.checkmark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Position in bottom-right corner
        self.checkmark_label.move(self.width() - 25, self.height() - 25)
        self.checkmark_label.show()
    
    def hide_checkmark(self):
        """Hide checkmark."""
        if hasattr(self, 'checkmark_label'):
            self.checkmark_label.hide()
    
    def load_thumbnail(self):
        """Load and display the thumbnail image."""
        try:
            thumbnail_path = self.photo_data.get("thumbnail_path", "")
            
            if thumbnail_path and Path(thumbnail_path).exists():
                # Load thumbnail
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    # Scale to fit
                    scaled = pixmap.scaled(
                        180, 135,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled)
                    return
            
            # Try to load original image as fallback
            filepath = self.photo_data.get("filepath", "")
            if filepath and Path(filepath).exists():
                pixmap = QPixmap(filepath)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        180, 135,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled)
                    return
            
            # Show placeholder with better styling
            self.image_label.setText("无图片")
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc; 
                    background-color: #f5f5f5;
                    color: #999;
                    font-size: 10px;
                }
            """)
            
        except Exception as e:
            self.logger.error("Failed to load thumbnail", 
                            photo_id=self.photo_id, 
                            error=str(e))
            self.image_label.setText("加载失败")
            self.image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ff9999; 
                    background-color: #fff5f5;
                    color: #cc0000;
                    font-size: 10px;
                }
            """)
    
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
    
    def __init__(self):
        super().__init__()
        self.photos = []
        self.thumbnail_items = []
        self.columns = 3
        self.selected_items = []
        self.logger = structlog.get_logger("picman.gui.thumbnail_widget")
        self.drag_start_position = None
        self.multi_select_mode = False
        self._displaying_photos = False
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the thumbnail widget UI."""
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Create container widget
        self.container = QWidget()
        self.setWidget(self.container)
        
        # Create grid layout
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Show placeholder
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder when no photos are loaded."""
        placeholder = QLabel("No photos to display")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-size: 14px;")
        self.grid_layout.addWidget(placeholder, 0, 0)
    
    def display_photos(self, photos: List[Dict[str, Any]]):
        """Display a list of photos as thumbnails."""
        try:
            # Prevent recursive calls
            if hasattr(self, '_displaying_photos') and self._displaying_photos:
                return
            self._displaying_photos = True
            
            # Clear existing thumbnails
            self.clear_thumbnails()
            
            self.photos = photos
            self.selected_items = []
            
            if not photos:
                self.show_placeholder()
                return
            
            # Calculate columns based on widget width
            self.update_columns()
            
            # Create thumbnail items
            for i, photo in enumerate(photos):
                row = i // self.columns
                col = i % self.columns
                
                thumbnail_item = ThumbnailItem(photo)
                thumbnail_item.clicked.connect(self.on_thumbnail_clicked)
                thumbnail_item.context_menu_requested.connect(self.show_context_menu)
                

                
                self.grid_layout.addWidget(thumbnail_item, row, col)
                self.thumbnail_items.append(thumbnail_item)
            
            self.logger.info("Displayed thumbnails", count=len(photos), multi_select_mode=self.multi_select_mode)
            
        except Exception as e:
            self.logger.error("Failed to display photos", error=str(e))
        finally:
            self._displaying_photos = False
    
    def clear_thumbnails(self):
        """Clear all thumbnail items."""
        # Remove all widgets from layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.thumbnail_items.clear()
    
    def update_columns(self):
        """Update number of columns based on widget width."""
        widget_width = self.width()
        item_width = 220  # thumbnail width + margins
        
        new_columns = max(1, widget_width // item_width)
        
        if new_columns != self.columns:
            self.columns = new_columns
            # Redisplay photos with new column count
            if self.photos and hasattr(self, '_displaying_photos') and not self._displaying_photos:
                self._displaying_photos = True
                self.display_photos(self.photos)
                self._displaying_photos = False
    
    def on_thumbnail_clicked(self, photo_id: int):
        """Handle thumbnail click events."""
        self.logger.info("Thumbnail clicked", photo_id=photo_id, multi_select_mode=self.multi_select_mode)
        
        if self.multi_select_mode:
            # In multi-select mode, toggle selection
            self.toggle_item_selection(photo_id)
        else:
            # In single-select mode, emit selection signal
            self.logger.info("Emitting photo_selected signal", photo_id=photo_id)
            self.photo_selected.emit(photo_id)
            
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_items)
    
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
        """Select a single item."""
        for item in self.thumbnail_items:
            if item.photo_id == photo_id:
                item.set_selected(True)
                self.selected_items = [photo_id]
                break
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_items.copy())
    
    def clear_selection(self):
        """Clear all selected items."""
        for item in self.thumbnail_items:
            item.set_selected(False)
        self.selected_items = []
        
        # Emit selection changed signal
        self.selection_changed.emit(self.selected_items.copy())
    
    def select_all(self):
        """Select all displayed photos."""
        self.selected_items = []
        for item in self.thumbnail_items:
            item.set_selected(True)
            self.selected_items.append(item.photo_id)
        
        self.selection_changed.emit(self.selected_items)
        self.logger.info("Selected all photos", count=len(self.selected_items))
    
    def deselect_all(self):
        """Deselect all photos."""
        self.clear_selection()
        self.selection_changed.emit(self.selected_items)
        self.logger.info("Deselected all photos")
    
    def set_multi_select_mode(self, enabled: bool):
        """Enable or disable multi-select mode."""
        self.multi_select_mode = enabled
        
        if not enabled:
            # Clear all selections when switching to single-select mode
            for item in self.thumbnail_items:
                item.set_selected(False)
            self.selected_items.clear()
            self.selection_changed.emit([])
    
    def on_thumbnail_selection_changed(self, photo_id: int, selected: bool):
        """Handle thumbnail selection change."""
        if selected and photo_id not in self.selected_items:
            self.selected_items.append(photo_id)
        elif not selected and photo_id in self.selected_items:
            self.selected_items.remove(photo_id)
        
        self.selection_changed.emit(self.selected_items.copy())
    
    def get_selected_photos(self) -> List[Dict[str, Any]]:
        """Get selected photo data."""
        selected_photos = []
        for photo in self.photos:
            if photo.get("id") in self.selected_items:
                selected_photos.append(photo)
        return selected_photos
    
    def show_context_menu(self, photo_id: int, position):
        """Show context menu for a photo."""
        # If the item is not already selected, select it
        if photo_id not in self.selected_items:
            self.clear_selection()
            self.select_item(photo_id)
            self.selection_changed.emit(self.selected_items)
        
        menu = QMenu(self)
        
        # View action
        view_action = QAction("View", self)
        view_action.triggered.connect(lambda: self.photo_selected.emit(photo_id))
        menu.addAction(view_action)
        
        menu.addSeparator()
        
        # Rating actions
        rating_menu = menu.addMenu("Set Rating")
        for i in range(6):
            rating_action = QAction(f"{i} Stars", self)
            rating_action.triggered.connect(lambda checked, r=i: self.set_rating(photo_id, r))
            rating_menu.addAction(rating_action)
        
        # Favorite action
        favorite_action = QAction("Toggle Favorite", self)
        favorite_action.triggered.connect(lambda: self.toggle_favorite(photo_id))
        menu.addAction(favorite_action)
        
        # Add to album action
        add_to_album_action = QAction("Add to Album...", self)
        add_to_album_action.triggered.connect(lambda: self.add_to_album(photo_id))
        menu.addAction(add_to_album_action)
        
        # Add tags action
        add_tags_action = QAction("添加标签...", self)
        add_tags_action.triggered.connect(lambda: self.add_tags(photo_id))
        menu.addAction(add_tags_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_photo(photo_id))
        menu.addAction(delete_action)
        
        menu.exec(position)
    
    def set_rating(self, photo_id: int, rating: int):
        """Set photo rating."""
        # In a real implementation, this would update the database
        self.logger.info("Set rating", photo_id=photo_id, rating=rating)
        self.photos_updated.emit()
    
    def toggle_favorite(self, photo_id: int):
        """Toggle photo favorite status."""
        # In a real implementation, this would update the database
        self.logger.info("Toggle favorite", photo_id=photo_id)
        self.photos_updated.emit()
    
    def add_to_album(self, photo_id: int):
        """Add photo to album."""
        # In a real implementation, this would show an album selector
        QMessageBox.information(self, "添加到相册", "相册选择器尚未实现。")
    
    def add_tags(self, photo_id: int):
        """Add tags to photo."""
        # In a real implementation, this would show a tag selector
        QMessageBox.information(self, "添加标签", "标签选择器尚未实现。")
    
    def delete_photo(self, photo_id: int):
        """Delete photo with confirmation."""
        reply = QMessageBox.question(
            self, "删除照片",
            f"确定要删除选中的 {len(self.selected_items)} 张照片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # In a real implementation, this would delete from database
            self.logger.info("Deleting photos", count=len(self.selected_items))
            QMessageBox.information(self, "删除照片", "照片删除成功。")
            # Refresh display
            self.clear_thumbnails()
    
    def delete_single_photo(self, photo_id: int):
        """Delete a single photo with confirmation."""
        reply = QMessageBox.question(
            self, "删除照片",
            "确定要删除这张照片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.update_columns()
    
    # Drag and drop support
    def mousePressEvent(self, event):
        """Handle mouse press events for drag and drop."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for drag and drop."""
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self.drag_start_position:
            return
        
        # Check if the mouse has moved far enough to start a drag
        if (event.position() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        
        # Only start drag if we have selected items
        if not self.selected_items:
            return
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Set data for internal use
        selected_ids = ",".join(map(str, self.selected_items))
        mime_data.setText(selected_ids)
        
        # If we have photo paths, add them as URLs for external drops
        urls = []
        for photo in self.get_selected_photos():
            if "filepath" in photo:
                urls.append(QUrl.fromLocalFile(photo["filepath"]))
        
        if urls:
            mime_data.setUrls(urls)
        
        drag.setMimeData(mime_data)
        
        # Set drag pixmap (thumbnail of first selected photo)
        if self.thumbnail_items:
            for item in self.thumbnail_items:
                if item.photo_id == self.selected_items[0]:
                    if hasattr(item, 'image_label') and item.image_label.pixmap():
                        pixmap = item.image_label.pixmap()
                        drag.setPixmap(pixmap.scaled(100, 75, Qt.AspectRatioMode.KeepAspectRatio))
                    break
        
        # Execute drag
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        # Accept drag events with files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events."""
        # Process dropped files
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                file_paths.append(file_path)
            
            if file_paths:
                self.logger.info("Files dropped", count=len(file_paths))
                # In a real implementation, this would import the files
                QMessageBox.information(self, "Import Files", 
                                      f"Would import {len(file_paths)} files.")
            
            event.acceptProposedAction()