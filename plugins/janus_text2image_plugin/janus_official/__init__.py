# Copyright (c) 2023-2024 DeepSeek.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# 简化版本：直接导出核心模块，避免复杂的导入检查
import sys
from pathlib import Path

# 获取当前文件所在目录
try:
    current_dir = Path(__file__).parent
except NameError:
    # 如果__file__未定义，使用相对路径
    current_dir = Path(".")

# 将当前目录添加到sys.path（如果还没有的话）
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 尝试导入核心模块
try:
    # 直接导入models模块
    import sys
    import os
    current_dir = Path(__file__).parent if '__file__' in globals() else Path(".")
    
    # 确保models目录在路径中
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from models import VLChatProcessor, MultiModalityCausalLM, VLMImageProcessor
    print("Janus核心模块导入成功")
    
    # 导出核心模块
    __all__ = [
        "VLChatProcessor",
        "MultiModalityCausalLM", 
        "VLMImageProcessor",
    ]
    
    # 创建janus命名空间
    class JanusNamespace:
        """Janus模块命名空间"""
        def __init__(self):
            self.VLChatProcessor = VLChatProcessor
            self.MultiModalityCausalLM = MultiModalityCausalLM
            self.VLMImageProcessor = VLMImageProcessor
        
        @property
        def models(self):
            """返回models命名空间"""
            return type('models', (), {
                'VLChatProcessor': VLChatProcessor,
                'MultiModalityCausalLM': MultiModalityCausalLM,
                'VLMImageProcessor': VLMImageProcessor,
            })
    
    # 创建全局janus对象
    janus = JanusNamespace()
    
    # 为了兼容性，也导出janus_official
    janus_official = type('janus_official', (), {
        'janus': janus,
        'models': janus.models,
    })
    
except ImportError as e:
    print(f"Janus模块导入失败: {e}")
    print("这可能是由于PyTorch版本不兼容导致的")
    
    # 创建占位符类
    class PlaceholderClass:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Janus模块未正确加载，请检查PyTorch版本兼容性")
    
    # 导出占位符
    VLChatProcessor = PlaceholderClass
    MultiModalityCausalLM = PlaceholderClass
    VLMImageProcessor = PlaceholderClass
    
    __all__ = [
        "VLChatProcessor",
        "MultiModalityCausalLM", 
        "VLMImageProcessor",
    ]
    
    # 创建占位符命名空间
    janus = type('janus', (), {
        'models': type('models', (), {
            'VLChatProcessor': VLChatProcessor,
            'MultiModalityCausalLM': MultiModalityCausalLM,
            'VLMImageProcessor': VLMImageProcessor,
        })
    })
    
    janus_official = type('janus_official', (), {
        'janus': janus,
        'models': janus.models,
    })
