"""
JoyCaption插件GPU工具类
"""

import logging
from typing import Dict, Any, Optional, List
import torch


class GPUUtils:
    """GPU工具类"""
    
    @staticmethod
    def is_cuda_available() -> bool:
        """检查CUDA是否可用"""
        try:
            return torch.cuda.is_available()
        except Exception as e:
            logging.error(f"检查CUDA可用性失败: {str(e)}")
            return False
    
    @staticmethod
    def get_gpu_count() -> int:
        """获取GPU数量"""
        try:
            if torch.cuda.is_available():
                return torch.cuda.device_count()
            return 0
        except Exception as e:
            logging.error(f"获取GPU数量失败: {str(e)}")
            return 0
    
    @staticmethod
    def get_gpu_info(device_id: int = 0) -> Dict[str, Any]:
        """获取GPU信息"""
        try:
            if not torch.cuda.is_available():
                return {"error": "CUDA不可用"}
            
            if device_id >= torch.cuda.device_count():
                return {"error": f"GPU设备 {device_id} 不存在"}
            
            device = torch.cuda.get_device_properties(device_id)
            
            return {
                "device_id": device_id,
                "name": device.name,
                "total_memory_gb": device.total_memory / (1024**3),
                "multi_processor_count": device.multi_processor_count,
                "major": device.major,
                "minor": device.minor,
                "compute_capability": f"{device.major}.{device.minor}",
                "is_integrated": device.is_integrated,
                "is_multi_gpu_board": device.is_multi_gpu_board
            }
            
        except Exception as e:
            logging.error(f"获取GPU信息失败 {device_id}: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def get_memory_info(device_id: int = 0) -> Dict[str, Any]:
        """获取GPU内存信息"""
        try:
            if not torch.cuda.is_available():
                return {"error": "CUDA不可用"}
            
            if device_id >= torch.cuda.device_count():
                return {"error": f"GPU设备 {device_id} 不存在"}
            
            # 设置当前设备
            torch.cuda.set_device(device_id)
            
            # 获取内存信息
            total_memory = torch.cuda.get_device_properties(device_id).total_memory
            allocated_memory = torch.cuda.memory_allocated(device_id)
            reserved_memory = torch.cuda.memory_reserved(device_id)
            free_memory = total_memory - reserved_memory
            
            return {
                "device_id": device_id,
                "total_memory_gb": total_memory / (1024**3),
                "allocated_memory_gb": allocated_memory / (1024**3),
                "reserved_memory_gb": reserved_memory / (1024**3),
                "free_memory_gb": free_memory / (1024**3),
                "memory_usage_percent": (reserved_memory / total_memory) * 100
            }
            
        except Exception as e:
            logging.error(f"获取GPU内存信息失败 {device_id}: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def clear_gpu_memory(device_id: int = 0) -> bool:
        """清理GPU内存"""
        try:
            if not torch.cuda.is_available():
                return True
            
            if device_id >= torch.cuda.device_count():
                logging.warning(f"GPU设备 {device_id} 不存在")
                return False
            
            # 设置当前设备
            torch.cuda.set_device(device_id)
            
            # 清理缓存
            torch.cuda.empty_cache()
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            logging.info(f"GPU内存清理完成，设备 {device_id}")
            return True
            
        except Exception as e:
            logging.error(f"清理GPU内存失败 {device_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_optimal_device() -> str:
        """获取最优设备"""
        try:
            if torch.cuda.is_available():
                # 检查可用内存
                device_id = 0
                memory_info = GPUUtils.get_memory_info(device_id)
                
                if "error" not in memory_info:
                    free_memory_gb = memory_info["free_memory_gb"]
                    if free_memory_gb >= 4.0:  # 至少4GB可用内存
                        return "cuda"
                    else:
                        logging.warning(f"GPU可用内存不足: {free_memory_gb:.2f}GB，使用CPU")
                        return "cpu"
                else:
                    logging.warning(f"无法获取GPU内存信息: {memory_info['error']}")
                    return "cpu"
            else:
                return "cpu"
                
        except Exception as e:
            logging.error(f"获取最优设备失败: {str(e)}")
            return "cpu"
    
    @staticmethod
    def get_recommended_precision(device_id: int = 0) -> str:
        """获取推荐的精度模式"""
        try:
            if not torch.cuda.is_available():
                return "Full Precision (fp32)"
            
            memory_info = GPUUtils.get_memory_info(device_id)
            if "error" in memory_info:
                return "Balanced (8-bit)"
            
            free_memory_gb = memory_info["free_memory_gb"]
            
            if free_memory_gb >= 16.0:
                return "Full Precision (fp32)"
            elif free_memory_gb >= 12.0:
                return "Full Precision (bf16)"
            elif free_memory_gb >= 8.0:
                return "Full Precision (fp16)"
            elif free_memory_gb >= 4.0:
                return "Balanced (8-bit)"
            else:
                return "Maximum Savings (4-bit)"
                
        except Exception as e:
            logging.error(f"获取推荐精度失败: {str(e)}")
            return "Balanced (8-bit)"
    
    @staticmethod
    def check_memory_sufficient(model_size_gb: float, device_id: int = 0) -> bool:
        """检查内存是否足够"""
        try:
            if not torch.cuda.is_available():
                return True  # CPU模式总是可用
            
            memory_info = GPUUtils.get_memory_info(device_id)
            if "error" in memory_info:
                return False
            
            free_memory_gb = memory_info["free_memory_gb"]
            
            # 需要额外的内存用于推理
            required_memory_gb = model_size_gb * 1.5
            
            return free_memory_gb >= required_memory_gb
            
        except Exception as e:
            logging.error(f"检查内存是否足够失败: {str(e)}")
            return False
    
    @staticmethod
    def get_all_gpu_info() -> List[Dict[str, Any]]:
        """获取所有GPU信息"""
        try:
            gpu_count = GPUUtils.get_gpu_count()
            gpu_info_list = []
            
            for device_id in range(gpu_count):
                gpu_info = GPUUtils.get_gpu_info(device_id)
                memory_info = GPUUtils.get_memory_info(device_id)
                
                if "error" not in gpu_info and "error" not in memory_info:
                    combined_info = {**gpu_info, **memory_info}
                    gpu_info_list.append(combined_info)
                else:
                    gpu_info_list.append({
                        "device_id": device_id,
                        "error": gpu_info.get("error", memory_info.get("error", "未知错误"))
                    })
            
            return gpu_info_list
            
        except Exception as e:
            logging.error(f"获取所有GPU信息失败: {str(e)}")
            return []
    
    @staticmethod
    def set_memory_fraction(fraction: float, device_id: int = 0) -> bool:
        """设置GPU内存使用比例"""
        try:
            if not torch.cuda.is_available():
                return True
            
            if device_id >= torch.cuda.device_count():
                return False
            
            # 设置内存使用比例
            torch.cuda.set_per_process_memory_fraction(fraction, device_id)
            
            logging.info(f"设置GPU内存使用比例: {fraction:.2%}, 设备 {device_id}")
            return True
            
        except Exception as e:
            logging.error(f"设置GPU内存使用比例失败: {str(e)}")
            return False
    
    @staticmethod
    def get_cuda_version() -> str:
        """获取CUDA版本"""
        try:
            if torch.cuda.is_available():
                return torch.version.cuda
            return "N/A"
        except Exception as e:
            logging.error(f"获取CUDA版本失败: {str(e)}")
            return "N/A"
    
    @staticmethod
    def get_torch_version() -> str:
        """获取PyTorch版本"""
        try:
            return torch.__version__
        except Exception as e:
            logging.error(f"获取PyTorch版本失败: {str(e)}")
            return "N/A"
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """获取系统信息"""
        try:
            import platform
            
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "torch_version": GPUUtils.get_torch_version(),
                "cuda_version": GPUUtils.get_cuda_version(),
                "cuda_available": GPUUtils.is_cuda_available(),
                "gpu_count": GPUUtils.get_gpu_count(),
                "optimal_device": GPUUtils.get_optimal_device()
            }
            
        except Exception as e:
            logging.error(f"获取系统信息失败: {str(e)}")
            return {"error": str(e)} 