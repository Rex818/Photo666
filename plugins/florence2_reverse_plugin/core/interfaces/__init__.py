"""
Florence2插件接口定义模块
定义核心组件的抽象接口，实现依赖倒置原则
"""

from .model_provider import IModelProvider
from .inference_service import IInferenceService
from .result_repository import IResultRepository
from .config_service import IConfigService

__all__ = [
    'IModelProvider',
    'IInferenceService', 
    'IResultRepository',
    'IConfigService'
] 