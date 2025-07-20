#!/bin/bash

echo "========================================"
echo "           Photo666 v0.1.0"
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

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误：创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "检查依赖包..."
pip install -r requirements.txt --quiet

# 运行程序
echo "启动Photo666..."
echo
python main.py

# 如果程序异常退出，显示错误信息
if [ $? -ne 0 ]; then
    echo
    echo "程序异常退出，请检查错误信息"
    read -p "按回车键继续..."
fi

# 退出虚拟环境
deactivate 