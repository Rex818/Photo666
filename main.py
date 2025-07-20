#!/usr/bin/env python3
"""
PyPhotoManager - Professional Photo Management Software
Main entry point for the application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for PyPhotoManager."""
    try:
        from picman.gui.main_window import main as gui_main
        return gui_main()
    except ImportError as e:
        print(f"Error importing GUI module: {e}")
        print("Please ensure all dependencies are installed.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())