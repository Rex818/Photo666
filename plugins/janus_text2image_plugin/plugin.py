from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PIL import Image
import numpy as np

from picman.plugins.base import Plugin as BasePlugin, PluginInfo
from picman.database.manager import DatabaseManager

from .ui import JanusT2IMainWidget
from .official_janus_generator import OfficialJanusGenerator


class JanusGenerateWorker(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, params: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.params = params
        self.logger = logging.getLogger(__name__)

    def run(self) -> None:  # noqa: D401
        try:
            # 读取序号
            db_path = Path("data/picman.db")
            db = DatabaseManager(str(db_path))
            row = db.fetch_one("SELECT value FROM settings WHERE key = ?", ("janus_t2i_last_index",))
            start_index = int(row[0]) if row and str(row[0]).isdigit() else 1

            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)

            # 解析参数
            prompt = self.params.get("prompt", "").strip()
            seed = int(self.params.get("seed", 666666666666666))
            batch_size = max(1, int(self.params.get("batch_size", 1)))
            cfg_weight = float(self.params.get("cfg_weight", 5.0))
            temperature = float(self.params.get("temperature", 1.0))
            top_p = float(self.params.get("top_p", 0.95))
            model_path = self.params.get("model_path", "").strip()
            model_name = self.params.get("model", "deepseek-ai/Janus-Pro-1B")

            if not model_path:
                raise Exception("请先配置模型路径")

            self.progress_updated.emit(10)

            # 使用官方Janus实现
            try:
                self.progress_updated.emit(20)
                
                # 创建官方Janus生成器
                generator = OfficialJanusGenerator(model_path=model_path)
                
                # 加载模型
                if not generator.load_model():
                    raise Exception("模型加载失败")
                
                self.progress_updated.emit(40)
                
                # 使用官方Janus生成
                img_size = int(self.params.get("img_size", 384))
                image_paths = generator.generate_image(
                    prompt=prompt,
                    temperature=temperature,
                    parallel_size=batch_size,
                    cfg_weight=cfg_weight,
                    img_size=img_size,
                    output_dir="output/temp"
                )
                
                # 将生成的图片路径转换为图片数组
                images = []
                for path in image_paths:
                    img = Image.open(path)
                    images.append(np.array(img))
                
            except Exception as e:
                # 如果Janus生成失败，提供详细的错误信息和解决建议
                error_msg = f"Janus生成失败: {str(e)}"
                self.logger.error(error_msg)
                
                # 根据错误类型提供具体建议
                if "CUDA out of memory" in str(e):
                    error_msg += "\n建议：减少批量大小或使用更小的图像尺寸"
                elif "No module named" in str(e):
                    error_msg += "\n建议：检查是否正确安装了janus库和相关依赖"
                elif "模型路径不存在" in str(e):
                    error_msg += "\n建议：检查模型路径配置是否正确"
                elif "模型文件可能不完整" in str(e):
                    error_msg += "\n建议：重新下载完整的模型文件"
                
                raise Exception(error_msg)

            self.progress_updated.emit(80)

            # 保存图片
            last_path = None
            for i, img_array in enumerate(images):
                # 确保是numpy数组
                if isinstance(img_array, list):
                    img_array = np.array(img_array)
                
                # 转换为PIL图像
                img = Image.fromarray(img_array.astype(np.uint8))
                
                index = start_index + i
                filepath = output_dir / f"Janus{index}.png"
                img.save(filepath)
                last_path = filepath

                # 写入数据库
                try:
                    db.add_photo({
                        "filename": f"Janus{index}.png",
                        "filepath": str(filepath.resolve()),
                        "width": img.size[0],
                        "height": img.size[1],
                        "format": "PNG",
                        "is_ai_generated": True,
                        "ai_metadata": {
                            "model_name": model_name,
                            "positive_prompt": prompt,
                            "seed": seed,
                            "cfg_weight": cfg_weight,
                            "temperature": temperature,
                            "top_p": top_p,
                            "batch_size": batch_size,
                        },
                    })
                except Exception:
                    pass

            # 更新序号
            try:
                db.execute(
                    "INSERT INTO settings(key,value,updated_date) VALUES(?,?,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_date=datetime('now')",
                    ("janus_t2i_last_index", str(start_index + batch_size)),
                )
            except Exception:
                pass

            self.progress_updated.emit(95)

            # 返回最后一张图片
            from PIL.ImageQt import ImageQt
            qimg = ImageQt(img)
            pix = QPixmap.fromImage(qimg)
            self.progress_updated.emit(100)
            self.finished.emit({"pixmap": pix, "path": str(last_path) if last_path else ""})

        except Exception as e:
            self.error_occurred.emit(str(e))




class JanusText2ImagePlugin(BasePlugin):
    """Janus 文生图插件"""
    
    def __init__(self) -> None:
        super().__init__()
        self.main_widget: Optional[JanusT2IMainWidget] = None
        self.logger = logging.getLogger(__name__)
        
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="Janus文生图",
            version="1.0.0",
            description="基于Janus模型的文本到图像生成插件",
            author="Photo666"
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.logger.info("Janus文生图插件初始化中...")
            return True
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """返回菜单动作"""
        return [
            {
                "text": "打开Janus生图",
                "category": "工具",
                "callback": self.show_main_dialog,
                "shortcut": "Ctrl+Shift+J"
            }
        ]
    
    def show_main_dialog(self):
        """显示主对话框"""
        try:
            if self.main_widget is None:
                self.main_widget = JanusT2IMainWidget()
                # 连接生成请求信号
                self.main_widget.generate_requested.connect(self.handle_generate_request)
            
            self.main_widget.show()
            self.main_widget.raise_()
            self.main_widget.activateWindow()
            
        except Exception as e:
            self.logger.error(f"显示对话框失败: {e}")
            QMessageBox.critical(None, "错误", f"显示对话框失败: {e}")
    
    def handle_generate_request(self, params: Dict[str, Any]):
        """处理生成请求"""
        try:
            # 创建工作线程
            self.worker = JanusGenerateWorker(params)
            
            # 连接信号
            self.worker.progress_updated.connect(self.main_widget.update_progress)
            self.worker.finished.connect(self.on_generation_finished)
            self.worker.error_occurred.connect(self.on_generation_error)
            
            # 启动生成
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"启动生成失败: {e}")
            QMessageBox.critical(self.main_widget, "错误", f"启动生成失败: {e}")
    
    def on_generation_finished(self, result: Dict[str, Any]):
        """生成完成回调"""
        try:
            pixmap = result.get("pixmap")
            if pixmap and self.main_widget:
                self.main_widget.show_generated_image(pixmap)
                QMessageBox.information(self.main_widget, "成功", "图像生成完成！")
            
        except Exception as e:
            self.logger.error(f"处理生成结果失败: {e}")
    
    def on_generation_error(self, error_msg: str):
        """生成错误回调"""
        if self.main_widget:
            QMessageBox.critical(self.main_widget, "生成失败", f"图像生成失败: {error_msg}")
    
    def generate_from_main_window(self, params: Dict[str, Any], janus_page):
        """从主窗口调用的生成方法"""
        try:
            # 创建工作线程
            self.worker = JanusGenerateWorker(params)
            
            # 连接信号到主窗口页面
            self.worker.progress_updated.connect(janus_page.set_progress)
            
            def _on_finish(result: Dict[str, Any]):
                try:
                    pixmap = result.get("pixmap")
                    if pixmap:
                        janus_page.show_generated_image(pixmap)
                        self.logger.info("生成完成，已显示图片")
                    else:
                        self.logger.error("生成失败，未返回图片")
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(None, "Janus", "生成失败，未返回图片")
                except Exception as e:
                    self.logger.error(f"显示生成图片失败: {e}")
            
            def _on_error(error_msg: str):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Janus", f"生成出错: {error_msg}")
            
            self.worker.finished.connect(_on_finish)
            self.worker.error_occurred.connect(_on_error)
            
            # 启动生成
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"启动生成失败: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "错误", f"启动生成失败: {e}")

    def shutdown(self) -> None:
        """关闭插件"""
        if self.main_widget:
            self.main_widget.close()
            self.main_widget = None
    
    def cleanup(self) -> None:
        """清理资源"""
        self.shutdown()


# 插件入口点
def create_plugin() -> BasePlugin:
    return JanusText2ImagePlugin()