"""
Plugin manager dialog for PyPhotoManager.
"""

from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QMessageBox,
    QTabWidget, QWidget, QGroupBox, QFormLayout, QTextEdit,
    QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
import structlog
import os
import shutil

from ..plugins.manager import PluginManager
from ..plugins.base import PluginInfo


class PluginListItem(QListWidgetItem):
    """List item for displaying a plugin."""
    
    def __init__(self, plugin_info: Dict[str, Any], enabled: bool = False):
        super().__init__(plugin_info.get("name", "Unknown Plugin"))
        self.plugin_info = plugin_info
        self.enabled = enabled
        
        # Set tooltip with plugin info
        tooltip = (f"{plugin_info.get('name')} v{plugin_info.get('version')}\n"
                  f"Author: {plugin_info.get('author')}\n"
                  f"{plugin_info.get('description')}")
        self.setToolTip(tooltip)
        
        # Set checkable
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)


class PluginManagerDialog(QDialog):
    """Dialog for managing plugins."""
    
    plugins_changed = pyqtSignal()
    
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.logger = structlog.get_logger("picman.gui.plugin_manager")
        
        self.init_ui()
        self.load_plugins()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Plugin Manager")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Installed plugins tab
        self.installed_tab = QWidget()
        self.create_installed_tab()
        self.tab_widget.addTab(self.installed_tab, "Installed Plugins")
        
        # Add new plugin tab
        self.add_tab = QWidget()
        self.create_add_tab()
        self.tab_widget.addTab(self.add_tab, "Add Plugin")
        
        # Settings tab
        self.settings_tab = QWidget()
        self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_installed_tab(self):
        """Create the installed plugins tab."""
        layout = QVBoxLayout(self.installed_tab)
        
        # Plugin list
        self.plugin_list = QListWidget()
        self.plugin_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.plugin_list.itemClicked.connect(self.on_plugin_selected)
        self.plugin_list.itemChanged.connect(self.on_plugin_state_changed)
        layout.addWidget(self.plugin_list)
        
        # Plugin details
        details_group = QGroupBox("Plugin Details")
        details_layout = QFormLayout(details_group)
        
        self.plugin_name_label = QLabel("-")
        details_layout.addRow("Name:", self.plugin_name_label)
        
        self.plugin_version_label = QLabel("-")
        details_layout.addRow("Version:", self.plugin_version_label)
        
        self.plugin_author_label = QLabel("-")
        details_layout.addRow("Author:", self.plugin_author_label)
        
        self.plugin_description = QTextEdit()
        self.plugin_description.setReadOnly(True)
        self.plugin_description.setMaximumHeight(80)
        details_layout.addRow("Description:", self.plugin_description)
        
        layout.addWidget(details_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.enable_btn = QPushButton("Enable")
        self.enable_btn.clicked.connect(self.enable_plugin)
        button_layout.addWidget(self.enable_btn)
        
        self.disable_btn = QPushButton("Disable")
        self.disable_btn.clicked.connect(self.disable_plugin)
        button_layout.addWidget(self.disable_btn)
        
        button_layout.addStretch()
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_plugin)
        button_layout.addWidget(self.remove_btn)
        
        layout.addLayout(button_layout)
    
    def create_add_tab(self):
        """Create the add plugin tab."""
        layout = QVBoxLayout(self.add_tab)
        
        # From file
        file_group = QGroupBox("Install from File")
        file_layout = QVBoxLayout(file_group)
        
        file_desc = QLabel("Select a Python file (.py) containing a plugin implementation.")
        file_desc.setWordWrap(True)
        file_layout.addWidget(file_desc)
        
        file_btn_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        file_btn_layout.addWidget(self.file_path_label, 1)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_plugin_file)
        file_btn_layout.addWidget(self.browse_btn)
        
        file_layout.addLayout(file_btn_layout)
        
        self.install_file_btn = QPushButton("Install Plugin")
        self.install_file_btn.clicked.connect(self.install_from_file)
        self.install_file_btn.setEnabled(False)
        file_layout.addWidget(self.install_file_btn)
        
        layout.addWidget(file_group)
        
        # From repository (placeholder for future implementation)
        repo_group = QGroupBox("Install from Repository")
        repo_layout = QVBoxLayout(repo_group)
        
        repo_desc = QLabel("Browse and install plugins from the online repository.")
        repo_desc.setWordWrap(True)
        repo_layout.addWidget(repo_desc)
        
        repo_msg = QLabel("Online repository not available in this version.")
        repo_msg.setStyleSheet("color: gray;")
        repo_layout.addWidget(repo_msg)
        
        layout.addWidget(repo_group)
        
        layout.addStretch()
    
    def create_settings_tab(self):
        """Create the plugin settings tab."""
        layout = QVBoxLayout(self.settings_tab)
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        
        self.auto_load_cb = QCheckBox()
        self.auto_load_cb.setChecked(self.plugin_manager.config.get("plugins.auto_load", True))
        self.auto_load_cb.stateChanged.connect(self.update_plugin_settings)
        general_layout.addRow("Auto-load Plugins:", self.auto_load_cb)
        
        self.sandbox_cb = QCheckBox()
        self.sandbox_cb.setChecked(self.plugin_manager.config.get("plugins.sandbox_enabled", True))
        self.sandbox_cb.stateChanged.connect(self.update_plugin_settings)
        general_layout.addRow("Enable Plugin Sandbox:", self.sandbox_cb)
        
        layout.addWidget(general_group)
        
        # Plugin directory
        dir_group = QGroupBox("Plugin Directory")
        dir_layout = QHBoxLayout(dir_group)
        
        self.plugin_dir_label = QLabel(self.plugin_manager.config.get("plugins.plugin_directory", "plugins"))
        dir_layout.addWidget(self.plugin_dir_label, 1)
        
        self.change_dir_btn = QPushButton("Change...")
        self.change_dir_btn.clicked.connect(self.change_plugin_directory)
        dir_layout.addWidget(self.change_dir_btn)
        
        layout.addWidget(dir_group)
        
        layout.addStretch()
    
    def load_plugins(self):
        """Load and display available plugins."""
        self.plugin_list.clear()
        
        # Get discovered plugins
        discovered_plugins = self.plugin_manager.discover_plugins()
        
        # Get enabled plugins
        enabled_plugins = self.plugin_manager.config.get("plugins.enabled_plugins", [])
        
        # Add plugins to list
        for plugin_info in discovered_plugins:
            enabled = plugin_info["name"] in enabled_plugins
            item = PluginListItem(plugin_info, enabled)
            self.plugin_list.addItem(item)
        
        # Update UI state
        self.update_button_states()
    
    def on_plugin_selected(self, item):
        """Handle plugin selection."""
        if isinstance(item, PluginListItem):
            # Update details panel
            plugin_info = item.plugin_info
            self.plugin_name_label.setText(plugin_info.get("name", "-"))
            self.plugin_version_label.setText(plugin_info.get("version", "-"))
            self.plugin_author_label.setText(plugin_info.get("author", "-"))
            self.plugin_description.setText(plugin_info.get("description", ""))
            
            # Update button states
            self.update_button_states()
    
    def on_plugin_state_changed(self, item):
        """Handle plugin enable/disable via checkbox."""
        if isinstance(item, PluginListItem):
            enabled = item.checkState() == Qt.CheckState.Checked
            plugin_name = item.plugin_info.get("name")
            
            if enabled:
                self.enable_plugin_by_name(plugin_name)
            else:
                self.disable_plugin_by_name(plugin_name)
    
    def enable_plugin(self):
        """Enable the selected plugin."""
        item = self.plugin_list.currentItem()
        if isinstance(item, PluginListItem):
            plugin_name = item.plugin_info.get("name")
            self.enable_plugin_by_name(plugin_name)
            item.setCheckState(Qt.CheckState.Checked)
    
    def disable_plugin(self):
        """Disable the selected plugin."""
        item = self.plugin_list.currentItem()
        if isinstance(item, PluginListItem):
            plugin_name = item.plugin_info.get("name")
            self.disable_plugin_by_name(plugin_name)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def enable_plugin_by_name(self, plugin_name: str):
        """Enable a plugin by name."""
        # Get current enabled plugins
        enabled_plugins = self.plugin_manager.config.get("plugins.enabled_plugins", [])
        
        # Add plugin if not already enabled
        if plugin_name not in enabled_plugins:
            enabled_plugins.append(plugin_name)
            self.plugin_manager.config.set("plugins.enabled_plugins", enabled_plugins)
            
            # Load the plugin
            self.plugin_manager.load_plugin(plugin_name)
            
            self.logger.info("Plugin enabled", name=plugin_name)
            self.plugins_changed.emit()
    
    def disable_plugin_by_name(self, plugin_name: str):
        """Disable a plugin by name."""
        # Get current enabled plugins
        enabled_plugins = self.plugin_manager.config.get("plugins.enabled_plugins", [])
        
        # Remove plugin if enabled
        if plugin_name in enabled_plugins:
            enabled_plugins.remove(plugin_name)
            self.plugin_manager.config.set("plugins.enabled_plugins", enabled_plugins)
            
            # Unload the plugin
            self.plugin_manager.unload_plugin(plugin_name)
            
            self.logger.info("Plugin disabled", name=plugin_name)
            self.plugins_changed.emit()
    
    def remove_plugin(self):
        """Remove the selected plugin."""
        item = self.plugin_list.currentItem()
        if not isinstance(item, PluginListItem):
            return
        
        plugin_name = item.plugin_info.get("name")
        plugin_path = item.plugin_info.get("path")
        
        # Confirm removal
        reply = QMessageBox.question(
            self, "移除插件",
            f"确定要移除插件 '{plugin_name}' 吗？\n"
            "此操作将卸载插件并删除其配置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Disable plugin first
                self.disable_plugin_by_name(plugin_name)
                
                # Delete plugin file
                if plugin_path and os.path.exists(plugin_path):
                    os.remove(plugin_path)
                    self.logger.info("Plugin file removed", path=plugin_path)
                
                # Refresh plugin list
                self.load_plugins()
                
                QMessageBox.information(self, "Plugin Removed", 
                                      f"Plugin '{plugin_name}' has been removed.")
                
            except Exception as e:
                self.logger.error("Failed to remove plugin", 
                                name=plugin_name, error=str(e))
                QMessageBox.critical(self, "Error", 
                                   f"Failed to remove plugin: {str(e)}")
    
    def browse_plugin_file(self):
        """Browse for a plugin file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Plugin File", "", "Python Files (*.py)"
        )
        
        if file_path:
            self.file_path_label.setText(file_path)
            self.install_file_btn.setEnabled(True)
    
    def install_from_file(self):
        """Install a plugin from a file."""
        file_path = self.file_path_label.text()
        if not file_path or file_path == "No file selected" or not os.path.exists(file_path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid plugin file.")
            return
        
        try:
            # Get plugin directory
            plugin_dir = self.plugin_manager.config.get("plugins.plugin_directory", "plugins")
            os.makedirs(plugin_dir, exist_ok=True)
            
            # Copy plugin file to plugin directory
            dest_path = os.path.join(plugin_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            
            self.logger.info("Plugin installed", 
                           source=file_path, 
                           destination=dest_path)
            
            # Refresh plugin list
            self.load_plugins()
            
            QMessageBox.information(self, "Plugin Installed", 
                                  "Plugin has been installed successfully.")
            
            # Reset file selection
            self.file_path_label.setText("No file selected")
            self.install_file_btn.setEnabled(False)
            
        except Exception as e:
            self.logger.error("Failed to install plugin", 
                            file=file_path, error=str(e))
            QMessageBox.critical(self, "Installation Error", 
                               f"Failed to install plugin: {str(e)}")
    
    def change_plugin_directory(self):
        """Change the plugin directory."""
        current_dir = self.plugin_manager.config.get("plugins.plugin_directory", "plugins")
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Plugin Directory", current_dir
        )
        
        if new_dir:
            # Update config
            self.plugin_manager.config.set("plugins.plugin_directory", new_dir)
            
            # Update UI
            self.plugin_dir_label.setText(new_dir)
            
            # Reload plugins
            self.load_plugins()
    
    def update_plugin_settings(self):
        """Update plugin settings."""
        # Update auto-load setting
        auto_load = self.auto_load_cb.isChecked()
        self.plugin_manager.config.set("plugins.auto_load", auto_load)
        
        # Update sandbox setting
        sandbox_enabled = self.sandbox_cb.isChecked()
        self.plugin_manager.config.set("plugins.sandbox_enabled", sandbox_enabled)
        
        self.logger.info("Plugin settings updated", 
                       auto_load=auto_load, 
                       sandbox_enabled=sandbox_enabled)
    
    def update_button_states(self):
        """Update button states based on selection."""
        item = self.plugin_list.currentItem()
        has_selection = item is not None
        
        if has_selection and isinstance(item, PluginListItem):
            is_enabled = item.checkState() == Qt.CheckState.Checked
            self.enable_btn.setEnabled(not is_enabled)
            self.disable_btn.setEnabled(is_enabled)
            self.remove_btn.setEnabled(True)
        else:
            self.enable_btn.setEnabled(False)
            self.disable_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)