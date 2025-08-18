#!/bin/bash

echo "========================================"
echo "Photo666 v0.3.0 启动脚本"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3，请先安装Python 3.8+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "错误：创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "正在检查依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "警告：依赖安装可能不完整，程序可能无法正常运行"
    echo "建议手动运行：pip install -r requirements.txt"
fi

# 启动程序
echo
echo "正在启动Photo666..."
python main.py
