"""
结果仓库接口
定义推理结果存储的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IResultRepository(ABC):
    """结果仓库接口"""
    
    @abstractmethod
    def save_result(self, result: Dict[str, Any]) -> bool:
        """保存推理结果
        
        Args:
            result: 推理结果字典
            
        Returns:
            保存是否成功
        """
        pass
    
    @abstractmethod
    def save_results(self, results: List[Dict[str, Any]]) -> bool:
        """批量保存推理结果
        
        Args:
            results: 推理结果列表
            
        Returns:
            保存是否成功
        """
        pass
    
    @abstractmethod
    def get_result(self, image_path: str, description_level: str) -> Optional[Dict[str, Any]]:
        """获取推理结果
        
        Args:
            image_path: 图片路径
            description_level: 描述级别
            
        Returns:
            推理结果字典，如果不存在返回None
        """
        pass
    
    @abstractmethod
    def save_to_file(self, result: Dict[str, Any], output_config: Dict[str, Any]) -> bool:
        """保存结果到文件
        
        Args:
            result: 推理结果
            output_config: 输出配置
            
        Returns:
            保存是否成功
        """
        pass
    
    @abstractmethod
    def get_result_from_file(self, image_path: str, description_level: str) -> Optional[str]:
        """从文件获取结果
        
        Args:
            image_path: 图片路径
            description_level: 描述级别
            
        Returns:
            结果内容，如果不存在返回None
        """
        pass 