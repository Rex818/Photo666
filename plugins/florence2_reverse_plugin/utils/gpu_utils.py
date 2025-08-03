"""
GPU工具类
"""

import torch
import psutil
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class GPUUtils:
    """GPU相关工具类"""
    
    @staticmethod
    def check_cuda_available() -> bool:
        """检查CUDA是否可用"""
        try:
            return torch.cuda.is_available()
        except Exception as e:
            logger.error("检查CUDA可用性失败", error=str(e))
            return False
    
    @staticmethod
    def get_gpu_info() -> Dict[str, Any]:
        """获取GPU信息"""
        try:
            if not GPUUtils.check_cuda_available():
                return {"available": False, "error": "CUDA不可用"}
            
            gpu_info = {
                "available": True,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "devices": []
            }
            
            for i in range(torch.cuda.device_count()):
                device_info = {
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_total": torch.cuda.get_device_properties(i).total_memory,
                    "memory_allocated": torch.cuda.memory_allocated(i),
                    "memory_cached": torch.cuda.memory_reserved(i)
                }
                gpu_info["devices"].append(device_info)
            
            return gpu_info
            
        except Exception as e:
            logger.error("获取GPU信息失败", error=str(e))
            return {"available": False, "error": str(e)}
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            # 系统内存
            system_memory = psutil.virtual_memory()
            
            # GPU内存
            gpu_memory = {}
            if GPUUtils.check_cuda_available():
                for i in range(torch.cuda.device_count()):
                    gpu_memory[f"gpu_{i}"] = {
                        "allocated": torch.cuda.memory_allocated(i),
                        "cached": torch.cuda.memory_reserved(i),
                        "total": torch.cuda.get_device_properties(i).total_memory
                    }
            
            return {
                "system": {
                    "total": system_memory.total,
                    "available": system_memory.available,
                    "used": system_memory.used,
                    "percent": system_memory.percent
                },
                "gpu": gpu_memory
            }
            
        except Exception as e:
            logger.error("获取内存使用情况失败", error=str(e))
            return {}
    
    @staticmethod
    def clear_gpu_cache(device_id: Optional[int] = None) -> bool:
        """清理GPU缓存"""
        try:
            if not GPUUtils.check_cuda_available():
                return False
            
            if device_id is None:
                # 清理所有GPU缓存
                torch.cuda.empty_cache()
                logger.info("已清理所有GPU缓存")
            else:
                # 清理指定GPU缓存
                with torch.cuda.device(device_id):
                    torch.cuda.empty_cache()
                logger.info("已清理GPU缓存", device_id=device_id)
            
            return True
            
        except Exception as e:
            logger.error("清理GPU缓存失败", device_id=device_id, error=str(e))
            return False
    
    @staticmethod
    def get_optimal_batch_size(model_size_mb: float, max_memory_usage: float = 0.8) -> int:
        """根据模型大小和内存使用率计算最优批大小"""
        try:
            if not GPUUtils.check_cuda_available():
                return 1
            
            # 获取GPU内存信息
            gpu_info = GPUUtils.get_gpu_info()
            if not gpu_info.get("available", False):
                return 1
            
            # 使用第一个GPU
            device_info = gpu_info["devices"][0]
            total_memory = device_info["memory_total"]
            available_memory = total_memory * max_memory_usage
            
            # 估算模型内存占用（MB转字节）
            model_memory = model_size_mb * 1024 * 1024
            
            # 预留一些内存给中间结果
            reserved_memory = 512 * 1024 * 1024  # 512MB
            
            # 计算可用内存
            usable_memory = available_memory - model_memory - reserved_memory
            
            if usable_memory <= 0:
                return 1
            
            # 估算每张图片的内存占用（假设224x224 RGB图像）
            image_memory = 224 * 224 * 3 * 4  # 4字节浮点数
            
            # 计算批大小
            batch_size = max(1, int(usable_memory / image_memory))
            
            # 限制最大批大小
            batch_size = min(batch_size, 16)
            
            logger.info("计算最优批大小", 
                       model_size_mb=model_size_mb,
                       total_memory=GPUUtils.format_memory(total_memory),
                       batch_size=batch_size)
            
            return batch_size
            
        except Exception as e:
            logger.error("计算最优批大小失败", error=str(e))
            return 1
    
    @staticmethod
    def format_memory(bytes_value: int) -> str:
        """格式化内存大小"""
        if bytes_value == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while bytes_value >= 1024 and i < len(size_names) - 1:
            bytes_value /= 1024.0
            i += 1
        
        return f"{bytes_value:.1f}{size_names[i]}"
    
    @staticmethod
    def set_memory_fraction(fraction: float, device_id: Optional[int] = None) -> bool:
        """设置GPU内存使用比例"""
        try:
            if not GPUUtils.check_cuda_available():
                return False
            
            if device_id is None:
                device_id = torch.cuda.current_device()
            
            torch.cuda.set_per_process_memory_fraction(fraction, device_id)
            logger.info("设置GPU内存使用比例", device_id=device_id, fraction=fraction)
            return True
            
        except Exception as e:
            logger.error("设置GPU内存使用比例失败", device_id=device_id, fraction=fraction, error=str(e))
            return False
    
    @staticmethod
    def get_device_info() -> Dict[str, Any]:
        """获取当前设备信息"""
        try:
            device_info = {
                "cuda_available": GPUUtils.check_cuda_available(),
                "device_count": torch.cuda.device_count() if GPUUtils.check_cuda_available() else 0,
                "current_device": torch.cuda.current_device() if GPUUtils.check_cuda_available() else None
            }
            
            if GPUUtils.check_cuda_available():
                device_info["current_device_name"] = torch.cuda.get_device_name(device_info["current_device"])
                device_info["memory_info"] = GPUUtils.get_memory_usage()
            
            return device_info
            
        except Exception as e:
            logger.error("获取设备信息失败", error=str(e))
            return {"cuda_available": False, "error": str(e)} 