"""
文件工具类
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """确保目录存在，如果不存在则创建"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error("创建目录失败", path=path, error=str(e))
            return False
    
    @staticmethod
    def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            if not os.path.exists(file_path):
                logger.warning("文件不存在", file_path=file_path)
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("加载JSON文件失败", file_path=file_path, error=str(e))
            return None
    
    @staticmethod
    def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
        """保存JSON文件"""
        try:
            # 确保目录存在
            FileUtils.ensure_directory(os.path.dirname(file_path))
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info("JSON文件保存成功", file_path=file_path)
            return True
        except Exception as e:
            logger.error("保存JSON文件失败", file_path=file_path, error=str(e))
            return False
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """获取文件大小（字节）"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error("获取文件大小失败", file_path=file_path, error=str(e))
            return 0
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    @staticmethod
    def is_image_file(file_path: str) -> bool:
        """检查是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        return Path(file_path).suffix.lower() in image_extensions
    
    @staticmethod
    def get_image_files(directory: str) -> list:
        """获取目录中的所有图片文件"""
        try:
            image_files = []
            for file_path in Path(directory).rglob("*"):
                if file_path.is_file() and FileUtils.is_image_file(str(file_path)):
                    image_files.append(str(file_path))
            return image_files
        except Exception as e:
            logger.error("获取图片文件失败", directory=directory, error=str(e))
            return [] 