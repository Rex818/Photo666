"""
配置服务接口
定义配置管理的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IConfigService(ABC):
    """配置服务接口"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化配置服务
        
        Returns:
            初始化是否成功
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """获取配置
        
        Returns:
            配置字典
        """
        pass
    
    @abstractmethod
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新配置
        
        Args:
            config: 新配置
            
        Returns:
            更新是否成功
        """
        pass
    
    @abstractmethod
    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型配置字典
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> list:
        """获取可用模型列表
        
        Returns:
            模型列表
        """
        pass
    
    @abstractmethod
    def save_config_to_file(self) -> bool:
        """保存配置到文件
        
        Returns:
            保存是否成功
        """
        pass
    
    @abstractmethod
    def load_config_from_file(self) -> bool:
        """从文件加载配置
        
        Returns:
            加载是否成功
        """
        pass 