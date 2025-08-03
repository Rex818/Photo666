# JoyCaption图片反推信息插件

## 概述
JoyCaption图片反推信息插件是一个基于JoyCaption模型的AI图片描述生成工具，支持多种描述类型和精度模式，能够根据用户选择生成不同详细程度的信息描述。

## 功能特性

### 🎯 核心功能
- **多模型支持**: 支持JoyCaption Beta One和Alpha Two模型
- **三级描述系统**: 简单描述、普通描述、详细描述
- **多种描述类型**: 支持15种不同的描述风格
- **批量处理**: 支持单张、多张图片或目录批量处理
- **结果保存**: 反推结果自动保存为.txt文件并集成到标签系统

### 🔧 技术特性
- **多精度支持**: fp32, bf16, fp16, 8-bit, 4-bit量化
- **GPU加速**: 支持CUDA加速，优化推理性能
- **内存优化**: 智能内存管理，支持大模型运行
- **自动下载**: 模型自动下载和缓存机制
- **进度反馈**: 实时显示处理进度和状态

### 📝 描述类型
1. **Descriptive** - 描述性
2. **Descriptive (Casual)** - 描述性(随意)
3. **Straightforward** - 直白
4. **Tags** - 标签
5. **Technical** - 技术性
6. **Artistic** - 艺术性
7. **Stable Diffusion Prompt** - SD提示词
8. **MidJourney** - MJ提示词
9. **Danbooru tag list** - Danbooru标签
10. **e621 tag list** - e621标签
11. **Rule34 tag list** - Rule34标签
12. **Booru-like tag list** - Booru类标签
13. **Art Critic** - 艺术评论
14. **Product Listing** - 产品列表

## 系统要求
- Python 3.11+
- PyQt6 6.4+
- CUDA支持（推荐）
- 8GB+ RAM
- 4GB+ VRAM（最低要求）

## 安装说明
1. 插件已集成到Photo666系统中
2. 首次使用会自动下载所需模型
3. 确保网络连接正常以下载模型

## 使用说明
1. 启动Photo666程序
2. 点击工具栏"JoyCaption图片反推信息"按钮
3. 选择模型和配置参数
4. 选择要处理的图片或目录
5. 开始反推处理
6. 查看结果文件

## 配置说明

### 模型选择
- **JoyCaption Beta One**: 基础模型，平衡性能和精度
- **JoyCaption Alpha Two**: 高级模型，更高精度

### 精度模式
- **Full Precision (fp32)**: 最高精度，需要最多VRAM
- **Full Precision (bf16)**: 高精度，平衡性能
- **Balanced (8-bit)**: 推荐模式，平衡性能和内存
- **Maximum Savings (4-bit)**: 最低内存使用

### 描述级别
- **简单描述**: 词、词组组成的简单描述
- **普通描述**: 简单自然语句描述
- **详细描述**: 多句话组成的详细描述

## 技术架构

### 核心组件
- **ModelManager**: 模型管理和下载
- **InferenceEngine**: 推理引擎
- **ResultProcessor**: 结果处理
- **ConfigManager**: 配置管理

### 文件结构
```
joycaption_reverse_plugin/
├── config/          # 配置文件
├── models/          # 模型文件
├── ui/             # 用户界面
├── core/           # 核心功能
└── utils/          # 工具类
```

## 版本历史
- **v1.0.0**: 初始版本，基础功能实现

## 技术支持
如有问题，请查看日志文件或联系开发团队。

## 许可证
本插件遵循GPL-3.0许可证。 