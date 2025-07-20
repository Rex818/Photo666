"""
GPS位置查询插件

该插件能够自动读取照片中的GPS经纬度信息，并通过调用地理位置API来获取具体的地点名称。

作者: PicMan开发团队
版本: 1.0.0
"""

from .plugin import GPSLocationPlugin

__version__ = "1.0.0"
__author__ = "PicMan开发团队"
__description__ = "GPS位置查询插件 - 自动查询照片拍摄地点"

# 导出主插件类
__all__ = ["GPSLocationPlugin"]