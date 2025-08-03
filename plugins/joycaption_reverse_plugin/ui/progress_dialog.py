"""
JoyCaption插件进度对话框
"""

import logging
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QGroupBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class JoyCaptionProgressDialog(QDialog):
    """JoyCaption进度对话框"""
    
    def __init__(self, parent=None, title: str = "JoyCaption处理进度"):
        super().__init__(parent)
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.ui.progress_dialog")
        
        # 进度回调
        self.progress_callback = None
        
        # 状态变量
        self.current_stage = ""
        self.current_progress = 0
        self.current_message = ""
        self.is_cancelled = False
        
        self.setup_ui(title)
    
    def setup_ui(self, title: str):
        """设置用户界面"""
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 当前阶段显示
        stage_group = QGroupBox("当前阶段")
        stage_layout = QVBoxLayout()
        
        self.stage_label = QLabel("准备中...")
        self.stage_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stage_layout.addWidget(self.stage_label)
        
        stage_group.setLayout(stage_layout)
        main_layout.addWidget(stage_group)
        
        # 进度条
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 消息显示
        message_group = QGroupBox("处理信息")
        message_layout = QVBoxLayout()
        
        self.message_text = QTextEdit()
        self.message_text.setMaximumHeight(150)
        self.message_text.setReadOnly(True)
        message_layout.addWidget(self.message_text)
        
        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_operation)
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def update_progress(self, stage: str, progress: int, message: str):
        """更新进度"""
        try:
            self.current_stage = stage
            self.current_progress = progress
            self.current_message = message
            
            # 更新UI
            self.stage_label.setText(stage)
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"{progress}%")
            
            # 添加消息到日志
            if message:
                self.message_text.append(f"[{stage}] {message}")
                # 滚动到底部
                self.message_text.verticalScrollBar().setValue(
                    self.message_text.verticalScrollBar().maximum()
                )
            
            # 处理完成
            if progress >= 100:
                self.progress_completed()
                
        except Exception as e:
            self.logger.error(f"更新进度失败: {str(e)}")
    
    def progress_completed(self):
        """进度完成"""
        try:
            self.cancel_button.setEnabled(False)
            self.close_button.setEnabled(True)
            self.stage_label.setText("处理完成")
            self.message_text.append("✅ 处理完成")
            
        except Exception as e:
            self.logger.error(f"处理进度完成失败: {str(e)}")
    
    def cancel_operation(self):
        """取消操作"""
        try:
            self.is_cancelled = True
            self.cancel_button.setEnabled(False)
            self.stage_label.setText("正在取消...")
            self.message_text.append("⚠️ 用户取消操作")
            
            # 调用取消回调
            if self.progress_callback:
                self.progress_callback("cancelled", 0, "用户取消操作")
            
        except Exception as e:
            self.logger.error(f"取消操作失败: {str(e)}")
    
    def add_message(self, message: str):
        """添加消息"""
        try:
            self.message_text.append(message)
            # 滚动到底部
            self.message_text.verticalScrollBar().setValue(
                self.message_text.verticalScrollBar().maximum()
            )
        except Exception as e:
            self.logger.error(f"添加消息失败: {str(e)}")
    
    def clear_messages(self):
        """清空消息"""
        try:
            self.message_text.clear()
        except Exception as e:
            self.logger.error(f"清空消息失败: {str(e)}")
    
    def reset(self):
        """重置对话框"""
        try:
            self.current_stage = ""
            self.current_progress = 0
            self.current_message = ""
            self.is_cancelled = False
            
            self.stage_label.setText("准备中...")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            self.message_text.clear()
            
            self.cancel_button.setEnabled(True)
            self.close_button.setEnabled(False)
            
        except Exception as e:
            self.logger.error(f"重置对话框失败: {str(e)}")
    
    def is_cancelled_operation(self) -> bool:
        """检查是否已取消操作"""
        return self.is_cancelled
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            if self.is_cancelled_operation():
                event.accept()
            else:
                # 如果操作未完成，询问用户
                reply = self.question("确认", "确定要关闭进度对话框吗？")
                if reply:
                    event.accept()
                else:
                    event.ignore()
                    
        except Exception as e:
            self.logger.error(f"关闭事件处理失败: {str(e)}")
            event.accept()
    
    def question(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, title, message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        except Exception as e:
            self.logger.error(f"显示确认对话框失败: {str(e)}")
            return True 