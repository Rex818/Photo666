"""
JoyCaption图片反推信息插件主入口
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from .core.config_manager import ConfigManager
from .core.model_manager import ModelManager
from .core.inference_engine import InferenceEngine
from .core.proxy_manager import ProxyManager
from .ui.main_dialog import JoyCaptionDialog
from .utils.logger import setup_logger


class JoyCaptionPlugin(QObject):
    """JoyCaption图片反推信息插件主类"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, str)  # 阶段, 进度, 消息
    model_loaded = pyqtSignal(str)  # 模型名称
    inference_completed = pyqtSignal(str, str)  # 图片路径, 结果
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        
        # 设置日志
        self.logger = setup_logger("joycaption_plugin")
        self.logger.info("JoyCaption图片反推信息插件实例创建")
        
        # 初始化组件
        self.config_manager = config_manager
        self.proxy_manager = ProxyManager()
        self.model_manager = ModelManager(config_manager, self.proxy_manager)
        self.inference_engine = None  # 延迟初始化
        
        # 状态变量
        self.current_model = None
        self.current_config = None
        self.is_initialized = False
        self.main_window = None  # 主窗口引用
        
        self.logger.info("JoyCaption图片反推信息插件初始化完成")
    
    def show_dialog(self):
        """显示JoyCaption反推对话框"""
        try:
            self.logger.info("显示JoyCaption反推对话框")
            
            # 获取主窗口
            main_window = self.main_window
            if not main_window:
                app = QApplication.instance()
                main_window = None
                
                # 尝试多种方式获取主窗口
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'setWindowTitle'):
                        title = widget.windowTitle()
                        if 'Photo666' in title or 'picman' in title.lower():
                            main_window = widget
                            break
                
                # 如果还是找不到，使用第一个顶级窗口
                if not main_window and app.topLevelWidgets():
                    main_window = app.topLevelWidgets()[0]
            
            if not main_window:
                self.logger.error("无法找到主窗口")
                return
            
            # 创建并显示对话框
            dialog = JoyCaptionDialog(main_window, self)
            dialog.show()
            
        except Exception as e:
            self.logger.error(f"显示对话框失败: {e}")
            self.error_occurred.emit(f"显示对话框失败: {e}")
    
    def load_model(self, model_name: str, config: Dict[str, Any]) -> bool:
        """加载指定的模型"""
        try:
            self.logger.info(f"开始加载模型: {model_name}")
            self.progress_updated.emit("loading", 0, f"正在加载模型: {model_name}")
            
            # 加载模型
            success = self.model_manager.load_model(model_name, config)
            
            if success:
                self.current_model = model_name
                self.current_config = config
                self.inference_engine = InferenceEngine(self.model_manager, self.config_manager)
                self.is_initialized = True
                
                self.logger.info(f"模型加载成功: {model_name}")
                self.progress_updated.emit("loading", 100, f"模型加载完成: {model_name}")
                self.model_loaded.emit(model_name)
                return True
            else:
                self.logger.error(f"模型加载失败: {model_name}")
                self.progress_updated.emit("loading", 0, f"模型加载失败: {model_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"模型加载异常: {e}")
            self.progress_updated.emit("loading", 0, f"模型加载异常: {e}")
            self.error_occurred.emit(f"模型加载异常: {e}")
            return False
    
    def perform_inference(self, image_paths: list, detail_level: str) -> Dict[str, Any]:
        """执行图片反推推理"""
        try:
            if not self.is_initialized or not self.inference_engine:
                raise Exception("模型未初始化，请先加载模型")
            
            self.logger.info(f"开始执行反推推理，图片数量: {len(image_paths)}, 详细程度: {detail_level}")
            self.progress_updated.emit("inference", 0, f"开始反推推理，共{len(image_paths)}张图片")
            
            results = {}
            total_images = len(image_paths)
            
            for i, image_path in enumerate(image_paths):
                try:
                    # 更新进度
                    progress = int((i / total_images) * 100)
                    self.progress_updated.emit("inference", progress, f"正在处理: {Path(image_path).name}")
                    
                    # 执行推理
                    result = self.inference_engine.inference_single_image(
                        image_path, detail_level
                    )
                    
                    if result:
                        results[image_path] = result
                        self.inference_completed.emit(image_path, result)
                        self.logger.info(f"图片反推成功: {image_path}")
                    else:
                        self.logger.warning(f"图片反推失败: {image_path}")
                        
                except Exception as e:
                    self.logger.error(f"处理图片失败 {image_path}: {e}")
                    results[image_path] = f"错误: {e}"
            
            self.progress_updated.emit("inference", 100, f"反推推理完成，成功处理{len(results)}张图片")
            self.logger.info(f"反推推理完成，成功处理{len(results)}张图片")
            
            return results
            
        except Exception as e:
            self.logger.error(f"反推推理异常: {e}")
            self.progress_updated.emit("inference", 0, f"反推推理异常: {e}")
            self.error_occurred.emit(f"反推推理异常: {e}")
            return {}
    
    def unload_model(self):
        """卸载当前模型"""
        try:
            if self.inference_engine:
                self.inference_engine = None
            
            if self.model_manager:
                self.model_manager.unload_model()
            
            self.current_model = None
            self.current_config = None
            self.is_initialized = False
            
            self.logger.info("模型已卸载")
            
        except Exception as e:
            self.logger.error(f"卸载模型异常: {e}")
    
    def shutdown(self):
        """关闭插件"""
        try:
            self.logger.info("开始关闭JoyCaption图片反推信息插件")
            
            # 卸载模型
            self.unload_model()
            
            # 关闭组件
            if self.model_manager:
                self.model_manager.shutdown()
            
            self.logger.info("JoyCaption图片反推信息插件关闭完成")
            
        except Exception as e:
            self.logger.error(f"插件关闭异常: {e}")
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": "JoyCaption图片反推信息插件",
            "version": "1.0.0",
            "description": "基于JoyCaption模型进行图片信息反向推导",
            "author": "Photo666 Team",
            "is_initialized": self.is_initialized,
            "current_model": self.current_model
        } 