"""
Janus图片反推信息插件主类
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt6.QtCore import QThread, pyqtSignal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from picman.plugins.base import Plugin, PluginInfo
from .core.config_manager import ConfigManager
from .core.model_manager import ModelManager
from .core.inference_engine import InferenceEngine
from .core.result_processor import ResultProcessor
from .ui.config_dialog import JanusConfigDialog


class JanusReversePlugin(Plugin):
    """Janus图片反推信息插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "Janus图片反推信息插件"
        self.version = "1.0.0"
        self.author = "Photo666 Team"
        self.description = "基于Janus-Pro模型的AI图片反推和生成工具"
        
        # 核心组件
        self.config_manager = None
        self.model_manager = None
        self.inference_engine = None
        self.result_processor = None
        
        # UI组件
        self.config_dialog = None
        
        # 状态
        self.is_initialized = False
        self.current_config = None
        self._pending_image_paths = None  # 等待目标模型就绪后要处理的图片
        self._pending_model_id = None     # 期望加载/下载的目标模型ID
        self.progress_dialog = None       # 统一进度对话框
        
        # 使用标准logging而不是structlog
        self.logger = logging.getLogger(f"picman.plugins.{self.__class__.__name__}")
        self.logger.info("Janus图片反推信息插件实例创建")
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.logger.info("开始初始化Janus图片反推信息插件")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            self.config_manager.initialize()
            
            # 初始化模型管理器
            self.model_manager = ModelManager(self.config_manager)
            
            # 初始化推理引擎
            self.inference_engine = InferenceEngine()
            self.inference_engine.initialize(self.config_manager, self.model_manager)
            
            # 初始化结果处理器
            self.result_processor = ResultProcessor(self.config_manager)
            
            self.is_initialized = True
            self.logger.info("Janus图片反推信息插件初始化完成")
            
            # 检查Janus库是否可用
            if not hasattr(self.inference_engine, "JANUS_AVAILABLE") or not self.inference_engine.JANUS_AVAILABLE:
                self.logger.warning("Janus库不可用，部分功能将被禁用")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Janus图片反推信息插件初始化失败: {str(e)}")
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
        actions = []
        
        # 如果Janus库可用，添加其他选项
        if hasattr(self.inference_engine, "JANUS_AVAILABLE") and self.inference_engine.JANUS_AVAILABLE:
            actions.extend([
                {
                    "title": "Janus图片反推",
                    "action": "janus_process",
                    "description": "使用Janus模型进行图片反推",
                    "menu": "工具"
                }
                # 移除Janus图片生成选项，因为功能未实现
                # {
                #     "title": "Janus图片生成",
                #     "action": "show_image_generation_dialog",
                #     "description": "使用Janus模型生成图片",
                #     "menu": "工具"
                # }
            ])
        
        return actions
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        actions = []
        
        # 合并反推和配置为一个按钮
        actions.append({
            "title": "Janus图片反推",
            "action": "janus_process",
            "description": "使用Janus模型进行图片反推和配置",
            "icon": "reverse"
        })
        # 新增：Janus快速处理（对当前显示图片，使用默认配置直接反推）
        actions.append({
            "title": "Janus快速处理",
            "action": "janus_quick_process",
            "description": "使用默认配置对当前显示图片快速反推",
            "icon": "flash"
        })
        
        # 移除Janus生成按钮，因为功能未实现
        # 只有在Janus库可用时才显示生成按钮
        # if hasattr(self.inference_engine, "JANUS_AVAILABLE") and self.inference_engine.JANUS_AVAILABLE:
        #     actions.append({
        #         "title": "Janus生成",
        #         "action": "janus_quick_generate",
        #         "description": "使用Janus模型生成图片",
        #         "icon": "generate"
        #     })
        
        return actions
    
    def janus_process(self, parent=None):
        """Janus图片反推处理 - 合并配置和图片选择功能"""
        try:
            self.logger.info("显示Janus配置和图片选择对话框")
            
            if not self.is_initialized:
                QMessageBox.warning(parent, "插件未初始化", "Janus插件尚未初始化，请检查配置")
                return
            
            # 运行时检查Janus库是否可用
            if not self._check_janus_available():
                self._show_janus_unavailable_message(parent)
                return
            
            # 显示配置对话框（包含图片选择功能）
            self.show_config_dialog(parent)
            
        except Exception as e:
            self.logger.error(f"显示Janus配置对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示Janus配置对话框失败：{str(e)}")
    
    def _check_janus_available(self) -> bool:
        """检查Janus库是否可用"""
        try:
            # 检查推理引擎是否存在
            if not hasattr(self, 'inference_engine') or self.inference_engine is None:
                self.logger.warning("推理引擎未初始化")
                return False
            
            # 检查JANUS_AVAILABLE属性
            if not hasattr(self.inference_engine, "JANUS_AVAILABLE"):
                self.logger.warning("推理引擎缺少JANUS_AVAILABLE属性")
                return False
            
            # 检查值是否为True
            if not self.inference_engine.JANUS_AVAILABLE:
                self.logger.warning("推理引擎JANUS_AVAILABLE为False")
                return False
            
            self.logger.info("Janus库可用性检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"检查Janus库可用性时出错: {e}")
            return False
    
    def _show_janus_unavailable_message(self, parent=None):
        """显示Janus库不可用的消息"""
        try:
            # 尝试获取已选择的图片路径
            image_paths = self._get_selected_images()
            
            if image_paths:
                # 如果有选择的图片，显示详细信息
                QMessageBox.information(parent, "Janus反推", 
                    f"Janus库暂不可用，但插件已准备就绪。\n\n"
                    f"已选择 {len(image_paths)} 张图片：\n"
                    f"• {Path(image_paths[0]).name}" + 
                    (f"\n• ... 等 {len(image_paths)} 张图片" if len(image_paths) > 1 else "") +
                    f"\n\n实际推理功能需要安装Janus库。\n"
                    f"占位功能将显示反推对话框，但不会进行实际推理。")
            else:
                # 如果没有选择图片，显示简单消息
                QMessageBox.information(parent, "Janus反推", 
                    "Janus库暂不可用，但插件已准备就绪。\n\n"
                    "实际推理功能需要安装Janus库。\n"
                    "占位功能将显示反推对话框，但不会进行实际推理。")
                    
        except Exception as e:
            self.logger.error(f"显示Janus库不可用消息时出错: {e}")
            QMessageBox.warning(parent, "Janus反推", "Janus库暂不可用")
    
    def _get_selected_images(self) -> List[str]:
        """获取已选择的图片路径"""
        try:
            # 这里应该从主程序获取当前选择的图片
            # 暂时返回空列表，实际实现时需要与主程序集成
            return []
        except Exception as e:
            self.logger.error(f"获取已选择图片时出错: {e}")
            return []
    
    def _show_janus_unavailable_message_with_images(self, image_paths: List[str]):
        """显示Janus库不可用的消息（带图片信息）"""
        try:
            if image_paths:
                QMessageBox.information(None, "Janus反推", 
                    f"Janus库暂不可用，但插件已准备就绪。\n\n"
                    f"已选择 {len(image_paths)} 张图片：\n"
                    f"• {Path(image_paths[0]).name}" + 
                    (f"\n• ... 等 {len(image_paths)} 张图片" if len(image_paths) > 1 else "") +
                    f"\n\n实际推理功能需要安装Janus库。\n"
                    f"占位功能将显示反推对话框，但不会进行实际推理。")
            else:
                self._show_janus_unavailable_message(None)
        except Exception as e:
            self.logger.error(f"显示Janus库不可用消息（带图片）时出错: {e}")
            QMessageBox.warning(None, "Janus反推", "Janus库暂不可用")
    
    def show_config_dialog(self, parent=None):
        """显示配置对话框"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "警告", "插件未初始化")
                return
            
            self.config_dialog = JanusConfigDialog(self.config_manager, parent)
            self.config_dialog.config_confirmed.connect(self.on_config_confirmed)
            self.config_dialog.exec()
            
        except Exception as e:
            self.logger.error(f"显示配置对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示配置对话框失败: {str(e)}")
    
    def on_config_confirmed(self, config: Dict[str, Any]):
        """配置确认回调"""
        try:
            self.current_config = config
            self.logger.info("Janus配置已确认")

            # 持久化用户选择为默认配置（包含本地模型路径与反推参数）
            try:
                persist_payload: Dict[str, Any] = {}
                if "model" in config:
                    persist_payload["model"] = {
                        "model_id": config["model"].get("model_id", ""),
                        "model_path": config["model"].get("model_path", ""),
                        "auto_download": config["model"].get("auto_download", True),
                    }
                if "reverse_inference" in config:
                    # 直接写入到主配置，便于快速处理读取
                    persist_payload["reverse_inference"] = config["reverse_inference"]
                # 可选系统项
                if "system" in config:
                    persist_payload["system"] = config["system"]
                if persist_payload:
                    self.config_manager.save_default_config(persist_payload)
            except Exception as e:
                self.logger.warning(f"保存默认配置失败（不影响本次处理）: {e}")
            
            # 获取图片路径
            image_paths = config.get("image_paths", [])
            if not image_paths:
                QMessageBox.warning(None, "错误", "没有选择图片")
                return
            
            # 运行时检查Janus库是否可用
            if not self._check_janus_available():
                self._show_janus_unavailable_message_with_images(image_paths)
                return
            
            # 记录Janus库状态
            self.logger.info(f"Janus库状态: {self.inference_engine.JANUS_AVAILABLE}")
            
            # 打开统一进度对话框
            try:
                from plugins.janus_reverse_plugin.ui.progress_dialog import JanusProgressDialog
                if self.progress_dialog is None:
                    self.progress_dialog = JanusProgressDialog(title="Janus反推", parent=None)
                self.progress_dialog.show()
                self.progress_dialog.update_progress("checking", 0, "检查模型...")
            except Exception:
                pass

            # 如果配置了模型，尝试加载
            model_config = config.get("model", {})
            model_id = model_config.get("model_id")
            model_path = model_config.get("model_path")
            
            if model_id:
                # 检查模型是否存在（包含用户自定义路径优先）
                custom_paths = []
                if model_path:
                    custom_paths.append(model_path)
                if not self.model_manager.check_model_exists(model_id, custom_paths=custom_paths):
                    if model_config.get("auto_download", True):
                        # 自动下载模型：等待下载完成后再启动反推
                        self._pending_image_paths = image_paths
                        self._pending_model_id = model_id
                        self.progress_dialog.update_progress("downloading", 0, f"开始下载模型: {model_id}")
                        self.download_and_load_model(model_id)
                        return
                    else:
                        QMessageBox.warning(None, "警告", f"模型 {model_id} 不存在，请先下载")
                        return
                else:
                    # 如果已存在但不是当前加载的目标模型，则先加载
                    if (not self.model_manager.is_model_ready()) or (self.model_manager.get_current_model_id() != model_id):
                        if self.progress_dialog:
                            self.progress_dialog.update_progress("loading", 10, f"加载模型: {model_id}")
                        self.load_model(model_id, model_path)
                        # load_model 为同步加载，加载完成后再继续
                        if (not self.model_manager.is_model_ready()) or (self.model_manager.get_current_model_id() != model_id):
                            QMessageBox.warning(None, "警告", f"模型 {model_id} 加载未就绪")
                            return
            
            # 开始反推处理（确保此时目标模型已就绪且匹配）
            if self.model_manager.is_model_ready() and (not model_id or self.model_manager.get_current_model_id() == model_id):
                if self.progress_dialog:
                    self.progress_dialog.update_progress("processing", 20, "开始推理...")
                self.start_reverse_inference(image_paths, config, None)
            else:
                # 兜底：记录为待处理，等待下载/加载回调触发
                self._pending_image_paths = image_paths
                self._pending_model_id = model_id
            
        except Exception as e:
            self.logger.error(f"处理配置确认失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"处理配置确认失败: {str(e)}")
    
    def download_and_load_model(self, model_id: str):
        """下载并加载模型"""
        try:
            self.logger.info(f"开始下载并加载模型: {model_id}")
            
            # 1. 检查模型是否存在
            if self.model_manager.check_model_exists(model_id):
                self.logger.info(f"模型已存在: {model_id}")
                self.load_model(model_id)
                return
            
            # 2. 下载模型
            self.logger.info(f"开始下载模型: {model_id}")
            
            # 启动下载线程
            self.download_thread = ModelDownloadThread(self.model_manager, model_id)
            if self.progress_dialog:
                self.download_thread.progress_updated.connect(self.progress_dialog.update_progress)
            self.download_thread.finished.connect(lambda: self.on_download_finished(model_id))
            self.download_thread.error_occurred.connect(lambda msg: self.on_download_error(msg))
            
            self.download_thread.start()
            
        except Exception as e:
            self.logger.error(f"下载并加载模型失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"下载并加载模型失败: {str(e)}")
    
    def on_download_finished(self, model_id: str):
        """下载完成回调"""
        try:
            self.logger.info(f"模型下载完成: {model_id}")
            
            # 加载模型
            if self.progress_dialog:
                self.progress_dialog.update_progress("loading", 60, f"加载模型: {model_id}")
            self.load_model(model_id)
            
            # 如果有待处理任务且目标模型已就绪且匹配，则启动反推
            if self._pending_image_paths and self.model_manager.is_model_ready() and self.model_manager.get_current_model_id() == model_id:
                pending_images = self._pending_image_paths
                pending_config = self.current_config
                # 清空待处理
                self._pending_image_paths = None
                self._pending_model_id = None
                if self.progress_dialog:
                    self.progress_dialog.update_progress("processing", 80, "开始推理...")
                self.start_reverse_inference(pending_images, pending_config, None)

        except Exception as e:
            self.logger.error(f"处理下载完成回调失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"处理下载完成回调失败: {str(e)}")
    
    def on_download_error(self, error_message: str):
        """下载错误回调"""
        try:
            self.logger.error(f"模型下载失败: {error_message}")
            QMessageBox.critical(None, "下载失败", f"模型下载失败: {error_message}")
            
        except Exception as e:
            self.logger.error(f"处理下载错误回调失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"处理下载错误回调失败: {str(e)}")
    
    def load_model(self, model_id: str, custom_path: Optional[str] = None):
        """加载模型"""
        try:
            if self.model_manager.load_model(model_id, custom_path):
                self.logger.info(f"模型加载成功: {model_id}")
                # 不再弹出确认提示，统一在进度里显示
            else:
                self.logger.error(f"模型加载失败: {model_id}")
                QMessageBox.critical(None, "错误", f"模型加载失败: {model_id}")
                
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"加载模型失败: {str(e)}")
    
    def show_image_generation_dialog(self, parent=None):
        """显示图片生成对话框"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "警告", "插件未初始化")
                return
            
            # 这里应该显示图片生成对话框
            QMessageBox.information(parent, "信息", "图片生成功能暂未实现")
            
        except Exception as e:
            self.logger.error(f"显示图片生成对话框失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"显示图片生成对话框失败: {str(e)}")
    
    def janus_quick_generate(self, parent=None):
        """Janus快速生成"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "警告", "插件未初始化")
                return
            
            # 检查Janus库是否可用
            if not hasattr(self.inference_engine, "JANUS_AVAILABLE") or not self.inference_engine.JANUS_AVAILABLE:
                QMessageBox.information(parent, "Janus生成", 
                    "Janus库暂不可用，图片生成功能将被禁用。\n\n"
                    "请先安装Janus库以启用图片生成功能。")
                return
            
            # 显示图片生成对话框
            self.show_image_generation_dialog(parent)
            
        except Exception as e:
            self.logger.error(f"Janus快速生成失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"Janus快速生成失败: {str(e)}")

    def janus_quick_process(self, parent=None):
        """Janus快速处理：使用默认配置对当前显示图片进行反推并将结果保存到图片所在目录"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "警告", "插件未初始化")
                return
            # 检查Janus库
            if not hasattr(self.inference_engine, "JANUS_AVAILABLE") or not self.inference_engine.JANUS_AVAILABLE:
                QMessageBox.information(parent, "Janus快速处理", "Janus库暂不可用，无法进行快速反推。")
                return
            # 获取当前显示图片
            current_image = self.get_current_displayed_image(parent)
            if not current_image:
                QMessageBox.warning(parent, "提示", "未检测到当前显示的图片。")
                return
            # 从已保存的默认配置构建快速处理配置
            cfg = self._build_quick_config_from_saved()
            # 确保保存结果到图片目录
            cfg.setdefault("reverse_inference", {})["save_results"] = True
            # 设置当前图片
            cfg["image_paths"] = [current_image]
            # 直接复用统一流程
            self.on_config_confirmed(cfg)
        except Exception as e:
            self.logger.error(f"Janus快速处理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"Janus快速处理失败: {str(e)}")

    def _build_quick_config_from_saved(self) -> Dict[str, Any]:
        """基于已保存的默认配置与用户设置，构建快速处理所需配置。"""
        cfg: Dict[str, Any] = {}
        try:
            # 从主配置读取反推默认
            ri = self.config_manager.get_reverse_inference_config() or {}
            # 从用户设置读取最近使用模型信息
            us = self.config_manager.get_user_settings() or {}
            us_core = us.get("user_settings", {}) if isinstance(us, dict) else {}
            model_id = us_core.get("last_used_model") or self.config_manager.get_default_model()
            model_path = us_core.get("last_used_model_path") or ""
            auto_download = us_core.get("auto_download_models", True)

            cfg["model"] = {
                "model_id": model_id,
                "model_path": model_path,
                "auto_download": auto_download,
                "device": "cuda"
            }
            cfg["reverse_inference"] = {
                "question": ri.get("default_question", "Describe this image in detail."),
                "temperature": ri.get("default_temperature", 0.1),
                "top_p": ri.get("default_top_p", 0.95),
                "max_new_tokens": ri.get("default_max_new_tokens", 512),
                "seed": ri.get("default_seed", 666666666),
                "save_results": True,
                "result_file_suffix": ri.get("result_file_suffix", ".txt"),
            }
        except Exception as e:
            self.logger.warning(f"构建快速配置失败，回退内置默认: {e}")
            cfg = self.get_default_config()
        return cfg
    
    def start_reverse_inference(self, image_paths: List[str], config: Dict[str, Any], parent=None):
        """开始反推推理"""
        try:
            if not self.is_initialized:
                QMessageBox.warning(parent, "警告", "插件未初始化")
                return
            
            if not self.model_manager.is_model_ready():
                QMessageBox.warning(parent, "警告", "模型未加载")
                return
            
            # 验证图片文件
            valid_images = []
            for image_path in image_paths:
                if self.result_processor.validate_image_file(image_path):
                    valid_images.append(image_path)
                else:
                    self.logger.warning(f"无效的图片文件: {image_path}")
            
            if not valid_images:
                QMessageBox.warning(parent, "警告", "没有有效的图片文件")
                return
            
            # 启动反推线程
            self.reverse_thread = ReverseInferenceThread(
                self.model_manager,
                self.inference_engine,
                self.result_processor,
                config,
                valid_images
            )
            
            self.reverse_thread.progress_updated.connect(self.on_progress_updated)
            if self.progress_dialog:
                self.reverse_thread.progress_updated.connect(self.progress_dialog.update_progress)
            self.reverse_thread.finished.connect(self.on_reverse_finished)
            self.reverse_thread.error_occurred.connect(self.on_reverse_error)
            
            self.reverse_thread.start()
            
        except Exception as e:
            self.logger.error(f"开始反推推理失败: {str(e)}")
            QMessageBox.critical(parent, "错误", f"开始反推推理失败: {str(e)}")
    
    def on_progress_updated(self, step: str, progress: int, message: str):
        """进度更新回调"""
        self.logger.info(f"进度更新: {step} - {progress}% - {message}")
    
    def on_reverse_finished(self, results: List[Dict[str, Any]]):
        """反推完成回调"""
        try:
            self.logger.info(f"反推完成，共处理 {len(results)} 张图片")
            # 关闭进度对话框
            try:
                if self.progress_dialog:
                    self.progress_dialog.close()
                    self.progress_dialog = None
            except Exception:
                pass
            
            # 处理结果
            if self.current_config:
                summary = self.result_processor.process_batch_reverse_inference_results(
                    results, self.current_config.get("reverse_inference", {})
                )
                
                summary_text = self.result_processor.format_result_summary(summary)
                QMessageBox.information(None, "反推完成", summary_text)
            
        except Exception as e:
            self.logger.error(f"处理反推结果失败: {str(e)}")
    
    def on_reverse_error(self, error_message: str):
        """反推错误回调"""
        self.logger.error(f"反推错误: {error_message}")
        QMessageBox.critical(None, "反推错误", error_message)
    
    def get_current_displayed_image(self, parent=None) -> Optional[str]:
        """获取当前显示的图片路径"""
        try:
            # 从主应用程序获取当前显示的图片
            app = QApplication.instance()
            if not app:
                return None
            
            # 查找主窗口
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'photo_viewer') and widget.photo_viewer:
                    main_window = widget
                    break
            
            if main_window and hasattr(main_window, 'photo_viewer'):
                photo_viewer = main_window.photo_viewer
                if hasattr(photo_viewer, 'current_photo') and photo_viewer.current_photo:
                    return photo_viewer.current_photo.get('filepath')
            
            # 如果上面的方法失败，尝试其他方式
            if main_window and hasattr(main_window, 'current_photo'):
                current_photo = main_window.current_photo
                if current_photo and isinstance(current_photo, dict):
                    return current_photo.get('filepath')
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取当前图片失败: {str(e)}")
            return None
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "model": {
                "model_id": "deepseek-ai/janus-pro-1b",
                "model_path": "",
                "auto_download": True,
                "device": "cuda"
            },
            "reverse_inference": {
                "question": "Describe this image in detail.",
                "temperature": 0.1,
                "top_p": 0.95,
                "max_new_tokens": 512,
                "seed": 666666666,  # 使用较小的数值
                "save_results": True,
                "result_file_suffix": ".txt"
            },
            "generation": {
                "prompt": "",
                "cfg_weight": 7.5,
                "temperature": 1.0,
                "top_p": 0.9,
                "batch_size": 1,
                "image_size": 512,
                "seed": 666666666  # 使用较小的数值
            }
        }
    
    def shutdown(self):
        """关闭插件"""
        try:
            self.logger.info("开始关闭Janus图片反推信息插件")
            
            # 停止正在运行的线程
            if hasattr(self, 'reverse_thread') and self.reverse_thread.isRunning():
                self.reverse_thread.cancel_operation()
                self.reverse_thread.wait()
            
            # 停止下载线程
            if hasattr(self, 'download_thread') and self.download_thread.isRunning():
                self.download_thread.cancel_operation()
                self.download_thread.wait()
            
            # 卸载模型
            if self.model_manager:
                self.model_manager.unload_model()
            
            # 清理缓存
            if self.model_manager:
                self.model_manager.cleanup_cache()
            
            self.logger.info("Janus图片反推信息插件关闭完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Janus图片反推信息插件关闭失败: {str(e)}")
            return False


class ReverseInferenceThread(QThread):
    """反推推理线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, str)  # step, progress, message
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
        
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.ReverseInferenceThread")
    
    def run(self):
        """运行线程"""
        try:
            self.logger.info(f"开始反推推理，共 {len(self.image_paths)} 张图片")
            
            results = []
            total = len(self.image_paths)
            
            for i, image_path in enumerate(self.image_paths):
                if self.is_cancelled:
                    self.logger.info("反推推理被取消")
                    break
                
                try:
                    # 更新进度
                    progress = int((i / total) * 100)
                    self.progress_updated.emit("processing", progress, f"正在处理: {Path(image_path).name}")
                    
                    # 执行反推
                    reverse_config = self.config.get("reverse_inference", {})
                    result = self.inference_engine.reverse_inference(
                        image_path=image_path,
                        question=reverse_config.get("question", "Describe this image in detail."),
                        temperature=reverse_config.get("temperature", 0.1),
                        top_p=reverse_config.get("top_p", 0.95),
                        max_new_tokens=reverse_config.get("max_new_tokens", 512),
                        seed=reverse_config.get("seed", 666666666),
                        progress_callback=self.on_progress_callback
                    )
                    
                    results.append({
                        "image_path": image_path,
                        "result": result,
                        "success": result is not None
                    })
                    
                except Exception as e:
                    self.logger.error(f"处理图片失败: {image_path}, 错误: {str(e)}")
                    results.append({
                        "image_path": image_path,
                        "result": None,
                        "success": False,
                        "error": str(e)
                    })
            
            # 发送完成信号
            self.finished.emit(results)
            
        except Exception as e:
            self.logger.error(f"反推推理线程失败: {str(e)}")
            self.error_occurred.emit(str(e))
    
    def on_progress_callback(self, step: str, progress: int, message: str):
        """进度回调"""
        self.progress_updated.emit(step, progress, message)
    
    def cancel_operation(self):
        """取消操作"""
        self.is_cancelled = True


class ModelDownloadThread(QThread):
    """模型下载线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, str)  # step, progress, message
    finished = pyqtSignal()  # 下载完成
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, model_manager, model_id):
        super().__init__()
        self.model_manager = model_manager
        self.model_id = model_id
        self.is_cancelled = False
        
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.ModelDownloadThread")
    
    def run(self):
        """运行下载线程"""
        try:
            self.logger.info(f"开始下载模型: {self.model_id}")
            
            # 更新进度
            self.progress_updated.emit("downloading", 0, f"开始下载模型: {self.model_id}")
            
            # 调用模型管理器的下载方法
            success = self.model_manager.download_model(
                self.model_id,
                progress_callback=self.on_progress_callback
            )
            
            if success:
                self.logger.info(f"模型下载完成: {self.model_id}")
                self.progress_updated.emit("downloading", 100, f"模型下载完成: {self.model_id}")
                self.finished.emit()
            else:
                error_msg = f"模型下载失败: {self.model_id}"
                self.logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                
        except Exception as e:
            error_msg = f"模型下载异常: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def on_progress_callback(self, step: str, progress: int, message: str):
        """进度回调"""
        if not self.is_cancelled:
            self.progress_updated.emit(step, progress, message)
    
    def cancel_operation(self):
        """取消操作"""
        self.is_cancelled = True
