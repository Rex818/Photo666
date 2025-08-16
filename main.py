#!/usr/bin/env python3
"""
Photo666 - Professional Photo Management Software
Main entry point for the application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for Photo666."""
    try:
        from picman.gui.main_window import main as gui_main
        return gui_main()
    except ImportError as e:
        print(f"Error importing GUI module: {e}")
        print("Please ensure all dependencies are installed.")
        return 1
    except Exception as e:
        import traceback
        print(f"Unexpected error: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
