# 多语言支持文档

## 概述

PyPhotoManager 支持多语言界面，允许用户根据自己的偏好选择应用程序的显示语言。目前支持以下语言：

- 英语 (English)
- 简体中文 (Chinese Simplified)
- 日语 (Japanese)

## 实现细节

多语言支持通过以下组件实现：

1. **语言管理器 (LanguageManager)**
   - 位于 `src/picman/utils/language_manager.py`
   - 负责加载和切换应用程序语言
   - 自动检测可用的翻译文件
   - 提供语言切换功能

2. **语言对话框 (LanguageDialog)**
   - 位于 `src/picman/gui/language_dialog.py`
   - 提供用户界面让用户选择应用程序语言
   - 显示可用语言列表并允许用户切换

3. **翻译文件**
   - 存储在 `translations` 目录中
   - 使用 Qt 的 TS 格式 (XML) 存储翻译
   - 可以编译为二进制 QM 格式以提高性能

4. **翻译管理工具**
   - `translation_manager.py` - 用于提取、创建、更新和编译翻译文件
   - `compile_translations.py` - 专门用于编译翻译文件

## 使用方法

### 切换语言

用户可以通过以下方式切换应用程序语言：

1. 从主菜单选择 "Language" 菜单
2. 选择所需的语言，或者
3. 选择 "Language Settings..." 打开语言设置对话框

### 添加新的翻译

要添加新的语言支持，请按照以下步骤操作：

1. 使用翻译管理工具提取需要翻译的字符串：
   ```
   python translation_manager.py extract --src src
   ```

2. 创建新的翻译文件（例如，法语）：
   ```
   python translation_manager.py create --lang fr
   ```

3. 编辑生成的 `translations/picman_fr.ts` 文件，翻译其中的字符串

4. 编译翻译文件：
   ```
   python compile_translations.py
   ```

### 更新现有翻译

当应用程序代码更改时，可能会添加新的需要翻译的字符串。要更新现有翻译文件：

1. 使用翻译管理工具更新所有翻译文件：
   ```
   python translation_manager.py update
   ```

2. 编辑更新后的翻译文件，翻译新添加的字符串

3. 编译翻译文件：
   ```
   python compile_translations.py
   ```

## 开发指南

### 标记需要翻译的字符串

在代码中使用 `self.tr()` 方法标记需要翻译的字符串：

```python
# 示例
label = QLabel(self.tr("Hello, world!"))
button = QPushButton(self.tr("Click me"))
```

### 处理动态内容

对于包含动态内容的字符串，请使用占位符：

```python
# 错误方式
message = self.tr("Found ") + str(count) + self.tr(" photos")

# 正确方式
message = self.tr("Found {} photos").format(count)
```

### 测试翻译

在开发过程中，可以通过以下方式测试翻译：

1. 切换到目标语言
2. 检查所有 UI 元素是否正确翻译
3. 确保布局在不同语言下仍然合理（某些语言的文本可能更长）

## 注意事项

- 某些 UI 元素可能需要重启应用程序才能完全应用新的语言设置
- 确保翻译文件使用 UTF-8 编码以支持各种语言的字符
- 定期更新翻译文件以包含新添加的字符串