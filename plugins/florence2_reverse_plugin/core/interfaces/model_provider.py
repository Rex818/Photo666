"""
模型提供者接口
定义模型查找、下载、加载的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable


class IModelProvider(ABC):
    """模型提供者接口"""
    
    @abstractmethod
    def find_model(self, model_name: str, custom_path: Optional[str] = None) -> Optional[str]:
        """查找模型文件
        
        Args:
            model_name: 模型名称
            custom_path: 自定义路径
            
        Returns:
            模型路径，如果未找到返回None
        """
        pass
    
    @abstractmethod
    def download_model(self, model_name: str, target_path: Optional[str] = None) -> bool:
        """下载模型
        
        Args:
            model_name: 模型名称
            target_path: 目标路径
            
        Returns:
            下载是否成功
        """
        pass
    
    @abstractmethod
    def load_model(self, model_name: str, custom_path: Optional[str] = None) -> bool:
        """加载模型
        
        Args:
            model_name: 模型名称
            custom_path: 自定义路径
            
        Returns:
            加载是否成功
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> bool:
        """卸载模型
        
        Returns:
            卸载是否成功
        """
        pass
    
    @abstractmethod
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载
        
        Returns:
            模型是否已加载
        """
        pass
    
    @abstractmethod
    def get_loaded_model_info(self) -> Optional[Dict[str, Any]]:
        """获取已加载模型信息
        
        Returns:
            模型信息字典
        """
        pass
    
    @abstractmethod
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，参数为 (step, progress, message)
        """
        pass 