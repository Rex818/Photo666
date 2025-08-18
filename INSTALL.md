# Photo666 v0.3.0 安装指南

## 系统要求

### 操作系统
- **Windows**: 10/11 (推荐)
- **Linux**: Ubuntu 18.04+, CentOS 7+, 或其他主流发行版
- **macOS**: 10.15+ (Catalina及以上)

### Python环境
- **Python版本**: 3.10 或更高版本
- **推荐**: Python 3.11
- **必需**: pip 包管理器

### 硬件要求
- **内存**: 最低 8GB，推荐 16GB+
- **存储**: 最低 5GB 可用空间
- **GPU**: 可选，支持CUDA 12.8的NVIDIA GPU（用于AI功能加速）
- **GPU**: 如果做图片反推，建议至少16G显存的显卡，推荐安装CUDA 12.8的NVIDIA GPU

## 安装步骤

### 1. 下载和准备

1. 下载 Photo666 v0.3.0 发布包
2. 解压到目标目录
3. 确保有足够的磁盘空间

### 2. 创建虚拟环境（推荐）

#### Windows
```cmd
# 进入项目目录
cd Photo666-v0.3.0

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 验证激活
python --version
pip --version
```

#### Linux/macOS
```bash
# 进入项目目录
cd Photo666-v0.3.0

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 验证激活
python --version
pip --version
```

### 3. 安装依赖

#### 基础安装
```bash
# 升级pip
pip install --upgrade pip

# 安装基础依赖
pip install -r requirements.txt
```

#### GPU支持安装（推荐）
如果使用NVIDIA GPU，建议安装CUDA版本：
```bash
# 这是通用安装CUDA版本的PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

#推荐安装的版本如下，需要先在操作系统内安装CUDA 12.8。
#实测CUDA可以在系统内安装多个版本，不需要卸载原版本。
pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128


# 然后安装其他依赖
pip install -r requirements.txt
```

### 4. 验证安装

```bash
# 检查PyTorch是否支持CUDA
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# 检查主要依赖
python -c "import PyQt6, torch, transformers; print('主要依赖安装成功')"
```

## 配置说明

### 1. 基础配置
- 配置文件位于 `config/app.yaml`
- 首次运行会自动创建默认配置

### 2. 插件配置
- 每个插件都有独立的配置界面
- 支持模型路径自定义配置
- 配置文件位于 `config/plugins/` 目录

### 3. 模型下载
- AI插件首次使用时会提示下载模型
- 模型文件会下载到 `models/` 目录
- 支持自定义模型路径

## 启动程序

### 方法1: 命令行启动
```bash
# 确保虚拟环境已激活
python main.py
```

### 方法2: 脚本启动（Windows）
```cmd
# 双击 start.bat 文件
start.bat
```

### 方法3: 直接运行
```bash
# 直接运行主程序
python main.py
```

## 故障排除

### 常见问题

#### 1. Python版本问题
```bash
# 检查Python版本
python --version

# 如果版本过低，请升级到3.10+
```

#### 2. 依赖安装失败
```bash
# 尝试使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或者使用conda
conda install --file requirements.txt
```

#### 3. CUDA不可用
```bash
# 检查PyTorch版本
python -c "import torch; print(torch.__version__)"

# 重新安装CUDA版本
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

#### 4. 内存不足
- 减少批量处理大小
- 使用CPU模式运行
- 关闭其他占用内存的程序

### 获取帮助

1. **查看日志**: 程序运行时会生成详细的日志信息
2. **检查配置**: 确认配置文件是否正确
3. **依赖验证**: 使用验证脚本检查环境
4. **社区支持**: 提交Issue获取帮助

## 性能优化建议

### 1. GPU加速
- 安装CUDA版本的PyTorch
- 确保NVIDIA驱动是最新的
- 使用适当的批量大小

### 2. 内存优化
- 定期清理缓存
- 使用SSD存储模型文件
- 合理设置图片处理参数

### 3. 网络优化
- 使用国内镜像源下载模型
- 配置代理服务器（如需要）
- 批量下载模型文件

## 更新说明

### 从v0.2.0升级
1. 备份现有配置和数据
2. 安装新版本
3. 迁移配置文件
4. 测试功能完整性

### 版本兼容性
- v0.3.0 与 v0.2.0 配置文件兼容
- 数据库格式向后兼容
- 插件接口保持稳定

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

---

**Photo666 v0.3.0** - 智能图片管理解决方案

如有问题，请查看RELEASE_README.md或提交Issue。
