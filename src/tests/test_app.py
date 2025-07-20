"""
Basic tests for the PyPhotoManager application.
"""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from picman.config.manager import ConfigManager
from picman.utils.logging import LoggingManager
from picman.database.manager import DatabaseManager
from picman.core.photo_manager import PhotoManager
from picman.gui.main_window import MainWindow


@pytest.fixture
def app():
    """Create a QApplication instance."""
    return QApplication(sys.argv)


@pytest.fixture
def config_manager():
    """Create a ConfigManager instance."""
    return ConfigManager("config/app.yaml")


@pytest.fixture
def logging_manager(config_manager):
    """Create a LoggingManager instance."""
    logging_manager = LoggingManager(config_manager.config)
    logging_manager.setup_logging(level="DEBUG", log_file=None)
    return logging_manager


@pytest.fixture
def db_manager(config_manager):
    """Create a DatabaseManager instance with in-memory database."""
    return DatabaseManager(":memory:", config_manager.config)


@pytest.fixture
def photo_manager(config_manager, db_manager):
    """Create a PhotoManager instance."""
    return PhotoManager(config_manager, db_manager)


@pytest.mark.skip(reason="Requires GUI environment")
def test_main_window_creation(app, config_manager, db_manager, photo_manager):
    """Test creating the main window."""
    window = MainWindow()
    assert window is not None
    assert window.windowTitle() == "PyPhotoManager - Professional Photo Management"


def test_config_manager():
    """Test basic ConfigManager functionality."""
    config = ConfigManager()
    assert config is not None
    assert config.config is not None


def test_database_manager():
    """Test basic DatabaseManager functionality."""
    db = DatabaseManager(":memory:")
    assert db is not None
    
    # Test database initialization
    stats = db.get_stats()
    assert "total_photos" in stats
    assert stats["total_photos"] == 0