"""
Janus插件下载管理器 - 增强版本
参照Florence2插件的优化方式进行改进
"""

import os
import logging
import requests
import time
import hashlib
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import torch
from transformers import AutoModelForCausalLM
from huggingface_hub import snapshot_download, hf_hub_download, HfApi, list_repo_files
import concurrent.futures


class DownloadManager:
    """Janus插件下载管理器 - 增强版本"""
    
    def __init__(self, config_manager):
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.core.download_manager")
        self.config_manager = config_manager
        self.plugin_dir = Path(__file__).parent.parent
        self.models_dir = self.config_manager.get_models_directory()
        
        # 确保目录存在
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载临时目录
        self.temp_dir = self.plugin_dir / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载配置 - 参照Florence2优化
        self.download_chunk_size = 8192  # 8KB chunks
        self.download_cancelled = False  # 下载取消标志
        self.download_sessions = {}  # 下载会话信息
        
        # 进度回调
        self.progress_callback = None
        
        self.logger.info(f"Janus下载管理器初始化完成 - 模型目录: {self.models_dir}, 临时目录: {self.temp_dir}")
    
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def cancel_download(self):
        """取消当前下载"""
        self.download_cancelled = True
        self.logger.info("用户请求取消下载")
    
    def reset_download_state(self):
        """重置下载状态"""
        self.download_cancelled = False
    
    def _update_progress(self, step: str, progress: int, message: str, speed: str = ""):
        """更新进度显示"""
        # 统一在日志中输出当前工作进程
        try:
            full_message = f"[{step}] {message}{(' - ' + speed) if speed else ''} ({progress}%)"
            self.logger.info(full_message)
        except Exception:
            pass
        # UI/外部回调
        if self.progress_callback:
            try:
                self.progress_callback(step, progress, message if not speed else f"{message} - {speed}")
            except Exception as e:
                self.logger.warning(f"进度回调执行失败: {str(e)}")
    
    def _format_speed(self, bytes_per_second: float) -> str:
        """格式化下载速度"""
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.1f} B/s"
        elif bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
    
    def _format_size(self, bytes_size: int) -> str:
        """格式化文件大小"""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _download_file_with_resume(self, url: str, file_path: Path, progress_callback=None) -> bool:
        """带断点续传的文件下载"""
        try:
            # 创建目录
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查是否存在部分下载的文件
            temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
            resume_pos = 0
            
            if temp_path.exists():
                resume_pos = temp_path.stat().st_size
                self.logger.info(f"发现部分下载文件，从 {self._format_size(resume_pos)} 处继续下载")
            
            # 设置请求头
            headers = {}
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
            
            # 发送请求
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            if 'content-range' in response.headers:
                total_size = int(response.headers['content-range'].split('/')[-1])
            elif 'content-length' in response.headers:
                total_size = int(response.headers['content-length'])
            else:
                total_size = 0
            
            # 打开文件进行写入
            mode = 'ab' if resume_pos > 0 else 'wb'
            with open(temp_path, mode) as f:
                downloaded = resume_pos
                start_time = time.time()
                last_update_time = start_time
                
                for chunk in response.iter_content(chunk_size=self.download_chunk_size):
                    # 检查是否取消下载
                    if self.download_cancelled:
                        self.logger.info("下载被用户取消")
                        return False
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新进度（每秒最多更新一次）
                        current_time = time.time()
                        if current_time - last_update_time >= 1.0:
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                speed = (downloaded - resume_pos) / (current_time - start_time)
                                speed_str = self._format_speed(speed)
                                message = f"下载中: {self._format_size(downloaded)}/{self._format_size(total_size)}"
                                
                                if progress_callback:
                                    progress_callback("downloading", progress, message, speed_str)
                            
                            last_update_time = current_time
            
            # 重命名临时文件
            if file_path.exists():
                file_path.unlink()
            temp_path.rename(file_path)
            
            self.logger.info(f"文件下载完成: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"文件下载失败 {url}: {str(e)}")
            return False
    
    def _download_model_files(self, model_id: str, target_dir: Path, progress_callback=None) -> bool:
        """下载模型文件"""
        try:
            # 获取模型文件列表
            self._update_progress("downloading", 5, f"获取模型文件列表: {model_id}")
            files = list_repo_files(model_id)
            
            if not files:
                self.logger.error(f"无法获取模型文件列表: {model_id}")
                return False
            
            # 仅保留必要文件，排除README、图片等非关键文件，避免网络抖动导致失败
            allowed_exts = {'.bin', '.safetensors', '.json', '.py'}
            required_files = [f for f in files if any(f.endswith(ext) for ext in allowed_exts)]

            # 标记关键文件，关键文件失败则整体失败；非关键文件失败仅告警
            critical_files = {
                'config.json',
                'tokenizer.json',
                'tokenizer_config.json',
                'special_tokens_map.json',
                'preprocessor_config.json',
                'processor_config.json',
                'pytorch_model.bin',
                'model.safetensors',
                'pytorch_model.bin.index.json',
                'model.safetensors.index.json',
            }
            
            total_files = len(required_files)
            downloaded_files = 0
            
            self._update_progress("downloading", 10, f"开始下载 {total_files} 个文件")
            
            for file in required_files:
                try:
                    # 构建下载URL
                    file_url = f"https://huggingface.co/{model_id}/resolve/main/{file}"
                    file_path = target_dir / file
                    
                    # 创建子目录
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 下载文件
                    self._update_progress("downloading", 10 + int((downloaded_files / total_files) * 80), 
                                        f"下载文件: {file}")
                    
                    if self._download_file_with_resume(file_url, file_path, progress_callback):
                        downloaded_files += 1
                    else:
                        # 非关键文件失败仅记录并继续；关键文件失败则终止
                        if Path(file).name in critical_files:
                            self.logger.error(f"关键文件下载失败: {file}")
                            return False
                        else:
                            self.logger.warning(f"非关键文件下载失败，已跳过: {file}")
                        
                except Exception as e:
                    self.logger.error(f"下载文件失败 {file}: {str(e)}")
                    return False
            
            self._update_progress("downloading", 95, "下载完成，正在验证...")
            
            # 验证下载的文件
            if self._is_valid_model_directory(target_dir):
                self._update_progress("downloading", 100, "模型下载完成")
                return True
            else:
                self.logger.error(f"下载的模型无效: {target_dir}")
                return False
                
        except Exception as e:
            self.logger.error(f"模型文件下载失败 {model_id}: {str(e)}")
            return False
    
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
    
    def check_model_exists(self, model_id: str) -> bool:
        """检查模型是否已存在"""
        try:
            model_path = self.get_model_path(model_id)
            return self._is_valid_model_directory(model_path)
            
        except Exception as e:
            self.logger.error(f"检查模型存在性失败: {str(e)}")
            return False
    
    def get_model_path(self, model_id: str) -> Path:
        """获取模型路径"""
        model_name = model_id.split('/')[-1]
        return self.models_dir / model_name
    
    def download_model(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """下载模型（增强版）"""
        try:
            # 重置下载状态
            self.reset_download_state()
            
            self.logger.info(f"开始下载模型: {model_id}")
            
            # 检查模型是否已存在
            if self.check_model_exists(model_id):
                self.logger.info(f"模型已存在: {model_id}")
                self._update_progress("downloading", 100, f"模型已存在: {model_id}")
                return True
            
            # 获取模型信息
            model_info = self.config_manager.get_model_by_id(model_id)
            if not model_info:
                self.logger.error(f"未找到模型信息: {model_id}")
                return False
            
            model_path = self.get_model_path(model_id)
            
            # 如果目录存在但模型无效，删除目录重新下载
            if model_path.exists():
                self.logger.info(f"删除无效的模型目录: {model_path}")
                shutil.rmtree(model_path)
            
            model_path.mkdir(parents=True, exist_ok=True)
            
            self._update_progress("downloading", 0, f"开始下载模型: {model_id}")
            
            # 尝试使用增强的下载方法
            if self._download_model_files(model_id, model_path, progress_callback):
                return True
            
            # 如果增强下载失败，回退到原始方法（仅下载必要文件，忽略README等）
            self.logger.warning("增强下载失败，使用原始下载方法")
            self._update_progress("downloading", 0, f"使用原始方法下载模型: {model_id}")
            
            # 直接下载模型文件
            snapshot_download(
                repo_id=model_id,
                local_dir=str(model_path),
                local_dir_use_symlinks=False,
                resume_download=True,
                max_workers=8,
                ignore_patterns=["*.md", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.webp", "*.ipynb", "*.git*"],
                allow_patterns=["*.json", "*.bin", "*.safetensors", "*.model", "*.py"],
                tqdm_class=None,
            )
            
            # 验证下载的模型是否有效
            if not self._is_valid_model_directory(model_path):
                self.logger.error(f"下载的模型无效: {model_path}")
                self._update_progress("downloading", 0, f"下载的模型无效: {model_path}")
                return False
            
            self._update_progress("downloading", 100, f"模型下载完成: {model_path}")
            self.logger.info(f"模型下载完成 - 模型名称: {model_id}, 目标路径: {model_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"模型下载失败 {model_id}: {str(e)}")
            self._update_progress("downloading", 0, f"下载失败: {str(e)}")
            return False
    
    def download_model_with_progress(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """带进度显示的模型下载"""
        return self.download_model(model_id, progress_callback)
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        return self.config_manager.get_model_by_id(model_id)
    
    def get_download_size(self, model_id: str) -> str:
        """获取下载大小"""
        model_info = self.get_model_info(model_id)
        if model_info:
            return model_info.get("download_size", "未知")
        return "未知"
    
    def get_model_requirements(self, model_id: str) -> Dict[str, str]:
        """获取模型要求"""
        model_info = self.get_model_info(model_id)
        if model_info:
            return model_info.get("requirements", {})
        return {}
    
    def check_system_requirements(self, model_id: str) -> Dict[str, bool]:
        """检查系统要求"""
        requirements = self.get_model_requirements(model_id)
        results = {}
        
        # 检查内存
        if "min_memory" in requirements:
            try:
                import psutil
                memory_gb = psutil.virtual_memory().total / (1024**3)
                min_memory = float(requirements["min_memory"].replace("GB", ""))
                results["memory"] = memory_gb >= min_memory
            except ImportError:
                results["memory"] = True  # 无法检查时默认通过
        
        # 检查GPU
        if "gpu_memory" in requirements:
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                required_gpu = float(requirements["gpu_memory"].replace("GB", ""))
                results["gpu"] = gpu_memory >= required_gpu
            else:
                results["gpu"] = False
        
        # 检查磁盘空间
        model_info = self.get_model_info(model_id)
        if model_info and "download_size" in model_info:
            disk_usage = shutil.disk_usage(self.models_dir)
            free_space_gb = disk_usage.free / (1024**3)
            download_size_gb = float(model_info["download_size"].replace("GB", ""))
            results["disk"] = free_space_gb >= download_size_gb * 2  # 预留2倍空间
        
        return results
    
    def cleanup_download_cache(self):
        """清理下载缓存"""
        try:
            cache_dir = Path.home() / ".cache" / "huggingface"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                self.logger.info("下载缓存清理完成")
        except Exception as e:
            self.logger.error(f"清理下载缓存失败: {str(e)}")
    
    def get_download_progress(self, model_id: str) -> Dict[str, Any]:
        """获取下载进度"""
        model_path = self.get_model_path(model_id)
        
        if not model_path.exists():
            return {"status": "not_started", "progress": 0, "speed": "0 MB/s"}
        
        # 检查已下载的文件
        required_files = ["config.json", "pytorch_model.bin", "tokenizer.json"]
        downloaded_files = 0
        downloaded_size = 0
        
        for file in required_files:
            file_path = model_path / file
            if file_path.exists():
                downloaded_files += 1
                downloaded_size += file_path.stat().st_size
        
        progress = (downloaded_files / len(required_files)) * 100
        
        # 计算下载速度（如果有进度信息）
        speed = "0 MB/s"
        if hasattr(self, '_download_start_time') and hasattr(self, '_last_download_size'):
            if self._download_start_time:
                elapsed_time = time.time() - self._download_start_time
                if elapsed_time > 0:
                    speed_bytes = (downloaded_size - self._last_download_size) / elapsed_time
                    speed = f"{speed_bytes / (1024*1024):.1f} MB/s"
        
        if progress >= 100:
            return {"status": "completed", "progress": 100, "speed": speed}
        elif progress > 0:
            return {"status": "in_progress", "progress": progress, "speed": speed}
        else:
            return {"status": "not_started", "progress": 0, "speed": speed}