#!/usr/bin/env python3
"""
Setup script for PyPhotoManager.
Creates virtual environment and installs dependencies.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def main():
    """Main setup function."""
    print("Setting up PyPhotoManager development environment...")
    
    # Create virtual environment
    venv_dir = ".venv"
    if not Path(venv_dir).exists():
        print(f"Creating virtual environment in {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    else:
        print(f"Virtual environment already exists in {venv_dir}")
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = os.path.join(venv_dir, "Scripts", "activate")
        python_path = os.path.join(venv_dir, "Scripts", "python")
        pip_path = os.path.join(venv_dir, "Scripts", "pip")
    else:
        activate_script = os.path.join(venv_dir, "bin", "activate")
        python_path = os.path.join(venv_dir, "bin", "python")
        pip_path = os.path.join(venv_dir, "bin", "pip")
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    
    # Create necessary directories
    dirs = ["data", "data/thumbnails", "logs", "config"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"Created directory: {dir_name}")
    
    print("\nSetup completed successfully!")
    print("\nTo activate the virtual environment:")
    if platform.system() == "Windows":
        print(f"    {venv_dir}\\Scripts\\activate")
    else:
        print(f"    source {venv_dir}/bin/activate")
    
    print("\nTo run the application:")
    print("    python main.py")


if __name__ == "__main__":
    main()