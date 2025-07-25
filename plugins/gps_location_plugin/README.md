# GPS位置查询插件

## 概述

GPS位置查询插件是为PicMan照片管理软件开发的插件，能够自动读取照片中的GPS经纬度信息，并通过调用地理位置API来获取具体的地点名称，为用户提供便捷的照片地理位置标注功能。

## 功能特性

- **自动GPS提取**: 从照片EXIF数据中自动提取GPS坐标信息
- **多API支持**: 支持多个地理位置API服务，包括OpenStreetMap、Google Maps等
- **智能缓存**: 缓存查询结果，避免重复API调用，提高响应速度
- **批量处理**: 支持批量查询多张照片的位置信息
- **无缝集成**: 完美集成到PicMan的用户界面中
- **灵活配置**: 丰富的配置选项，满足不同用户需求

## 安装和配置

### 1. 插件安装

插件已包含在PicMan中，无需单独安装。如果需要手动安装：

1. 将插件文件夹复制到PicMan的`plugins/`目录下
2. 重启PicMan应用程序
3. 在插件管理器中启用"GPS位置查询插件"

### 2. 基础配置

首次使用时，插件会使用默认配置。如需自定义：

1. 打开PicMan设置界面
2. 选择"插件设置"
3. 找到"GPS位置查询插件"
4. 根据需要调整配置选项

### 3. API密钥配置（可选）

为了获得更好的查询效果，建议配置API密钥：

#### Google Maps API
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目并启用Geocoding API
3. 创建API密钥
4. 在插件设置中输入API密钥

#### 百度地图API
1. 访问 [百度地图开放平台](https://lbsyun.baidu.com/)
2. 注册账号并创建应用
3. 获取API密钥（AK）
4. 在插件设置中输入API密钥

#### 高德地图API
1. 访问 [高德开放平台](https://lbs.amap.com/)
2. 注册账号并创建应用
3. 获取API Key
4. 在插件设置中输入API密钥

## 使用方法

### 1. 自动查询

1. 在PicMan中选择包含GPS信息的照片
2. 查看照片信息面板，位置信息会自动显示
3. 如果启用了自动查询，位置信息会自动获取

### 2. 手动查询

1. 右键点击照片
2. 选择"查询位置信息"
3. 等待查询完成，结果会显示在照片信息面板中

### 3. 批量查询

1. 选择多张照片
2. 右键选择"批量查询位置"
3. 在弹出的对话框中点击"开始查询"
4. 查看处理进度和结果统计

## 配置选项说明

### API设置
- **优先级**: 设置API服务的使用优先级
- **API密钥**: 配置各个API服务的密钥
- **超时时间**: API请求的超时时间（秒）
- **重试次数**: 请求失败时的重试次数

### 缓存设置
- **启用缓存**: 是否启用位置信息缓存
- **缓存有效期**: 缓存数据的有效天数
- **最大缓存数量**: 缓存条目的最大数量
- **坐标精度**: 坐标匹配的精度范围

### 界面设置
- **自动查询**: 选择照片时是否自动查询位置
- **显示在信息面板**: 是否在照片信息面板显示位置
- **显示地图链接**: 是否显示在地图中查看的链接
- **显示格式**: 位置信息的显示格式

## 故障排除

### 常见问题

#### 1. 无法获取位置信息
- **检查网络连接**: 确保网络连接正常
- **检查API配置**: 验证API密钥是否正确配置
- **检查GPS数据**: 确认照片包含有效的GPS信息

#### 2. 查询速度慢
- **启用缓存**: 确保缓存功能已启用
- **调整API优先级**: 将响应快的API设置为优先
- **检查网络状况**: 网络延迟可能影响查询速度

#### 3. API调用失败
- **检查API密钥**: 确认密钥有效且未过期
- **检查配额限制**: 确认API调用未超出配额
- **查看错误日志**: 检查日志文件获取详细错误信息

### 日志文件

插件日志记录在PicMan的日志文件中，通常位于：
- Windows: `logs/picman.log`
- 搜索关键词: `gps_location_plugin`

### 重置配置

如果配置出现问题，可以：
1. 删除配置文件: `plugins/gps_location_plugin/config.json`
2. 重启PicMan
3. 插件会使用默认配置重新初始化

## 技术支持

如果遇到问题或需要帮助：

1. 查看本文档的故障排除部分
2. 检查PicMan的日志文件
3. 在PicMan项目页面提交Issue
4. 联系开发团队

## 版本历史

### v1.0.0 (2025-07-20)
- 初始版本发布
- 支持基础GPS位置查询功能
- 支持多个API服务
- 实现缓存机制
- 集成到PicMan用户界面

## 许可证

本插件遵循与PicMan主程序相同的许可证。

## 致谢

- OpenStreetMap Nominatim服务
- Google Maps Geocoding API
- 百度地图API
- 高德地图API
- PicMan开发团队和社区贡献者