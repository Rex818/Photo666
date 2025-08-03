"""
JoyCaption插件文件工具类
"""

import os
import logging
from pathlib import Path
from typing import List, Set, Optional
from PIL import Image


class FileUtils:
    """文件工具类"""
    
    # 支持的图片格式
    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    @staticmethod
    def get_image_files(directory: str, recursive: bool = True) -> List[str]:
        """获取目录中的图片文件"""
        try:
            directory_path = Path(directory)
            if not directory_path.exists() or not directory_path.is_dir():
                return []
            
            image_files = []
            
            if recursive:
                # 递归搜索
                for file_path in directory_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in FileUtils.SUPPORTED_IMAGE_EXTENSIONS:
                        image_files.append(str(file_path))
            else:
                # 只搜索当前目录
                for file_path in directory_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in FileUtils.SUPPORTED_IMAGE_EXTENSIONS:
                        image_files.append(str(file_path))
            
            return sorted(image_files)
            
        except Exception as e:
            logging.error(f"获取图片文件失败 {directory}: {str(e)}")
            return []
    
    @staticmethod
    def validate_image_file(file_path: str) -> bool:
        """验证图片文件"""
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                return False
            
            # 检查文件扩展名
            if path.suffix.lower() not in FileUtils.SUPPORTED_IMAGE_EXTENSIONS:
                return False
            
            # 检查文件大小
            if path.stat().st_size == 0:
                return False
            
            # 尝试打开图片验证格式
            try:
                with Image.open(file_path) as img:
                    img.verify()
                return True
            except Exception:
                return False
            
        except Exception as e:
            logging.error(f"验证图片文件失败 {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """获取文件大小（MB）"""
        try:
            size_bytes = Path(file_path).stat().st_size
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logging.error(f"获取文件大小失败 {file_path}: {str(e)}")
            return 0.0
    
    @staticmethod
    def get_directory_size_mb(directory: str) -> float:
        """获取目录大小（MB）"""
        try:
            total_size = 0
            directory_path = Path(directory)
            
            for file_path in directory_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size / (1024 * 1024)
            
        except Exception as e:
            logging.error(f"获取目录大小失败 {directory}: {str(e)}")
            return 0.0
    
    @staticmethod
    def create_directory(directory: str) -> bool:
        """创建目录"""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"创建目录失败 {directory}: {str(e)}")
            return False
    
    @staticmethod
    def ensure_directory_exists(file_path: str) -> bool:
        """确保文件所在目录存在"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"确保目录存在失败 {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_relative_path(base_path: str, file_path: str) -> str:
        """获取相对路径"""
        try:
            base = Path(base_path).resolve()
            file = Path(file_path).resolve()
            return str(file.relative_to(base))
        except Exception as e:
            logging.error(f"获取相对路径失败 {base_path} -> {file_path}: {str(e)}")
            return file_path
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """获取文件信息"""
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                "name": path.name,
                "stem": path.stem,
                "suffix": path.suffix,
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "exists": path.exists()
            }
            
        except Exception as e:
            logging.error(f"获取文件信息失败 {file_path}: {str(e)}")
            return {}
    
    @staticmethod
    def is_image_file(file_path: str) -> bool:
        """检查是否为图片文件"""
        try:
            return Path(file_path).suffix.lower() in FileUtils.SUPPORTED_IMAGE_EXTENSIONS
        except Exception:
            return False
    
    @staticmethod
    def get_image_dimensions(file_path: str) -> Optional[tuple]:
        """获取图片尺寸"""
        try:
            with Image.open(file_path) as img:
                return img.size
        except Exception as e:
            logging.error(f"获取图片尺寸失败 {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def get_image_format(file_path: str) -> Optional[str]:
        """获取图片格式"""
        try:
            with Image.open(file_path) as img:
                return img.format
        except Exception as e:
            logging.error(f"获取图片格式失败 {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def copy_file(source: str, destination: str) -> bool:
        """复制文件"""
        try:
            import shutil
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            logging.error(f"复制文件失败 {source} -> {destination}: {str(e)}")
            return False
    
    @staticmethod
    def move_file(source: str, destination: str) -> bool:
        """移动文件"""
        try:
            import shutil
            shutil.move(source, destination)
            return True
        except Exception as e:
            logging.error(f"移动文件失败 {source} -> {destination}: {str(e)}")
            return False
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """删除文件"""
        try:
            Path(file_path).unlink()
            return True
        except Exception as e:
            logging.error(f"删除文件失败 {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_unique_filename(directory: str, filename: str) -> str:
        """获取唯一文件名"""
        try:
            path = Path(directory) / filename
            if not path.exists():
                return str(path)
            
            # 如果文件存在，添加数字后缀
            stem = path.stem
            suffix = path.suffix
            counter = 1
            
            while True:
                new_filename = f"{stem}_{counter}{suffix}"
                new_path = Path(directory) / new_filename
                if not new_path.exists():
                    return str(new_path)
                counter += 1
                
        except Exception as e:
            logging.error(f"获取唯一文件名失败 {directory}/{filename}: {str(e)}")
            return filename
    
    @staticmethod
    def get_available_disk_space(directory: str) -> float:
        """获取可用磁盘空间（MB）"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(directory)
            return free / (1024 * 1024)
        except Exception as e:
            logging.error(f"获取可用磁盘空间失败 {directory}: {str(e)}")
            return 0.0 