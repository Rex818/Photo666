"""
Plugin manager for PyPhotoManager.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
import logging

from ..config.manager import ConfigManager
from .base import Plugin, PluginInfo


class PluginManager:
    """Manages plugin loading, initialization, and execution."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger("picman.plugins.manager")
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_classes: Dict[str, Type[Plugin]] = {}
        self.app_context: Dict[str, Any] = {}
    
    def set_app_context(self, context: Dict[str, Any]):
        """Set application context for plugins."""
        self.app_context = context
    
    def discover_plugins(self) -> List[Dict[str, Any]]:
        """Discover available plugins."""
        plugin_dir = self.config.get("plugins.plugin_directory", "plugins")
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists() or not plugin_path.is_dir():
            self.logger.warning(f"Plugin directory not found - path: {plugin_path}")
            return []
        
        discovered_plugins = []
        discovered_names = set()  # 用于去重
        
        # Look for directory-based plugins first (优先级更高)
        for dir_path in plugin_path.iterdir():
            if dir_path.is_dir() and not dir_path.name.startswith("__"):
                try:
                    discovered = self._discover_plugin_from_directory(dir_path)
                    for plugin in discovered:
                        if plugin["name"] not in discovered_names:
                            discovered_plugins.append(plugin)
                            discovered_names.add(plugin["name"])
                    
                except Exception as e:
                    self.logger.error(f"Failed to load plugin directory - path: {dir_path}, error: {str(e)}")
        
        # Look for Python files in the plugin directory (如果目录中没有找到对应的插件)
        for file_path in plugin_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            
            # 检查是否已经有同名的目录插件
            plugin_name = file_path.stem
            if plugin_name in discovered_names:
                continue  # 跳过，因为目录插件优先级更高
            
            try:
                discovered = self._discover_plugin_from_file(file_path)
                for plugin in discovered:
                    if plugin["name"] not in discovered_names:
                        discovered_plugins.append(plugin)
                        discovered_names.add(plugin["name"])
                
            except Exception as e:
                self.logger.error(f"Failed to load plugin module - path: {file_path}, error: {str(e)}")
        
        self.logger.info(f"Discovered plugins - count: {len(discovered_plugins)}")
        return discovered_plugins
    
    def _discover_plugin_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Discover plugins from a single Python file."""
        discovered_plugins = []
        
        # Load module
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return discovered_plugins
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Plugin) and 
                attr is not Plugin):
                
                # Create temporary instance to get info
                try:
                    plugin_instance = attr()
                    plugin_info = plugin_instance.get_info()
                    
                    plugin_data = {
                        "name": plugin_info.name,
                        "version": plugin_info.version,
                        "description": plugin_info.description,
                        "author": plugin_info.author,
                        "module": module_name,
                        "class_name": attr_name,
                        "path": str(file_path),
                        "type": "file"
                    }
                    
                    discovered_plugins.append(plugin_data)
                    self.plugin_classes[plugin_info.name] = attr
                    
                except Exception as e:
                    self.logger.error(f"Failed to get plugin info - module: {module_name}, class_name: {attr_name}, error: {str(e)}")
        
        return discovered_plugins
    
    def _discover_plugin_from_directory(self, dir_path: Path) -> List[Dict[str, Any]]:
        """Discover plugins from a directory."""
        discovered_plugins = []
        
        # Look for __init__.py or main plugin file
        plugin_files = []
        
        # Check for __init__.py
        init_file = dir_path / "__init__.py"
        if init_file.exists():
            plugin_files.append(init_file)
        
        # Check for main plugin file (same name as directory)
        main_file = dir_path / f"{dir_path.name}.py"
        if main_file.exists():
            plugin_files.append(main_file)
        
        # Check for plugin.py
        plugin_file = dir_path / "plugin.py"
        if plugin_file.exists():
            plugin_files.append(plugin_file)
        
        # If no specific files found, look for any .py files
        if not plugin_files:
            plugin_files = list(dir_path.glob("*.py"))
        
        for file_path in plugin_files:
            try:
                # Create module name that includes directory
                module_name = f"{dir_path.name}.{file_path.stem}"
                
                # Add directory to Python path temporarily
                original_path = sys.path.copy()
                sys.path.insert(0, str(dir_path.parent))
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find plugin classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, Plugin) and 
                            attr is not Plugin):
                            
                            # Create temporary instance to get info
                            try:
                                plugin_instance = attr()
                                plugin_info = plugin_instance.get_info()
                                
                                plugin_data = {
                                    "name": plugin_info.name,
                                    "version": plugin_info.version,
                                    "description": plugin_info.description,
                                    "author": plugin_info.author,
                                    "module": module_name,
                                    "class_name": attr_name,
                                    "path": str(file_path),
                                    "type": "directory",
                                    "plugin_dir": str(dir_path)
                                }
                                
                                discovered_plugins.append(plugin_data)
                                self.plugin_classes[plugin_info.name] = attr
                                
                            except Exception as e:
                                self.logger.error(f"Failed to get plugin info - module: {module_name}, class_name: {attr_name}, error: {str(e)}")
                
                except Exception as e:
                    self.logger.error(f"Failed to load plugin from directory - path: {str(file_path)}, error: {str(e)}")
                
                finally:
                    # Restore original path
                    sys.path = original_path
                    
            except Exception as e:
                self.logger.error(f"Failed to load plugin from directory - path: {file_path}, error: {str(e)}")
        
        return discovered_plugins
    
    def load_plugins(self) -> bool:
        """Load and initialize enabled plugins."""
        try:
            # Get enabled plugins from config
            enabled_plugins = self.config.get("plugins.enabled_plugins", [])
            auto_load = self.config.get("plugins.auto_load", True)
            
            # Discover available plugins
            discovered = self.discover_plugins()
            
            # If auto-load is enabled, load all discovered plugins
            if auto_load:
                enabled_plugins = [p["name"] for p in discovered]
            
            # Load and initialize each enabled plugin
            for plugin_name in enabled_plugins:
                if plugin_name in self.plugin_classes:
                    self.load_plugin(plugin_name)
            
            self.logger.info(f"Loaded plugins - count: {len(self.plugins)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugins - error: {str(e)}")
            return False
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load and initialize a specific plugin."""
        try:
            if plugin_name in self.plugins:
                self.logger.warning(f"Plugin already loaded - name: {plugin_name}")
                return True
            
            if plugin_name not in self.plugin_classes:
                self.logger.error(f"Plugin not found - name: {plugin_name}")
                return False
            
            # Create plugin instance with proper error handling
            plugin_class = self.plugin_classes[plugin_name]
            
            try:
                plugin = plugin_class()
            except Exception as e:
                self.logger.error(f"Failed to create plugin instance - name: {plugin_name}, class_name: {plugin_class.__name__}, error: {str(e)}")
                return False
            
            # Initialize plugin with proper error handling
            try:
                if plugin.initialize(self.app_context):
                    self.plugins[plugin_name] = plugin
                    self.logger.info(f"Plugin loaded - name: {plugin_name}")
                    return True
                else:
                    self.logger.error(f"Plugin initialization failed - name: {plugin_name}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Plugin initialization exception - name: {plugin_name}, error: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin - name: {plugin_name}, error: {str(e)}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin."""
        try:
            if plugin_name not in self.plugins:
                self.logger.warning(f"Plugin not loaded - name: {plugin_name}")
                return False
            
            # Shutdown plugin
            plugin = self.plugins[plugin_name]
            if plugin.shutdown():
                del self.plugins[plugin_name]
                self.logger.info(f"Plugin unloaded - name: {plugin_name}")
                return True
            else:
                self.logger.error(f"Plugin shutdown failed - name: {plugin_name}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin - name: {plugin_name}, error: {str(e)}")
            return False
    
    def unload_all_plugins(self) -> bool:
        """Unload all plugins."""
        success = True
        for plugin_name in list(self.plugins.keys()):
            if not self.unload_plugin(plugin_name):
                success = False
        
        return success
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)
    
    def get_loaded_plugins(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins."""
        loaded_plugins = []
        
        for name, plugin in self.plugins.items():
            info = plugin.get_info()
            loaded_plugins.append(info.to_dict())
        
        return loaded_plugins
    
    def get_plugin_menu_actions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get menu actions from all plugins."""
        menu_actions = {}
        
        for name, plugin in self.plugins.items():
            actions = plugin.get_menu_actions()
            if actions:
                menu_actions[name] = actions
        
        return menu_actions
    
    def get_plugin_toolbar_actions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get toolbar actions from all plugins."""
        toolbar_actions = {}
        
        for name, plugin in self.plugins.items():
            actions = plugin.get_toolbar_actions()
            if actions:
                toolbar_actions[name] = actions
        
        return toolbar_actions