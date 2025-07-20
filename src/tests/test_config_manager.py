"""
Tests for the ConfigManager class.
"""

import os
import tempfile
import pytest
import yaml
from pathlib import Path

from picman.config.manager import ConfigManager, AppConfig


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a temporary config file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.yaml")
        
        # Create a test config
        test_config = {
            "database": {
                "path": "test_data/test.db",
                "pool_size": 5
            },
            "ui": {
                "theme": "dark",
                "window_size": [1200, 800]
            }
        }
        
        # Write test config to file
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        # Create config manager
        self.config_manager = ConfigManager(self.config_path)
    
    def teardown_method(self):
        """Clean up after test."""
        self.temp_dir.cleanup()
    
    def test_load_config(self):
        """Test loading configuration."""
        # Verify config loaded correctly
        assert self.config_manager.get("database.path") == "test_data/test.db"
        assert self.config_manager.get("database.pool_size") == 5
        assert self.config_manager.get("ui.theme") == "dark"
        assert self.config_manager.get("ui.window_size") == [1200, 800]
    
    def test_get_default(self):
        """Test getting default value for non-existent key."""
        assert self.config_manager.get("non_existent_key", "default") == "default"
    
    def test_set_config(self):
        """Test setting configuration value."""
        # Set a value
        self.config_manager.set("database.pool_size", 10)
        
        # Verify value was set
        assert self.config_manager.get("database.pool_size") == 10
        
        # Verify value was saved to file
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            assert config_data["database"]["pool_size"] == 10