"""
Base plugin system for PyPhotoManager.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging


class PluginInfo:
    """Information about a plugin."""
    
    def __init__(self, name: str, version: str, description: str, author: str):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author
        }


class Plugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"picman.plugins.{self.__class__.__name__}")
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        pass
    
    @abstractmethod
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Initialize the plugin with application context."""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the plugin."""
        pass
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions provided by this plugin."""
        return []
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """Get toolbar actions provided by this plugin."""
        return []
    
    def get_settings(self) -> Dict[str, Any]:
        """Get plugin settings."""
        return {}
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Update plugin settings."""
        return True


class PhotoFilterPlugin(Plugin):
    """Base class for photo filter plugins."""
    
    @abstractmethod
    def apply_filter(self, image_path: str, output_path: str, params: Dict[str, Any] = None) -> bool:
        """Apply filter to an image."""
        pass
    
    @abstractmethod
    def get_filter_name(self) -> str:
        """Get the name of the filter."""
        pass
    
    @abstractmethod
    def get_filter_params(self) -> List[Dict[str, Any]]:
        """Get filter parameters."""
        pass


class MetadataPlugin(Plugin):
    """Base class for metadata plugins."""
    
    @abstractmethod
    def extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """Extract metadata from an image."""
        pass
    
    @abstractmethod
    def write_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """Write metadata to an image."""
        pass