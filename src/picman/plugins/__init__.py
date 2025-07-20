"""
Plugin system for PyPhotoManager.
"""

from .base import Plugin, PluginInfo, PhotoFilterPlugin, MetadataPlugin
from .manager import PluginManager

__all__ = [
    "Plugin",
    "PluginInfo",
    "PhotoFilterPlugin",
    "MetadataPlugin",
    "PluginManager"
]