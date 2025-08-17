"""
Janus插件模型管理器
"""

import os
import json
import logging
import torch
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# 尝试导入Janus库
try:
    from transformers import AutoModelForCausalLM
    
    # 尝试从本地janus_official模块导入
    import sys
    import os
    plugin_dir = Path(os.path.dirname(os.path.dirname(__file__)))
    janus_official_path = plugin_dir.parent / "janus_text2image_plugin" / "janus_official"
    
    if janus_official_path.exists():
        # 将janus_official路径添加到sys.path
        sys.path.insert(0, str(janus_official_path))
        try:
            from models import VLChatProcessor
            JANUS_AVAILABLE = True
            logging.getLogger("plugins.janus_reverse_plugin.core.model_manager").info("Janus库从本地模块导入成功")
        except ImportError as e1:
            # 如果直接导入失败，尝试从janus命名空间导入
            try:
                # 重新添加路径并尝试导入
                sys.path.insert(0, str(janus_official_path))
                from janus_official import janus
                VLChatProcessor = janus.models.VLChatProcessor
                JANUS_AVAILABLE = True
                logging.getLogger("plugins.janus_reverse_plugin.core.model_manager").info("Janus库从janus命名空间导入成功")
            except ImportError as e2:
                JANUS_AVAILABLE = False
                logging.getLogger("plugins.janus_reverse_plugin.core.model_manager").warning(f"本地Janus模块导入失败: {e1}, {e2}")
    else:
        JANUS_AVAILABLE = False
        logging.getLogger("plugins.janus_reverse_plugin.core.model_manager").warning(f"本地Janus模块路径不存在: {janus_official_path}")
        
except ImportError as e:
    JANUS_AVAILABLE = False
    logging.getLogger("plugins.janus_reverse_plugin.core.model_manager").warning(f"Janus库导入失败: {e}")


class ModelManager:
    """Janus插件模型管理器"""
    
    def __init__(self, config_manager):
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.core.model_manager")
        self.config_manager = config_manager
        
        # 模型状态
        self.current_model = None
        self.current_processor = None
        self.current_model_id = None
        self.is_model_loaded = False
        
        # Janus库可用性
        self.JANUS_AVAILABLE = JANUS_AVAILABLE
        
        # 初始化模型目录
        plugin_dir = Path(os.path.dirname(os.path.dirname(__file__)))
        self.models_dir = plugin_dir / "models"
        self.cache_dir = plugin_dir / "cache"
        
        self.models_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"模型目录初始化完成 - 插件目录: {plugin_dir}, 缓存目录: {self.cache_dir}")
    
    # -------------------- 辅助校验方法 --------------------
    def _is_valid_model_directory(self, model_path: Path) -> bool:
        """检查是否为有效的模型目录（与下载管理器一致）"""
        try:
            if not model_path or not model_path.exists() or not model_path.is_dir():
                return False
            # 关键文件
            required_files = [
                "config.json",
            ]
            # 任一模型权重存在即可
            weight_files = [
                "pytorch_model.bin",
                "model.safetensors",
                "pytorch_model.bin.index.json",
                "model.safetensors.index.json",
            ]
            for f in required_files:
                if not (model_path / f).exists():
                    return False
            # 基础config可解析性校验
            try:
                with open(model_path / "config.json", "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                return False
            # 权重文件或分片存在其一
            has_weight = False
            if (model_path / "pytorch_model.bin").exists() or (model_path / "model.safetensors").exists():
                # 简单完整性：文件体积需大于50MB，防止半包
                weight_path = (model_path / "pytorch_model.bin") if (model_path / "pytorch_model.bin").exists() else (model_path / "model.safetensors")
                try:
                    if weight_path.stat().st_size > 50 * 1024 * 1024:
                        has_weight = True
                except Exception:
                    return False
            elif (model_path / "pytorch_model.bin.index.json").exists() or (model_path / "model.safetensors.index.json").exists():
                # 粗略检查至少存在一个分片文件
                shard = next(iter(model_path.glob("pytorch_model-*.bin")), None)
                if shard is None:
                    shard = next(iter(model_path.glob("model-*.safetensors")), None)
                if shard is not None:
                    try:
                        if shard.stat().st_size > 10 * 1024 * 1024:  # 分片最少也应有一定体积
                            has_weight = True
                    except Exception:
                        return False
            return has_weight
        except Exception as e:
            self.logger.warning(f"检查模型目录有效性失败: {str(e)}")
            return False

    def _find_valid_model_dir_in_path(self, base_path: Path, model_id: str) -> Optional[Path]:
        """在给定路径内递归浅层查找有效模型目录（支持HF缓存结构）。"""
        try:
            if base_path.is_dir() and self._is_valid_model_directory(base_path):
                return base_path
            candidates: list[Path] = []
            # 常见命名
            model_name = model_id.split('/')[-1]
            name_variants = [model_name, model_id.replace('/', '_'), model_id.replace('/', '-')]
            for name in name_variants:
                candidates.append(base_path / name)
            # HF缓存结构 models--org--repo/snapshots/<rev>
            for p in base_path.rglob("snapshots"):
                # 只向下1层
                for snap in p.iterdir():
                    if snap.is_dir():
                        candidates.append(snap)
            # 扫描候选
            for c in candidates:
                if c.is_dir() and self._is_valid_model_directory(c):
                    return c
            # 限制深度的广度优先扫描（最多两层）
            for child in base_path.iterdir() if base_path.is_dir() else []:
                if child.is_dir() and self._is_valid_model_directory(child):
                    return child
                if child.is_dir():
                    for sub in child.iterdir():
                        if sub.is_dir() and self._is_valid_model_directory(sub):
                            return sub
            return None
        except Exception:
            return None
    
    def load_model(self, model_id: str, custom_path: Optional[str] = None) -> bool:
        """加载模型"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法加载模型")
            return False
        
        try:
            self.logger.info(f"开始加载模型: {model_id}")
            
            # 1) 解析模型路径（优先使用自定义路径）
            model_path: Optional[Path] = None
            if custom_path:
                candidate = Path(custom_path)
                if candidate.is_dir():
                    found = self._find_valid_model_dir_in_path(candidate, model_id)
                    if found is not None:
                        model_path = found
                    else:
                        self.logger.warning(f"自定义路径无效或不包含有效模型: {custom_path}")
            
            if model_path is None:
                # 2) 使用默认models目录
                model_path_str = self.get_model_path(model_id)
                model_path = Path(model_path_str) if model_path_str else (self.models_dir / model_id.split('/')[-1])
                
                # 如果存在但无效：优先不下载，先尝试在默认目录内深搜有效子目录（处理用户手动拷贝的层级差异）
                if model_path.exists() and not self._is_valid_model_directory(model_path):
                    self.logger.warning(f"检测到无效模型目录，尝试在目录内查找有效子目录: {model_path}")
                    found = self._find_valid_model_dir_in_path(model_path, model_id)
                    if found is not None:
                        model_path = found
                    else:
                        # 再考虑下载
                        self.logger.warning(f"未找到有效子目录，开始重新下载: {model_path}")
                        from .download_manager import DownloadManager
                        dm = DownloadManager(self.config_manager)
                        if not dm.download_model(model_id, None):
                            self.logger.error("重新下载失败")
                            return False
                
                # 如果不存在，则下载
                if not model_path.exists():
                    self.logger.info(f"未找到模型，开始下载: {model_id}")
                    from .download_manager import DownloadManager
                    dm = DownloadManager(self.config_manager)
                    if not dm.download_model(model_id, None):
                        self.logger.error("下载失败")
                        return False
            
            # 再次校验有效性
            if not self._is_valid_model_directory(model_path):
                self.logger.error(f"模型目录无效: {model_path}")
                return False
            
            # 加载模型和处理器（失败则自动尝试重新下载一次）
            def _do_load() -> bool:
                # 优先使用GPU（如可用），否则回退CPU；并显式log设备与dtype
                use_cuda = torch.cuda.is_available()
                # 统一选择bfloat16以避免与某些权重偏置的Half冲突；CPU回退float32
                dtype = torch.bfloat16 if use_cuda and hasattr(torch, 'bfloat16') else (torch.float16 if use_cuda else torch.float32)
                device_map = "auto" if use_cuda else None
                self.logger.info(f"开始加载模型到设备: {'cuda' if use_cuda else 'cpu'}, dtype: {dtype}")

                self.current_model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    torch_dtype=dtype,
                    device_map=device_map,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                )

                # 如果未使用device_map，将模型显式移动到cuda
                if use_cuda and device_map is None:
                    self.current_model = self.current_model.to('cuda')

                self.current_processor = VLChatProcessor.from_pretrained(str(model_path))
                self.logger.info("模型与处理器加载完成")
                # 输出显存占用情况（如可用）
                if use_cuda:
                    try:
                        mem_alloc = torch.cuda.memory_allocated() / (1024**3)
                        mem_reserved = torch.cuda.memory_reserved() / (1024**3)
                        self.logger.info(f"GPU内存 - 已分配: {mem_alloc:.2f} GB, 已保留: {mem_reserved:.2f} GB")
                    except Exception:
                        pass
                return True

            try:
                _do_load()
            except Exception as load_err:
                self.logger.warning(f"模型加载失败，尝试自动修复并重新下载: {load_err}")
                from .download_manager import DownloadManager
                dm = DownloadManager(self.config_manager)
                # 删除旧目录后重下
                try:
                    if model_path.exists():
                        import shutil as _shutil
                        _shutil.rmtree(model_path, ignore_errors=True)
                except Exception:
                    pass
                if not dm.download_model(model_id, None):
                    self.logger.error("自动重新下载失败")
                    return False
                # 重新定位目录（避免download_manager内部重定向）
                model_path = Path(self.get_model_path(model_id) or model_path)
                if not self._is_valid_model_directory(model_path):
                    self.logger.error("重新下载后模型仍无效")
                    return False
                # 再次尝试加载
                _do_load()
            
            # 更新状态
            self.current_model_id = model_id
            self.is_model_loaded = True
            
            self.logger.info(f"模型加载成功: {model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {model_id}, 错误: {str(e)}")
            return False
    
    def unload_model(self) -> bool:
        """卸载模型"""
        if self.is_model_loaded:
            self.current_model = None
            self.current_processor = None
            self.current_model_id = None
            self.is_model_loaded = False
            
            # 清理GPU内存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("模型已卸载")
            return True
        return True
    
    def get_loaded_model(self) -> Optional[Tuple[Any, Any]]:
        """获取已加载的模型"""
        if not self.is_model_loaded:
            return None
        return self.current_model, self.current_processor
    
    def is_model_ready(self) -> bool:
        """检查模型是否准备就绪"""
        return self.is_model_loaded and self.current_model is not None
    
    def get_current_model_id(self) -> Optional[str]:
        """获取当前模型ID"""
        return self.current_model_id
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        return self.config_manager.get_model_info(model_id)
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        return self.config_manager.get_available_models()
    
    def check_model_exists(self, model_id: str, custom_paths: Optional[List[str]] = None) -> bool:
        """检查模型是否存在（支持自定义路径优先）"""
        try:
            # 1) 先检查自定义路径
            if custom_paths:
                for p in custom_paths:
                    if not p:
                        continue
                    candidate = Path(p)
                    if candidate.exists():
                        found = self._find_valid_model_dir_in_path(candidate, model_id)
                        if found is not None:
                            return True
            # 2) 再检查默认models目录
            model_path = self.get_model_path(model_id)
            if model_path:
                return self._is_valid_model_directory(Path(model_path))
            return False
        except Exception as e:
            self.logger.error(f"检查模型存在性失败: {model_id}, 错误: {str(e)}")
            return False
    
    def download_model(self, model_id: str, progress_callback=None) -> bool:
        """下载模型（使用下载管理器）"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法下载模型")
            return False
        
        try:
            # 使用下载管理器
            from .download_manager import DownloadManager
            download_manager = DownloadManager(self.config_manager)
            
            # 设置进度回调
            if progress_callback:
                download_manager.set_progress_callback(progress_callback)
            
            # 执行下载
            return download_manager.download_model(model_id, progress_callback)
            
        except Exception as e:
            self.logger.error(f"下载模型失败: {model_id}, 错误: {str(e)}")
            return False
    
    def get_model_path(self, model_id: str) -> Optional[str]:
        """获取模型路径"""
        try:
            # 构建模型路径
            model_path = self.models_dir / model_id.split('/')[-1]
            
            # 检查路径是否存在
            if model_path.exists():
                return str(model_path)
            
            # 如果不存在，返回None
            return None
            
        except Exception as e:
            self.logger.error(f"获取模型路径失败: {model_id}, 错误: {str(e)}")
            return None
    
    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        if torch.cuda.is_available():
            return {
                "allocated": torch.cuda.memory_allocated() / 1024**3,  # GB
                "cached": torch.cuda.memory_reserved() / 1024**3  # GB
            }
        return {"allocated": 0, "cached": 0}
    
    def check_system_requirements(self, model_id: str) -> Dict[str, bool]:
        """检查系统要求"""
        model_info = self.get_model_info(model_id)
        if not model_info:
            return {"memory": False, "gpu": False}
        
        requirements = model_info.get("requirements", {})
        gpu_memory = requirements.get("gpu_memory", "0GB")
        gpu_memory = float(gpu_memory.replace("GB", ""))
        
        if torch.cuda.is_available():
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            has_enough_memory = total_memory >= gpu_memory
        else:
            has_enough_memory = False
        
        return {
            "memory": has_enough_memory,
            "gpu": torch.cuda.is_available()
        }
    
    def get_model_requirements(self, model_id: str) -> Dict[str, Any]:
        """获取模型要求"""
        model_info = self.get_model_info(model_id)
        if not model_info:
            return {}
        return model_info.get("requirements", {})
    
    def cleanup_cache(self) -> bool:
        """清理缓存"""
        try:
            if self.cache_dir.exists():
                for file in self.cache_dir.glob("*"):
                    if file.is_file():
                        file.unlink()
            self.logger.info("模型缓存清理完成")
            return True
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}")
            return False
    
    def get_model_status(self) -> Dict[str, Any]:
        """获取模型状态"""
        return {
            "is_loaded": self.is_model_loaded,
            "current_model": self.current_model_id,
            "memory_usage": self.get_memory_usage(),
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }