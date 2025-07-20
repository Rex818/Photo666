"""
Settings dialog for PyPhotoManager.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QComboBox, QSpinBox,
    QCheckBox, QLineEdit, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
import structlog

from ..config.manager import ConfigManager
from ..utils.translation import TranslationManager


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    settings_saved = pyqtSignal()
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.logger = structlog.get_logger("picman.gui.settings_dialog")
        
        # Get translation manager from parent if available
        self.translation_manager = None
        if hasattr(parent, "translation_manager"):
            self.translation_manager = parent.translation_manager
        else:
            # Create a new translation manager if not available
            self.translation_manager = TranslationManager(config_manager)
        
        self.tr = self.translation_manager.tr
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle(self.tr("settings.title"))
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # General tab
        self.general_tab = QWidget()
        self.create_general_tab()
        self.tab_widget.addTab(self.general_tab, "General")
        
        # Import tab
        self.import_tab = QWidget()
        self.create_import_tab()
        self.tab_widget.addTab(self.import_tab, "Import")
        
        # Display tab
        self.display_tab = QWidget()
        self.create_display_tab()
        self.tab_widget.addTab(self.display_tab, "Display")
        
        # Advanced tab
        self.advanced_tab = QWidget()
        self.create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton(self.tr("settings.apply"))
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton(self.tr("settings.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(self.tr("settings.save"))
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_general_tab(self):
        """Create the general settings tab."""
        layout = QVBoxLayout(self.general_tab)
        
        # Language settings
        language_group = QGroupBox("界面")
        language_layout = QFormLayout(language_group)
        
        self.language_combo = QComboBox()
        available_languages = self.translation_manager.get_available_languages()
        for code, name in available_languages.items():
            self.language_combo.addItem(name, code)
        
        language_layout.addRow(self.tr("settings.language"), self.language_combo)
        
        layout.addWidget(language_group)
        
        # Other general settings can be added here
        
        layout.addStretch()
    
    def create_import_tab(self):
        """Create the import settings tab."""
        layout = QVBoxLayout(self.import_tab)
        
        # Import settings
        import_group = QGroupBox("导入设置")
        import_layout = QFormLayout(import_group)
        
        self.duplicate_check_cb = QCheckBox()
        import_layout.addRow("检查重复文件:", self.duplicate_check_cb)
        
        self.generate_thumbnails_cb = QCheckBox()
        import_layout.addRow("导入时生成缩略图:", self.generate_thumbnails_cb)
        
        self.recursive_import_cb = QCheckBox()
        import_layout.addRow("递归导入目录:", self.recursive_import_cb)
        
        layout.addWidget(import_group)
        
        # Default locations
        locations_group = QGroupBox("默认位置")
        locations_layout = QFormLayout(locations_group)
        
        self.default_import_dir = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_import_dir)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.default_import_dir)
        dir_layout.addWidget(browse_btn)
        
        locations_layout.addRow("默认导入目录:", dir_layout)
        
        layout.addWidget(locations_group)
        
        layout.addStretch()
    
    def create_display_tab(self):
        """Create the display settings tab."""
        layout = QVBoxLayout(self.display_tab)
        
        # Thumbnail settings
        thumbnail_group = QGroupBox("缩略图")
        thumbnail_layout = QFormLayout(thumbnail_group)
        
        self.thumbnail_size = QSpinBox()
        self.thumbnail_size.setRange(50, 500)
        self.thumbnail_size.setSingleStep(10)
        thumbnail_layout.addRow("缩略图大小:", self.thumbnail_size)
        
        self.thumbnail_quality = QSpinBox()
        self.thumbnail_quality.setRange(1, 100)
        thumbnail_layout.addRow("缩略图质量:", self.thumbnail_quality)
        
        layout.addWidget(thumbnail_group)
        
        # Viewer settings
        viewer_group = QGroupBox("照片查看器")
        viewer_layout = QFormLayout(viewer_group)
        
        self.zoom_factor = QSpinBox()
        self.zoom_factor.setRange(5, 50)
        self.zoom_factor.setSingleStep(5)
        viewer_layout.addRow("缩放步长 (%):", self.zoom_factor)
        
        self.fit_to_window_cb = QCheckBox()
        viewer_layout.addRow("默认适应窗口:", self.fit_to_window_cb)
        
        layout.addWidget(viewer_group)
        
        layout.addStretch()
    
    def create_advanced_tab(self):
        """Create the advanced settings tab."""
        layout = QVBoxLayout(self.advanced_tab)
        
        # Database settings
        db_group = QGroupBox("数据库")
        db_layout = QFormLayout(db_group)
        
        self.db_path = QLineEdit()
        self.db_path.setReadOnly(True)
        db_layout.addRow("数据库路径:", self.db_path)
        
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(0, 30)
        self.backup_interval.setSpecialValueText("从不")
        db_layout.addRow("自动备份间隔 (天):", self.backup_interval)
        
        layout.addWidget(db_group)
        
        # Logging settings
        log_group = QGroupBox("日志")
        log_layout = QFormLayout(log_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_layout.addRow("日志级别:", self.log_level_combo)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
    
    def load_settings(self):
        """Load current settings into UI."""
        # General tab
        current_language = self.config.get("ui.language", "zh_CN")
        index = self.language_combo.findData(current_language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        
        # Import tab
        self.duplicate_check_cb.setChecked(self.config.get("import_settings.check_duplicates", True))
        self.generate_thumbnails_cb.setChecked(self.config.get("thumbnail.generate_on_import", True))
        self.recursive_import_cb.setChecked(self.config.get("import_settings.recursive", True))
        self.default_import_dir.setText(self.config.get("import_settings.default_directory", ""))
        
        # Display tab
        self.thumbnail_size.setValue(self.config.get("thumbnail.size", 200))
        self.thumbnail_quality.setValue(self.config.get("thumbnail.quality", 85))
        self.zoom_factor.setValue(self.config.get("viewer.zoom_step", 20))
        self.fit_to_window_cb.setChecked(self.config.get("viewer.fit_to_window", True))
        
        # Advanced tab
        self.db_path.setText(self.config.get("database.path", "data/picman.db"))
        self.backup_interval.setValue(self.config.get("database.backup_interval", 7))
        
        log_level = self.config.get("logging.level", "INFO")
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
    
    def apply_settings(self):
        """Apply settings without closing dialog."""
        # General tab
        language_code = self.language_combo.currentData()
        # Save language setting
        old_language = self.config.get("ui.language", "zh_CN")
        
        if language_code != old_language:
            self.translation_manager.set_language(language_code)
            # Signal that UI needs to be updated
            self.settings_saved.emit()
        
        # Import tab
        self.config.set("import_settings.check_duplicates", self.duplicate_check_cb.isChecked())
        self.config.set("thumbnail.generate_on_import", self.generate_thumbnails_cb.isChecked())
        self.config.set("import_settings.recursive", self.recursive_import_cb.isChecked())
        self.config.set("import_settings.default_directory", self.default_import_dir.text())
        
        # Display tab
        self.config.set("thumbnail.size", self.thumbnail_size.value())
        self.config.set("thumbnail.quality", self.thumbnail_quality.value())
        self.config.set("viewer.zoom_step", self.zoom_factor.value())
        self.config.set("viewer.fit_to_window", self.fit_to_window_cb.isChecked())
        
        # Advanced tab
        self.config.set("database.backup_interval", self.backup_interval.value())
        self.config.set("logging.level", self.log_level_combo.currentText())
        
        self.logger.info("Settings applied")
    
    def save_settings(self):
        """Save settings and close dialog."""
        self.apply_settings()
        self.accept()
    
    def browse_import_dir(self):
        """Browse for default import directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "选择默认导入目录", self.default_import_dir.text()
        )
        if directory:
            self.default_import_dir.setText(directory)