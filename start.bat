@echo off
chcp 65001 >nul
echo ========================================
echo        Photo666 v0.3.0 启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查虚拟环境是否存在
if not exist ".venv" (
    echo 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo 正在激活虚拟环境...
call .venv\Scripts\activate.bat

REM 安装依赖
echo 正在检查依赖...
pip install -r requirements.txt

REM 启动程序
echo.
echo 正在启动Photo666 v0.3.0...
echo.
python main.py

REM 保持窗口打开
pause
