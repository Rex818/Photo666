"""
Main application window for PyPhotoManager.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QSplitter, QFileDialog,
    QMessageBox, QProgressDialog, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QDockWidget, QFrame,
    QDialog, QGroupBox, QDateEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate, QByteArray
from PyQt6.QtGui import QAction, QIcon, QKeySequence
import structlog
from datetime import datetime

from ..config.manager import ConfigManager
from ..database.manager import DatabaseManager
from ..core.photo_manager import PhotoManager
from ..core.image_processor import ImageProcessor
from ..utils.logging import LoggingManager
from ..utils.language_manager import LanguageManager
from ..plugins.manager import PluginManager
from .photo_viewer import PhotoViewer
from .thumbnail_widget import ThumbnailWidget
from .album_manager import AlbumManager
from .tag_manager import TagManager
from .settings_dialog import SettingsDialog
from .batch_processor import BatchProcessorDialog
from .language_dialog import LanguageDialog
from .tag_import_dialog import TagImportDialog


class ImportWorker(QThread):
    """Worker thread for importing photos."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(dict)  # result
    error = pyqtSignal(str)
    
    def __init__(self, photo_manager: PhotoManager, directory: str, recursive: bool = True, album_id: Optional[int] = None):
        super().__init__()
        self.photo_manager = photo_manager
        self.directory = directory
        self.recursive = recursive
        self.album_id = album_id
    
    def run(self):
        try:
            result = self.photo_manager.import_directory(self.directory, self.recursive, self.album_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ImportWorkerWithTags(QThread):
    """Worker thread for importing photos with tag settings."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(dict)  # result
    error = pyqtSignal(str)
    
    def __init__(self, photo_manager: PhotoManager, directory: str, recursive: bool = True, album_id: Optional[int] = None, import_settings: Optional[dict] = None):
        super().__init__()
        self.photo_manager = photo_manager
        self.directory = directory
        self.recursive = recursive
        self.album_id = album_id
        self.import_settings = import_settings or {}
    
    def run(self):
        try:
            # 使用带标签设置的导入方法
            result = self.photo_manager.import_directory(
                self.directory, 
                self.recursive, 
                self.album_id, 
                self.import_settings
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.logging_manager = LoggingManager(self.config_manager.config)
        self.logger = self.logging_manager.setup_logging()
        
        # Initialize language manager and set language BEFORE UI creation
        self.language_manager = LanguageManager(self.config_manager)
        self.language_manager.initialize()
        
        # Set language immediately
        current_lang = self.config_manager.get("ui.language", "zh_CN")
        self.language_manager.set_language(current_lang)
        
        # Initialize database
        db_path = self.config_manager.get("database.path", "data/picman.db")
        self.db_manager = DatabaseManager(db_path, self.config_manager.config)
        
        # Initialize core components
        self.photo_manager = PhotoManager(self.config_manager, self.db_manager)
        self.image_processor = ImageProcessor(self.config_manager)
        
        # Initialize plugin manager
        self.plugin_manager = PluginManager(self.config_manager)
        self.plugin_manager.set_app_context({
            "config_manager": self.config_manager,
            "photo_manager": self.photo_manager,
            "image_processor": self.image_processor
        })
        self.plugin_manager.load_plugins()
        
        # UI components
        self.thumbnail_widget = None
        self.photo_viewer = None
        self.album_manager = None
        self.tag_manager = None
        self.status_label = None
        self.search_box = None
        
        # Worker threads
        self.import_worker = None
        
        # Selected photos
        self.selected_photos = []
        
        # Language actions
        self.language_actions = []
        
        # Create UI after language is set
        self.init_ui()
        self.load_settings()
        
        self.logger.info("Application started")    
    
    def get_text(self, english_text: str, chinese_text: str) -> str:
        """Get localized text based on current language setting.
        
        Args:
            english_text: English text
            chinese_text: Chinese text
            
        Returns:
            Localized text
        """
        current_lang = self.config_manager.get("ui.language", "zh_CN")  # 默认中文
        if current_lang == "zh_CN":
            return chinese_text
        else:
            return english_text

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Photo666 - AI图片管理软件")
        self.setMinimumSize(1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Create central area for photo display (empty initially)
        central_placeholder = QWidget()
        central_placeholder.setStyleSheet("background-color: #f0f0f0; border: 2px dashed #ccc;")
        central_label = QLabel("请选择相册或进行搜索以查看照片")
        central_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_label.setStyleSheet("font-size: 16px; color: #666;")
        central_layout = QVBoxLayout(central_placeholder)
        central_layout.addWidget(central_label)
        self.main_splitter.addWidget(central_placeholder)
        
        # Set splitter proportions
        self.main_splitter.setSizes([800])
        
        # Create dock widgets
        self.create_dock_widgets()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.create_status_bar()
        
        # Connect signals
        self.connect_signals()
        
        # 加载保存的搜索条件
        self.load_saved_search_condition()
        
        # 尝试恢复保存的布局（在所有UI组件初始化完成后）
        self.restore_layout()
    

    
    def create_search_controls(self) -> QWidget:
        """Create the search controls panel (compact version for dock widget)."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumHeight(280)  # 固定高度，为搜索结果留出空间
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 基础搜索区域
        basic_search_group = QGroupBox("基础搜索")
        basic_layout = QVBoxLayout(basic_search_group)
        basic_layout.setSpacing(4)
        
        # 搜索输入框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("关键词:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("输入搜索关键词...")
        self.search_box.returnPressed.connect(self.search_photos)
        search_layout.addWidget(self.search_box)
        
        # 搜索按钮
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.search_photos)
        search_layout.addWidget(self.search_btn)
        
        basic_layout.addLayout(search_layout)
        layout.addWidget(basic_search_group)
        
        # 高级筛选区域（紧凑布局）
        advanced_group = QGroupBox("高级筛选")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(4)
        
        # 第一行：评分、收藏、快速筛选
        row1_layout = QHBoxLayout()
        
        # 评分筛选
        row1_layout.addWidget(QLabel("评分:"))
        self.rating_filter = QSpinBox()
        self.rating_filter.setRange(0, 5)
        self.rating_filter.setValue(0)
        self.rating_filter.setMaximumWidth(60)
        self.rating_filter.valueChanged.connect(self.search_photos)
        row1_layout.addWidget(self.rating_filter)
        
        # 仅收藏
        self.favorites_only = QCheckBox("收藏")
        self.favorites_only.stateChanged.connect(self.search_photos)
        row1_layout.addWidget(self.favorites_only)
        
        # 快速筛选
        row1_layout.addWidget(QLabel("快速:"))
        self.quick_filter_combo = QComboBox()
        self.quick_filter_combo.addItems([
            "所有照片", "收藏", "最近", "未标签", "大尺寸", "小尺寸"
        ])
        self.quick_filter_combo.setMaximumWidth(100)
        self.quick_filter_combo.currentIndexChanged.connect(self.apply_quick_filter)
        row1_layout.addWidget(self.quick_filter_combo)
        
        row1_layout.addStretch()
        advanced_layout.addLayout(row1_layout)
        
        # 第二行：尺寸和大小筛选
        row2_layout = QHBoxLayout()
        
        # 尺寸筛选
        row2_layout.addWidget(QLabel("最小尺寸:"))
        self.min_width = QSpinBox()
        self.min_width.setRange(0, 10000)
        self.min_width.setValue(0)
        self.min_width.setSuffix(" px")
        self.min_width.setMaximumWidth(80)
        self.min_width.valueChanged.connect(self.search_photos)
        row2_layout.addWidget(self.min_width)
        
        row2_layout.addWidget(QLabel("×"))
        self.min_height = QSpinBox()
        self.min_height.setRange(0, 10000)
        self.min_height.setValue(0)
        self.min_height.setSuffix(" px")
        self.min_height.setMaximumWidth(80)
        self.min_height.valueChanged.connect(self.search_photos)
        row2_layout.addWidget(self.min_height)
        
        # 文件大小筛选
        row2_layout.addWidget(QLabel("大小:"))
        self.min_size = QSpinBox()
        self.min_size.setRange(0, 1000000)
        self.min_size.setValue(0)
        self.min_size.setSuffix(" KB")
        self.min_size.setMaximumWidth(80)
        self.min_size.valueChanged.connect(self.search_photos)
        row2_layout.addWidget(self.min_size)
        
        row2_layout.addStretch()
        advanced_layout.addLayout(row2_layout)
        
        # 第三行：相机和日期筛选
        row3_layout = QHBoxLayout()
        
        # 相机品牌
        row3_layout.addWidget(QLabel("相机:"))
        self.camera_filter = QLineEdit()
        self.camera_filter.setPlaceholderText("相机品牌")
        self.camera_filter.setMaximumWidth(120)
        self.camera_filter.textChanged.connect(self.search_photos)
        row3_layout.addWidget(self.camera_filter)
        
        # 拍摄日期范围
        row3_layout.addWidget(QLabel("日期:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-365))
        self.date_from.setMaximumWidth(100)
        self.date_from.dateChanged.connect(self.search_photos)
        row3_layout.addWidget(self.date_from)
        
        row3_layout.addWidget(QLabel("至"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMaximumWidth(100)
        self.date_to.dateChanged.connect(self.search_photos)
        row3_layout.addWidget(self.date_to)
        
        row3_layout.addStretch()
        advanced_layout.addLayout(row3_layout)
        
        layout.addWidget(advanced_group)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        # 清除筛选按钮
        self.clear_filters_btn = QPushButton("清除")
        self.clear_filters_btn.clicked.connect(self.clear_search_filters)
        buttons_layout.addWidget(self.clear_filters_btn)
        
        # 保存搜索按钮
        self.save_search_btn = QPushButton("保存")
        self.save_search_btn.clicked.connect(self.save_search_condition)
        buttons_layout.addWidget(self.save_search_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return panel
    

    
    def create_search_dock_widget(self) -> QWidget:
        """Create the search dock widget with search controls and results."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 上半部分：搜索控件（固定高度）
        search_controls = self.create_search_controls()
        layout.addWidget(search_controls)
        
        # 下半部分：搜索结果（可伸缩）
        self.search_results_widget = ThumbnailWidget()
        self.search_results_widget.photo_selected.connect(self.on_search_photo_selected)
        layout.addWidget(self.search_results_widget)
        
        return widget
    
    def create_photo_display_dock_widget(self) -> QWidget:
        """Create the photo display dock widget with photo viewer only."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Main photo viewer (主图片显示区域)
        self.photo_viewer = PhotoViewer()
        layout.addWidget(self.photo_viewer)
        
        return widget
    

    

    

    
    def create_dock_widgets(self):
        """Create dock widgets for albums, search, photo display, and tags."""
        # Albums dock (相册管理面板)
        self.albums_dock = QDockWidget(self.get_text("Albums", "相册管理"), self)
        self.albums_dock.setObjectName("albums_dock")
        self.albums_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.album_manager = AlbumManager(self.db_manager, self.photo_manager)
        self.albums_dock.setWidget(self.album_manager)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.albums_dock)
        
        # Search dock (照片搜索面板)
        self.search_dock = QDockWidget(self.get_text("Photo Search", "照片搜索"), self)
        self.search_dock.setObjectName("search_dock")
        self.search_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        search_widget = self.create_search_dock_widget()
        self.search_dock.setWidget(search_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.search_dock)
        
        # Photo display dock (图片显示面板)
        self.photo_display_dock = QDockWidget(self.get_text("Photo Display", "图片显示"), self)
        self.photo_display_dock.setObjectName("photo_display_dock")
        self.photo_display_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        photo_display_widget = self.create_photo_display_dock_widget()
        self.photo_display_dock.setWidget(photo_display_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.photo_display_dock)
        
        # Tags dock (标签面板)
        self.tags_dock = QDockWidget(self.get_text("Tags", "标签"), self)
        self.tags_dock.setObjectName("tags_dock")
        self.tags_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.tag_manager = TagManager(self.db_manager, self.album_manager)
        self.tags_dock.setWidget(self.tag_manager)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.tags_dock)
        
        # 设置面板的默认大小和位置
        self.setup_panel_layout()
        
        # 确保所有面板默认可见
        self.albums_dock.setVisible(True)
        self.search_dock.setVisible(True)
        self.photo_display_dock.setVisible(True)
        self.tags_dock.setVisible(True)
    
    def setup_panel_layout(self):
        """Setup the default panel layout for better usability."""
        # 设置面板的默认大小比例
        # 相册管理面板 - 左侧，占20%宽度
        self.albums_dock.setMinimumWidth(200)
        self.albums_dock.resize(250, self.height())
        
        # 照片搜索面板 - 左侧，占20%宽度
        self.search_dock.setMinimumWidth(200)
        self.search_dock.resize(250, self.height())
        
        # 图片显示面板 - 右侧，占40%宽度
        self.photo_display_dock.setMinimumWidth(300)
        self.photo_display_dock.resize(400, self.height())
        
        # 标签面板 - 右侧，占20%宽度
        self.tags_dock.setMinimumWidth(200)
        self.tags_dock.resize(250, self.height())
        
        # 设置面板的关闭按钮可见，允许用户临时关闭不需要的面板
        self.albums_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                                    QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                    QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        self.search_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                                    QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                    QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        self.photo_display_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                                           QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                           QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        self.tags_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                                  QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                  QDockWidget.DockWidgetFeature.DockWidgetFloatable)
    
    def save_layout(self):
        """保存当前面板布局到配置文件."""
        try:
            layout_data = {
                'window_geometry': {
                    'x': self.geometry().x(),
                    'y': self.geometry().y(),
                    'width': self.geometry().width(),
                    'height': self.geometry().height()
                },
                'window_state': self.saveState().toHex().data().decode(),
                'panels_visible': {
                    'albums': self.albums_dock.isVisible(),
                    'search': self.search_dock.isVisible(),
                    'photo_display': self.photo_display_dock.isVisible(),
                    'tags': self.tags_dock.isVisible()
                },
                'panels_floating': {
                    'albums': self.albums_dock.isFloating(),
                    'search': self.search_dock.isFloating(),
                    'photo_display': self.photo_display_dock.isFloating(),
                    'tags': self.tags_dock.isFloating()
                },
                'panels_geometry': {
                    'albums': {
                        'x': self.albums_dock.geometry().x(),
                        'y': self.albums_dock.geometry().y(),
                        'width': self.albums_dock.geometry().width(),
                        'height': self.albums_dock.geometry().height()
                    } if self.albums_dock.isFloating() else None,
                    'search': {
                        'x': self.search_dock.geometry().x(),
                        'y': self.search_dock.geometry().y(),
                        'width': self.search_dock.geometry().width(),
                        'height': self.search_dock.geometry().height()
                    } if self.search_dock.isFloating() else None,
                    'photo_display': {
                        'x': self.photo_display_dock.geometry().x(),
                        'y': self.photo_display_dock.geometry().y(),
                        'width': self.photo_display_dock.geometry().width(),
                        'height': self.photo_display_dock.geometry().height()
                    } if self.photo_display_dock.isFloating() else None,
                    'tags': {
                        'x': self.tags_dock.geometry().x(),
                        'y': self.tags_dock.geometry().y(),
                        'width': self.tags_dock.geometry().width(),
                        'height': self.tags_dock.geometry().height()
                    } if self.tags_dock.isFloating() else None
                }
            }
            
            # 保存到配置文件
            self.config_manager.set('ui.layout', layout_data)
            self.logger.info("Layout saved successfully")
            
        except Exception as e:
            self.logger.error("Failed to save layout", error=str(e))
    
    def restore_layout(self):
        """从配置文件恢复面板布局."""
        try:
            layout_data = self.config_manager.get('ui.layout', {})
            self.logger.info("Attempting to restore layout", layout_data=layout_data)
            
            if not layout_data:
                self.logger.info("No saved layout found, using default")
                return
            
            # 恢复窗口几何形状
            if 'window_geometry' in layout_data:
                geo = layout_data['window_geometry']
                self.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
                self.logger.info("Window geometry restored", geometry=geo)
            
            # 恢复窗口状态（包括停靠面板位置）
            if 'window_state' in layout_data:
                state_data = layout_data['window_state']
                state = QByteArray.fromHex(state_data.encode())
                self.restoreState(state)
                self.logger.info("Window state restored")
            
            # 恢复面板可见性
            if 'panels_visible' in layout_data:
                panels = layout_data['panels_visible']
                if 'albums' in panels:
                    self.albums_dock.setVisible(panels['albums'])
                    self.albums_panel_action.setChecked(panels['albums'])
                if 'search' in panels:
                    self.search_dock.setVisible(panels['search'])
                    self.search_panel_action.setChecked(panels['search'])
                if 'photo_display' in panels:
                    self.photo_display_dock.setVisible(panels['photo_display'])
                    self.photo_display_panel_action.setChecked(panels['photo_display'])
                if 'tags' in panels:
                    self.tags_dock.setVisible(panels['tags'])
                    self.tags_panel_action.setChecked(panels['tags'])
                self.logger.info("Panel visibility restored", panels=panels)
            
            # 恢复浮动面板的位置和大小
            if 'panels_floating' in layout_data and 'panels_geometry' in layout_data:
                floating = layout_data['panels_floating']
                geometry = layout_data['panels_geometry']
                
                # 恢复浮动面板
                if 'albums' in floating and floating['albums'] and geometry['albums']:
                    self.albums_dock.setFloating(True)
                    geo = geometry['albums']
                    self.albums_dock.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
                
                if 'search' in floating and floating['search'] and geometry['search']:
                    self.search_dock.setFloating(True)
                    geo = geometry['search']
                    self.search_dock.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
                
                if 'photo_display' in floating and floating['photo_display'] and geometry['photo_display']:
                    self.photo_display_dock.setFloating(True)
                    geo = geometry['photo_display']
                    self.photo_display_dock.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
                
                if 'tags' in floating and floating['tags'] and geometry['tags']:
                    self.tags_dock.setFloating(True)
                    geo = geometry['tags']
                    self.tags_dock.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
                
                self.logger.info("Floating panels restored", floating=floating)
            
            self.logger.info("Layout restored successfully")
            
        except Exception as e:
            self.logger.error("Failed to restore layout", error=str(e))
    
    def reset_layout(self):
        """重置面板布局到默认状态."""
        try:
            # 显示所有面板
            self.albums_dock.setVisible(True)
            self.search_dock.setVisible(True)
            self.photo_display_dock.setVisible(True)
            self.tags_dock.setVisible(True)
            
            # 更新菜单项状态
            self.albums_panel_action.setChecked(True)
            self.search_panel_action.setChecked(True)
            self.photo_display_panel_action.setChecked(True)
            self.tags_panel_action.setChecked(True)
            
            # 重置到默认布局
            self.setup_panel_layout()
            
            # 清除保存的布局
            self.config_manager.set('ui.layout', {})
            
            self.logger.info("Layout reset to default")
            QMessageBox.information(self, "布局重置", "面板布局已重置为默认状态。")
            
        except Exception as e:
            self.logger.error("Failed to reset layout", error=str(e))
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(self.get_text("File", "文件"))
        
        # Import actions
        import_photos_action = QAction(self.get_text("Import Photos", "导入图片"), self)
        import_photos_action.setShortcut(QKeySequence.StandardKey.Open)
        import_photos_action.triggered.connect(self.import_photos)
        file_menu.addAction(import_photos_action)
        
        import_folder_action = QAction(self.get_text("Import Folder", "导入文件夹"), self)
        import_folder_action.triggered.connect(self.import_folder)
        file_menu.addAction(import_folder_action)
        
        file_menu.addSeparator()
        
        # Export actions
        export_action = QAction(self.get_text("Export Selected", "导出选中"), self)
        export_action.triggered.connect(self.export_selected_photos)
        file_menu.addAction(export_action)
        
        export_album_action = QAction(self.get_text("Export Album", "导出相册"), self)
        export_album_action.triggered.connect(self.export_album)
        file_menu.addAction(export_album_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction(self.get_text("Exit", "退出"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu(self.get_text("Edit", "编辑"))
        
        select_all_action = QAction(self.get_text("Select All", "全选"), self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.select_all_photos)
        edit_menu.addAction(select_all_action)
        
        deselect_all_action = QAction(self.get_text("Deselect All", "取消全选"), self)
        deselect_all_action.triggered.connect(self.deselect_all_photos)
        edit_menu.addAction(deselect_all_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction(self.get_text("Delete Selected", "删除选中"), self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected_photos)
        edit_menu.addAction(delete_action)
        
        # View menu
        view_menu = menubar.addMenu(self.get_text("View", "视图"))
        
        # Album panel toggle
        self.albums_panel_action = QAction(self.get_text("Albums Panel", "相册管理面板"), self)
        self.albums_panel_action.setCheckable(True)
        self.albums_panel_action.setChecked(True)
        self.albums_panel_action.triggered.connect(self.toggle_albums_panel)
        view_menu.addAction(self.albums_panel_action)
        
        # Search panel toggle
        self.search_panel_action = QAction(self.get_text("Search Panel", "照片搜索面板"), self)
        self.search_panel_action.setCheckable(True)
        self.search_panel_action.setChecked(True)
        self.search_panel_action.triggered.connect(self.toggle_search_panel)
        view_menu.addAction(self.search_panel_action)
        
        # Photo display panel toggle
        self.photo_display_panel_action = QAction(self.get_text("Photo Display Panel", "图片显示面板"), self)
        self.photo_display_panel_action.setCheckable(True)
        self.photo_display_panel_action.setChecked(True)
        self.photo_display_panel_action.triggered.connect(self.toggle_photo_display_panel)
        view_menu.addAction(self.photo_display_panel_action)
        
        # Tags panel toggle
        self.tags_panel_action = QAction(self.get_text("Tags Panel", "标签面板"), self)
        self.tags_panel_action.setCheckable(True)
        self.tags_panel_action.setChecked(True)
        self.tags_panel_action.triggered.connect(self.toggle_tags_panel)
        view_menu.addAction(self.tags_panel_action)
        
        view_menu.addSeparator()
        
        # Layout management
        save_layout_action = QAction(self.get_text("Save Layout", "保存布局"), self)
        save_layout_action.triggered.connect(self.save_layout)
        view_menu.addAction(save_layout_action)
        
        reset_layout_action = QAction(self.get_text("Reset Layout", "重置布局"), self)
        reset_layout_action.triggered.connect(self.reset_layout)
        view_menu.addAction(reset_layout_action)
        
        # Tools menu
        tools_menu = menubar.addMenu(self.get_text("Tools", "工具"))
        
        batch_processor_action = QAction(self.get_text("Batch Processor", "批处理器"), self)
        batch_processor_action.triggered.connect(self.show_batch_processor)
        tools_menu.addAction(batch_processor_action)
        
        tag_manager_action = QAction(self.get_text("Tag Manager", "标签管理器"), self)
        tag_manager_action.triggered.connect(self.show_tag_manager)
        tools_menu.addAction(tag_manager_action)
        
        tools_menu.addSeparator()
        
        # File path repair action
        repair_paths_action = QAction(self.get_text("Repair File Paths", "修复文件路径"), self)
        repair_paths_action.triggered.connect(self.repair_file_paths)
        tools_menu.addAction(repair_paths_action)
        
        plugin_manager_action = QAction(self.get_text("Plugin Manager", "插件管理器"), self)
        plugin_manager_action.triggered.connect(self.show_plugin_manager)
        tools_menu.addAction(plugin_manager_action)
        
        # 添加插件菜单动作
        self.add_plugin_menu_actions(tools_menu)
        
        tools_menu.addSeparator()
        
        # 代理配置
        proxy_config_action = QAction(self.get_text("Proxy Configuration", "代理服务器配置"), self)
        proxy_config_action.triggered.connect(self.show_proxy_config)
        tools_menu.addAction(proxy_config_action)
        
        # Settings menu
        settings_menu = menubar.addMenu(self.get_text("Settings", "设置"))
        
        preferences_action = QAction(self.get_text("Preferences", "首选项"), self)
        preferences_action.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences_action)
        
        # Language submenu
        language_menu = settings_menu.addMenu(self.get_text("Language", "语言"))
        
        # Language actions
        self.language_actions = []
        languages = [
            ("en", "English", "英语"),
            ("zh_CN", "中文", "中文")
        ]
        
        for lang_code, eng_name, ch_name in languages:
            action = QAction(self.get_text(eng_name, ch_name), self)
            action.setCheckable(True)
            action.setData(lang_code)
            action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            language_menu.addAction(action)
            self.language_actions.append(action)
        
        # Help menu
        help_menu = menubar.addMenu(self.get_text("Help", "帮助"))
        
        help_action = QAction(self.get_text("User Manual", "用户手册"), self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        log_viewer_action = QAction(self.get_text("Log Viewer", "日志查看器"), self)
        log_viewer_action.triggered.connect(self.show_log_viewer)
        help_menu.addAction(log_viewer_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(self.get_text("About", "关于"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = self.addToolBar(self.get_text("Main Toolbar", "主工具栏"))
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(True)
        
        # Import actions
        import_photos_action = QAction(self.get_text("Import Photos", "导入图片"), self)
        import_photos_action.triggered.connect(self.import_photos)
        toolbar.addAction(import_photos_action)
        
        import_folder_action = QAction(self.get_text("Import Folder", "导入文件夹"), self)
        import_folder_action.triggered.connect(self.import_folder)
        toolbar.addAction(import_folder_action)
        
        toolbar.addSeparator()
        
        # View mode combo
        toolbar.addWidget(QLabel(self.get_text("View:", "视图:")))
        self.view_combo = QComboBox()
        view_items = [
            self.get_text("Thumbnails", "缩略图"),
            self.get_text("List", "列表"),
            self.get_text("Details", "详情")
        ]
        self.view_combo.addItems(view_items)
        self.view_combo.currentIndexChanged.connect(self.on_view_mode_changed)
        toolbar.addWidget(self.view_combo)
        
        toolbar.addSeparator()
        
        # Quick filters
        toolbar.addWidget(QLabel(self.get_text("Filter:", "筛选:")))
        self.filter_combo = QComboBox()
        filter_items = [
            self.get_text("All", "全部"),
            self.get_text("Favorites", "收藏"),
            self.get_text("Recent", "最近"),
            self.get_text("Untagged", "未标签")
        ]
        self.filter_combo.addItems(filter_items)
        self.filter_combo.currentIndexChanged.connect(self.apply_quick_filter)
        toolbar.addWidget(self.filter_combo)
        
        toolbar.addSeparator()
        
        # AI信息刷新按钮
        refresh_current_ai_action = QAction(self.get_text("Refresh Current AI Info", "刷新当前图片AI信息"), self)
        refresh_current_ai_action.triggered.connect(self.refresh_current_photo_ai_info)
        toolbar.addAction(refresh_current_ai_action)
        
        refresh_album_ai_action = QAction(self.get_text("Refresh Album AI Info", "刷新相册AI信息"), self)
        refresh_album_ai_action.triggered.connect(self.refresh_album_ai_info)
        toolbar.addAction(refresh_album_ai_action)
        
        # 添加插件工具栏动作
        self.add_plugin_toolbar_actions(toolbar)
    
    def create_status_bar(self):
        """Create the status bar."""
        status_bar = self.statusBar()
        
        self.status_label = QLabel(self.get_text("Ready", "就绪"))
        status_bar.addWidget(self.status_label)
        
        # Photo count
        self.photo_count_label = QLabel(self.get_text("0 photos", "0 张照片"))
        status_bar.addPermanentWidget(self.photo_count_label)
    
    def connect_signals(self):
        """Connect signals and slots."""
        if self.thumbnail_widget:
            self.thumbnail_widget.selection_changed.connect(self.on_selection_changed)
            self.thumbnail_widget.photo_selected.connect(self.on_photo_selected)
        
        if self.album_manager:
            self.album_manager.album_selected.connect(self.on_album_selected)
            self.album_manager.photo_selected.connect(self.on_photo_selected)  # 连接相册管理器的照片选择信号
        
        if self.search_results_widget:
            self.search_results_widget.photo_selected.connect(self.on_search_photo_selected)
        
        if self.tag_manager:
            self.tag_manager.tag_selected.connect(self.on_tag_selected)
        
        # 连接照片查看器的信号
        if self.photo_viewer:
            self.photo_viewer.previous_photo_requested.connect(self.show_previous_photo)
            self.photo_viewer.next_photo_requested.connect(self.show_next_photo)
            self.photo_viewer.photo_updated.connect(self.on_photo_updated)
    
    def on_selection_changed(self, selected_ids: list):
        """Handle photo selection change."""
        self.selected_photos = selected_ids
        self.update_photo_count(len(selected_ids))
    
    def on_photo_selected(self, photo_id: int):
        """Handle photo selection."""
        self.logger.info("Photo selected", photo_id=photo_id)
        
        # 获取照片详细信息
        photo_data = self.photo_manager.get_photo_info(photo_id)
        if photo_data and self.photo_viewer:
            # 直接显示照片，让PhotoViewer处理原图查找逻辑
            self.photo_viewer.display_photo(photo_data)
            
            # 更新照片信息面板
            self.update_photo_info(photo_id)
            
            # 更新标签面板
            self.update_tags_for_photo(photo_id)
        else:
            self.logger.warning("Photo data not found or photo viewer not available", photo_id=photo_id)
    
    def load_settings(self):
        """Load application settings."""
        # Load window geometry
        window_size = self.config_manager.get("ui.window_size", [1400, 900])
        window_position = self.config_manager.get("ui.window_position", [100, 100])
        
        try:
            if isinstance(window_size, (list, tuple)) and len(window_size) == 2:
                self.resize(*window_size)
        except (TypeError, ValueError):
            self.resize(1400, 900)
        
        try:
            if isinstance(window_position, (list, tuple)) and len(window_position) == 2:
                self.move(*window_position)
        except (TypeError, ValueError):
            self.move(100, 100)
        
        # Load splitter sizes
        splitter_sizes = self.config_manager.get("ui.splitter_sizes", [400, 800])
        if hasattr(self, 'main_splitter'):
            self.main_splitter.setSizes(splitter_sizes)
    
    def save_settings(self):
        """Save application settings."""
        # Save window geometry
        self.config_manager.set("ui.window_size", [self.width(), self.height()])
        self.config_manager.set("ui.window_position", [self.x(), self.y()])
        
        # Save splitter sizes
        if hasattr(self, 'main_splitter'):
            self.config_manager.set("ui.splitter_sizes", self.main_splitter.sizes())
        
        self.config_manager.save_config()
    
    def import_photos(self):
        """Import photos from file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择照片文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;所有文件 (*)"
        )
        
        if files:
            self.import_files(files)
    
    def import_folder(self):
        """Import photos from folder dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择照片目录",
            ""
        )
        
        if directory:
            self.import_directory(directory)
    
    def import_files(self, files: List[str]):
        """Import specific files."""
        if not files:
            return
        
        # Create album for imported files
        album_data = {
            "name": f"导入的照片 ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            "description": f"导入了 {len(files)} 张照片",
            "import_on_create": True
        }
        
        album_id = self.db_manager.create_album(album_data)
        if not album_id:
            QMessageBox.critical(self, "导入错误", "为导入的照片创建相册失败")
            return
        
        # Show progress dialog
        progress = QProgressDialog("正在导入照片...", "取消", 0, len(files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        imported_photo_ids = []
        
        try:
            for i, file_path in enumerate(files):
                if progress.wasCanceled():
                    break
                
                progress.setValue(i + 1)
                progress.setLabelText(f"正在导入 {Path(file_path).name}...")
                
                # Import the file
                photo_id = self.photo_manager.import_photo(file_path)
                if photo_id:
                    imported_count += 1
                    imported_photo_ids.append(photo_id)
                    # Add to album
                    self.db_manager.add_photo_to_album(photo_id, album_id)
                elif photo_id is None:
                    error_count += 1
                else:
                    skipped_count += 1
                
                # Process events to keep UI responsive
                QApplication.processEvents()
            
            # Show results
            message = f"导入完成！\n已导入: {imported_count}\n已跳过: {skipped_count}\n错误: {error_count}"
            QMessageBox.information(self, "导入完成", message)
            
            # Update album manager and select the new album
            if self.album_manager:
                self.album_manager.load_albums()
                self.album_manager.select_album(album_id)
            
        except Exception as e:
            self.logger.error("Failed to import photos", error=str(e))
            QMessageBox.critical(self, "导入错误", f"导入照片失败: {str(e)}")
            progress.close()
        
        finally:
            progress.close()
            self.refresh_photos()
    
    def import_directory(self, directory: str):
        """Import photos from a directory."""
        try:
            # Create album with directory name
            directory_name = Path(directory).name
            album_data = {
                "name": directory_name,
                "description": f"从 {directory} 导入",
                "directory": directory,
                "import_on_create": True
            }
            
            # Create album first
            album_id = self.db_manager.create_album(album_data)
            if album_id:
                self.logger.info("Created album for directory", 
                               directory=directory, album_id=album_id)
                
                # Update album manager
                if self.album_manager:
                    self.album_manager.load_albums()
                    self.album_manager.select_album(album_id)
            
            # Start import worker
            self.import_worker = ImportWorker(
                self.photo_manager, 
                directory, 
                True, 
                album_id
            )
            self.import_worker.progress.connect(self.update_import_progress)
            self.import_worker.finished.connect(lambda result: self.on_import_finished(result, None))
            self.import_worker.error.connect(lambda error: self.on_import_error(error, None))
            self.import_worker.start()
            
        except Exception as e:
            self.logger.error("Failed to import directory", 
                            directory=directory, error=str(e))
            QMessageBox.critical(self, "Import Error", f"Failed to import directory: {str(e)}")
    

    
    def update_import_progress(self, current: int, total: int):
        """Update import progress."""
        if hasattr(self, 'import_progress_dialog'):
            self.import_progress_dialog.setValue(current)
            self.import_progress_dialog.setMaximum(total)
        else:
            # Create progress dialog if not exists
            self.import_progress_dialog = QProgressDialog("正在导入照片...", "取消", 0, total, self)
            self.import_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.import_progress_dialog.show()

    def on_import_finished(self, result: dict, progress: QProgressDialog):
        """Handle import completion."""
        # Close progress dialog
        if hasattr(self, 'import_progress_dialog'):
            self.import_progress_dialog.close()
            delattr(self, 'import_progress_dialog')
        
        if progress:
            progress.close()
        
        imported_count = result.get("imported", 0)
        skipped_count = result.get("skipped", 0)
        errors = result.get("errors", 0)  # This is an integer, not a list
        
        # Show result message
        message = f"导入完成！\n已导入: {imported_count}\n已跳过: {skipped_count}"
        if errors > 0:
            message += f"\n错误: {errors}"
        
        QMessageBox.information(self, "导入完成", message)
        
        # Refresh photos display
        self.refresh_photos()
        
        # Update album manager
        if self.album_manager:
            self.album_manager.load_albums()
        
        self.logger.info("Import completed", 
                        imported=imported_count, 
                        skipped=skipped_count, 
                        errors=errors)
    
    def on_import_error(self, error: str, progress: QProgressDialog):
        """Handle import error."""
        progress.close()
        self.logger.error("Import error", error_msg=error)
        QMessageBox.critical(self, "导入错误", f"导入照片失败: {error}")
    
    def on_search_photo_selected(self, photo_id: int):
        """Handle photo selection from search results."""
        self.logger.info("Search photo selected", photo_id=photo_id)
        
        # Get photo information
        photo_data = self.photo_manager.get_photo_info(photo_id)
        if photo_data:
            # Try to find original image
            original_path = self.photo_manager.find_original_image_by_hash(photo_data["file_hash"])
            
            if original_path:
                # Original image found, display it
                self.photo_viewer.display_photo(photo_data)
                self.logger.info("Original image displayed", path=original_path)
            else:
                # Original image not found, but we can still show metadata
                self.photo_viewer.display_photo_info_only(photo_data)
                self.logger.warning("Original image not found, showing metadata only", 
                                  photo_id=photo_id)
            
            # Update photo info panel (5区)
            self.update_photo_info(photo_id)
            
            # Update tags panel (6区)
            self.update_tags_for_photo(photo_id)
    
    def update_tags_for_photo(self, photo_id: int):
        """Update tags panel for selected photo."""
        if hasattr(self, 'tag_manager'):
            photo_data = self.photo_manager.get_photo_info(photo_id)
            if photo_data:
                # 更新tag_manager中的照片标签显示
                self.tag_manager.update_photo_tags_display(photo_data)
    
    def search_photos(self):
        """Enhanced search photos based on current filters."""
        # 获取基础搜索参数
        search_text = self.search_box.text() if self.search_box else ""
        min_rating = self.rating_filter.value() if hasattr(self, 'rating_filter') else 0
        favorites_only = self.favorites_only.isChecked() if hasattr(self, 'favorites_only') else False
        
        # 获取高级筛选参数
        min_width = self.min_width.value() if hasattr(self, 'min_width') else 0
        min_height = self.min_height.value() if hasattr(self, 'min_height') else 0
        min_size = self.min_size.value() if hasattr(self, 'min_size') else 0
        camera_filter = self.camera_filter.text() if hasattr(self, 'camera_filter') else ""
        date_from = self.date_from.date() if hasattr(self, 'date_from') else QDate.currentDate().addDays(-365)
        date_to = self.date_to.date() if hasattr(self, 'date_to') else QDate.currentDate()
        
        # 解析搜索关键词
        search_terms = self.parse_search_terms(search_text)
        
        # Build search parameters
        search_params = {
            "query": search_text,
            "search_terms": search_terms,
            "rating_min": min_rating,
            "min_width": min_width,
            "min_height": min_height,
            "min_size_kb": min_size,
            "camera_filter": camera_filter,
            "date_from": date_from.toString("yyyy-MM-dd"),
            "date_to": date_to.toString("yyyy-MM-dd"),
            "limit": 500  # 增加结果数量
        }
        
        if favorites_only:
            search_params["favorites_only"] = True
        
        # Perform search
        results = self.photo_manager.search_photos(**search_params)
        
        # 如果没有搜索结果，尝试更宽松的搜索
        if not results and search_text:
            self.logger.info("No results found, trying broader search")
            # 只使用文本搜索，忽略其他筛选条件
            broader_params = {
                "query": search_text,
                "search_terms": search_terms,
                "limit": 500
            }
            results = self.photo_manager.search_photos(**broader_params)
            
            if results:
                self.logger.info("Broader search found results", count=len(results))
        
        # 保存搜索结果用于导航
        self.current_search_results = results
        
        # 清除相册照片列表，因为现在显示的是搜索结果
        self.current_album_photos = None
        
        # Display results in search results widget
        if hasattr(self, 'search_results_widget'):
            self.search_results_widget.display_photos(results)
        else:
            self.logger.warning("search_results_widget not found")
        
        # Update status
        self.update_photo_count(len(results))
        
        self.logger.info("Enhanced search completed", 
                        query=search_text, 
                        search_terms=search_terms,
                        results_count=len(results),
                        min_rating=min_rating,
                        favorites_only=favorites_only,
                        min_width=min_width,
                        min_height=min_height,
                        min_size=min_size,
                        camera_filter=camera_filter)
    
    def save_search_condition(self):
        """保存当前搜索条件"""
        try:
            # 获取当前搜索条件
            search_condition = {
                "search_text": self.search_box.text() if self.search_box else "",
                "min_rating": self.rating_filter.value() if hasattr(self, 'rating_filter') else 0,
                "favorites_only": self.favorites_only.isChecked() if hasattr(self, 'favorites_only') else False,
                "min_width": self.min_width.value() if hasattr(self, 'min_width') else 0,
                "min_height": self.min_height.value() if hasattr(self, 'min_height') else 0,
                "min_size": self.min_size.value() if hasattr(self, 'min_size') else 0,
                "camera_filter": self.camera_filter.text() if hasattr(self, 'camera_filter') else "",
                "date_from": self.date_from.date().toString("yyyy-MM-dd") if hasattr(self, 'date_from') else "",
                "date_to": self.date_to.date().toString("yyyy-MM-dd") if hasattr(self, 'date_to') else "",
                "quick_filter": self.quick_filter_combo.currentIndex() if hasattr(self, 'quick_filter_combo') else 0
            }
            
            # 保存到配置文件
            self.config_manager.set("search.last_condition", search_condition)
            self.config_manager.save()
            
            QMessageBox.information(self, "保存成功", "搜索条件已保存")
            self.logger.info("Search condition saved", condition=search_condition)
            
        except Exception as e:
            self.logger.error("Failed to save search condition", error=str(e))
            QMessageBox.critical(self, "保存失败", f"保存搜索条件失败：{str(e)}")
    
    def load_saved_search_condition(self):
        """加载保存的搜索条件"""
        try:
            saved_condition = self.config_manager.get("search.last_condition", {})
            if not saved_condition:
                return
            
            # 恢复搜索条件
            if self.search_box and "search_text" in saved_condition:
                self.search_box.setText(saved_condition["search_text"])
            
            if hasattr(self, 'rating_filter') and "min_rating" in saved_condition:
                self.rating_filter.setValue(saved_condition["min_rating"])
            
            if hasattr(self, 'favorites_only') and "favorites_only" in saved_condition:
                self.favorites_only.setChecked(saved_condition["favorites_only"])
            
            if hasattr(self, 'min_width') and "min_width" in saved_condition:
                self.min_width.setValue(saved_condition["min_width"])
            
            if hasattr(self, 'min_height') and "min_height" in saved_condition:
                self.min_height.setValue(saved_condition["min_height"])
            
            if hasattr(self, 'min_size') and "min_size" in saved_condition:
                self.min_size.setValue(saved_condition["min_size"])
            
            if hasattr(self, 'camera_filter') and "camera_filter" in saved_condition:
                self.camera_filter.setText(saved_condition["camera_filter"])
            
            if hasattr(self, 'date_from') and "date_from" in saved_condition:
                date_from = QDate.fromString(saved_condition["date_from"], "yyyy-MM-dd")
                if date_from.isValid():
                    self.date_from.setDate(date_from)
            
            if hasattr(self, 'date_to') and "date_to" in saved_condition:
                date_to = QDate.fromString(saved_condition["date_to"], "yyyy-MM-dd")
                if date_to.isValid():
                    self.date_to.setDate(date_to)
            
            if hasattr(self, 'quick_filter_combo') and "quick_filter" in saved_condition:
                self.quick_filter_combo.setCurrentIndex(saved_condition["quick_filter"])
            
            self.logger.info("Saved search condition loaded", condition=saved_condition)
            
        except Exception as e:
            self.logger.error("Failed to load saved search condition", error=str(e))
    
    def parse_search_terms(self, search_text: str) -> List[str]:
        """Parse search text into individual terms.
        
        Supports:
        - Short phrases separated by commas or semicolons
        - Words separated by spaces
        - Mixed format
        
        Args:
            search_text: Raw search text
            
        Returns:
            List of parsed search terms
        """
        if not search_text.strip():
            return []
        
        terms = []
        
        # 首先按逗号和分号分割短句
        phrases = []
        for separator in [',', ';']:
            if separator in search_text:
                phrases.extend(search_text.split(separator))
                break
        else:
            phrases = [search_text]
        
        # 处理每个短句，按空格分割单词
        for phrase in phrases:
            phrase = phrase.strip()
            if phrase:
                # 按空格分割单词
                words = phrase.split()
                terms.extend(words)
        
        # 去重并过滤空字符串
        unique_terms = []
        for term in terms:
            term = term.strip()
            if term and term not in unique_terms:
                unique_terms.append(term)
        
        return unique_terms
    
    def refresh_photos(self):
        """Refresh the photo display."""
        if self.thumbnail_widget:
            # Load photos from database and update display
            photos = self.photo_manager.search_photos(limit=1000)
            self.thumbnail_widget.display_photos(photos)
            self.update_photo_count(len(photos))
            self.logger.info("Photos refreshed", count=len(photos))
    
    def update_photo_info(self, photo_id: int):
        """Update photo information display."""
        # In a real implementation, this would update the photo viewer
        self.logger.info("Updating photo info", photo_id=photo_id)
    
    def update_photo_count(self, count: int):
        """Update the photo count display."""
        if hasattr(self, 'photo_count_label'):
            self.photo_count_label.setText(f"{count} 张照片")
    
    def on_photo_updated(self, photo_id: int):
        """Handle photo update."""
        self.update_photo_info(photo_id)
    
    def show_previous_photo(self):
        """显示上一张图片"""
        try:
            # 获取当前显示的照片列表
            current_photos = self.get_current_photo_list()
            if not current_photos:
                return
            
            # 获取当前照片ID
            current_photo_id = self.get_current_photo_id()
            if current_photo_id is None:
                return
            
            # 找到当前照片在列表中的位置
            current_index = None
            for i, photo in enumerate(current_photos):
                if photo.get('id') == current_photo_id:
                    current_index = i
                    break
            
            if current_index is None or current_index <= 0:
                # 已经是第一张，循环到最后一张
                next_photo = current_photos[-1]
            else:
                # 显示上一张
                next_photo = current_photos[current_index - 1]
            
            # 显示照片
            self.on_photo_selected(next_photo.get('id'))
            
        except Exception as e:
            self.logger.error("Failed to show previous photo", error=str(e))
    
    def show_next_photo(self):
        """显示下一张图片"""
        try:
            # 获取当前显示的照片列表
            current_photos = self.get_current_photo_list()
            if not current_photos:
                return
            
            # 获取当前照片ID
            current_photo_id = self.get_current_photo_id()
            if current_photo_id is None:
                return
            
            # 找到当前照片在列表中的位置
            current_index = None
            for i, photo in enumerate(current_photos):
                if photo.get('id') == current_photo_id:
                    current_index = i
                    break
            
            if current_index is None or current_index >= len(current_photos) - 1:
                # 已经是最后一张，循环到第一张
                next_photo = current_photos[0]
            else:
                # 显示下一张
                next_photo = current_photos[current_index + 1]
            
            # 显示照片
            self.on_photo_selected(next_photo.get('id'))
            
        except Exception as e:
            self.logger.error("Failed to show next photo", error=str(e))
    
    def get_current_photo_list(self) -> list:
        """获取当前显示的照片列表"""
        # 根据当前状态返回相应的照片列表
        if hasattr(self, 'current_search_results') and self.current_search_results:
            return self.current_search_results
        elif hasattr(self, 'current_album_photos') and self.current_album_photos:
            return self.current_album_photos
        else:
            # 返回所有照片
            return self.db_manager.search_photos(limit=1000)
    
    def get_current_photo_id(self) -> int:
        """获取当前显示的照片ID"""
        if hasattr(self, 'photo_viewer') and self.photo_viewer.current_photo:
            return self.photo_viewer.current_photo.get('id')
        return None
        self.refresh_photos()
    
    def on_album_selected(self, album_id: int):
        """Handle album selection."""
        try:
            # 设置当前选中的相册ID
            self.current_album_id = album_id
            
            # 获取相册中的照片列表
            album_photos = self.db_manager.get_album_photos(album_id)
            self.current_album_photos = album_photos
            
            # 清除搜索结果，因为现在显示的是相册照片
            self.current_search_results = None
            
            self.logger.info("Album selected", album_id=album_id, photo_count=len(album_photos))
            
        except Exception as e:
            self.logger.error("Failed to handle album selection", album_id=album_id, error=str(e))
    
    def on_tag_selected(self, tag_id: int):
        """Handle tag selection."""
        # In a real implementation, this would filter photos by tag
        self.logger.info("Tag selected", tag_id=tag_id)
    
    def select_all_photos(self):
        """Select all displayed photos."""
        if self.thumbnail_widget:
            self.thumbnail_widget.select_all()
    
    def deselect_all_photos(self):
        """Deselect all photos."""
        if self.thumbnail_widget:
            self.thumbnail_widget.deselect_all()
    
    def delete_selected_photos(self):
        """Delete selected photos."""
        if not self.selected_photos:
            QMessageBox.information(self, "无选择", "未选择照片。")
            return
        
        reply = QMessageBox.question(
            self,
            "删除照片",
            f"确定要删除选中的 {len(self.selected_photos)} 张照片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # In a real implementation, this would delete from database
            self.logger.info("Deleting photos", count=len(self.selected_photos))
            QMessageBox.information(self, "删除照片", "照片删除成功。")
            self.refresh_photos()
    
    def set_view_mode(self, mode: str):
        """Set the view mode."""
        if mode == "thumbnails":
            self.view_combo.setCurrentIndex(0)
        elif mode == "list":
            self.view_combo.setCurrentIndex(1)
        elif mode == "details":
            self.view_combo.setCurrentIndex(2)
        
        # In a real implementation, this would change the view
        self.logger.info("View mode changed", mode=mode)
    
    def on_view_mode_changed(self, index: int):
        """Handle view mode combo box change."""
        modes = ["thumbnails", "list", "details"]
        if 0 <= index < len(modes):
            self.set_view_mode(modes[index])
    
    def clear_search_filters(self):
        """Clear all search filters."""
        if self.search_box:
            self.search_box.clear()
        if hasattr(self, 'rating_filter'):
            self.rating_filter.setValue(0)
        if hasattr(self, 'favorites_only'):
            self.favorites_only.setChecked(False)
        if hasattr(self, 'quick_filter_combo'):
            self.quick_filter_combo.setCurrentIndex(0)
        
        # 清除新的筛选条件
        if hasattr(self, 'min_width'):
            self.min_width.setValue(0)
        if hasattr(self, 'min_height'):
            self.min_height.setValue(0)
        if hasattr(self, 'min_size'):
            self.min_size.setValue(0)
        if hasattr(self, 'camera_filter'):
            self.camera_filter.clear()
        if hasattr(self, 'date_from'):
            self.date_from.setDate(QDate.currentDate().addDays(-365))
        if hasattr(self, 'date_to'):
            self.date_to.setDate(QDate.currentDate())
        
        # Refresh search
        self.search_photos()
        
        self.logger.info("All search filters cleared")

    def apply_quick_filter(self, index: int):
        """Apply quick filter."""
        filters = ["all", "favorites", "recent", "untagged", "large_size", "small_size"]
        if 0 <= index < len(filters):
            filter_name = filters[index]
            
            # 清除所有筛选条件
            self.clear_search_filters()
            
            # 应用特定筛选
            if filter_name == "favorites":
                self.favorites_only.setChecked(True)
            elif filter_name == "recent":
                # 最近30天
                self.date_from.setDate(QDate.currentDate().addDays(-30))
                self.date_to.setDate(QDate.currentDate())
            elif filter_name == "untagged":
                # 未标签的照片（所有标签字段都为空）
                self.search_box.setText("untagged")
            elif filter_name == "large_size":
                # 大尺寸照片（宽度或高度大于2000像素）
                self.min_width.setValue(2000)
                self.min_height.setValue(2000)
            elif filter_name == "small_size":
                # 小尺寸照片（宽度和高度都小于1000像素）
                # 这里需要特殊处理，因为我们需要小于而不是大于
                self.search_box.setText("small_size")
            
            # 执行搜索
            self.search_photos()
            
            self.logger.info("Quick filter applied", filter=filter_name)
    
    def toggle_albums_panel(self, checked: bool):
        """Toggle albums panel visibility."""
        if hasattr(self, 'albums_dock'):
            self.albums_dock.setVisible(checked)
    
    def toggle_search_panel(self, checked: bool):
        """Toggle search panel visibility."""
        if hasattr(self, 'search_dock'):
            self.search_dock.setVisible(checked)
    
    def toggle_photo_display_panel(self, checked: bool):
        """Toggle photo display panel visibility."""
        if hasattr(self, 'photo_display_dock'):
            self.photo_display_dock.setVisible(checked)
    
    def toggle_tags_panel(self, checked: bool):
        """Toggle tags panel visibility."""
        if hasattr(self, 'tags_dock'):
            self.tags_dock.setVisible(checked)
    
    def create_new_album(self):
        """Create a new album."""
        if hasattr(self, 'album_manager'):
            self.album_manager.create_album()
    
    def add_selected_to_album(self):
        """Add selected photos to an album."""
        if not self.selected_photos:
            QMessageBox.information(self, "无选择", "未选择照片。")
            return
        
        # In a real implementation, this would show an album selector
        QMessageBox.information(self, "添加到相册", 
                               "相册选择器尚未实现。")
    
    def export_selected_photos(self):
        """Export selected photos."""
        if not self.selected_photos:
            QMessageBox.information(self, "无选择", "未选择照片。")
            return
        
        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if export_dir:
            # In a real implementation, this would export the photos
            QMessageBox.information(self, "导出照片", 
                                   f"正在导出 {len(self.selected_photos)} 张照片到 {export_dir}。")
    
    def export_album(self):
        """Export an album."""
        # In a real implementation, this would show an album selector
        QMessageBox.information(self, "导出相册", 
                               "相册导出功能尚未实现。")
    
    def show_batch_processor(self):
        """Show batch processor dialog."""
        if not self.selected_photos:
            QMessageBox.information(self, "无选择", "未选择照片。")
            return
        
        batch_dialog = BatchProcessorDialog(
            self.config_manager,
            self.photo_manager,
            self.image_processor,
            self.selected_photos,
            self
        )
        batch_dialog.exec()
    
    def show_tag_manager(self):
        """Show tag manager dialog."""
        if hasattr(self, 'tags_dock'):
            self.tags_dock.setVisible(True)
            self.tags_dock.raise_()
    
    def show_plugin_manager(self):
        """Show the plugin manager dialog."""
        from .plugin_manager_dialog import PluginManagerDialog
        dialog = PluginManagerDialog(self.plugin_manager, self)
        dialog.plugins_changed.connect(self.on_plugins_changed)
        dialog.exec()
    
    def add_plugin_menu_actions(self, tools_menu):
        """添加插件菜单动作"""
        try:
            # 获取插件的菜单动作
            plugin_menu_actions = self.plugin_manager.get_plugin_menu_actions()
            
            for plugin_name, actions in plugin_menu_actions.items():
                for action_data in actions:
                    if action_data.get("menu") == "工具":
                        # 创建动作
                        action = QAction(action_data["title"], self)
                        action.setData({
                            "plugin_name": plugin_name,
                            "action_name": action_data["action"]
                        })
                        action.triggered.connect(self.handle_plugin_action)
                        tools_menu.addAction(action)
                        
        except Exception as e:
            self.logger.error("Failed to add plugin menu actions", error=str(e))
    
    def handle_plugin_action(self):
        """处理插件动作"""
        try:
            action = self.sender()
            if action and hasattr(action, 'data'):
                data = action.data()
                plugin_name = data["plugin_name"]
                action_name = data["action_name"]
                
                # 获取插件实例
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin and hasattr(plugin, action_name):
                    # 调用插件方法
                    method = getattr(plugin, action_name)
                    method(self)  # 传递self作为parent参数
                else:
                    self.logger.error("Plugin action not found", plugin=plugin_name, action=action_name)
                    
        except Exception as e:
            self.logger.error("Failed to handle plugin action", error=str(e))
            QMessageBox.critical(self, "错误", f"插件动作执行失败：{str(e)}")
    
    def add_plugin_toolbar_actions(self, toolbar):
        """添加插件工具栏动作"""
        try:
            # 获取插件的工具栏动作
            plugin_toolbar_actions = self.plugin_manager.get_plugin_toolbar_actions()
            
            for plugin_name, actions in plugin_toolbar_actions.items():
                for action_data in actions:
                    # 创建动作
                    action = QAction(action_data["title"], self)
                    action.setToolTip(action_data.get("description", ""))
                    action.setData({
                        "plugin_name": plugin_name,
                        "action_name": action_data["action"]
                    })
                    action.triggered.connect(self.handle_plugin_action)
                    toolbar.addAction(action)
                    
        except Exception as e:
            self.logger.error("Failed to add plugin toolbar actions", error=str(e))
    
    def show_google_translate_config(self):
        """显示Google翻译插件配置对话框"""
        try:
            from .plugin_config_dialog import PluginConfigDialog
            dialog = PluginConfigDialog(self)
            dialog.exec()
        except Exception as e:
            self.logger.error("Failed to show Google Translate config", error=str(e))
            QMessageBox.critical(self, "错误", f"无法打开Google翻译插件配置：{str(e)}")
    
    def show_proxy_config(self):
        """显示代理配置对话框"""
        try:
            # 导入代理配置对话框
            from plugins.florence2_reverse_plugin.ui.proxy_config_dialog import ProxyConfigDialog
            dialog = ProxyConfigDialog(self)
            dialog.exec()
        except Exception as e:
            self.logger.error("Failed to show proxy config", error=str(e))
            QMessageBox.critical(self, "错误", f"无法打开代理配置对话框：{str(e)}")
    
    def repair_file_paths(self):
        """Repair missing file paths by searching for moved files."""
        try:
            # 显示进度对话框
            progress = QProgressDialog(
                self.get_text("Checking file paths...", "正在检查文件路径..."),
                self.get_text("Cancel", "取消"),
                0, 0, self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(False)
            progress.show()
            
            # 在后台线程中执行文件路径检查
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class PathRepairWorker(QThread):
                finished = pyqtSignal(dict)
                progress = pyqtSignal(str)
                
                def __init__(self, photo_manager):
                    super().__init__()
                    self.photo_manager = photo_manager
                
                def run(self):
                    self.progress.emit(self.tr("Scanning photos..."))
                    result = self.photo_manager.find_and_fix_missing_files()
                    self.finished.emit(result)
            
            # 创建并启动工作线程
            self.path_repair_worker = PathRepairWorker(self.photo_manager)
            self.path_repair_worker.finished.connect(
                lambda result: self.on_path_repair_finished(result, progress)
            )
            self.path_repair_worker.progress.connect(progress.setLabelText)
            self.path_repair_worker.start()
            
        except Exception as e:
            self.logger.error("Failed to start path repair", error=str(e))
            QMessageBox.critical(
                self,
                self.get_text("Error", "错误"),
                self.get_text("Failed to start path repair", "启动路径修复失败") + f": {str(e)}"
            )
    
    def on_path_repair_finished(self, result: dict, progress: QProgressDialog):
        """Handle path repair completion."""
        progress.close()
        
        # 显示结果
        total_photos = result.get("total_photos", 0)
        missing_files = result.get("missing_files", 0)
        fixed_files = result.get("fixed_files", 0)
        errors = result.get("errors", 0)
        
        message = f"{self.get_text('Path repair completed', '路径修复完成')}\n\n"
        message += f"{self.get_text('Total photos', '总照片数')}: {total_photos}\n"
        message += f"{self.get_text('Missing files', '缺失文件')}: {missing_files}\n"
        message += f"{self.get_text('Fixed files', '修复文件')}: {fixed_files}\n"
        message += f"{self.get_text('Errors', '错误')}: {errors}"
        
        if fixed_files > 0:
            message += f"\n\n{self.get_text('Some files were found and their paths were updated.', '找到了一些文件并更新了它们的路径。')}"
            QMessageBox.information(
                self,
                self.get_text("Success", "成功"),
                message
            )
            
            # 刷新照片显示
            self.refresh_photos()
        elif missing_files > 0:
            message += f"\n\n{self.get_text('Some files could not be found. You may need to manually locate them.', '一些文件无法找到。您可能需要手动定位它们。')}"
            QMessageBox.warning(
                self,
                self.get_text("Partial Success", "部分成功"),
                message
            )
        else:
            QMessageBox.information(
                self,
                self.get_text("No Issues Found", "未发现问题"),
                message
            )
        
        # 记录结果
        self.logger.info("Path repair completed", **result)
    
    def show_settings(self):
        """Show settings dialog."""
        settings_dialog = SettingsDialog(self.config_manager, self)
        settings_dialog.exec()
    
    def show_help(self):
        """Show help contents."""
        QMessageBox.information(self, "帮助", "帮助文档尚未实现。")
    
    def show_log_viewer(self):
        """Show log viewer dialog."""
        from .log_viewer_dialog import LogViewerDialog
        
        log_dialog = LogViewerDialog(self.logging_manager, self)
        log_dialog.exec()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "关于 PyPhotoManager", 
                         "PyPhotoManager v1.2.0\n\n"
                         "专业照片管理软件\n"
                         "使用 PyQt6 和 Python 构建")
    
    def show_language_dialog(self):
        """Show language selection dialog."""
        from .language_dialog import LanguageDialog
        
        language_dialog = LanguageDialog(self.language_manager, self)
        language_dialog.language_changed.connect(self.on_language_changed)
        language_dialog.exec()
    
    def change_language(self, language_code: str):
        """Change application language.
        
        Args:
            language_code: Language code to set.
        """
        if self.language_manager.set_language(language_code):
            self.logger.info("Language changed", language=language_code)
            
            # Update checked state of language actions
            for action in self.language_actions:
                if hasattr(action, 'data'):
                    action.setChecked(action.data() == language_code)
            
            # Show notification
            QMessageBox.information(
                self, 
                "语言已更改",
                "语言已更改。某些元素可能需要重启应用程序。"
            )
    
    def on_language_changed(self, language_code: str):
        """Handle language change from dialog.
        
        Args:
            language_code: New language code.
        """
        # Update checked state of language actions
        for action in self.language_actions:
            if hasattr(action, 'data'):
                action.setChecked(action.data() == language_code)
    

    

    
    def on_plugins_changed(self):
        """Handle plugin changes."""
        # In a real implementation, this would reload plugins
        self.logger.info("Plugins changed")
    
    def refresh_current_photo_ai_info(self):
        """刷新当前选中图片的AI信息"""
        try:
            current_photo_id = self.get_current_photo_id()
            if current_photo_id <= 0:
                QMessageBox.warning(self, "警告", "请先选择一张图片")
                return
            
            # 显示进度对话框
            progress = QProgressDialog("正在刷新AI信息...", "取消", 0, 1, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(0)
            
            # 刷新AI信息
            success = self.photo_manager.refresh_photo_ai_metadata(current_photo_id)
            
            progress.setValue(1)
            
            if success:
                QMessageBox.information(self, "成功", "AI信息刷新成功")
                # 重新加载当前图片信息
                self.update_photo_info(current_photo_id)
                self.update_tags_for_photo(current_photo_id)
            else:
                QMessageBox.warning(self, "警告", "AI信息刷新失败")
        
        except Exception as e:
            self.logger.error("Failed to refresh current photo AI info", error=str(e))
            QMessageBox.critical(self, "错误", f"刷新AI信息时发生错误：{str(e)}")
    
    def refresh_album_ai_info(self):
        """刷新当前相册中所有图片的AI信息"""
        try:
            # 获取当前选中的相册
            if not hasattr(self, 'current_album_id') or not self.current_album_id:
                QMessageBox.warning(self, "警告", "请先选择一个相册")
                return
            
            # 确认对话框
            reply = QMessageBox.question(
                self, 
                "确认刷新", 
                f"确定要刷新相册中所有图片的AI信息吗？\n这可能需要一些时间。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 显示进度对话框
            progress = QProgressDialog("正在刷新相册AI信息...", "取消", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(0)
            
            # 刷新相册AI信息
            result = self.photo_manager.refresh_album_ai_metadata(self.current_album_id)
            
            progress.close()
            
            # 显示结果
            message = f"刷新完成！\n成功：{result['success']} 张\n失败：{result['failed']} 张\n总计：{result['total']} 张"
            QMessageBox.information(self, "刷新完成", message)
            
            # 重新加载相册
            if self.album_manager:
                self.album_manager.load_album_photos(self.current_album_id)
        
        except Exception as e:
            self.logger.error("Failed to refresh album AI info", error=str(e))
            QMessageBox.critical(self, "错误", f"刷新相册AI信息时发生错误：{str(e)}")
    
    def closeEvent(self, event):
        """Handle application close."""
        # 保存当前布局
        self.save_layout()
        
        # 保存其他设置
        self.save_settings()
        
        # Unload plugins
        self.plugin_manager.unload_all_plugins()
        
        self.logger.info("Application closing")
        event.accept()


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PyPhotoManager")
    app.setApplicationVersion("0.1.0")
    
    window = MainWindow()
    window.show()
    
    return app.exec()
    