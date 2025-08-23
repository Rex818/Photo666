#!/bin/bash

echo "========================================"
echo "Photo666 v0.3.2 - AI图片管理软件"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3，请先安装Python 3.8+"
    echo "Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "CentOS/RHEL: sudo yum install python3 python3-venv"
    echo "macOS: brew install python3"
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

# 启动程序
echo
echo "正在启动Photo666..."
echo
python main.py
