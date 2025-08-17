# Photo666 v0.3.0 发布说明

## 版本信息
- **版本号**: v0.3.0
- **发布日期**: 2025年8月17日
- **Python版本要求**: 3.10+
- **操作系统支持**: Windows 10/11, Linux, macOS

## 主要更新

### 🎯 核心功能增强
- 优化了图片管理核心功能
- 改进了数据库性能和稳定性
- 增强了标签管理系统

### 🔌 插件系统升级
- **florence2_reverse_plugin**: 图像识别和描述生成
- **joycaption_reverse_plugin**: 智能图片标注
- **janus_reverse_plugin**: 图片反推分析（已集成Janus官方代码）
- **janus_text2image_plugin**: AI图像生成（已集成Janus官方代码）
- **gps_location_plugin**: GPS位置信息提取
- **google_translate_plugin**: 多语言翻译支持

### 🚀 性能优化
- 支持CUDA 12.8和PyTorch 2.7
- GPU加速推理支持
- 内存使用优化
- 启动速度提升

### 🛠️ 技术改进
- 修复了Python 3.10+兼容性问题
- 集成了Janus官方代码，无需外部下载
- 优化了依赖管理
- 改进了错误处理机制

## 安装说明

### 环境要求
- Python 3.10 或更高版本
- 推荐使用虚拟环境
- 支持CUDA 12.8的NVIDIA GPU（可选，用于AI功能加速）

### 安装步骤

1. **创建虚拟环境**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **启动程序**
   ```bash
   python main.py
   # 或者双击 start.bat (Windows)
   ```

### GPU支持安装（推荐）
如果使用NVIDIA GPU，建议安装CUDA版本：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

#本人实测，建议安装版本如下，需要在本地安装cuda 12.8版本
pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128
```

## 文件结构

```
Photo666-v0.3.0/
├── main.py                 # 主程序入口
├── start.bat              # Windows启动脚本
├── requirements.txt        # 依赖列表
├── README.md              # 项目说明
├── LICENSE                # 许可证
├── config/                # 配置文件
│   ├── app.yaml          # 主配置
│   └── plugins/          # 插件配置
├── src/                   # 核心源代码
│   └── picman/           # 主要功能模块
├── plugins/               # 插件目录
│   ├── florence2_reverse_plugin/
│   ├── joycaption_reverse_plugin/
│   ├── janus_reverse_plugin/
│   ├── janus_text2image_plugin/
│   ├── gps_location_plugin/
│   └── google_translate_plugin/
└── translations/          # 多语言支持
```

## 使用说明

### 基本功能
1. **图片导入**: 支持拖拽导入和文件夹扫描
2. **标签管理**: 智能标签生成和编辑
3. **AI分析**: 图像识别、描述生成、反推分析
4. **批量处理**: 支持批量标签和元数据处理

### 插件使用
- 每个插件都有独立的配置界面
- 支持模型路径自定义配置
- 提供详细的错误提示和解决建议

## 故障排除

### 常见问题
1. **CUDA不可用**: 检查PyTorch是否为CUDA版本
2. **模型加载失败**: 检查模型路径和文件完整性
3. **内存不足**: 减少批量大小或使用CPU模式

### 获取帮助
- 查看日志文件了解详细错误信息
- 检查配置文件是否正确
- 确认所有依赖已正确安装

## 更新日志

### v0.3.0 (2025-08-17)
- ✨ 新增Janus AI功能集成
- 🚀 支持CUDA 12.8和PyTorch 2.7
- 🔧 修复Python 3.10+兼容性问题
- 📦 优化依赖管理和安装流程
- 🎯 改进插件系统稳定性

### v0.2.0 (2025-01-17)
- 基础图片管理功能
- 插件系统框架
- 标签管理功能

## 许可证
本项目采用MIT许可证，详见LICENSE文件。

## 贡献
欢迎提交Issue和Pull Request来改进项目。

---
**Photo666 v0.3.0** - 智能图片管理解决方案
