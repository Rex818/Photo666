@echo off
chcp 65001 >nul
title Photo666 v0.1.0

echo ========================================
echo           Photo666 v0.1.0
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查虚拟环境是否存在
if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo 检查依赖包...
pip install -r requirements.txt --quiet

:: 运行程序
echo 启动Photo666...
echo.
python main.py

:: 如果程序异常退出，暂停显示错误信息
if errorlevel 1 (
    echo.
    echo 程序异常退出，请检查错误信息
    pause
)

:: 退出虚拟环境
deactivate 