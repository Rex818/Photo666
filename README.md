# Photo666

Photo666的设计目标是做一款功能强大的专业照片管理软件。

它使用Python和PyQt6开发。

它预期逐步为用户提供丰富的功能，帮助用户组织、浏览和编辑照片。

## 🎉 主要功能

- **照片导入**：支持从文件或文件夹导入照片，支持拖放操作
- **照片浏览**：缩略图网格视图，支持列表和详细信息视图
- **照片编辑**：基本的图像处理功能（调整大小、旋转、亮度/对比度等）
- **相册管理**：创建和管理相册，将照片组织到不同的相册中
- **分类标签系统**：重新设计的标签系统，支持分类标签和AI图片信息
- **GPS位置查询**：从照片EXIF数据中提取GPS坐标并查询详细位置信息
- **AI图片信息面板**：显示模型、Lora、触发词等AI生成参数
- **搜索和过滤**：按名称、标签、评分等搜索和过滤照片
- **批处理**：批量处理照片（调整大小、旋转、转换格式等）
- **插件系统**：支持扩展功能的插件系统
- **多语言支持**：支持中文、英文、日文等多种语言

## 🔧 技术架构

Photo666采用模块化设计，主要包含以下组件：

- **配置管理**：管理应用程序配置，基于YAML
- **数据库管理**：使用SQLite存储照片元数据
- **核心功能**：照片管理、缩略图生成、图像处理
- **GUI界面**：基于PyQt6的用户界面
- **插件系统**：支持第三方插件扩展功能
- **日志系统**：结构化日志记录

## 📋 系统要求

- Python 3.8+
- PyQt6
- Pillow
- SQLite
- PyYAML
- structlog
- requests (GPS插件)
- geopy (GPS插件)

## 🚀 快速安装

### 方法一：便携版（推荐）
1. 下载并解压Photo666_v0.1.0_Portable.zip
2. 双击运行 `Photo666.bat` 或 `Photo666.sh`

### 方法二：源码安装
1. 克隆仓库：
   ```
   git clone https://github.com/Rex818/photo666.git
   cd photo666
   ```

2. 设置环境：
   ```
   python setup_env.py
   ```

3. 激活虚拟环境：
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

4. 运行应用：
   ```
   python main.py
   ```

## 📖 快速入门

### 基本操作
1. **导入照片**：点击"导入照片"按钮或直接拖放照片到程序窗口
2. **创建相册**：在相册管理器中点击"新建相册"
3. **添加标签**：在照片查看器中编辑分类标签
4. **查看位置**：带有GPS信息的照片会自动显示位置信息
5. **搜索照片**：使用搜索框按标签、文件名等搜索

### 插件功能
- **GPS位置查询**：自动从照片EXIF数据提取GPS坐标并查询位置
- **Google翻译**：支持标签和文本的自动翻译
- **图像滤镜**：提供灰度、棕褐色、水印等滤镜效果

## 📁 项目结构

```
Photo666/
├── config/                # 配置文件
│   └── app.yaml          # 应用程序配置
├── data/                 # 数据文件（运行时创建）
│   ├── photo666.db       # SQLite数据库
│   └── thumbnails/       # 缩略图缓存
├── docs/                 # 文档
│   ├── quick_start_guide.md # 快速入门指南
│   ├── user_manual.md    # 用户手册
│   └── plugin_development.md # 插件开发指南
├── plugins/              # 插件目录
│   ├── gps_location_plugin/  # GPS位置查询插件
│   ├── google_translate_plugin.py  # Google翻译插件
│   └── ...               # 其他插件
├── src/                  # 源代码
│   └── picman/           # 主包
│       ├── config/       # 配置管理
│       ├── core/         # 核心功能
│       ├── database/     # 数据库管理
│       ├── gui/          # 图形界面
│       ├── plugins/      # 插件系统
│       └── utils/        # 工具函数
├── translations/         # 多语言文件
├── main.py               # 主入口
├── requirements.txt      # 依赖项
└── README.md             # 项目说明
```

## 🔌 插件开发

插件应继承`Plugin`基类，并实现必要的方法：

```python
from src.picman.plugins.base import Plugin, PluginInfo

class MyPlugin(Plugin):
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="My Plugin",
            version="1.0.0",
            description="My plugin description",
            author="Author Name"
        )
    
    def initialize(self, app_context) -> bool:
        # 初始化插件
        return True
    
    def shutdown(self) -> bool:
        # 关闭插件
        return True
```

详细插件开发指南请参考 `docs/plugin_development.md`。

## 📝 文档

- [用户手册](docs/user_manual.md)
- [快速入门指南](docs/quick_start_guide.md)
- [插件开发指南](docs/plugin_development.md)
- [更新日志](CHANGELOG.md)

## 🐛 问题反馈

如果您遇到问题或有建议，请：

1. 查看[常见问题](docs/faq.md)
2. 在GitHub Issues中提交问题
3. 发送邮件到：support@photo666.com

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用Apache2.0许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [Pillow](https://python-pillow.org/)
- [SQLite](https://www.sqlite.org/)
- [PyYAML](https://pyyaml.org/)
- [structlog](https://www.structlog.org/)
- [OpenStreetMap](https://www.openstreetmap.org/) (GPS位置查询)

## 📞 联系我们

- 官网：无
- 邮箱：无
- GitHub：https://github.com/Rex818/photo666

---

**Photo666 v0.1.0** - 让照片管理更简单、更智能！ 