"""
JoyCaption插件模型管理器
负责模型下载、加载和管理
"""

import os
import logging
import torch
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from huggingface_hub import snapshot_download, hf_hub_download
from transformers import AutoProcessor, LlavaForConditionalGeneration, BitsAndBytesConfig

try:
    from .proxy_manager import ProxyManager
except ImportError:
    ProxyManager = None


class ModelManager:
    """JoyCaption模型管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.plugin_dir = Path(__file__).parent.parent
        self.models_dir = self.plugin_dir / "models"
        self.cache_dir = self.plugin_dir / "cache"
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.core.model_manager")
        
        # 初始化代理管理器
        self.proxy_manager = ProxyManager() if ProxyManager else None
        
        # 确保目录存在
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型缓存
        self.loaded_models = {}
        self.model_info = {}
        
        self.logger.info(f"模型目录初始化完成 - 插件目录: {self.plugin_dir}, 缓存目录: {self.cache_dir}")
    
    def get_model_path(self, model_id: str) -> Path:
        """获取模型路径"""
        # 从模型ID中提取模型名称
        model_name = model_id.split('/')[-1]
        return self.models_dir / model_name
    
    def find_local_model(self, model_id: str, custom_paths: List[str] = None) -> Optional[Path]:
        """在本地目录中查找模型"""
        try:
            # 获取模型名称
            model_name = model_id.split('/')[-1]
            
            # 1. 首先检查用户指定的本地模型路径
            if custom_paths:
                for custom_path in custom_paths:
                    potential_path = Path(custom_path)
                    if potential_path.exists() and potential_path.is_dir():
                        # 检查是否包含必要的模型文件
                        if self._is_valid_model_directory(potential_path):
                            self.logger.info(f"在用户指定路径找到模型: {potential_path}")
                            return potential_path
            
            # 2. 检查插件目录下的models目录
            plugin_model_path = self.models_dir / model_name
            if plugin_model_path.exists() and plugin_model_path.is_dir():
                if self._is_valid_model_directory(plugin_model_path):
                    self.logger.info(f"在插件目录找到模型: {plugin_model_path}")
                    return plugin_model_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"查找本地模型失败 {model_id}: {str(e)}")
            return None
    
    def _is_valid_model_directory(self, path: Path) -> bool:
        """检查目录是否是有效的模型目录"""
        try:
            # 检查必要文件
            required_files = ["config.json"]
            if not all((path / file).exists() for file in required_files):
                return False
            
            # 检查可选文件（至少需要一个模型权重文件）
            optional_files = [
                "pytorch_model.bin",  # PyTorch格式
                "model.safetensors",  # SafeTensors格式（单个文件）
                "model.safetensors.index.json",  # SafeTensors格式（分片文件）
                "model-00001-of-00004.safetensors",  # SafeTensors分片格式
                "model-00001-of-00002.safetensors",  # SafeTensors分片格式
                "model-00001-of-00003.safetensors",  # SafeTensors分片格式
                "model-00001-of-00005.safetensors",  # SafeTensors分片格式
                "model-00001-of-00006.safetensors",  # SafeTensors分片格式
                "model-00001-of-00007.safetensors",  # SafeTensors分片格式
                "model-00001-of-00008.safetensors",  # SafeTensors分片格式
            ]
            
            for file in optional_files:
                if (path / file).exists():
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查模型目录有效性失败 {path}: {str(e)}")
            return False
            
            for search_path in search_paths:
                # 处理相对路径
                if search_path.startswith('./'):
                    search_path = str(self.plugin_dir / search_path[2:])
                elif search_path.startswith('../'):
                    search_path = str(self.plugin_dir.parent / search_path[3:])
                
                potential_path = Path(search_path)
                if potential_path.exists() and potential_path.is_dir():
                    # 检查是否包含必要的模型文件
                    required_files = ["config.json"]
                    
                    # 检查可选文件（至少需要一个模型权重文件）
                    optional_files = [
                        "pytorch_model.bin",  # PyTorch格式
                        "model.safetensors",  # SafeTensors格式（单个文件）
                        "model.safetensors.index.json",  # SafeTensors格式（分片文件）
                        "model-00001-of-00004.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00002.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00003.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00005.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00006.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00007.safetensors",  # SafeTensors分片格式
                        "model-00001-of-00008.safetensors",  # SafeTensors分片格式
                    ]
                    
                    # 检查必要文件
                    if not all((potential_path / file).exists() for file in required_files):
                        continue
                    
                    # 检查可选文件（至少需要一个模型权重文件）
                    has_model_file = False
                    for file in optional_files:
                        if (potential_path / file).exists():
                            has_model_file = True
                            break
                    
                    if has_model_file:
                        self.logger.info(f"在本地找到模型: {potential_path}")
                        return potential_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"查找本地模型失败 {model_id}: {str(e)}")
            return None
    
    def copy_local_model(self, source_path: Path, model_id: str) -> bool:
        """复制本地模型到插件目录"""
        try:
            target_path = self.get_model_path(model_id)
            
            # 如果目标目录已存在，先删除
            if target_path.exists():
                shutil.rmtree(target_path)
            
            # 复制模型文件
            shutil.copytree(source_path, target_path)
            
            self.logger.info(f"本地模型复制成功: {source_path} -> {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"复制本地模型失败: {str(e)}")
            return False
    
    def is_model_downloaded(self, model_id: str, custom_paths: List[str] = None) -> bool:
        """检查模型是否已下载或本地可用"""
        try:
            # 1. 首先检查本地模型路径（用户指定路径或插件目录）
            local_model_path = self.find_local_model(model_id, custom_paths)
            if local_model_path:
                self.logger.info(f"找到本地模型: {local_model_path}")
                return True
            
            # 2. 如果本地没有找到，检查插件目录下的模型
            model_path = self.get_model_path(model_id)
            if model_path.exists() and model_path.is_dir():
                if self._is_valid_model_directory(model_path):
                    self.logger.info(f"在插件目录找到模型: {model_path}")
                    return True
            
            # 3. 都没有找到，需要下载
            self.logger.info(f"模型未找到，需要下载: {model_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"检查模型下载状态失败 {model_id}: {str(e)}")
            return False
    
    def download_model(self, model_id: str, progress_callback=None) -> bool:
        """下载模型"""
        try:
            self.logger.info(f"开始下载模型: {model_id}")
            
            # 设置代理环境变量
            if self.proxy_manager:
                self.proxy_manager.set_proxy_environment()
                
                # 测试代理连接
                if not self.proxy_manager.test_proxy_connection():
                    self.logger.warning("代理连接测试失败，尝试直接连接")
            
            model_path = self.get_model_path(model_id)
            
            # 如果模型已存在，跳过下载
            if self.is_model_downloaded(model_id):
                self.logger.info(f"模型已存在，跳过下载: {model_id}")
                return True
            
            # 创建模型目录
            model_path.mkdir(parents=True, exist_ok=True)
            
            # 设置huggingface_hub的代理
            import os
            proxy_config = self.proxy_manager.get_proxy_config() if self.proxy_manager else {}
            
            # 设置环境变量
            if proxy_config:
                for protocol, proxy_url in proxy_config.items():
                    os.environ[f"{protocol.upper()}_PROXY"] = proxy_url
                    os.environ[f"{protocol}_proxy"] = proxy_url
                self.logger.info(f"设置huggingface_hub代理: {proxy_config}")
            
            # 下载模型
            snapshot_download(
                repo_id=model_id,
                local_dir=str(model_path),
                local_dir_use_symlinks=False,
                resume_download=True
            )
            
            self.logger.info(f"模型下载完成: {model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"模型下载失败 {model_id}: {str(e)}")
            return False
    
    def load_model(self, model_id: str, precision: str = "Balanced (8-bit)", custom_paths: List[str] = None) -> Optional[Dict[str, Any]]:
        """加载模型"""
        try:
            # 检查模型是否已加载
            cache_key = f"{model_id}_{precision}"
            if cache_key in self.loaded_models:
                self.logger.info(f"模型已加载，使用缓存: {model_id}")
                return self.loaded_models[cache_key]
            
            # 检查模型是否已下载或本地可用
            if not self.is_model_downloaded(model_id, custom_paths):
                self.logger.error(f"模型未下载或本地不可用: {model_id}")
                return None
            
            # 获取模型路径（优先使用本地路径）
            local_model_path = self.find_local_model(model_id, custom_paths)
            if local_model_path:
                model_path = local_model_path
                self.logger.info(f"使用本地模型路径: {model_path}")
            else:
                model_path = self.get_model_path(model_id)
                self.logger.info(f"使用插件目录模型路径: {model_path}")
            self.logger.info(f"开始加载模型: {model_id}, 精度: {precision}")
            
            # 设置设备
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 加载处理器 - 尝试多种方法
            processor = None
            load_methods = [
                # 方法1: 使用快速分词器
                lambda: AutoProcessor.from_pretrained(
                    str(model_path),
                    use_fast=True,
                    trust_remote_code=True
                ),
                # 方法2: 使用慢速分词器
                lambda: AutoProcessor.from_pretrained(
                    str(model_path),
                    use_fast=False,
                    trust_remote_code=True
                ),
                # 方法3: 不指定use_fast参数
                lambda: AutoProcessor.from_pretrained(
                    str(model_path),
                    trust_remote_code=True
                ),
                # 方法4: 使用transformers的默认设置
                lambda: AutoProcessor.from_pretrained(str(model_path))
            ]
            
            for i, load_method in enumerate(load_methods):
                try:
                    self.logger.info(f"尝试加载处理器方法 {i+1}")
                    processor = load_method()
                    self.logger.info(f"处理器加载成功，使用方法 {i+1}")
                    break
                except Exception as e:
                    self.logger.warning(f"处理器加载方法 {i+1} 失败: {str(e)}")
                    continue
            
            if processor is None:
                self.logger.error("所有处理器加载方法都失败了")
                return None
            
            # 根据精度模式加载模型
            model = None
            model_load_methods = [
                # 方法1: 使用trust_remote_code
                lambda: LlavaForConditionalGeneration.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                ),
                # 方法2: 不使用trust_remote_code
                lambda: LlavaForConditionalGeneration.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.float16,
                    device_map="auto"
                ),
                # 方法3: 使用默认设置
                lambda: LlavaForConditionalGeneration.from_pretrained(str(model_path))
            ]
            
            for i, load_method in enumerate(model_load_methods):
                try:
                    self.logger.info(f"尝试加载模型方法 {i+1}")
                    model = load_method()
                    self.logger.info(f"模型加载成功，使用方法 {i+1}")
                    break
                except Exception as e:
                    self.logger.warning(f"模型加载方法 {i+1} 失败: {str(e)}")
                    continue
            
            if model is None:
                self.logger.error("所有模型加载方法都失败了")
                return None
            
            # 设置为评估模式
            model.eval()
            
            # 缓存模型
            model_info = {
                "model": model,
                "processor": processor,
                "device": device,
                "precision": precision,
                "model_id": model_id
            }
            
            self.loaded_models[cache_key] = model_info
            self.logger.info(f"模型加载完成: {model_id}, 精度: {precision}")
            
            return model_info
            
        except Exception as e:
            self.logger.error(f"模型加载失败 {model_id}: {str(e)}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def unload_model(self, model_id: str, precision: str = "Balanced (8-bit)"):
        """卸载模型"""
        try:
            cache_key = f"{model_id}_{precision}"
            if cache_key in self.loaded_models:
                model_info = self.loaded_models[cache_key]
                
                # 清理模型内存
                if "model" in model_info:
                    del model_info["model"]
                
                if "processor" in model_info:
                    del model_info["processor"]
                
                # 从缓存中移除
                del self.loaded_models[cache_key]
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                self.logger.info(f"模型已卸载: {model_id}")
                
        except Exception as e:
            self.logger.error(f"模型卸载失败 {model_id}: {str(e)}")
    
    def get_loaded_models(self) -> List[str]:
        """获取已加载的模型列表"""
        return list(self.loaded_models.keys())
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        return self.config_manager.get_model_config(model_id)
    
    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        return self.config_manager.get_available_models()
    
    def check_model_status(self, model_id: str) -> Dict[str, Any]:
        """检查模型状态"""
        model_path = self.get_model_path(model_id)
        model_info = self.get_model_info(model_id)
        
        status = {
            "model_id": model_id,
            "downloaded": self.is_model_downloaded(model_id),
            "path": str(model_path),
            "size": "未知",
            "local_found": False
        }
        
        if model_info:
            status.update({
                "name": model_info.get("name", model_id),
                "description": model_info.get("description", ""),
                "size": model_info.get("size", "未知"),
                "recommended": model_info.get("recommended", False),
                "file_structure": model_info.get("file_structure", {}),
                "local_search_paths": model_info.get("local_search_paths", [])
            })
        
        # 检查本地模型
        local_path = self.find_local_model(model_id)
        if local_path:
            status["local_found"] = True
            status["local_path"] = str(local_path)
        
        if status["downloaded"] and model_path.exists():
            try:
                # 计算实际文件大小
                total_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
                status["actual_size"] = f"{total_size / (1024**3):.2f}GB"
            except Exception as e:
                self.logger.warning(f"计算模型大小失败: {str(e)}")
        
        return status
    
    def cleanup_cache(self):
        """清理缓存"""
        try:
            # 卸载所有已加载的模型
            for cache_key in list(self.loaded_models.keys()):
                model_id, precision = cache_key.rsplit('_', 1)
                self.unload_model(model_id, precision)
            
            self.logger.info("模型缓存清理完成")
            
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}")
    
    def get_model_size(self, model_id: str) -> str:
        """获取模型大小"""
        model_info = self.get_model_info(model_id)
        if model_info:
            return model_info.get("size", "未知")
        return "未知"
    
    def validate_model(self, model_id: str) -> bool:
        """验证模型完整性"""
        try:
            if not self.is_model_downloaded(model_id):
                return False
            
            model_path = self.get_model_path(model_id)
            
            # 检查关键文件是否存在
            required_files = [
                "config.json",
                "pytorch_model.bin",
                "tokenizer.json",
                "tokenizer_config.json"
            ]
            
            for file_name in required_files:
                if not (model_path / file_name).exists():
                    self.logger.warning(f"模型文件缺失: {file_name}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"模型验证失败 {model_id}: {str(e)}")
            return False 