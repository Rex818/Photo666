# PyPhotoManager 插件开发指南

## 简介

PyPhotoManager的插件系统允许开发者扩展应用程序的功能，而无需修改核心代码。本指南将帮助您了解如何创建、测试和分发PyPhotoManager插件。

## 插件类型

PyPhotoManager支持以下类型的插件：

1. **基本插件**：继承自`Plugin`基类，可以添加菜单项和工具栏按钮
2. **照片滤镜插件**：继承自`PhotoFilterPlugin`，可以对照片应用滤镜效果
3. **元数据插件**：继承自`MetadataPlugin`，可以提取和写入照片元数据

## 创建插件

### 基本结构

插件是一个Python模块，包含一个或多个继承自`Plugin`基类的类。插件文件应放在`plugins`目录中。

基本插件结构如下：

```python
from src.picman.plugins.base import Plugin, PluginInfo

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        # 初始化插件
    
    def get_info(self) -> PluginInfo:
        """获取插件信息。"""
        return PluginInfo(
            name="My Plugin",
            version="1.0.0",
            description="My plugin description",
            author="Author Name"
        )
    
    def initialize(self, app_context) -> bool:
        """初始化插件。"""
        # app_context包含应用程序的核心组件
        self.config_manager = app_context.get("config_manager")
        self.photo_manager = app_context.get("photo_manager")
        self.image_processor = app_context.get("image_processor")
        
        self.logger.info("My plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        """关闭插件。"""
        self.logger.info("My plugin shutdown")
        return True
    
    def get_menu_actions(self) -> list:
        """获取菜单操作。"""
        return [
            {
                "menu": "Tools",  # 菜单名称
                "title": "My Plugin Action",  # 操作名称
                "action": "my_action"  # 操作ID
            }
        ]
    
    def get_toolbar_actions(self) -> list:
        """获取工具栏操作。"""
        return [
            {
                "title": "My Plugin",  # 操作名称
                "action": "my_action",  # 操作ID
                "icon": "path/to/icon.png"  # 图标路径（可选）
            }
        ]
```

### 照片滤镜插件

照片滤镜插件继承自`PhotoFilterPlugin`，用于对照片应用滤镜效果：

```python
from src.picman.plugins.base import PhotoFilterPlugin, PluginInfo
from PIL import Image, ImageFilter

class MyFilterPlugin(PhotoFilterPlugin):
    def __init__(self):
        super().__init__()
        self.settings = {
            "intensity": 1.0
        }
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="My Filter",
            version="1.0.0",
            description="My custom photo filter",
            author="Author Name"
        )
    
    def initialize(self, app_context) -> bool:
        self.logger.info("My filter plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        self.logger.info("My filter plugin shutdown")
        return True
    
    def get_filter_name(self) -> str:
        return "My Filter"
    
    def get_filter_params(self) -> list:
        return [
            {
                "name": "intensity",
                "type": "float",
                "min": 0.1,
                "max": 2.0,
                "default": 1.0,
                "label": "Intensity"
            }
        ]
    
    def apply_filter(self, image_path: str, output_path: str, params: dict = None) -> bool:
        try:
            # 使用提供的参数或默认设置
            filter_params = params or self.settings
            intensity = filter_params.get("intensity", 1.0)
            
            # 打开图像
            with Image.open(image_path) as img:
                # 应用滤镜
                filtered_img = img.filter(ImageFilter.BLUR)
                
                # 保存结果
                filtered_img.save(output_path)
            
            self.logger.info("Filter applied successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to apply filter", error=str(e))
            return False
```

### 元数据插件

元数据插件继承自`MetadataPlugin`，用于提取和写入照片元数据：

```python
from src.picman.plugins.base import MetadataPlugin, PluginInfo
from PIL import Image
from PIL.ExifTags import TAGS

class MyMetadataPlugin(MetadataPlugin):
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="My Metadata Plugin",
            version="1.0.0",
            description="Custom metadata extractor",
            author="Author Name"
        )
    
    def initialize(self, app_context) -> bool:
        self.logger.info("My metadata plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        self.logger.info("My metadata plugin shutdown")
        return True
    
    def extract_metadata(self, image_path: str) -> dict:
        try:
            metadata = {}
            
            with Image.open(image_path) as img:
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        metadata[tag] = value
            
            return metadata
            
        except Exception as e:
            self.logger.error("Failed to extract metadata", error=str(e))
            return {}
    
    def write_metadata(self, image_path: str, metadata: dict) -> bool:
        # 实现写入元数据的逻辑
        self.logger.info("Writing metadata not implemented")
        return False
```

## 插件生命周期

1. **发现**：应用程序启动时，插件管理器会扫描`plugins`目录，查找插件文件
2. **加载**：插件管理器创建插件实例，并调用`get_info()`方法获取插件信息
3. **初始化**：如果插件被启用，插件管理器调用`initialize()`方法，传入应用程序上下文
4. **使用**：用户可以通过菜单或工具栏使用插件功能
5. **关闭**：应用程序关闭时，插件管理器调用`shutdown()`方法

## 应用程序上下文

插件的`initialize()`方法接收一个应用程序上下文对象，包含以下组件：

- `config_manager`：配置管理器，用于访问应用程序配置
- `photo_manager`：照片管理器，用于管理照片
- `image_processor`：图像处理器，用于处理图像

## 插件设置

插件可以定义自己的设置，并通过`get_settings()`和`update_settings()`方法访问和更新这些设置：

```python
def get_settings(self) -> dict:
    """获取插件设置。"""
    return self.settings

def update_settings(self, settings: dict) -> bool:
    """更新插件设置。"""
    self.settings.update(settings)
    return True
```

## 日志记录

插件可以使用内置的日志记录器记录日志：

```python
self.logger.info("Information message")
self.logger.warning("Warning message")
self.logger.error("Error message", error=str(e))
```

## 测试插件

要测试插件，可以将插件文件放在`plugins`目录中，然后启动应用程序。插件将被自动发现和加载。

您可以在插件管理器中启用或禁用插件，并配置插件设置。

## 分发插件

要分发插件，只需将插件文件提供给用户，并指导他们将文件放在应用程序的`plugins`目录中。

## 最佳实践

1. **错误处理**：始终捕获和记录异常，避免插件崩溃影响整个应用程序
2. **资源管理**：在`shutdown()`方法中释放所有资源
3. **文档**：为插件提供清晰的文档，包括功能、参数和使用示例
4. **版本控制**：使用语义化版本号，便于用户了解插件的更新情况
5. **配置验证**：验证用户提供的配置，确保插件正常工作

## 示例插件

PyPhotoManager提供了三个示例插件：

1. `grayscale_filter.py`：将照片转换为灰度
2. `sepia_filter.py`：将照片转换为棕褐色调
3. `watermark_filter.py`：为照片添加文本水印

您可以查看这些插件的源代码，了解如何创建自己的插件。

## 常见问题

### 插件无法加载

- 确保插件文件位于`plugins`目录中
- 检查插件类是否正确继承了`Plugin`基类
- 检查`get_info()`方法是否返回了有效的`PluginInfo`对象

### 插件功能无法使用

- 检查`initialize()`方法是否返回了`True`
- 检查菜单操作和工具栏操作是否正确定义
- 查看应用程序日志，了解可能的错误

### 插件设置无法保存

- 确保`update_settings()`方法正确实现
- 检查设置值是否可序列化（如字符串、数字、布尔值、列表或字典）