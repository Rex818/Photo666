"""
推理服务接口
定义图片推理的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable


class IInferenceService(ABC):
    """推理服务接口"""
    
    @abstractmethod
    def initialize(self, model_provider, config_service) -> bool:
        """初始化推理服务
        
        Args:
            model_provider: 模型提供者
            config_service: 配置服务
            
        Returns:
            初始化是否成功
        """
        pass
    
    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """加载模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            加载是否成功
        """
        pass
    
    @abstractmethod
    def infer_single_image(self, image_path: str, description_level: str = "normal") -> Dict[str, Any]:
        """推理单张图片
        
        Args:
            image_path: 图片路径
            description_level: 描述级别
            
        Returns:
            推理结果字典
        """
        pass
    
    @abstractmethod
    def infer_batch_images(self, image_paths: List[str], 
                          description_level: str = "normal",
                          progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量推理图片
        
        Args:
            image_paths: 图片路径列表
            description_level: 描述级别
            progress_callback: 进度回调函数
            
        Returns:
            推理结果列表
        """
        pass
    
    @abstractmethod
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，参数为 (step, progress, message)
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """关闭推理服务
        
        Returns:
            关闭是否成功
        """
        pass 