"""
Language selection dialog for PyPhotoManager.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QMessageBox, QListWidget,
    QListWidgetItem, QGridLayout, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ..utils.language_manager import LanguageManager


class LanguageDialog(QDialog):
    """Dialog for selecting application language."""
    
    language_changed = pyqtSignal(str)
    
    def __init__(self, language_manager: LanguageManager, parent=None):
        """Initialize the language dialog.
        
        Args:
            language_manager: The language manager.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.language_manager = language_manager
        self.current_language = language_manager.get_current_language()
        self.available_languages = language_manager.available_languages
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(self.tr("Language Settings"))
        self.setMinimumWidth(450)
        self.setMinimumHeight(350)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(self.tr("Select Application Language"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Language list
        self.language_list = QListWidget()
        self.language_list.setMinimumHeight(200)
        
        # Add languages to list
        for code, info in self.available_languages.items():
            item = QListWidgetItem()
            
            # Display both native name and English name if different
            if "native_name" in info and info["native_name"] != info["name"]:
                item.setText(f"{info['native_name']} ({info['name']})")
            else:
                item.setText(info["name"])
                
            item.setData(Qt.ItemDataRole.UserRole, code)
            
            # Set current language selected
            if code == self.current_language:
                item.setSelected(True)
                self.language_list.setCurrentItem(item)
            
            self.language_list.addItem(item)
        
        layout.addWidget(self.language_list)
        
        # Note about restart
        note_label = QLabel(self.tr("Note: Some changes may require restarting the application to take full effect."))
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton(self.tr("Apply"))
        apply_button.clicked.connect(self.apply_language)
        
        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton(self.tr("OK"))
        ok_button.clicked.connect(self.accept_and_apply)
        ok_button.setDefault(True)
        
        button_layout.addWidget(apply_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
    
    def apply_language(self):
        """Apply the selected language."""
        selected_items = self.language_list.selectedItems()
        if not selected_items:
            return
            
        selected_language = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if selected_language != self.current_language:
            success = self.language_manager.set_language(selected_language)
            if success:
                self.language_changed.emit(selected_language)
                self.current_language = selected_language
                QMessageBox.information(
                    self, 
                    self.tr("Language Changed"),
                    self.tr("Language has been changed. Some elements may require restarting the application.")
                )
            else:
                QMessageBox.warning(
                    self, 
                    self.tr("Error"),
                    self.tr("Failed to change language.")
                )
    
    def accept_and_apply(self):
        """Apply language and accept dialog."""
        self.apply_language()
        self.accept()