# Florence2图片反推信息插件

## 概述

Florence2图片反推信息插件是Photo666照片管理软件的一个扩展功能，利用Microsoft Florence-2模型对图片进行反向推导，生成不同详细程度的信息描述。

## 功能特性

- **三级描述系统**：支持简单描述、普通描述、详细描述
- **多模型支持**：支持多种Florence2模型变体
- **批量处理**：支持单张、多张图片或基于目录的反推
- **GPU加速**：充分利用GPU资源，支持混合精度训练
- **结果保存**：自动保存到文件和数据库
- **标签集成**：结果自动显示在标签管理区

## 支持的模型

- microsoft/Florence-2-base
- microsoft/Florence-2-base-ft
- microsoft/Florence-2-large
- microsoft/Florence-2-large-ft
- MiaoshouAI/Florence-2-base-PromptGen-v1.5
- MiaoshouAI/Florence-2-large-PromptGen-v1.5

## 安装要求

- Python 3.11+
- PyTorch 2.0+ (CUDA支持)
- Transformers 4.39.0+
- GPU: RTX 4080S或更高性能显卡

## 使用方法

1. 选择图片（单张或多张）
2. 点击"AI反推"菜单或工具栏按钮
3. 选择模型和描述级别
4. 点击"开始反推"
5. 等待处理完成，查看结果

## 配置说明

插件配置文件位于 `config/config.json`，可以调整：
- 默认模型选择
- 推理参数设置
- 输出选项配置
- 性能优化参数

## 技术架构

- **插件化设计**：独立目录结构，易于维护和扩展
- **模型管理**：自动下载、缓存、版本管理
- **推理引擎**：高效的GPU推理，支持批处理
- **结果处理**：文件保存、数据库存储、标签集成

## 版本历史

- v1.0.0: 初始版本，支持基础Florence2模型反推功能 