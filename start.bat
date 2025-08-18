@echo off
chcp 65001 >nul
echo ========================================
echo Photo666 v0.3.0 Startup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found, please install Python 3.8+ first
    pause
    exit /b 1
)

REM Check virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Try to install dependencies
echo Checking dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Dependency installation may be incomplete
    echo This could be due to encoding issues on Windows
    echo.
    echo Trying alternative installation method...
    echo.
    
    REM Try installing PyTorch separately first
    echo Installing PyTorch with CUDA support...
    pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128
    
    REM Then install other dependencies
    echo Installing other dependencies...
    pip install PyQt6>=6.5.0 Pillow>=10.2.0 PyYAML>=6.0.0 sqlite-utils>=3.35.0 googletrans-py>=4.0.0 asyncio-mqtt>=0.11.0 aiofiles>=22.0.0 transformers>=4.55.0 huggingface_hub>=0.16.0 accelerate>=1.9.0 safetensors>=0.3.0 bitsandbytes>=0.41.0 numpy>=1.24.0 einops>=0.8.0 timm>=1.0.0 requests>=2.28.0 geopy>=2.3.0 tqdm>=4.60.0
    
    if errorlevel 1 (
        echo.
        echo ERROR: Alternative installation also failed
        echo Please check INSTALL_SIMPLE.md for manual installation steps
        pause
        exit /b 1
    )
)

REM Start the program
echo.
echo Starting Photo666...
python main.py

REM Keep window open
pause
