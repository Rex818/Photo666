"""
Florence2图片反推信息插件
支持Florence2模型对图片进行反向推导，生成不同详细程度的信息描述
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from picman.plugins.base import Plugin, PluginInfo
from plugins.florence2_reverse_plugin.core.config_manager import ConfigManager
from plugins.florence2_reverse_plugin.core.model_manager import ModelManager
from plugins.florence2_reverse_plugin.core.inference_engine import InferenceEngine
from plugins.florence2_reverse_plugin.core.result_processor import ResultProcessor
from plugins.florence2_reverse_plugin.ui.config_dialog import Florence2ConfigDialog
from plugins.florence2_reverse_plugin.ui.progress_dialog import ReverseInferenceProgressDialog
from plugins.florence2_reverse_plugin.ui.image_selection_dialog import ImageSelectionDialog


class Florence2ReversePlugin(Plugin):
    """Florence2图片反推信息插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "Florence2图片反推信息插件"
        self.version = "1.0.0"
        self.author = "Photo666 Team"
        self.description = "使用Florence2模型对图片进行反向推导，生成不同详细程度的信息描述"
        
        # 核心组件
        self.config_manager = None
        self.model_manager = None
        self.inference_engine = None
        self.result_processor = None
        
        # UI组件
        self.config_dialog = None
        self.progress_dialog = None
        self.image_selection_dialog = None
        
        # 状态
        self.is_initialized = False
        self.current_config = None
        
        # 使用标准logging而不是structlog
        self.logger = logging.getLogger(f"picman.plugins.{self.__class__.__name__}")
        self.logger.info("Florence2图片反推信息插件实例创建")
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.logger.info("开始初始化Florence2图片反推信息插件")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            self.config_manager.initialize()
            
            # 初始化模型管理器
            self.model_manager = ModelManager(self.config_manager)
            
            # 初始化推理引擎
            self.inference_engine = InferenceEngine()
            self.inference_engine.initialize(self.config_manager, self.model_manager)
            
            # 初始化结果处理器
            self.result_processor = ResultProcessor()
            self.result_processor.initialize(app_context)
            
            # 设置配置管理器引用
            self.result_processor.config_manager = self.config_manager
            
            self.is_initialized = True
            self.logger.info("Florence2图片反推信息插件初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Florence2图片反推信息插件初始化失败: {str(e)}")
            return False
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.name,
            version=self.version,
            author=self.author,
            description=self.description
        )
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """获取菜单动作"""
        return [
            {
                "menu": "工具",
                "title": "Florence2图片反推",
                "action": "show_reverse_inference_dialog",
                "shortcut": "Ctrl+Shift+F",
                "icon": "ai"
            }
        ]
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        return [
            {
                "title": "Florence2反推",
                "action": "show_reverse_inference_dialog",
                "icon": "ai",
                "tooltip": "使用Florence2模型进行图片反推"
            },
            {
                "title": "F2快速处理",
                "action": "florence2_quick_process",
                "icon": "ai",
                "tooltip": "使用Florence2默认配置快速处理当前图片"
            },
            {
                "title": "缓存管理",
                "action": "show_cache_manager",
                "icon": "settings",
                "tooltip": "管理模型缓存"
            }
        ]
    
    def show_reverse_inference_dialog(self, parent=None):
        """显示反推对话框"""
        try:
            self.logger.info("显示Florence2反推对话框")
            
            if not self.is_initialized:
                QMessageBox.warning(parent, "插件未初始化", "Florence2插件尚未初始化，请检查配置")
                return
            
            # 创建配置对话框（包含图片选择功能）
            self.config_dialog = Florence2ConfigDialog(self.config_manager, parent)
            self.config_dialog.config_confirmed.connect(self.on_config_confirmed)
            
            # 显示配置对话框
            if self.config_dialog.exec() == Florence2ConfigDialog.DialogCode.Accepted:
                # 配置已确认，开始处理
                self.start_reverse_inference(parent)
            
        except Exception as e:
            self.logger.error(f"显示反推对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示反推对话框失败：{str(e)}")
    
    def on_config_confirmed(self, config: Dict[str, Any]):
        """配置确认回调"""
        try:
            self.current_config = config
            self.logger.info(f"配置已确认 - 模型: {config.get('model_name', '未知')}, 级别: {config.get('description_level', '未知')}")
            
        except Exception as e:
            self.logger.error(f"处理配置确认失败: {str(e)}")
    
    def start_reverse_inference(self, parent=None):
        """开始反推处理"""
        try:
            if not self.current_config:
                QMessageBox.warning(parent, "配置错误", "请先配置反推参数")
                return
            
            # 从配置中获取图片路径
            image_paths = self.current_config.get("image_paths", [])
            if not image_paths:
                QMessageBox.warning(parent, "配置错误", "请先选择图片")
                return
            
            # 创建进度对话框
            self.progress_dialog = ReverseInferenceProgressDialog(parent)
            self.progress_dialog.cancelled.connect(self.on_operation_cancelled)
            
            # 创建处理线程
            self.inference_thread = ReverseInferenceThread(
                self.model_manager,
                self.inference_engine,
                self.result_processor,
                self.current_config,
                image_paths
            )
            
            # 连接信号
            self.inference_thread.progress_updated.connect(self.progress_dialog.update_progress)
            self.inference_thread.step_progress_updated.connect(self.progress_dialog.update_step_progress)
            self.inference_thread.download_progress_updated.connect(self.progress_dialog.update_download_progress)
            self.inference_thread.inference_progress_updated.connect(self.progress_dialog.update_inference_progress)
            self.inference_thread.finished.connect(self.on_inference_finished)
            self.inference_thread.error_occurred.connect(self.on_inference_error)
            
            # 设置取消回调
            self.progress_dialog.set_cancel_callback(self.inference_thread.cancel_operation)
            
            # 启动线程
            self.inference_thread.start()
            
            # 显示进度对话框
            self.progress_dialog.exec()
            
        except Exception as e:
            self.logger.error(f"开始反推处理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"开始反推处理失败：{str(e)}")
    


    
    def on_operation_cancelled(self):
        """操作取消回调"""
        try:
            self.logger.info("用户取消了反推操作")
            
            if hasattr(self, 'inference_thread') and self.inference_thread.isRunning():
                self.inference_thread.cancel_operation()
            
        except Exception as e:
            self.logger.error(f"处理操作取消失败: {str(e)}")
    
    def on_inference_finished(self, results: List[Dict[str, Any]]):
        """推理完成回调"""
        try:
            self.logger.info(f"反推推理完成 - 结果数量: {len(results)}")
            
            if self.progress_dialog:
                self.progress_dialog.set_success(f"成功处理 {len(results)} 张图片")
            
            # 显示结果统计
            success_count = sum(1 for r in results if r.get('success', False))
            QMessageBox.information(
                None, 
                "处理完成", 
                f"反推处理完成！\n"
                f"成功处理: {success_count} 张\n"
                f"失败: {len(results) - success_count} 张"
            )
            
        except Exception as e:
            self.logger.error(f"处理推理完成回调失败: {str(e)}")
    
    def on_inference_error(self, error_message: str):
        """推理错误回调"""
        try:
            self.logger.error(f"反推推理发生错误: {error_message}")
            
            if self.progress_dialog:
                self.progress_dialog.set_error(error_message)
            
            QMessageBox.critical(None, "处理错误", f"反推处理发生错误：{error_message}")
            
        except Exception as e:
            self.logger.error(f"处理推理错误回调失败: {str(e)}")
    
    def florence2_quick_process(self, parent=None):
        """F2快速处理 - 使用缓存模型进行快速推理"""
        try:
            # 获取当前显示的图片
            current_image_path = self.get_current_displayed_image(parent)
            if not current_image_path:
                QMessageBox.warning(parent, "错误", "无法获取当前显示的图片")
                return
            
            # 获取默认配置
            default_config = self.config_manager.get_default_processing_config() if self.config_manager else {}
            
            # 验证图片文件
            if not self.validate_image_file(current_image_path):
                QMessageBox.warning(parent, "错误", f"图片文件无效: {current_image_path}")
                return
            
            # 检查模型是否已加载，如果未加载则自动加载
            if not self.model_manager or not self.model_manager.is_model_loaded():
                self.logger.info("模型未加载，开始自动加载模型")
                
                # 获取默认模型配置
                model_name = default_config.get("model_name", "microsoft/Florence-2-base")
                custom_path = default_config.get("custom_path", "")
                
                # 自动加载模型
                try:
                    success = self.model_manager.load_model(model_name, custom_path, use_cache=True)
                    if not success:
                        QMessageBox.warning(parent, "错误", f"模型加载失败: {model_name}")
                        return
                    self.logger.info(f"模型自动加载成功: {model_name}")
                except Exception as e:
                    self.logger.error(f"模型自动加载失败: {str(e)}")
                    QMessageBox.critical(parent, "错误", f"模型自动加载失败：{str(e)}")
                    return
            
            # 添加图片路径到配置
            default_config["image_paths"] = [current_image_path]
            
            # 确保结果保存在图片所在目录
            default_config["save_to_file"] = True
            default_config["save_to_database"] = False  # 快速处理只保存到文件
            
            # 优化配置：使用更快的推理参数
            default_config["quick_mode"] = True
            default_config["use_cache"] = True  # 使用模型缓存，不是结果缓存
            
            self.logger.info(f"F2快速处理配置: {default_config}")
            
            # 开始处理
            self.current_config = default_config
            self.start_reverse_inference(parent)
            
        except Exception as e:
            self.logger.error(f"F2快速处理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"F2快速处理失败：{str(e)}")
    
    def _check_cached_result(self, image_path: str, config: Dict[str, Any]) -> Optional[str]:
        """检查是否有缓存结果 - 已废弃，不再使用结果缓存"""
        # 移除结果缓存逻辑，只使用模型缓存
        return None
    
    def _save_quick_result(self, image_path: str, result: str):
        """快速保存结果到文件 - 已废弃，结果由推理引擎直接保存"""
        # 此方法已废弃，结果保存由推理引擎和结果处理器处理
        pass
    
    def _get_result_file_path(self, image_path: str, config: Dict[str, Any]) -> Path:
        """获取结果文件路径"""
        image_path_obj = Path(image_path)
        image_dir = image_path_obj.parent
        image_name = image_path_obj.stem
        
        # 获取输出配置
        output_config = self.config_manager.get_output_config() if self.config_manager else {}
        file_prefix = output_config.get("file_prefix", "")
        file_suffix = output_config.get("file_suffix", ".txt")
        
        return image_dir / f"{file_prefix}{image_name}{file_suffix}"
    
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
    
    def shutdown(self):
        """关闭插件"""
        try:
            self.logger.info("开始关闭Florence2图片反推信息插件")
            
            # 取消正在进行的操作
            if hasattr(self, 'inference_thread') and self.inference_thread.isRunning():
                self.inference_thread.cancel_operation()
                self.inference_thread.wait()
            
            # 卸载模型
            if self.model_manager:
                self.model_manager.unload_model()
            
            # 关闭对话框
            if self.config_dialog:
                self.config_dialog.close()
            
            if self.progress_dialog:
                self.progress_dialog.close()
            
            self.logger.info("Florence2图片反推信息插件关闭完成")
            
        except Exception as e:
            self.logger.error(f"关闭Florence2图片反推信息插件失败: {str(e)}")
    
    # ==================== 缓存管理方法 ====================
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            if self.model_manager:
                return self.model_manager.get_cache_info()
            return {}
        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {str(e)}")
            return {}
    
    def clear_cache(self):
        """清除所有缓存"""
        try:
            if self.model_manager:
                self.model_manager.clear_all_cache()
                self.logger.info("模型缓存已清除")
        except Exception as e:
            self.logger.error(f"清除缓存失败: {str(e)}")
    
    def cleanup_expired_cache(self):
        """清理过期的缓存"""
        try:
            if self.model_manager:
                # 获取缓存信息
                cache_info = self.model_manager.get_cache_info()
                expired_models = []
                
                for model_name, info in cache_info.get('cached_models', {}).items():
                    if info.get('is_expired', False):
                        expired_models.append(model_name)
                
                # 移除过期的模型
                for model_name in expired_models:
                    self.model_manager._remove_from_cache(model_name)
                
                if expired_models:
                    self.logger.info(f"已清理过期缓存模型: {expired_models}")
                else:
                    self.logger.info("没有过期的缓存模型")
                    
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {str(e)}")
    
    def set_cache_config(self, max_cache_size: int = 2, cache_timeout: int = 3600):
        """设置缓存配置"""
        try:
            if self.model_manager:
                self.model_manager.max_cache_size = max_cache_size
                self.model_manager.cache_timeout = cache_timeout
                self.logger.info(f"缓存配置已更新 - 最大缓存数量: {max_cache_size}, 超时时间: {cache_timeout}秒")
        except Exception as e:
            self.logger.error(f"设置缓存配置失败: {str(e)}")
    
    def show_cache_manager(self, parent=None):
        """显示缓存管理对话框"""
        try:
            self.logger.info("显示缓存管理对话框")
            
            if not self.is_initialized:
                QMessageBox.warning(parent, "插件未初始化", "Florence2插件尚未初始化，请检查配置")
                return
            
            # 导入缓存管理对话框
            from plugins.florence2_reverse_plugin.ui.cache_manager_dialog import CacheManagerDialog
            
            # 创建并显示缓存管理对话框
            cache_dialog = CacheManagerDialog(self, parent)
            cache_dialog.exec()
            
        except Exception as e:
            self.logger.error(f"显示缓存管理对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示缓存管理对话框失败：{str(e)}")


class ReverseInferenceThread(QThread):
    """反推推理线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, str)  # step, progress, message
    step_progress_updated = pyqtSignal(str, int, int)  # step, current, total
    download_progress_updated = pyqtSignal(int, int, str)  # current_bytes, total_bytes, speed
    inference_progress_updated = pyqtSignal(int, int, str)  # current, total, current_file
    finished = pyqtSignal(list)  # results
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, model_manager, inference_engine, result_processor, config, image_paths):
        super().__init__()
        self.model_manager = model_manager
        self.inference_engine = inference_engine
        self.result_processor = result_processor
        self.config = config
        self.image_paths = image_paths
        self.is_cancelled = False
        
        # 设置进度回调
        self.model_manager.set_progress_callback(self._on_model_progress)
        self.inference_engine.set_progress_callback(self._on_inference_progress)
    
    def run(self):
        """运行推理线程"""
        try:
            results = []
            
            # 1. 加载模型
            if not self._load_model():
                return
            
            # 2. 处理每张图片
            for i, image_path in enumerate(self.image_paths):
                if self.is_cancelled:
                    break
                
                try:
                    # 更新进度
                    self.inference_progress_updated.emit(i + 1, len(self.image_paths), Path(image_path).name)
                    
                    # 执行推理
                    inference_results = self.inference_engine.infer_images(
                        [image_path], 
                        self.config['model_name'],
                        self.config['description_level']
                    )
                    
                    if inference_results and inference_results[0]['success']:
                        result = inference_results[0]
                        # 处理结果 - 传递配置参数
                        processed_results = self.result_processor.process_results(
                            [result], 
                            self.config['description_level'],
                            self.config  # 传递配置参数
                        )
                        
                        results.append({
                            'image_path': image_path,
                            'result': result['result'],
                            'success': True
                        })
                    else:
                        results.append({
                            'image_path': image_path,
                            'result': None,
                            'success': False,
                            'error': '推理失败'
                        })
                        
                except Exception as e:
                    results.append({
                        'image_path': image_path,
                        'result': None,
                        'success': False,
                        'error': str(e)
                    })
            
            # 3. 发送完成信号
            if not self.is_cancelled:
                self.finished.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _load_model(self) -> bool:
        """加载模型"""
        try:
            model_name = self.config['model_name']
            custom_path = self.config.get('custom_path')
            use_cache = self.config.get('use_cache', True)
            
            # 加载模型 - 传递自定义路径参数和缓存选项
            success = self.model_manager.load_model(model_name, custom_path, use_cache)
            
            if not success:
                self.error_occurred.emit("模型加载失败")
                return False
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"模型加载失败: {str(e)}")
            return False
    
    def _on_model_progress(self, step: str, progress: int, message: str):
        """模型进度回调"""
        self.progress_updated.emit(step, progress, message)
    
    def _on_inference_progress(self, step: str, progress: int, message: str):
        """推理进度回调"""
        self.progress_updated.emit(step, progress, message)
    
    def cancel_operation(self):
        """取消操作"""
        self.is_cancelled = True 