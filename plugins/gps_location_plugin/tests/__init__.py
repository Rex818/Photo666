"""
GPS位置查询插件测试模块

包含插件各个组件的单元测试和集成测试。
"""

import sys
import os
from pathlib import Path

# 添加插件目录到Python路径
plugin_dir = Path(__file__).parent.parent
if str(plugin_dir) not in sys.path:
    sys.path.insert(0, str(plugin_dir))

# 添加PicMan源码目录到Python路径
src_dir = Path(__file__).parent.parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

__version__ = "1.0.0"