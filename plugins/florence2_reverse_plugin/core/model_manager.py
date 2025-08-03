"""
模型管理器
负责模型的查找、下载、加载和缓存管理
"""

import os
import sys
import torch
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import hashlib
from unittest.mock import patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from plugins.florence2_reverse_plugin.core.config_manager import ConfigManager
from plugins.florence2_reverse_plugin.core.proxy_manager import ProxyManager
from plugins.florence2_reverse_plugin.utils.file_utils import FileUtils
from plugins.florence2_reverse_plugin.utils.gpu_utils import GPUUtils

# 基于ComfyUI-Florence2的flash_attn绕过方法
def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
    """修复flash_attn导入问题"""
    try:
        from transformers.dynamic_module_utils import get_imports
        if not str(filename).endswith("modeling_florence2.py"):
            return get_imports(filename)
        imports = get_imports(filename)
        if "flash_attn" in imports:
            imports.remove("flash_attn")
        return imports
    except RecursionError:
        # 防止递归深度超出限制
        print("fixed_get_imports: 递归深度超出限制，返回空列表")
        return []
    except Exception as e:
        print(f"fixed_get_imports error: {str(e)}")
        # 如果出错，返回空列表避免无限循环
        return []


class ModelManager:
    """模型管理器，负责模型的查找、下载、加载和缓存"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 模型状态
        self.model = None
        self.processor = None
        self.model_loaded = False
        self.current_model_name = None
        self.current_model_path = None
        
        # 进度回调
        self.loading_progress_callback = None
        
        # 代理管理器
        self.proxy_manager = ProxyManager()
        
        # 模型缓存管理
        self.model_cache = {}  # 缓存已加载的模型
        self.cache_info = {}   # 缓存信息（加载时间、使用次数等）
        self.max_cache_size = 2  # 最大缓存模型数量
        self.cache_timeout = 3600  # 缓存超时时间（秒）
        
        # 初始化目录
        self._init_directories()
    
    def _init_directories(self):
        """初始化必要的目录"""
        try:
            # 插件模型目录
            self.plugin_models_dir = Path(__file__).parent.parent / "models"
            self.plugin_models_dir.mkdir(parents=True, exist_ok=True)
            
            # 缓存目录
            self.cache_dir = Path(__file__).parent.parent / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"模型目录初始化完成 - 插件目录: {self.plugin_models_dir}, 缓存目录: {self.cache_dir}")
            
        except Exception as e:
            self.logger.error(f"模型目录初始化失败: {str(e)}")
            raise
    
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，参数为 (step, progress, message)
                step: 步骤名称 ('finding', 'downloading', 'loading')
                progress: 进度百分比 (0-100)
                message: 详细消息
        """
        self.loading_progress_callback = callback
    
    def _update_progress(self, step: str, progress: int, message: str):
        """更新进度"""
        if self.loading_progress_callback:
            try:
                self.loading_progress_callback(step, progress, message)
            except Exception as e:
                self.logger.warning(f"进度回调执行失败: {str(e)}")
    
    def find_model(self, model_name: str, custom_path: Optional[str] = None) -> Optional[str]:
        """查找模型文件
        
        Args:
            model_name: 模型名称
            custom_path: 自定义路径
            
        Returns:
            模型路径，如果未找到返回None
        """
        try:
            self._update_progress("finding", 0, f"正在查找模型: {model_name}")
            
            # 1. 检查是否为绝对路径
            if os.path.isabs(model_name) or ':' in model_name:  # Windows路径包含冒号
                model_path = Path(model_name)
                if self._is_valid_model_directory(model_path):
                    self._update_progress("finding", 100, f"在绝对路径找到模型: {model_path}")
                    return str(model_path)
                else:
                    self._update_progress("finding", 100, f"绝对路径无效: {model_name}")
                    return None
            
            # 2. 检查自定义路径
            if custom_path:
                # 首先检查自定义路径是否直接指向模型目录
                custom_path_obj = Path(custom_path)
                if self._is_valid_model_directory(custom_path_obj):
                    self._update_progress("finding", 100, f"自定义路径直接指向有效模型: {custom_path}")
                    return str(custom_path_obj)
                
                # 如果不是，则在自定义路径下查找模型子目录
                custom_model_path = self._check_model_in_path(custom_path, model_name)
                if custom_model_path:
                    self._update_progress("finding", 100, f"在自定义路径找到模型: {custom_model_path}")
                    return str(custom_model_path)
            
            # 3. 检查插件models目录
            plugin_model_path = self._check_model_in_path(self.plugin_models_dir, model_name)
            if plugin_model_path:
                self._update_progress("finding", 100, f"在插件目录找到模型: {plugin_model_path}")
                return str(plugin_model_path)
            
            # 4. 检查HuggingFace缓存
            hf_cache_path = self._check_huggingface_cache(model_name)
            if hf_cache_path:
                self._update_progress("finding", 100, f"在HuggingFace缓存找到模型: {hf_cache_path}")
                return str(hf_cache_path)
            
            self._update_progress("finding", 100, f"未找到模型: {model_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"查找模型失败 {model_name}: {str(e)}")
            return None
    
    def _check_model_in_path(self, base_path: Path, model_name: str) -> Optional[Path]:
        """检查指定路径中是否存在模型"""
        try:
            # 尝试多种可能的模型目录名
            possible_names = [
                model_name.split('/')[-1],  # microsoft/florence2-base -> florence2-base
                model_name.replace('/', '_'),  # microsoft/florence2-base -> microsoft_florence2-base
                model_name.replace('/', '-'),  # microsoft/florence2-base -> microsoft-florence2-base
            ]
            
            for name in possible_names:
                model_path = base_path / name
                if self._is_valid_model_directory(model_path):
                    return model_path
            
            return None
            
        except Exception as e:
            self.logger.warning(f"检查模型路径失败 {base_path} {model_name}: {str(e)}")
            return None
    
    def _is_valid_model_directory(self, model_path: Path) -> bool:
        """检查是否为有效的模型目录"""
        try:
            if not model_path.is_dir():
                return False
            
            # 检查必要的文件
            required_files = ['config.json']
            model_files = ['pytorch_model.bin', 'model.safetensors', 'pytorch_model.bin.index.json', 'model.safetensors.index.json']
            
            # 必须存在config.json
            if not (model_path / 'config.json').exists():
                return False
            
            # 检查是否有模型文件（支持多种格式）
            has_model_file = False
            
            # 检查完整的模型文件
            if (model_path / 'pytorch_model.bin').exists() or (model_path / 'model.safetensors').exists():
                has_model_file = True
            # 检查分片模型文件
            elif (model_path / 'pytorch_model.bin.index.json').exists() or (model_path / 'model.safetensors.index.json').exists():
                # 检查是否有对应的分片文件
                for file in model_path.glob('pytorch_model-*.bin'):
                    if file.exists():
                        has_model_file = True
                        break
                for file in model_path.glob('model-*.safetensors'):
                    if file.exists():
                        has_model_file = True
                        break
            
            return has_model_file
            
        except Exception as e:
            self.logger.warning(f"检查模型目录有效性失败: {str(e)}")
            return False
    
    def _check_huggingface_cache(self, model_name: str) -> Optional[Path]:
        """检查HuggingFace缓存"""
        try:
            from transformers import file_utils
            
            # 获取HuggingFace缓存目录
            cache_dir = file_utils.default_cache_path
            
            # 计算模型缓存路径
            model_hash = hashlib.md5(model_name.encode()).hexdigest()
            model_dir_name = "models--" + model_name.replace('/', '--')
            cache_path = Path(cache_dir) / model_dir_name / "snapshots" / model_hash
            
            if self._is_valid_model_directory(cache_path):
                return cache_path
            
            return None
            
        except Exception as e:
            self.logger.warning(f"检查HuggingFace缓存失败 {model_name}: {str(e)}")
            return None
    
    def download_model(self, model_name: str, target_path: Optional[str] = None) -> bool:
        """下载模型
        
        Args:
            model_name: 模型名称
            target_path: 目标路径，如果为None则使用插件默认路径
            
        Returns:
            下载是否成功
        """
        try:
            if target_path is None:
                target_path = str(self.plugin_models_dir / model_name.split('/')[-1])
            
            target_dir = Path(target_path)
            
            # 检查模型是否已经存在且有效
            if target_dir.exists() and self._is_valid_model_directory(target_dir):
                self.logger.info(f"模型已存在且有效，跳过下载: {target_path}")
                self._update_progress("downloading", 100, f"模型已存在: {target_path}")
                return True
            
            # 如果目录存在但模型无效，删除目录重新下载
            if target_dir.exists():
                self.logger.info(f"删除无效的模型目录: {target_path}")
                import shutil
                shutil.rmtree(target_dir)
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            self._update_progress("downloading", 0, f"开始下载模型: {model_name}")
            
            # 应用代理设置
            self.proxy_manager.apply_proxy_to_environment()
            
            # 使用huggingface_hub.snapshot_download直接下载模型文件，避免flash_attn检查
            from huggingface_hub import snapshot_download
            
            self.logger.info(f"开始下载模型 - 模型名称: {model_name}, 目标路径: {target_path}")
            
            # 直接下载模型文件
            snapshot_download(
                repo_id=model_name,
                local_dir=target_path,
                local_dir_use_symlinks=False
            )
            
            # 验证下载的模型是否有效
            if not self._is_valid_model_directory(target_dir):
                self.logger.error(f"下载的模型无效: {target_path}")
                self._update_progress("downloading", 0, f"下载的模型无效: {target_path}")
                return False
            
            self._update_progress("downloading", 100, f"模型下载完成: {target_path}")
            self.logger.info(f"模型下载完成 - 模型名称: {model_name}, 目标路径: {target_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"模型下载失败 {model_name}: {str(e)}")
            self._update_progress("downloading", 0, f"下载失败: {str(e)}")
            return False
    
    def load_model(self, model_name: str, custom_path: Optional[str] = None, use_cache: bool = True) -> bool:
        """加载模型（用户确认后调用）
        
        Args:
            model_name: 模型名称
            custom_path: 自定义模型路径
            use_cache: 是否使用缓存
            
        Returns:
            加载是否成功
        """
        try:
            self._update_progress("loading", 0, f"开始加载模型: {model_name}")
            
            # 1. 检查缓存
            if use_cache:
                cached_model = self.get_cached_model(model_name)
                if cached_model:
                    self.model = cached_model['model']
                    self.processor = cached_model['processor']
                    self.model_loaded = True
                    self.current_model_name = model_name
                    self.current_model_path = cached_model.get('path', 'cached')
                    
                    self._update_progress("loading", 100, f"从缓存加载模型完成: {model_name}")
                    self.logger.info(f"从缓存加载模型完成: {model_name}")
                    return True
            
            # 2. 查找模型
            model_path = self.find_model(model_name, custom_path)
            
            if model_path is None:
                # 3. 如果不存在则下载
                self._update_progress("loading", 10, "模型不存在，开始下载...")
                if not self.download_model(model_name, custom_path):
                    return False
                
                # 重新查找下载的模型
                model_path = self.find_model(model_name, custom_path)
                if model_path is None:
                    raise RuntimeError("模型下载后仍无法找到")
            
            # 4. 加载模型到GPU/CPU
            self._update_progress("loading", 50, "加载模型文件...")
            
            from transformers import AutoModelForCausalLM, AutoProcessor
            
            # 检查GPU可用性
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"使用设备: {device}")
            
            # 根据模型类型选择不同的加载方式
            if "Florence" in model_path:
                # Florence2模型 - 使用monkey patch绕过flash_attn检查
                self.logger.info("加载Florence2模型，使用monkey patch绕过flash_attn")
                
                # 临时修改transformers的导入检查机制
                import transformers
                original_imports = transformers.dynamic_module_utils.get_imports
                
                def safe_get_imports(filename):
                    """安全的导入检查，跳过flash_attn"""
                    try:
                        imports = original_imports(filename)
                        if "flash_attn" in imports:
                            imports.remove("flash_attn")
                        return imports
                    except:
                        return original_imports(filename)
                
                # 应用monkey patch
                transformers.dynamic_module_utils.get_imports = safe_get_imports
                
                try:
                    # 使用ComfyUI-Florence2的方法：对于transformers < 4.51.0，使用attn_implementation参数
                    from unittest.mock import patch
                    
                    with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports):
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            attn_implementation="eager",  # 使用eager实现避免_supports_sdpa问题
                            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                            trust_remote_code=True,
                            low_cpu_mem_usage=True,
                        ).to(device)
                finally:
                    # 恢复原始函数
                    transformers.dynamic_module_utils.get_imports = original_imports
            elif "git" in model_path.lower():
                # GIT模型
                from transformers import GitForCausalLM
                self.model = GitForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True
                )
                # 手动将模型移动到GPU
                if device == "cuda":
                    self.model = self.model.to("cuda")
            else:
                # 其他模型（如ViT-GPT2）
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map="auto" if device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
            
            # 加载处理器
            if "blip" in model_path.lower():
                # BLIP-2模型使用Blip2Processor
                from transformers import Blip2Processor
                self.processor = Blip2Processor.from_pretrained(model_path)
            elif "git" in model_path.lower():
                # GIT模型使用GitProcessor
                from transformers import GitProcessor
                self.processor = GitProcessor.from_pretrained(model_path)
            elif "Florence" in model_path:
                # Florence2模型处理器 - 使用monkey patch绕过flash_attn检查
                import transformers
                original_imports = transformers.dynamic_module_utils.get_imports
                
                def safe_get_imports(filename):
                    """安全的导入检查，跳过flash_attn"""
                    try:
                        imports = original_imports(filename)
                        if "flash_attn" in imports:
                            imports.remove("flash_attn")
                        return imports
                    except:
                        return original_imports(filename)
                
                # 应用monkey patch
                transformers.dynamic_module_utils.get_imports = safe_get_imports
                
                try:
                    # Florence2模型使用AutoProcessor
                    self.processor = AutoProcessor.from_pretrained(
                        model_path,
                        trust_remote_code=True
                    )
                finally:
                    # 恢复原始函数
                    transformers.dynamic_module_utils.get_imports = original_imports
            else:
                # 其他模型使用AutoProcessor
                self.processor = AutoProcessor.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
            
            # 5. 设置模型为可用状态
            self.model_loaded = True
            self.current_model_name = model_name
            self.current_model_path = str(model_path)
            
            # 6. 添加到缓存
            if use_cache:
                model_data = {
                    'model': self.model,
                    'processor': self.processor,
                    'path': str(model_path)
                }
                self.add_to_cache(model_name, model_data)
            
            self._update_progress("loading", 100, f"模型加载完成: {model_name}")
            self.logger.info(f"模型加载完成 - 模型名称: {model_name}, 路径: {model_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"模型加载失败 {model_name}: {str(e)}")
            self._update_progress("loading", 0, f"加载失败: {str(e)}")
            return False
    
    def unload_model(self):
        """卸载模型释放内存"""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.processor is not None:
                del self.processor
                self.processor = None
            
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.model_loaded = False
            self.current_model_name = None
            self.current_model_path = None
            
            self.logger.info("模型已卸载")
            
        except Exception as e:
            self.logger.error(f"模型卸载失败: {str(e)}")
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model_loaded
    
    def get_loaded_model_info(self) -> Optional[Dict[str, Any]]:
        """获取已加载模型的信息"""
        if not self.model_loaded:
            return None
        
        return {
            'name': self.current_model_name,
            'path': self.current_model_path,
            'device': str(next(self.model.parameters()).device) if self.model else 'unknown',
            'loaded_at': datetime.now().isoformat()
        }
    
    def get_available_models(self) -> list:
        """获取可用模型列表"""
        try:
            models = []
            
            # 扫描插件models目录
            if self.plugin_models_dir.exists():
                for model_dir in self.plugin_models_dir.iterdir():
                    if model_dir.is_dir() and self._is_valid_model_directory(model_dir):
                        models.append({
                            'name': model_dir.name,
                            'path': str(model_dir),
                            'type': 'local'
                        })
            
            # 扫描HuggingFace缓存
            try:
                from transformers import file_utils
                cache_dir = file_utils.default_cache_path
                cache_path = Path(cache_dir)
                
                if cache_path.exists():
                    for model_dir in cache_path.glob("models--*"):
                        if model_dir.is_dir():
                            # 提取模型名称
                            model_name = model_dir.name.replace("models--", "").replace("--", "/")
                            models.append({
                                'name': model_name,
                                'path': str(model_dir),
                                'type': 'cache'
                            })
            except Exception as e:
                self.logger.warning(f"扫描HuggingFace缓存失败: {str(e)}")
            
            return models
            
        except Exception as e:
            self.logger.error(f"获取可用模型列表失败: {str(e)}")
            return []
    
    def get_model_size(self, model_path: str) -> Optional[str]:
        """获取模型大小"""
        try:
            model_dir = Path(model_path)
            if not model_dir.exists():
                return None
            
            total_size = 0
            file_count = 0
            
            for file_path in model_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            # 转换为可读格式
            if total_size < 1024:
                return f"{total_size} B"
            elif total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                return f"{total_size / (1024 * 1024):.1f} MB"
            else:
                return f"{total_size / (1024 * 1024 * 1024):.1f} GB"
                
        except Exception as e:
            self.logger.warning(f"获取模型大小失败 {model_path}: {str(e)}")
            return None
    
    # ==================== 缓存管理方法 ====================
    
    def get_cached_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的模型"""
        try:
            if model_name in self.model_cache:
                cache_info = self.cache_info.get(model_name, {})
                
                # 检查缓存是否过期
                if self._is_cache_expired(cache_info):
                    self.logger.info(f"缓存已过期，移除模型: {model_name}")
                    self._remove_from_cache(model_name)
                    return None
                
                # 更新使用次数和时间
                self._update_cache_info(model_name)
                
                self.logger.info(f"使用缓存模型: {model_name}")
                return self.model_cache[model_name]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取缓存模型失败: {str(e)}")
            return None
    
    def add_to_cache(self, model_name: str, model_data: Dict[str, Any]):
        """添加模型到缓存"""
        try:
            # 检查缓存大小，如果超出限制则清理
            if len(self.model_cache) >= self.max_cache_size:
                self._cleanup_cache()
            
            # 添加到缓存
            self.model_cache[model_name] = model_data
            self.cache_info[model_name] = {
                'loaded_at': datetime.now(),
                'use_count': 0,
                'last_used': datetime.now()
            }
            
            self.logger.info(f"模型已添加到缓存: {model_name}")
            
        except Exception as e:
            self.logger.error(f"添加模型到缓存失败: {str(e)}")
    
    def _remove_from_cache(self, model_name: str):
        """从缓存中移除模型"""
        try:
            if model_name in self.model_cache:
                # 清理模型内存
                model_data = self.model_cache[model_name]
                if 'model' in model_data:
                    del model_data['model']
                if 'processor' in model_data:
                    del model_data['processor']
                
                # 从缓存中移除
                del self.model_cache[model_name]
                if model_name in self.cache_info:
                    del self.cache_info[model_name]
                
                # 清理GPU缓存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                self.logger.info(f"模型已从缓存移除: {model_name}")
            
        except Exception as e:
            self.logger.error(f"从缓存移除模型失败: {str(e)}")
    
    def _update_cache_info(self, model_name: str):
        """更新缓存信息"""
        try:
            if model_name in self.cache_info:
                self.cache_info[model_name]['use_count'] += 1
                self.cache_info[model_name]['last_used'] = datetime.now()
        except Exception as e:
            self.logger.warning(f"更新缓存信息失败: {str(e)}")
    
    def _is_cache_expired(self, cache_info: Dict[str, Any]) -> bool:
        """检查缓存是否过期"""
        try:
            if not cache_info or 'loaded_at' not in cache_info:
                return True
            
            loaded_time = cache_info['loaded_at']
            if isinstance(loaded_time, str):
                loaded_time = datetime.fromisoformat(loaded_time)
            
            elapsed = (datetime.now() - loaded_time).total_seconds()
            return elapsed > self.cache_timeout
            
        except Exception as e:
            self.logger.warning(f"检查缓存过期失败: {str(e)}")
            return True
    
    def _cleanup_cache(self):
        """清理缓存"""
        try:
            if not self.model_cache:
                return
            
            # 按使用次数和最后使用时间排序
            cache_items = []
            for model_name, cache_info in self.cache_info.items():
                cache_items.append({
                    'name': model_name,
                    'use_count': cache_info.get('use_count', 0),
                    'last_used': cache_info.get('last_used', datetime.now())
                })
            
            # 按使用次数降序，然后按最后使用时间升序排序
            cache_items.sort(key=lambda x: (-x['use_count'], x['last_used']))
            
            # 移除最少使用的模型
            while len(self.model_cache) >= self.max_cache_size and cache_items:
                least_used = cache_items.pop()
                self._remove_from_cache(least_used['name'])
            
            self.logger.info("缓存清理完成")
            
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}")
    
    def clear_all_cache(self):
        """清除所有缓存"""
        try:
            model_names = list(self.model_cache.keys())
            for model_name in model_names:
                self._remove_from_cache(model_name)
            
            self.logger.info("所有模型缓存已清除")
            
        except Exception as e:
            self.logger.error(f"清除所有缓存失败: {str(e)}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            cache_stats = {
                'total_models': len(self.model_cache),
                'max_cache_size': self.max_cache_size,
                'cache_timeout': self.cache_timeout,
                'cached_models': {}
            }
            
            for model_name, cache_info in self.cache_info.items():
                cache_stats['cached_models'][model_name] = {
                    'loaded_at': cache_info.get('loaded_at', 'unknown'),
                    'use_count': cache_info.get('use_count', 0),
                    'last_used': cache_info.get('last_used', 'unknown'),
                    'is_expired': self._is_cache_expired(cache_info)
                }
            
            return cache_stats
            
        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {str(e)}")
            return {} 