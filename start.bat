@echo off
chcp 65001 >nul
title Photo666 v0.3.1 启动器

echo.
echo ========================================
echo        Photo666 v0.3.1 启动器
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到Python，请先安装Python 3.8+
    echo.
    echo 请访问 https://www.python.org/downloads/ 下载并安装Python
    pause
    exit /b 1
)

:: 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo ✅ 检测到虚拟环境，正在激活...
    call .venv\Scripts\activate.bat
    echo ✅ 虚拟环境激活成功
) else (
    echo ⚠️  未检测到虚拟环境，将使用系统Python
    echo 建议创建虚拟环境以获得最佳体验
    echo.
)

:: 检查依赖
echo.
echo 🔍 检查依赖包...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 缺少PyQt6依赖
    echo.
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败，请检查网络连接或手动安装
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖检查通过
)

:: 创建必要的目录
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output" mkdir output

echo.
echo 🚀 启动Photo666 v0.3.1...
echo.

:: 启动程序
python main.py

:: 如果程序异常退出，显示错误信息
if errorlevel 1 (
    echo.
    echo ❌ 程序异常退出，错误代码: %errorlevel%
    echo 请检查日志文件或联系技术支持
    pause
)

echo.
echo �� Photo666已退出
pause
