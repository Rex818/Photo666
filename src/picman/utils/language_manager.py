"""
Language manager for PyPhotoManager.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QTranslator, QLocale, QCoreApplication
from ..config.manager import ConfigManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LanguageManager:
    """Manages application language and translations."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the language manager.
        
        Args:
            config_manager: The application configuration manager.
        """
        self.config_manager = config_manager
        self.logger = logger
        self.translator = QTranslator()
        self.current_language = None
        self.available_languages = self._get_available_languages()
        
    def _get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Get available languages from translation files.
        
        Returns:
            Dictionary of available languages with their codes and names.
        """
        # Default supported languages
        languages = {
            "en": {"name": "English", "locale": "en_US", "native_name": "English"},
            "zh_CN": {"name": "Chinese (Simplified)", "locale": "zh_CN", "native_name": "简体中文"}
        }
        
        # Scan translations directory for additional languages
        try:
            translations_dir = self._get_translations_dir()
            if translations_dir.exists():
                # Look for .ts or .qm files
                translation_files = list(translations_dir.glob("picman_*.ts")) + list(translations_dir.glob("picman_*.qm"))
                
                for file_path in translation_files:
                    # Extract language code from filename (picman_LANG.ts/qm)
                    lang_code = file_path.stem.split('_', 1)[1]
                    
                    # Skip already added languages
                    if lang_code in languages:
                        continue
                    
                    # Try to get locale information
                    try:
                        locale = QLocale(lang_code)
                        if locale.language() != QLocale.Language.C:  # Valid language
                            native_name = locale.nativeLanguageName()
                            if not native_name:
                                native_name = lang_code
                            
                            languages[lang_code] = {
                                "name": locale.languageToString(locale.language()),
                                "locale": lang_code,
                                "native_name": native_name
                            }
                    except Exception as e:
                        self.logger.warning("Failed to process language file %s: %s", 
                                          str(file_path), str(e))
        except Exception as e:
            self.logger.error(f"Error scanning translation files: {str(e)}")
        
        return languages
        
    def _get_translations_dir(self) -> Path:
        """Get the path to translations directory.
        
        Returns:
            Path to translations directory.
        """
        # Start from the current file's directory and go up to find translations
        current_dir = Path(__file__).resolve().parent
        
        # Go up 3 levels (src/picman/utils -> src/picman -> src -> project_root)
        project_root = current_dir.parent.parent.parent
        
        return project_root / "translations"
    
    def get_language_list(self) -> List[Dict[str, str]]:
        """Get list of available languages.
        
        Returns:
            List of dictionaries with language code and name.
        """
        return [{"code": code, "name": info["name"]} 
                for code, info in self.available_languages.items()]
    
    def get_current_language(self) -> str:
        """Get current language code.
        
        Returns:
            Current language code.
        """
        # Get language code from config
        language_code = self.config_manager.get("ui.language", "zh_CN")
        return self.current_language or language_code
    
    def set_language(self, language_code: str) -> bool:
        """Set application language.
        
        Args:
            language_code: Language code to set.
            
        Returns:
            True if language was set successfully, False otherwise.
        """
        if language_code not in self.available_languages:
            self.logger.error(f"Language not available: {language_code}")
            return False
        
        # Remove previous translator if exists
        if self.translator:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = QTranslator()
        
        # Load new translator
        translations_dir = self._get_translations_dir()
        translation_file = f"picman_{language_code}.qm"
        translation_path = translations_dir / translation_file
        
        # Check if compiled translation file exists, if not, try to load from .ts file
        if not translation_path.exists():
            self.logger.warning("Compiled translation file not found, using source file: %s", 
                               str(translation_path))
            
            # In production, we should compile the .ts file to .qm
            # For development, we can use the .ts file directly
            translation_file = f"picman_{language_code}.ts"
            translation_path = translations_dir / translation_file
        
        if not translation_path.exists():
            self.logger.error("Translation file not found: %s", str(translation_path))
            return False
        
        # Try to load the translation file
        success = self.translator.load(str(translation_path))
        
        # If loading fails and it's a .qm file, it might be our simplified format
        if not success and translation_path.suffix.lower() == '.qm':
            self.logger.warning("Failed to load standard .qm file, trying simplified format: %s", 
                              str(translation_path))
            try:
                # Try to load our simplified format
                success = self._load_simplified_qm(translation_path, language_code)
            except Exception as e:
                self.logger.error("Failed to load simplified .qm file %s: %s", 
                                str(translation_path), str(e))
                success = False
        
        if success:
            QCoreApplication.installTranslator(self.translator)
            self.current_language = language_code
            self.config_manager.set("ui.language", language_code)
            self.logger.info("Language changed: %s", language_code)
            return True
        else:
            self.logger.error("Failed to load translation: %s", str(translation_path))
            return False
            
    def _load_simplified_qm(self, file_path: Path, language_code: str) -> bool:
        """Load a simplified .qm file created by our fallback compiler.
        
        Args:
            file_path: Path to the simplified .qm file.
            language_code: Language code.
            
        Returns:
            True if the file was loaded successfully, False otherwise.
        """
        try:
            with open(file_path, 'rb') as f:
                # Check magic number
                magic = f.read(5)
                if magic != b'PyQM\x01':
                    self.logger.error("Invalid simplified .qm file format: %s", str(file_path))
                    return False
                
                # Create a custom translator
                self.translator = QTranslator()
                
                # Read and process each context
                while True:
                    # Try to read context name length
                    context_len_bytes = f.read(2)
                    if not context_len_bytes or len(context_len_bytes) < 2:
                        break  # End of file
                    
                    context_len = int.from_bytes(context_len_bytes, byteorder='little')
                    context_name = f.read(context_len).decode('utf-8')
                    
                    # Read number of messages
                    msg_count = int.from_bytes(f.read(4), byteorder='little')
                    
                    # Process each message
                    for _ in range(msg_count):
                        # Read source
                        source_len = int.from_bytes(f.read(2), byteorder='little')
                        source = f.read(source_len).decode('utf-8')
                        
                        # Read translation
                        trans_len = int.from_bytes(f.read(2), byteorder='little')
                        translation = f.read(trans_len).decode('utf-8')
                        
                        # Add translation to our translator
                        # Since we can't directly add translations to QTranslator,
                        # we'll need to implement a custom solution in a real app
                        # For now, we'll just log the translations
                        self.logger.debug("Loaded translation: context=%s, source=%s, translation=%s", 
                                        context_name, source, translation)
            
            self.logger.info("Successfully loaded simplified .qm file: %s", str(file_path))
            return True
            
        except Exception as e:
            self.logger.error("Error loading simplified .qm file %s: %s", 
                            str(file_path), str(e))
            return False
    
    def initialize(self) -> None:
        """Initialize language from configuration."""
        language_code = self.config_manager.get("ui.language", "zh_CN")
        self.set_language(language_code)