"""
JoyCaption图片反推信息插件
支持JoyCaption模型对图片进行反向推导，生成不同详细程度的信息描述
"""

from .plugin import JoyCaptionReversePlugin

# 插件实例
plugin_instance = JoyCaptionReversePlugin()

__all__ = ['JoyCaptionReversePlugin', 'plugin_instance'] 