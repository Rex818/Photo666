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

# check if python version is above 3.10
import sys

if sys.version_info >= (3, 10):
    print("Python version is above 3.10, patching the collections module.")
    # Monkey patch collections
    import collections
    import collections.abc

    for type_name in collections.abc.__all__:
        setattr(collections, type_name, getattr(collections.abc, type_name))
    
    # 特别处理Mapping类型
    try:
        from collections.abc import Mapping
        collections.Mapping = Mapping
    except ImportError:
        pass

# 导出Janus核心模块
try:
    from .models import VLMImageProcessor, VLChatProcessor, MultiModalityCausalLM
    from .janusflow.models import SigLIPVisionTransformer, VQModel
    
    __all__ = [
        "VLMImageProcessor",
        "VLChatProcessor", 
        "MultiModalityCausalLM",
        "SigLIPVisionTransformer",
        "VQModel",
    ]
    
    # 为了兼容性，也导出为janus命名空间
    class JanusNamespace:
        """Janus模块命名空间，提供兼容性导入"""
        from .models import VLChatProcessor, MultiModalityCausalLM, VLMImageProcessor
        from .janusflow.models import SigLIPVisionTransformer, VQModel
        
        models = type('models', (), {
            'VLChatProcessor': VLChatProcessor,
            'MultiModalityCausalLM': MultiModalityCausalLM,
            'VLMImageProcessor': VLMImageProcessor,
        })
        
        def __getattr__(self, name):
            if name == 'models':
                return self.models
            raise AttributeError(f"module 'janus' has no attribute '{name}'")
    
    # 创建janus模块的别名
    janus = JanusNamespace()
    
    # 为了兼容性，也导出janus_official模块
    janus_official = type('janus_official', (), {
        'janus': janus,
        'models': type('models', (), {
            'VLChatProcessor': VLChatProcessor,
            'MultiModalityCausalLM': MultiModalityCausalLM,
            'VLMImageProcessor': VLMImageProcessor,
        })
    })
    
except ImportError as e:
    print(f"Warning: Some Janus modules could not be imported: {e}")
    __all__ = []
