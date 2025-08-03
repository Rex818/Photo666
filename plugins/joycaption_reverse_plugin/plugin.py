"""
JoyCaption图片反推信息插件主类
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QThread, pyqtSignal

import sys
from pathlib import Path

# 添加PicMan源码目录到Python路径
src_dir = Path(__file__).parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from picman.plugins.base import Plugin, PluginInfo
except ImportError:
    # 如果无法导入，创建简单的基类
    class Plugin:
        def __init__(self):
            pass
        
        def get_info(self):
            pass
        
        def initialize(self, app_context):
            return True
        
        def shutdown(self):
            return True
    
    class PluginInfo:
        def __init__(self, name, version, description, author):
            self.name = name
            self.version = version
            self.description = description
            self.author = author

from .core.config_manager import ConfigManager
from .core.model_manager import ModelManager
from .core.inference_engine import InferenceEngine
from .core.result_processor import ResultProcessor
from .ui.config_dialog import JoyCaptionConfigDialog
from .ui.progress_dialog import JoyCaptionProgressDialog


class JoyCaptionReversePlugin(Plugin):
    """JoyCaption图片反推信息插件"""
    
    def __init__(self):
        super().__init__()
        # 设置日志
        self.setup_logging()
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin")
        
        # 初始化组件
        self.config_manager = ConfigManager()
        self.model_manager = ModelManager(self.config_manager)
        self.inference_engine = InferenceEngine()
        self.result_processor = ResultProcessor(self.config_manager)
        
        # 状态变量
        self.is_initialized = False
        self.current_model_info = None
        
        self.logger.info("JoyCaption插件实例创建")
    
    def setup_logging(self):
        """设置日志系统"""
        try:
            # 创建日志目录
            log_dir = Path(__file__).parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 配置日志
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "joycaption_plugin.log", encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            
        except Exception as e:
            print(f"设置日志系统失败: {str(e)}")
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name="JoyCaption图片反推信息插件",
            version="1.0.0",
            description="基于JoyCaption模型的AI图片描述生成工具",
            author="Photo666 Team"
        )
    
    def initialize(self, app_context: Dict[str, Any] = None) -> bool:
        """初始化插件"""
        try:
            self.logger.info("开始初始化JoyCaption插件")
            
            # 检查配置
            if not self.config_manager:
                self.logger.error("配置管理器初始化失败")
                return False
            
            # 检查模型管理器
            if not self.model_manager:
                self.logger.error("模型管理器初始化失败")
                return False
            
            # 检查推理引擎
            if not self.inference_engine:
                self.logger.error("推理引擎初始化失败")
                return False
            
            # 检查结果处理器
            if not self.result_processor:
                self.logger.error("结果处理器初始化失败")
                return False
            
            self.is_initialized = True
            self.logger.info("JoyCaption插件初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"插件初始化失败: {str(e)}")
            return False
    
    def show_config_dialog(self, parent=None) -> Optional[Dict[str, Any]]:
        """显示配置对话框"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "错误", "插件未初始化")
                return None
            
            dialog = JoyCaptionConfigDialog(
                self.config_manager,
                self.model_manager,
                parent=parent
            )
            
            if dialog.exec():
                config = dialog.get_config()
                self.logger.info(f"用户配置已更新: {config}")
                
                # 检查是否选择了图片
                image_paths = config.get("image_paths", [])
                if not image_paths:
                    QMessageBox.warning(parent, "警告", "请先选择要处理的图片")
                    return None
                
                # 开始处理图片
                self.start_joycaption_processing(config, parent)
                return config
            else:
                self.logger.info("用户取消配置")
                return None
                
        except Exception as e:
            self.logger.error(f"显示配置对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示配置对话框失败: {str(e)}")
            return None
    
    def process_single_image(self, image_path: str, config: Dict[str, Any], progress_callback: Callable = None) -> Optional[str]:
        """
        处理单张图片，使用JoyCaption模型生成图片描述
        
        Args:
            image_path (str): 图片文件路径
            config (Dict[str, Any]): 处理配置，包含模型ID、精度、推理参数等
            progress_callback (Callable, optional): 进度回调函数，用于报告处理进度
            
        Returns:
            Optional[str]: 生成的图片描述文本，失败时返回None
            
        Raises:
            Exception: 处理过程中的任何异常都会被捕获并记录
        """
        try:
            if not self.is_initialized:
                self.logger.error("插件未初始化")
                return None
            
            # 验证配置
            if not self.inference_engine.validate_config(config):
                self.logger.error("配置验证失败")
                return None
            
            # 检查图片文件
            if not Path(image_path).exists():
                self.logger.error(f"图片文件不存在: {image_path}")
                return None
            
            # 获取模型信息
            model_id = config.get("model_id")
            precision = config.get("precision", "Balanced (8-bit)")
            
            # 获取自定义路径
            custom_paths = config.get("custom_local_paths", [])
            
            # 检查模型是否已下载
            if not self.model_manager.is_model_downloaded(model_id, custom_paths):
                if progress_callback:
                    progress_callback("download", 0, f"开始下载模型: {model_id}")
                
                if not self.model_manager.download_model(model_id, progress_callback):
                    self.logger.error(f"模型下载失败: {model_id}")
                    return None
            
            # 加载模型
            if progress_callback:
                progress_callback("load", 0, "正在加载模型...")
            
            model_info = self.model_manager.load_model(model_id, precision, custom_paths)
            if not model_info:
                self.logger.error(f"模型加载失败: {model_id}")
                return None
            
            # 设置推理引擎
            self.inference_engine.setup_model(model_info)
            
            # 执行推理
            if progress_callback:
                progress_callback("inference", 0, "正在执行推理...")
            
            result_text = self.inference_engine.inference(image_path, config)
            
            if result_text:
                # 保存结果
                description_level = config.get("description_level", "normal")
                self.result_processor.save_result_to_file(image_path, result_text, description_level)
                
                self.logger.info(f"图片处理完成: {image_path}")
                return result_text
            else:
                self.logger.error(f"推理失败: {image_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"处理单张图片失败 {image_path}: {str(e)}")
            return None
    
    def process_multiple_images(self, image_paths: List[str], config: Dict[str, Any], progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        批量处理多张图片，使用JoyCaption模型生成图片描述
        
        Args:
            image_paths (List[str]): 图片文件路径列表
            config (Dict[str, Any]): 处理配置，包含模型ID、精度、推理参数等
            progress_callback (Callable, optional): 进度回调函数，用于报告处理进度
            
        Returns:
            List[Dict[str, Any]]: 处理结果列表，每个元素包含图片路径、成功状态、描述文本等
            
        Note:
            - 会自动过滤不存在的图片文件
            - 使用批量推理提高处理效率
            - 所有结果都会自动保存到文件
        """
        try:
            if not self.is_initialized:
                self.logger.error("插件未初始化")
                return []
            
            # 验证配置
            if not self.inference_engine.validate_config(config):
                self.logger.error("配置验证失败")
                return []
            
            # 检查图片文件
            valid_paths = []
            for path in image_paths:
                if Path(path).exists():
                    valid_paths.append(path)
                else:
                    self.logger.warning(f"图片文件不存在: {path}")
            
            if not valid_paths:
                self.logger.error("没有有效的图片文件")
                return []
            
            # 获取模型信息
            model_id = config.get("model_id")
            precision = config.get("precision", "Balanced (8-bit)")
            
            # 获取自定义路径
            custom_paths = config.get("custom_local_paths", [])
            
            # 检查模型是否已下载
            if not self.model_manager.is_model_downloaded(model_id, custom_paths):
                if progress_callback:
                    progress_callback("download", 0, f"开始下载模型: {model_id}")
                
                if not self.model_manager.download_model(model_id, progress_callback):
                    self.logger.error(f"模型下载失败: {model_id}")
                    return []
            
            # 加载模型
            if progress_callback:
                progress_callback("load", 0, "正在加载模型...")
            
            model_info = self.model_manager.load_model(model_id, precision, custom_paths)
            if not model_info:
                self.logger.error(f"模型加载失败: {model_id}")
                return []
            
            # 设置推理引擎
            self.inference_engine.setup_model(model_info)
            
            # 执行批量推理
            results = self.inference_engine.batch_inference(valid_paths, config, progress_callback)
            
            # 保存结果
            description_level = config.get("description_level", "normal")
            self.result_processor.save_batch_results(results, description_level)
            
            self.logger.info(f"批量处理完成: 成功 {len([r for r in results if r['success']])}/{len(results)}")
            return results
            
        except Exception as e:
            self.logger.error(f"批量处理失败: {str(e)}")
            return []
    
    def process_directory(self, directory_path: str, config: Dict[str, Any], progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """处理目录中的所有图片"""
        try:
            if not self.is_initialized:
                self.logger.error("插件未初始化")
                return []
            
            # 检查目录
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                self.logger.error(f"目录不存在: {directory_path}")
                return []
            
            # 查找图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            image_paths = []
            
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_paths.append(str(file_path))
            
            if not image_paths:
                self.logger.warning(f"目录中没有找到图片文件: {directory_path}")
                return []
            
            self.logger.info(f"找到 {len(image_paths)} 张图片")
            
            # 处理图片
            return self.process_multiple_images(image_paths, config, progress_callback)
            
        except Exception as e:
            self.logger.error(f"处理目录失败 {directory_path}: {str(e)}")
            return []
    
    def show_progress_dialog(self, parent=None, title: str = "JoyCaption处理进度") -> JoyCaptionProgressDialog:
        """显示进度对话框"""
        return JoyCaptionProgressDialog(parent=parent, title=title)
    
    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        try:
            return self.model_manager.get_available_models()
        except Exception as e:
            self.logger.error(f"获取可用模型失败: {str(e)}")
            return {}
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """获取模型状态"""
        try:
            return self.model_manager.check_model_status(model_id)
        except Exception as e:
            self.logger.error(f"获取模型状态失败 {model_id}: {str(e)}")
            return {}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            return self.inference_engine.get_memory_usage()
        except Exception as e:
            self.logger.error(f"获取内存使用情况失败: {str(e)}")
            return {}
    
    def shutdown(self) -> bool:
        """清理资源"""
        try:
            # 清理推理引擎
            if self.inference_engine:
                self.inference_engine.cleanup()
            
            # 清理模型管理器
            if self.model_manager:
                self.model_manager.cleanup_cache()
            
            self.is_initialized = False
            self.logger.info("JoyCaption插件资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {str(e)}")
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """获取菜单动作"""
        return [
            {
                "menu": "工具",
                "title": "JoyCaption图片描述",
                "action": "joycaption_process",
                "description": "使用JoyCaption模型生成图片描述（支持单张和批量处理）"
            }
        ]
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        return [
            {
                "title": "JoyCaption",
                "action": "joycaption_process",
                "icon": "🎨",
                "tooltip": "使用JoyCaption模型生成图片描述"
            },
            {
                "title": "JC快速处理",
                "action": "joycaption_quick_process",
                "icon": "⚡",
                "tooltip": "使用JoyCaption默认配置对当前图片进行反推"
            }
        ]
    
    def joycaption_process(self, parent=None):
        """JoyCaption图片描述处理 - 工具栏按钮调用的方法"""
        try:
            self.logger.info("显示JoyCaption配置对话框")
            
            if not self.is_initialized:
                QMessageBox.warning(parent, "插件未初始化", "JoyCaption插件尚未初始化，请检查配置")
                return
            
            # 调用原有的配置对话框方法
            self.show_config_dialog(parent)
            
        except Exception as e:
            self.logger.error(f"显示JoyCaption配置对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示JoyCaption配置对话框失败：{str(e)}")
    
    def start_joycaption_processing(self, config: Dict[str, Any], parent=None):
        """开始JoyCaption处理"""
        try:
            image_paths = config.get("image_paths", [])
            if not image_paths:
                QMessageBox.warning(parent, "错误", "没有选择图片")
                return
            
            # 创建进度对话框
            progress_dialog = self.show_progress_dialog(parent, "JoyCaption处理进度")
            
            # 根据图片数量选择处理方式
            if len(image_paths) == 1:
                # 单张图片处理
                result = self.process_single_image(image_paths[0], config, progress_dialog.update_progress)
                if result:
                    QMessageBox.information(parent, "成功", f"处理完成：{result[:100]}...")
                else:
                    QMessageBox.warning(parent, "失败", "图片处理失败")
            else:
                # 多张图片处理
                results = self.process_multiple_images(image_paths, config, progress_dialog.update_progress)
                if results:
                    success_count = sum(1 for r in results if r.get('success', False))
                    QMessageBox.information(parent, "成功", f"处理完成：{success_count}/{len(results)} 张图片成功")
                else:
                    QMessageBox.warning(parent, "失败", "批量处理失败")
            
        except Exception as e:
            self.logger.error(f"开始JoyCaption处理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"开始JoyCaption处理失败: {str(e)}")
    
    def joycaption_quick_process(self, parent=None):
        """JC快速处理 - 使用JoyCaption默认配置对当前图片进行反推"""
        try:
            self.logger.info("开始JC快速处理")
            
            if not self.is_initialized:
                QMessageBox.warning(parent, "插件未初始化", "JoyCaption插件尚未初始化，请检查配置")
                return
            
            # 获取默认配置
            default_config = self.get_default_config()
            if not default_config:
                QMessageBox.warning(
                    parent, 
                    "配置错误", 
                    "未找到默认配置，请先在配置对话框中设置并保存默认配置。"
                )
                return
            
            # 获取当前显示的图片路径
            current_image_path = self.get_current_displayed_image(parent)
            if not current_image_path:
                QMessageBox.warning(parent, "错误", "请先在图片显示区选择要处理的图片")
                return
            
            # 验证图片文件
            if not self.validate_image_file(current_image_path):
                QMessageBox.warning(parent, "错误", f"图片文件无效: {current_image_path}")
                return
            
            # 添加图片路径到配置
            default_config["image_paths"] = [current_image_path]
            
            # 确保结果保存在图片所在目录
            default_config["save_to_file"] = True
            default_config["save_to_database"] = False  # 快速处理只保存到文件
            
            self.logger.info(f"JC快速处理配置: {default_config}")
            
            # 开始处理
            self.start_joycaption_processing(default_config, parent)
            
        except Exception as e:
            self.logger.error(f"JC快速处理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"JC快速处理失败：{str(e)}")
    
    def get_current_displayed_image(self, parent=None) -> Optional[str]:
        """获取当前显示的图片路径"""
        try:
            # 尝试从主窗口获取当前显示的图片
            if parent and hasattr(parent, 'photo_viewer') and parent.photo_viewer:
                current_photo = parent.photo_viewer.current_photo
                if current_photo and current_photo.get('filepath'):
                    filepath = current_photo.get('filepath')
                    if Path(filepath).exists():
                        self.logger.info(f"获取到当前显示图片: {filepath}")
                        return filepath
                    else:
                        self.logger.warning(f"当前显示图片文件不存在: {filepath}")
                        return None
                else:
                    self.logger.warning("当前没有显示图片")
                    return None
            else:
                self.logger.warning("无法获取主窗口或图片查看器")
                return None
                
        except Exception as e:
            self.logger.error(f"获取当前图片失败: {str(e)}")
            return None
    
    def get_settings(self) -> Dict[str, Any]:
        """获取插件设置"""
        return {
            'config': self.config_manager.config if self.config_manager else {},
            'model_status': self.get_model_status("default") if hasattr(self, 'get_model_status') else {},
            'plugin_status': {
                'initialized': self.is_initialized,
                'enabled': True
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取插件配置"""
        return self.config_manager.config if self.config_manager else {}
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """更新插件设置"""
        try:
            if self.config_manager:
                self.config_manager.update_config(settings.get('config', {}))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update settings: {str(e)}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        try:
            inference_config = self.config_manager.get_inference_config()
            
            # 获取用户保存的自定义路径和额外选项
            current_config = self.config_manager.config
            custom_paths = current_config.get('models', {}).get('custom_local_paths', [])
            extra_options = inference_config.get('extra_options', [])
            
            return {
                "model_id": self.config_manager.get_default_model(),
                "precision": inference_config.get("precision", "Balanced (8-bit)"),
                "caption_type": inference_config.get("default_caption_type", "Descriptive"),
                "caption_length": "any",
                "description_level": inference_config.get("default_level", "normal"),
                "max_new_tokens": inference_config.get("max_new_tokens", 512),
                "temperature": inference_config.get("temperature", 0.6),
                "top_p": inference_config.get("top_p", 0.9),
                "top_k": inference_config.get("top_k", 0),
                "extra_options": extra_options,  # 包含用户保存的额外选项
                "name_input": "",
                "custom_local_paths": custom_paths  # 包含用户保存的自定义路径
            }
        except Exception as e:
            self.logger.error(f"获取默认配置失败: {str(e)}")
            return {}
    
    def validate_image_file(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            path = Path(image_path)
            if not path.exists():
                return False
            
            # 检查文件扩展名
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            if path.suffix.lower() not in image_extensions:
                return False
            
            # 检查文件大小
            if path.stat().st_size == 0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证图片文件失败 {image_path}: {str(e)}")
            return False 