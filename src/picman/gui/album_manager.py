"""
Album management UI components.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit, QTextEdit,
    QMessageBox, QInputDialog, QMenu, QFrame, QSplitter,
    QFileDialog, QCheckBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QContextMenuEvent
import structlog
from PyQt6.QtWidgets import QApplication # Added for QApplication.processEvents()

from ..database.manager import DatabaseManager
from ..core.photo_manager import PhotoManager
from .thumbnail_widget import ThumbnailWidget


class AlbumListItem(QListWidgetItem):
    """Album list item for display in the album list."""
    
    def __init__(self, album_data: Dict[str, Any]):
        # Create checkbox text
        checkbox_text = f"☐ {album_data.get('name', 'Unnamed Album')}"
        super().__init__(checkbox_text)
        self.album_id = album_data.get("id", 0)
        self.album_data = album_data
        self.is_selected = False
        
        # Set tooltip with album info
        description = album_data.get("description", "")
        photo_count = album_data.get("photo_count", 0)
        tooltip = f"{album_data.get('name')}\n{description}\n{photo_count} photos"
        self.setToolTip(tooltip)
    
    def set_selected(self, selected: bool):
        """Set the selection state and update checkbox."""
        self.is_selected = selected
        name = self.album_data.get('name', 'Unnamed Album')
        if selected:
            self.setText(f"☑ {name}")
        else:
            self.setText(f"☐ {name}")


class AlbumDialog(QDialog):
    """Dialog for creating or editing an album."""
    
    def __init__(self, parent=None, album_data: Optional[Dict[str, Any]] = None, photo_manager=None):
        super().__init__(parent)
        self.album_data = album_data or {}
        self.photo_manager = photo_manager
        self.selected_directory = ""
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("相册属性" if self.album_data else "创建相册")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Album name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.album_data.get("name", ""))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Album description
        layout.addWidget(QLabel("描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.album_data.get("description", ""))
        self.description_edit.setMaximumHeight(100)
        layout.addWidget(self.description_edit)
        
        # Directory selection (only for new albums)
        if not self.album_data:
            layout.addWidget(QLabel("关联图片目录 (可选):"))
            
            # Directory selection
            dir_layout = QHBoxLayout()
            self.dir_edit = QLineEdit()
            self.dir_edit.setPlaceholderText("选择包含图片的目录...")
            self.dir_edit.setReadOnly(True)
            dir_layout.addWidget(self.dir_edit)
            
            self.browse_btn = QPushButton("浏览...")
            self.browse_btn.clicked.connect(self.browse_directory)
            dir_layout.addWidget(self.browse_btn)
            
            layout.addLayout(dir_layout)
            
            # Import option
            self.import_checkbox = QCheckBox("创建相册时自动导入选中目录的图片")
            self.import_checkbox.setChecked(True)
            layout.addWidget(self.import_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("保存" if self.album_data else "创建")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def browse_directory(self):
        """Browse for a directory to associate with the album."""
        directory = QFileDialog.getExistingDirectory(
            self, "选择图片目录", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.selected_directory = directory
            self.dir_edit.setText(directory)
    
    def get_album_data(self) -> Dict[str, Any]:
        """Get the album data from the dialog."""
        self.album_data["name"] = self.name_edit.text()
        self.album_data["description"] = self.description_edit.toPlainText()
        if not self.album_data.get("id"):  # New album
            self.album_data["directory"] = self.selected_directory
            self.album_data["import_on_create"] = self.import_checkbox.isChecked()
        return self.album_data


class AlbumManager(QWidget):
    """Album management widget."""
    
    album_selected = pyqtSignal(int)  # album_id
    photos_updated = pyqtSignal()
    photo_selected = pyqtSignal(int) # photo_id
    
    def __init__(self, db_manager: DatabaseManager, photo_manager: PhotoManager):
        super().__init__()
        self.db_manager = db_manager
        self.photo_manager = photo_manager
        self.current_album_id = None
        self.logger = structlog.get_logger("picman.gui.album_manager")
        
        self.init_ui()
        self.load_albums()
        
        # 信号连接已在init_ui中完成
        self.logger.info("Album manager initialized")
    
    def on_thumbnail_photo_selected(self, photo_id: int):
        """Handle photo selection from thumbnail widget."""
        self.logger.info("Thumbnail photo selected", photo_id=photo_id)
        # Emit signal to main window to display photo
        self.photo_selected.emit(photo_id)
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create splitter for album list and photos
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Album list panel (1区 - 相册管理区)
        album_panel = QFrame()
        album_layout = QVBoxLayout(album_panel)
        
        # Album list header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>相册管理</b>"))
        
        # Album actions
        self.add_album_btn = QPushButton("新建相册")
        self.add_album_btn.clicked.connect(self.create_album)
        header_layout.addWidget(self.add_album_btn)
        
        self.remove_album_btn = QPushButton("移除相册")
        self.remove_album_btn.clicked.connect(self.remove_current_album)
        self.remove_album_btn.setEnabled(False)
        header_layout.addWidget(self.remove_album_btn)
        
        album_layout.addLayout(header_layout)
        
        # Album list
        self.album_list = QListWidget()
        self.album_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.album_list.customContextMenuRequested.connect(self.show_album_context_menu)
        self.album_list.itemClicked.connect(self.on_album_selected)
        self.album_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # 改为单选
        album_layout.addWidget(self.album_list)
        
        splitter.addWidget(album_panel)
        
        # Album photos panel (2区 - 相册照片区)
        photos_panel = QFrame()
        photos_layout = QVBoxLayout(photos_panel)
        
        # Photos header
        photos_header = QHBoxLayout()
        self.album_title_label = QLabel("<b>相册照片</b>")
        photos_header.addWidget(self.album_title_label)
        
        # Photo actions
        self.add_photos_btn = QPushButton("添加照片")
        self.add_photos_btn.clicked.connect(self.add_photos_to_album)
        self.add_photos_btn.setEnabled(False)
        photos_header.addWidget(self.add_photos_btn)
        
        # Import tags button
        self.import_tags_btn = QPushButton("导入标签")
        self.import_tags_btn.clicked.connect(self.import_tags_from_files)
        self.import_tags_btn.setEnabled(False)
        photos_header.addWidget(self.import_tags_btn)
        
        photos_layout.addLayout(photos_header)
        
        # Thumbnail grid for album photos
        self.thumbnail_widget = ThumbnailWidget()
        self.thumbnail_widget.selection_changed.connect(self.on_photo_selection_changed)
        self.thumbnail_widget.photo_selected.connect(self.on_thumbnail_photo_selected)  # 直接连接信号
        self.thumbnail_widget.set_multi_select_mode(False)  # 启用单选模式
        photos_layout.addWidget(self.thumbnail_widget)
        
        # Operation buttons (2区下方 - 操作按钮)
        self.create_operation_buttons(photos_layout)
        
        splitter.addWidget(photos_panel)
        
        # Set initial splitter sizes
        splitter.setSizes([200, 600])
    
    def create_operation_buttons(self, layout):
        """Create operation buttons for photo management."""
        button_layout = QHBoxLayout()
        
        # Multi-select mode button
        self.multi_select_btn = QPushButton("多选模式")
        self.multi_select_btn.setCheckable(True)
        self.multi_select_btn.setChecked(False)  # Default to single-select mode
        self.multi_select_btn.clicked.connect(self.toggle_multi_select_mode)
        button_layout.addWidget(self.multi_select_btn)
        
        button_layout.addStretch()  # Add spacing
        
        # Delete thumbnail button
        self.delete_thumbnail_btn = QPushButton("删除缩略图")
        self.delete_thumbnail_btn.clicked.connect(self.delete_selected_thumbnails)
        self.delete_thumbnail_btn.setEnabled(False)
        button_layout.addWidget(self.delete_thumbnail_btn)
        
        # Delete original button
        self.delete_original_btn = QPushButton("删除原图")
        self.delete_original_btn.clicked.connect(self.delete_selected_originals)
        self.delete_original_btn.setEnabled(False)
        button_layout.addWidget(self.delete_original_btn)
        
        # Export original button
        self.export_original_btn = QPushButton("导出原图")
        self.export_original_btn.clicked.connect(self.export_selected_originals)
        self.export_original_btn.setEnabled(False)
        button_layout.addWidget(self.export_original_btn)
        
        # Export thumbnail button
        self.export_thumbnail_btn = QPushButton("导出缩略图")
        self.export_thumbnail_btn.clicked.connect(self.export_selected_thumbnails)
        self.export_thumbnail_btn.setEnabled(False)
        button_layout.addWidget(self.export_thumbnail_btn)
        
        layout.addLayout(button_layout)
    
    def toggle_multi_select_mode(self):
        """Toggle multi-select mode."""
        is_multi_select = self.multi_select_btn.isChecked()
        self.thumbnail_widget.set_multi_select_mode(is_multi_select)
        
        if is_multi_select:
            self.multi_select_btn.setText("多选模式")
            self.multi_select_btn.setStyleSheet("background-color: #3498db; color: white;")
        else:
            self.multi_select_btn.setText("单选模式")
            self.multi_select_btn.setStyleSheet("")
    
    def on_photo_selection_changed(self, selected_ids: list):
        """Handle photo selection change."""
        has_selection = len(selected_ids) > 0
        
        # 检查按钮是否存在后再设置状态
        if hasattr(self, 'delete_thumbnail_btn'):
            self.delete_thumbnail_btn.setEnabled(has_selection)
        if hasattr(self, 'delete_original_btn'):
            self.delete_original_btn.setEnabled(has_selection)
        if hasattr(self, 'export_original_btn'):
            self.export_original_btn.setEnabled(has_selection)
        if hasattr(self, 'export_thumbnail_btn'):
            self.export_thumbnail_btn.setEnabled(has_selection)
        if hasattr(self, 'import_tags_btn'):
            # 导入标签按钮在有选中图片或有当前相册时都可以启用
            self.import_tags_btn.setEnabled(has_selection or self.current_album_id is not None)
    
    def delete_selected_thumbnails(self):
        """Delete selected photo thumbnails from database."""
        selected_photos = self.thumbnail_widget.get_selected_photos()
        if not selected_photos:
            return
        
        reply = QMessageBox.question(
            self, "确认删除缩略图", 
            f"确定要删除选中的 {len(selected_photos)} 张照片的缩略图吗？\n原图文件不会被删除，但数据库中的图片信息将被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for photo in selected_photos:
                photo_id = photo.get("id")
                if photo_id:
                    try:
                        # Delete thumbnail file
                        thumbnail_path = photo.get("thumbnail_path", "")
                        if thumbnail_path and Path(thumbnail_path).exists():
                            Path(thumbnail_path).unlink()
                        
                        # Delete from database
                        self.db_manager.delete_photo(photo_id)
                        deleted_count += 1
                        
                    except Exception as e:
                        self.logger.error("Failed to delete thumbnail", 
                                        photo_id=photo_id, error=str(e))
            
            # Refresh display
            if self.current_album_id:
                self.load_album_photos(self.current_album_id)
            
            QMessageBox.information(self, "删除完成", f"成功删除 {deleted_count} 张照片的缩略图和数据库信息")
    
    def delete_selected_originals(self):
        """Delete selected original photos with confirmation."""
        selected_photos = self.thumbnail_widget.get_selected_photos()
        if not selected_photos:
            return
        
        reply = QMessageBox.question(
            self, "确认删除原图", 
            f"确定要删除选中的 {len(selected_photos)} 张照片的原图文件吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Ask about database deletion
            db_reply = QMessageBox.question(
                self, "数据库删除确认", 
                "是否同时删除数据库中的缩略图和图片信息？\n选择'是'将删除所有相关信息，选择'否'将保留数据库信息。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            # Second confirmation for destructive action
            reply2 = QMessageBox.warning(
                self, "最终确认", 
                "这是最终确认！原图文件将被永久删除，确定要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply2 == QMessageBox.StandardButton.Yes:
                deleted_count = 0
                for photo in selected_photos:
                    photo_id = photo.get("id")
                    filepath = photo.get("filepath", "")
                    
                    if filepath and Path(filepath).exists():
                        try:
                            # Delete original file
                            Path(filepath).unlink()
                            
                            # Delete from database if requested
                            if db_reply == QMessageBox.StandardButton.Yes:
                                # Delete thumbnail file
                                thumbnail_path = photo.get("thumbnail_path", "")
                                if thumbnail_path and Path(thumbnail_path).exists():
                                    Path(thumbnail_path).unlink()
                                
                                # Delete from database
                                self.db_manager.delete_photo(photo_id)
                            
                            deleted_count += 1
                            self.logger.info("Deleted original photo", 
                                           photo_id=photo_id, filepath=filepath)
                        except Exception as e:
                            self.logger.error("Failed to delete original photo", 
                                            photo_id=photo_id, error=str(e))
                
                # Refresh display
                if self.current_album_id:
                    self.load_album_photos(self.current_album_id)
                
                QMessageBox.information(self, "删除完成", f"成功删除 {deleted_count} 张原图文件")
    
    def export_selected_originals(self):
        """Export selected original photos."""
        selected_photos = self.thumbnail_widget.get_selected_photos()
        if not selected_photos:
            return
        
        # Get export directory
        export_dir = QFileDialog.getExistingDirectory(
            self, "选择导出目录", "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if export_dir:
            exported_count = 0
            for photo in selected_photos:
                filepath = photo.get("filepath", "")
                if filepath and Path(filepath).exists():
                    try:
                        # Copy original file to export directory
                        dest_path = Path(export_dir) / Path(filepath).name
                        import shutil
                        shutil.copy2(filepath, dest_path)
                        exported_count += 1
                    except Exception as e:
                        self.logger.error("Failed to export original photo", 
                                        photo_id=photo.get("id"), error=str(e))
            
            QMessageBox.information(self, "导出完成", f"成功导出 {exported_count} 张原图")
    
    def export_selected_thumbnails(self):
        """Export selected photo thumbnails."""
        selected_photos = self.thumbnail_widget.get_selected_photos()
        if not selected_photos:
            return
        
        # Get export directory
        export_dir = QFileDialog.getExistingDirectory(
            self, "选择导出目录", "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if export_dir:
            exported_count = 0
            for photo in selected_photos:
                thumbnail_path = photo.get("thumbnail_path", "")
                if thumbnail_path and Path(thumbnail_path).exists():
                    try:
                        # Copy thumbnail file to export directory
                        dest_path = Path(export_dir) / f"thumb_{Path(photo.get('filename', 'unknown'))}"
                        import shutil
                        shutil.copy2(thumbnail_path, dest_path)
                        exported_count += 1
                    except Exception as e:
                        self.logger.error("Failed to export thumbnail", 
                                        photo_id=photo.get("id"), error=str(e))
            
            QMessageBox.information(self, "导出完成", f"成功导出 {exported_count} 张缩略图")

    def load_albums(self):
        """Load albums from database."""
        try:
            self.album_list.clear()
            
            # Get albums from database
            albums = self.db_manager.get_all_albums()
            
            for album in albums:
                item = AlbumListItem(album)
                self.album_list.addItem(item)
            
            self.logger.info("Loaded albums", count=len(albums))
            
        except Exception as e:
            self.logger.error("Failed to load albums", error=str(e))
            QMessageBox.critical(self, "加载失败", f"加载相册时发生错误：{str(e)}")
    
    def create_album(self):
        """Create a new album."""
        dialog = AlbumDialog(self, photo_manager=self.photo_manager)
        if dialog.exec():
            album_data = dialog.get_album_data()
            
            try:
                # Create album in database
                album_id = self.db_manager.create_album(album_data)
                
                # Import photos from directory if specified
                if album_data.get("import_on_create") and album_data.get("directory"):
                    self.import_photos_from_directory(album_data["directory"], album_id)
                
                # Refresh album list
                self.load_albums()
                
                # Select the new album
                self.select_album(album_id)
                
                self.logger.info("Album created successfully", 
                               album_id=album_id, 
                               name=album_data["name"])
                
            except Exception as e:
                self.logger.error("Failed to create album", 
                                name=album_data.get("name"), 
                                error=str(e))
                QMessageBox.critical(self, "创建失败", f"创建相册时发生错误：{str(e)}")
    
    def import_photos_from_directory(self, directory: str, album_id: int):
        """Import photos from a directory into the album."""
        try:
            # Show progress dialog
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("导入图片")
            progress_dialog.setFixedSize(400, 150)
            progress_dialog.setModal(True)
            
            layout = QVBoxLayout(progress_dialog)
            layout.addWidget(QLabel(f"正在从目录导入图片:\n{directory}"))
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 0)  # Indeterminate progress
            layout.addWidget(progress_bar)
            
            # Show dialog
            progress_dialog.show()
            QApplication.processEvents()
            
            # Import photos using photo manager
            result = self.photo_manager.import_directory(directory, recursive=True, album_id=album_id)
            
            # Close progress dialog
            progress_dialog.close()
            
            if result["success"]:
                imported_count = result["imported"]
                self.logger.info("Photos imported from directory", 
                               album_id=album_id, 
                               count=imported_count, 
                               directory=directory)
                
                # Refresh album photos
                self.load_album_photos(album_id)
                
                QMessageBox.information(self, "导入完成", 
                                       f"成功导入 {imported_count} 张照片到相册")
            else:
                QMessageBox.warning(self, "导入失败", 
                                   f"导入照片时发生错误：{result.get('error', '未知错误')}")
                
        except Exception as e:
            self.logger.error("Failed to import photos from directory", 
                            directory=directory, 
                            album_id=album_id, 
                            error=str(e))
            QMessageBox.critical(self, "导入失败", f"导入照片时发生错误：{str(e)}")
    
    def edit_album(self, album_id: int):
        """Edit an existing album."""
        # Find the album item
        for i in range(self.album_list.count()):
            item = self.album_list.item(i)
            if isinstance(item, AlbumListItem) and item.album_id == album_id:
                dialog = AlbumDialog(self, item.album_data)
                if dialog.exec():
                    updated_data = dialog.get_album_data()
                    
                    # Update item
                    item.album_data = updated_data
                    item.setText(updated_data["name"])
                    
                    # Update tooltip
                    description = updated_data.get("description", "")
                    photo_count = updated_data.get("photo_count", 0)
                    tooltip = f"{updated_data['name']}\n{description}\n{photo_count} photos"
                    item.setToolTip(tooltip)
                    
                    # Update album title if this is the current album
                    if self.current_album_id == album_id:
                        self.album_title_label.setText(f"<b>{updated_data['name']}</b>")
                    
                    self.logger.info("Album updated", name=updated_data["name"])
                break
    
    def remove_current_album(self):
        """Remove the currently selected album."""
        selected_items = self.album_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要移除的相册")
            return
        
        selected_album_ids = [item.album_id for item in selected_items if isinstance(item, AlbumListItem)]
        if not selected_album_ids:
            QMessageBox.information(self, "提示", "请先选择要移除的相册")
            return
        
        # Get album names for confirmation
        album_names = []
        for item in selected_items:
            if isinstance(item, AlbumListItem):
                album_names.append(item.album_data.get('name', 'Unknown Album'))
        
        album_names_text = ", ".join(album_names)
        
        reply = QMessageBox.question(
            self, "确认移除相册", 
            f"确定要移除选中的 {len(selected_album_ids)} 个相册吗？\n\n"
            f"相册：{album_names_text}\n\n"
            "注意：此操作只会移除相册记录，不会删除原始图片文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success_count = 0
                failed_albums = []
                
                # Remove albums one by one
                for album_id in selected_album_ids:
                    try:
                        # Remove album-photo associations but keep photos in database
                        if self.db_manager.remove_album_photos(album_id):
                            if self.db_manager.delete_album(album_id):
                                success_count += 1
                                self.logger.info("Successfully removed album", album_id=album_id)
                            else:
                                failed_albums.append(f"相册ID {album_id} (删除失败)")
                                self.logger.error("Failed to delete album", album_id=album_id)
                        else:
                            failed_albums.append(f"相册ID {album_id} (移除照片关联失败)")
                            self.logger.error("Failed to remove album photos", album_id=album_id)
                    except Exception as e:
                        failed_albums.append(f"相册ID {album_id} (错误: {str(e)})")
                        self.logger.error("Exception while removing album", album_id=album_id, error=str(e))
                
                # Clear current album if it was removed
                if self.current_album_id in selected_album_ids:
                    self.current_album_id = None
                    self.album_title_label.setText("<b>相册照片</b>")
                    self.thumbnail_widget.display_photos([])
                    self.add_photos_btn.setEnabled(False)
                    self.remove_album_btn.setEnabled(False)
                
                # Refresh album list
                self.load_albums()
                
                # Show results
                if success_count == len(selected_album_ids):
                    QMessageBox.information(self, "移除完成", 
                                          f"成功移除 {success_count} 个相册，原始图片文件已保留")
                else:
                    message = f"部分移除完成\n成功: {success_count} 个\n失败: {len(failed_albums)} 个"
                    if failed_albums:
                        message += f"\n\n失败的相册:\n" + "\n".join(failed_albums)
                    QMessageBox.warning(self, "移除结果", message)
                
                self.logger.info("Album removal completed", 
                               total=len(selected_album_ids), 
                               success=success_count, 
                               failed=len(failed_albums))
                
            except Exception as e:
                self.logger.error("Failed to remove albums", album_ids=selected_album_ids, error=str(e))
                QMessageBox.critical(self, "移除失败", f"移除相册时发生错误：{str(e)}")
        else:
            self.logger.info("Album removal cancelled", album_ids=selected_album_ids)

    def delete_album(self, album_id: int):
        """Delete an album without deleting original files."""
        try:
            # Get album info
            album = self.db_manager.get_album(album_id)
            if not album:
                return
            
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, "确认删除相册", 
                f"确定要删除相册 '{album.get('name', 'Unknown')}' 吗？\n\n"
                "注意：此操作只会删除相册记录，不会删除原始图片文件。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Remove album-photo associations but keep photos in database
                self.db_manager.remove_album_photos(album_id)
                
                # Delete album record
                self.db_manager.delete_album(album_id)
                
                # Refresh album list
                self.load_albums()
                
                # Clear current album if it was deleted
                if self.current_album_id == album_id:
                    self.current_album_id = None
                    self.album_title_label.setText("<b>相册照片</b>")
                    self.thumbnail_widget.display_photos([])
                    self.add_photos_btn.setEnabled(False)
                
                self.logger.info("Album deleted", album_id=album_id, album_name=album.get('name'))
                QMessageBox.information(self, "删除完成", "相册删除完成，原始图片文件已保留")
                
        except Exception as e:
            self.logger.error("Failed to delete album", album_id=album_id, error=str(e))
            QMessageBox.critical(self, "删除失败", f"删除相册时发生错误：{str(e)}")
    
    def select_album(self, album_id: int):
        """Select an album by ID."""
        for i in range(self.album_list.count()):
            item = self.album_list.item(i)
            if isinstance(item, AlbumListItem) and item.album_id == album_id:
                self.album_list.setCurrentItem(item)
                self.on_album_selected(item)
                break

    def on_album_selected(self, item):
        """Handle album selection."""
        if isinstance(item, AlbumListItem):
            # Update checkbox state for all items
            for i in range(self.album_list.count()):
                list_item = self.album_list.item(i)
                if isinstance(list_item, AlbumListItem):
                    is_selected = list_item in self.album_list.selectedItems()
                    list_item.set_selected(is_selected)
            
            # Get all selected albums
            selected_items = self.album_list.selectedItems()
            
            if len(selected_items) == 1:
                # Single selection
                self.current_album_id = item.album_id
                self.album_title_label.setText(f"<b>{item.album_data.get('name', 'Unknown')}</b>")
                self.add_photos_btn.setEnabled(True)
                self.import_tags_btn.setEnabled(True)
                self.remove_album_btn.setEnabled(True)
                
                # Load album photos
                self.load_album_photos(item.album_id)
                
                # Emit signal
                self.album_selected.emit(item.album_id)
                
                self.logger.info("Album selected", album_id=item.album_id)
            else:
                # Multiple selection
                selected_album_ids = [item.album_id for item in selected_items if isinstance(item, AlbumListItem)]
                self.current_album_id = None  # No single current album
                self.album_title_label.setText(f"<b>多个相册 ({len(selected_album_ids)} 个)</b>")
                self.add_photos_btn.setEnabled(False)  # Can't add to multiple albums
                self.import_tags_btn.setEnabled(False)  # Can't import to multiple albums
                self.remove_album_btn.setEnabled(True)
                
                # Load photos from all selected albums
                self.load_multiple_albums_photos(selected_album_ids)
                
                self.logger.info("Multiple albums selected", album_ids=selected_album_ids)
    
    def load_album_photos(self, album_id: int):
        """Load photos for the selected album."""
        try:
            # Get photos from database
            photos = self.db_manager.get_album_photos(album_id)
            
            # Display photos in thumbnail widget
            self.thumbnail_widget.display_photos(photos)
            
            # Update album title
            album = self.db_manager.get_album(album_id)
            if album:
                self.album_title_label.setText(f"<b>{album.get('name', 'Unknown')} ({len(photos)} 张照片)</b>")
            
            self.logger.info("Loaded album photos", album_id=album_id, count=len(photos))
            
        except Exception as e:
            self.logger.error("Failed to load album photos", album_id=album_id, error=str(e))
            QMessageBox.critical(self, "加载失败", f"加载相册照片时发生错误：{str(e)}")
    
    def load_multiple_albums_photos(self, album_ids: List[int]):
        """Load photos from multiple albums."""
        try:
            all_photos = []
            for album_id in album_ids:
                photos = self.db_manager.get_album_photos(album_id)
                all_photos.extend(photos)
            
            # Display all photos in thumbnail widget
            self.thumbnail_widget.display_photos(all_photos)
            
            self.logger.info("Loaded multiple albums photos", album_ids=album_ids, count=len(all_photos))
            
        except Exception as e:
            self.logger.error("Failed to load multiple albums photos", album_ids=album_ids, error=str(e))
            QMessageBox.critical(self, "加载失败", f"加载多个相册照片时发生错误：{str(e)}")
    
    def add_photos_to_album(self):
        """Add photos to the current album."""
        if not self.current_album_id:
            return
        
        # In a real implementation, this would show a photo selector
        QMessageBox.information(self, "Add Photos", 
                              "Photo selector not implemented yet.")
    
    def import_tags_from_files(self):
        """Import tags from files for selected photos or current album."""
        try:
            # 获取选中的图片路径
            selected_photo_paths = []
            
            # 检查是否有选中的图片
            selected_photos = self.thumbnail_widget.get_selected_photos()
            if selected_photos:
                # 获取选中图片的路径
                for photo in selected_photos:
                    photo_id = photo.get("id")
                    if photo_id:
                        photo_path = self.get_photo_path_by_id(photo_id)
                        if photo_path:
                            selected_photo_paths.append(photo_path)
            
            # 如果没有选中图片，则处理当前相册的所有图片
            if not selected_photo_paths and self.current_album_id:
                selected_photo_paths = self.get_all_photos_in_album(self.current_album_id)
            
            if not selected_photo_paths:
                QMessageBox.warning(self, "警告", "请先选择图片或相册")
                return
            
            # 导入标签对话框
            from src.picman.gui.tag_import_dialog import TagImportDialog
            dialog = TagImportDialog(selected_photo_paths, self.db_manager, self)
            
            if dialog.exec() == TagImportDialog.DialogCode.Accepted:
                # 导入成功，刷新显示
                self.load_album_photos(self.current_album_id)
                self.photos_updated.emit()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入标签失败: {str(e)}")
    
    def get_photo_path_by_id(self, photo_id: int) -> Optional[str]:
        """根据图片ID获取图片路径"""
        try:
            query = "SELECT filepath FROM photos WHERE id = ?"
            result = self.db_manager.fetch_one(query, (photo_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"获取图片路径失败: {str(e)}")
            return None
    
    def get_all_photos_in_album(self, album_id: int) -> List[str]:
        """获取相册中所有图片的路径"""
        try:
            query = """
                SELECT p.filepath 
                FROM photos p 
                JOIN album_photos ap ON p.id = ap.photo_id 
                WHERE ap.album_id = ?
            """
            results = self.db_manager.fetch_all(query, (album_id,))
            return [row[0] for row in results] if results else []
        except Exception as e:
            print(f"获取相册图片失败: {str(e)}")
            return []
    
    def show_album_context_menu(self, position):
        """Show context menu for an album."""
        item = self.album_list.itemAt(position)
        if not item:
            return
        
        album_id = item.album_id if isinstance(item, AlbumListItem) else 0
        
        menu = QMenu(self)
        
        # Edit action
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.edit_album(album_id))
        menu.addAction(edit_action)
        
        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_album(album_id))
        menu.addAction(delete_action)
        
        menu.exec(self.album_list.mapToGlobal(position))