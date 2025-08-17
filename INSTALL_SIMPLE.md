# Photo666 v0.3.0 简化安装指南

## 问题解决
如果您遇到以下错误：
```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xae in position 544: illegal multibyte sequence
```

这是因为Windows系统的编码问题。我们已经修复了这个问题，现在可以直接使用。

## 快速安装步骤

### 1. 创建虚拟环境
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 2. 安装依赖（推荐方法）
```cmd
# 方法1：直接安装（推荐）
pip install -r requirements.txt

# 方法2：如果上面失败，先升级pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 启动程序
```cmd
python main.py
```

## 如果仍然遇到编码问题

### 临时解决方案
如果requirements.txt仍然有问题，可以手动安装主要依赖：

```cmd
# 核心依赖
pip install PyQt6>=6.5.0
pip install Pillow>=10.2.0
pip install PyYAML>=6.0.0

# AI依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install transformers>=4.55.0
pip install accelerate>=1.9.0
pip install huggingface_hub>=0.16.0

# 其他依赖
pip install numpy>=1.24.0
pip install requests>=2.28.0
pip install geopy>=2.3.0
```

### 验证安装
```cmd
python -c "import torch; print('PyTorch version:', torch.__version__)"
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

## 常见问题

1. **编码错误**：已修复，使用新版本的requirements.txt
2. **PyTorch安装失败**：使用官方命令安装CUDA版本
3. **依赖冲突**：建议在干净的虚拟环境中安装

## 获取帮助
如果仍有问题，请：
1. 检查Python版本（需要3.10+）
2. 确保虚拟环境已激活
3. 查看完整安装指南：INSTALL.md
