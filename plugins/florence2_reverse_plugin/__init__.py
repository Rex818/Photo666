"""
Florence2图片反推信息插件
支持Florence2模型对图片进行反向推导，生成不同详细程度的信息描述
"""

__version__ = "1.0.0"
__author__ = "Photo666 Team"
__description__ = "Florence2图片反推信息插件"

# 导入插件类
from .plugin import Florence2ReversePlugin

__all__ = ["Florence2ReversePlugin"] 