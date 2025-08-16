"""
Janus插件进度对话框
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal


class JanusProgressDialog(QDialog):
    """Janus插件进度对话框"""
    
    # 信号定义
    cancelled = pyqtSignal()  # 取消信号
    
    def __init__(self, title: str = "处理进度", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.ui.progress_dialog")
        
        self.setWindowTitle(title)
        self.setMinimumSize(500, 300)
        self.setModal(True)
        
        self.setup_ui()
        
        self.logger.info("Janus进度对话框初始化完成")
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 状态标签
        self.status_label = QLabel("准备中...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # 主进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 详细进度标签
        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.on_cancel)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def update_progress(self, step: str, progress: int, message: str):
        """更新进度"""
        try:
            self.status_label.setText(f"{step}: {message}")
            self.progress_bar.setValue(progress)
            self.detail_label.setText(f"进度: {progress}%")
            
            # 添加日志
            self.log_text.append(f"[{step}] {message}")
            
        except Exception as e:
            self.logger.error(f"更新进度失败: {str(e)}")
    
    def update_download_progress(self, current_bytes: int, total_bytes: int, speed: str):
        """更新下载进度"""
        try:
            if total_bytes > 0:
                progress = int((current_bytes / total_bytes) * 100)
                downloaded_mb = current_bytes / (1024 * 1024)
                total_mb = total_bytes / (1024 * 1024)
                
                message = f"下载进度: {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({speed})"
                self.update_progress("downloading", progress, message)
            
        except Exception as e:
            self.logger.error(f"更新下载进度失败: {str(e)}")
    
    def update_inference_progress(self, current: int, total: int, current_file: str):
        """更新推理进度"""
        try:
            if total > 0:
                progress = int((current / total) * 100)
                message = f"处理文件: {current_file} ({current}/{total})"
                self.update_progress("inference", progress, message)
            
        except Exception as e:
            self.logger.error(f"更新推理进度失败: {str(e)}")
    
    def set_completed(self, message: str = "处理完成"):
        """设置完成状态"""
        try:
            self.status_label.setText(message)
            self.progress_bar.setValue(100)
            self.detail_label.setText("处理完成")
            self.cancel_btn.setText("关闭")
            self.cancel_btn.clicked.disconnect()
            self.cancel_btn.clicked.connect(self.accept)
            
            self.log_text.append(f"[完成] {message}")
            
        except Exception as e:
            self.logger.error(f"设置完成状态失败: {str(e)}")
    
    def set_error(self, error_message: str):
        """设置错误状态"""
        try:
            self.status_label.setText("处理失败")
            self.detail_label.setText(error_message)
            self.cancel_btn.setText("关闭")
            self.cancel_btn.clicked.disconnect()
            self.cancel_btn.clicked.connect(self.accept)
            
            self.log_text.append(f"[错误] {error_message}")
            
        except Exception as e:
            self.logger.error(f"设置错误状态失败: {str(e)}")
    
    def on_cancel(self):
        """取消操作"""
        try:
            self.logger.info("用户取消操作")
            self.cancelled.emit()
            self.reject()
            
        except Exception as e:
            self.logger.error(f"取消操作失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            self.cancelled.emit()
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭事件处理失败: {str(e)}")
            event.accept()
