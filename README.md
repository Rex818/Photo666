# Photo666 v0.3.0（图老六） - AI图片管理工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Photo666** 

​	是一个基于PyQt6的功能强大的AI图片管理工具，集成了多种AI功能，提供智能的图片分类、标签管理和信息识别服务。

​	专门用于管理和分析AI生成的图片。支持多种AI软件格式，提供完整的图片管理、标签分类和AI元数据分析功能。



## ✨ 功能简介

- ### 🏷️ 智能打标：支持JoyCaption2/3、Janus、Florence2打标和标签管理的软件哦！可以批量打标；可以单张图片、多张图片、整个目录图片打标。

- ### 🏷️标签翻译：支持标签的批量翻译。

- ### 🏷️图片搜索：基于图片标签的搜索。

- ###  🎨 AI图片信息识别：可以识别SD WebUI、ComfyUI、MJ生成的原始图片内的AI信息提取！！！




## ✨ 主要特性详解

### 🎯 核心功能

- **智能图片管理**: 自动分类、去重、缩略图生成
- **AI信息识别**: 支持多种AI生成图片的元数据识别
- **标签管理系统**: 智能标签分类、翻译、导入导出
- **相册管理**: 灵活的相册创建、分组、封面设置
- **高性能处理**: 异步加载、批量操作、智能缓存

### 🤖 AI功能集成

- **Florence2插件**: AI图片信息识别和分析
- **JoyCaption插件**: 智能图片描述生成
- **Janus插件**: 多模态AI推理和图片生成
- **Google翻译插件**: 多语言标签翻译

### 🔧 技术优势

- **性能优化**: 大目录导入速度提升3-5倍，显示速度提升5-8倍
- **用户体验**: 流畅的界面响应、智能滚动、虚拟化显示
- **系统稳定**: 完善的错误处理、内存优化、崩溃防护
- **向后兼容**: 完全兼容所有现有插件和功能



## ✨ 主要特性详解

### 🎯 核心功能

### 🏷️ 智能标签管理

- **多级标签分类**: 简单标签、普通标签、详细标签
- **自动标签翻译**: 支持中英文标签互译
- **标签导入导出**: 支持多种格式的标签文件
- **智能标签检测**: 自动识别标签文件类型

### 📁 相册管理

- **相册创建和管理**: 灵活的相册组织方式
- **图片分组**: 支持多种分组方式
- **相册封面**: 自动设置相册封面
- **批量操作**: 支持批量导入和管理

### 🎨 AI图片信息识别

- **Stable Diffusion WebUI**: 完整支持WebUI生成的图片信息提取
- **ComfyUI**: 支持ComfyUI工作流信息识别和显示
- **Midjourney**: 新增支持Midjourney图片参数识别
  - 任务ID (Job ID)
  - 版本 (Version)
  - 风格化 (Stylize)
  - 质量 (Quality)
  - 宽高比 (Aspect Ratio)
  - 原始模式 (Raw Mode)
  - 混乱度 (Chaos)
  - 平铺模式 (Tile)
  - Niji模式 (Niji)
  - 怪异度 (Weird)

- 🎯 高级功能

- **图片去重**: 基于文件哈希的智能去重
- **缩略图生成**: 自动生成和管理缩略图
- **多线程处理**: 提高大量图片处理性能
- **数据库优化**: 高效的SQLite数据库管理

## 🚀 快速开始

### 系统要求
- Windows 10/11
- Python 3.8 或更高版本
- 至少 4GB RAM (推荐 8GB RAM)
- 至少 2GB 可用磁盘空间

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/Rex818/Photo666
   cd Photo666
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

   

   - **补充安装对应cuda128版本的torch**

   ```bash
   pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128
   ```

4. **启动程序**

   ```bash
   python main.py
   ```

## 📖 使用指南

### 基本操作
1. **导入图片**: 点击"导入图片"按钮选择图片文件或目录
2. **查看AI信息**: 选择图片后在右侧面板查看AI生成参数
3. **管理标签**: 在标签面板中添加、编辑或删除标签
4. **创建相册**: 使用相册管理功能组织图片

### AI图片信息
- **WebUI图片**: 自动识别模型、采样器、步数等参数
- **ComfyUI图片**: 显示工作流信息和节点参数
- **Midjourney图片**: 显示Job ID、版本、风格化等参数

### 标签管理
- **简单标签**: 基础分类标签
- **普通标签**: 详细描述标签
- **详细标签**: 完整描述标签
- **自动翻译**: 支持中英文标签互译

## 🔧 配置说明

### 插件配置
插件配置文件位于 `config/plugins/` 目录：
- `google_translate_plugin.json`: Google翻译插件配置
- `gps_location_plugin.json`: GPS位置查询插件配置

### 数据库配置
- 主数据库: `data/picman.db`
- 缩略图目录: `data/thumbnails/`
- 日志文件: `logs/picman.log`

## 📁 项目结构

```
Photo666/
├── src/picman/           # 核心源代码
│   ├── core/            # 核心功能模块
│   ├── gui/             # 用户界面
│   ├── database/        # 数据库管理
│   ├── plugins/         # 插件系统
│   └── utils/           # 工具函数
├── plugins/             # 插件目录
├── config/              # 配置文件
├── data/                # 数据文件
├── docs/                # 文档
└── translations/        # 国际化文件
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 开发环境设置
1. Fork 项目
2. 创建功能分支: `git checkout -b feature/AmazingFeature`
3. 提交更改: `git commit -m 'Add some AmazingFeature'`
4. 推送分支: `git push origin feature/AmazingFeature`
5. 创建 Pull Request

## 📝 更新日志

详细更新日志请查看 [CHANGELOG.md](CHANGELOG.md)

### 最新版本 v0.3.0
- ✨ 新增 Midjourney 图片信息识别
- 🔧 优化数据库检索性能
- 🐛 修复 AI 元数据解析问题
- 📋 完善错误处理机制

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

## 📞 联系我们

- 项目主页: [GitHub Repository](https://github.com/your-username/Photo666)
- 问题反馈: [Issues](https://github.com/your-username/Photo666/issues)
- 功能建议: [Discussions](https://github.com/your-username/Photo666/discussions)

---

**Photo666** - 让AI图片管理更简单！ 🎨✨
