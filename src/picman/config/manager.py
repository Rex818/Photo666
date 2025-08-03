"""
Configuration management module for PyPhotoManager.
Handles application configuration using YAML files.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, Tuple, List
import yaml
from pathlib import Path
import logging

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str = "data/picman.db"
    pool_size: int = 10
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    auto_vacuum: bool = True

@dataclass
class ThumbnailConfig:
    """Thumbnail generation configuration."""
    size: Tuple[int, int] = (256, 256)
    quality: int = 85
    format: str = "JPEG"
    cache_size: int = 1000
    generate_on_import: bool = True

@dataclass
class UIConfig:
    """User interface configuration."""
    theme: str = "default"
    window_size: Tuple[int, int] = (1400, 900)
    window_position: Optional[Tuple[int, int]] = None
    thumbnail_grid_columns: int = 6
    show_image_info: bool = True
    auto_save_layout: bool = True
    layout: Optional[Dict[str, Any]] = field(default_factory=dict)

@dataclass
class ImportConfig:
    """Image import configuration."""
    supported_formats: List[str] = None
    auto_detect_duplicates: bool = True
    preserve_directory_structure: bool = True
    extract_exif: bool = True
    generate_thumbnails: bool = True
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']

@dataclass
class PluginConfig:
    """Plugin system configuration."""
    enabled_plugins: List[str] = None
    plugin_directory: str = "plugins"
    auto_load: bool = True
    sandbox_enabled: bool = True
    
    def __post_init__(self):
        if self.enabled_plugins is None:
            self.enabled_plugins = []

@dataclass
class LoggingConfig:
    """Logging system configuration."""
    level: str = "INFO"
    file_path: str = "logs/picman.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class AppConfig:
    """Main application configuration."""
    database: DatabaseConfig = None
    thumbnail: ThumbnailConfig = None
    ui: UIConfig = None
    import_settings: ImportConfig = None
    plugins: PluginConfig = None
    logging: LoggingConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.thumbnail is None:
            self.thumbnail = ThumbnailConfig()
        if self.ui is None:
            self.ui = UIConfig()
        if self.import_settings is None:
            self.import_settings = ImportConfig()
        if self.plugins is None:
            self.plugins = PluginConfig()
        if self.logging is None:
            self.logging = LoggingConfig()

class ConfigManager:
    """Configuration manager for PyPhotoManager."""
    
    def __init__(self, config_path: str = "config/app.yaml"):
        self.config_path = Path(config_path)
        self.config: AppConfig = AppConfig()
        self.logger = logging.getLogger(__name__)
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.load_config()
    
    def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                if config_data:
                    self._update_config_from_dict(self.config, config_data)
                
                self.logger.info("Configuration loaded successfully")
                return True
            else:
                # Create default configuration file
                self.save_config()
                self.logger.info("Created default configuration file")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save configuration to file."""
        try:
            config_dict = asdict(self.config)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            self.logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get(self, key_path: str, default=None):
        """Get configuration value by key path."""
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                value = getattr(value, key)
            
            return value
            
        except (AttributeError, KeyError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """Set configuration value by key path."""
        try:
            keys = key_path.split('.')
            config_obj = self.config
            
            # Navigate to parent object
            for key in keys[:-1]:
                config_obj = getattr(config_obj, key)
            
            # Set value
            setattr(config_obj, keys[-1], value)
            
            # Auto-save
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration: {key_path}={value}, error: {e}")
            return False
    
    def _update_config_from_dict(self, config_obj, config_dict):
        """Recursively update configuration from dictionary."""
        for key, value in config_dict.items():
            if hasattr(config_obj, key):
                attr = getattr(config_obj, key)
                if hasattr(attr, '__dict__') and isinstance(value, dict):
                    # Recursively update nested configuration objects
                    self._update_config_from_dict(attr, value)
                else:
                    # Set simple values
                    setattr(config_obj, key, value)
