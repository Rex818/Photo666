"""
进度对话框
显示模型加载、下载、推理等操作的进度
"""

import sys
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel,
    QPushButton, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


class ReverseInferenceProgressDialog(QDialog):
    """反推进度对话框"""
    
    # 信号定义
    cancelled = pyqtSignal()  # 取消信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cancel_callback = None
        self.is_cancelled = False
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("Florence2图片反推进度")
        self.setModal(True)
        self.resize(500, 300)
        self.setMinimumWidth(450)
        
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 当前步骤组
        step_group = self.create_step_group()
        main_layout.addWidget(step_group)
        
        # 总体进度组
        progress_group = self.create_progress_group()
        main_layout.addWidget(progress_group)
        
        # 详细信息组
        detail_group = self.create_detail_group()
        main_layout.addWidget(detail_group)
        
        # 按钮组
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_step_group(self) -> QGroupBox:
        """创建当前步骤组"""
        group = QGroupBox("当前步骤")
        layout = QVBoxLayout()
        
        self.step_label = QLabel("准备中...")
        self.step_label.setWordWrap(True)
        self.step_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        layout.addWidget(self.step_label)
        group.setLayout(layout)
        return group
    
    def create_progress_group(self) -> QGroupBox:
        """创建总体进度组"""
        group = QGroupBox("总体进度")
        layout = QVBoxLayout()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        
        # 进度百分比标签
        self.progress_label = QLabel("0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3498db;")
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        group.setLayout(layout)
        return group
    
    def create_detail_group(self) -> QGroupBox:
        """创建详细信息组"""
        group = QGroupBox("详细信息")
        layout = QVBoxLayout()
        
        # 详细信息文本
        self.detail_text = QTextEdit()
        self.detail_text.setMaximumHeight(80)
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("等待操作开始...")
        
        # 速度信息标签
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        
        layout.addWidget(self.detail_text)
        layout.addWidget(self.speed_label)
        group.setLayout(layout)
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        
        layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_operation)
        
        layout.addWidget(self.cancel_btn)
        
        return layout
    
    def setup_timer(self):
        """设置定时器用于更新进度动画"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.animation_dots = 0
    
    def update_animation(self):
        """更新动画效果"""
        self.animation_dots = (self.animation_dots + 1) % 4
        dots = "." * self.animation_dots
        current_text = self.step_label.text()
        if current_text.endswith("..."):
            base_text = current_text[:-3]
        else:
            base_text = current_text
        self.step_label.setText(f"{base_text}{dots}")
    
    def set_cancel_callback(self, callback: Callable[[], None]):
        """设置取消回调函数"""
        self.cancel_callback = callback
    
    def update_progress(self, step: str, progress: int, message: str, speed: str = ""):
        """更新进度显示
        
        Args:
            step: 步骤名称 ('finding', 'downloading', 'loading', 'inferring')
            progress: 进度百分比 (0-100)
            message: 详细消息
            speed: 速度信息 (可选)
        """
        try:
            # 更新步骤
            step_display_names = {
                'finding': '查找模型',
                'downloading': '下载模型',
                'loading': '加载模型',
                'inferring': '推理图片',
                'processing': '处理结果'
            }
            
            step_display = step_display_names.get(step, step)
            self.step_label.setText(f"{step_display}...")
            
            # 更新进度条
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"{progress}%")
            
            # 更新详细信息
            self.detail_text.append(f"[{step_display}] {message}")
            
            # 滚动到底部
            scrollbar = self.detail_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # 更新速度信息
            if speed:
                self.speed_label.setText(speed)
            
            # 启动动画
            if not self.timer.isActive():
                self.timer.start(500)  # 每500ms更新一次
            
            # 处理完成时停止动画
            if progress >= 100:
                self.timer.stop()
                self.step_label.setText("完成")
            
        except Exception as e:
            print(f"更新进度失败: {e}")
    
    def update_step_progress(self, step: str, current: int, total: int, message: str = ""):
        """更新步骤进度
        
        Args:
            step: 步骤名称
            current: 当前数量
            total: 总数量
            message: 额外消息
        """
        if total > 0:
            progress = int((current / total) * 100)
            if message:
                detail_message = f"{message} ({current}/{total})"
            else:
                detail_message = f"进度: {current}/{total}"
            
            self.update_progress(step, progress, detail_message)
    
    def update_download_progress(self, current_bytes: int, total_bytes: int, speed: str = ""):
        """更新下载进度
    
        Args:
            current_bytes: 当前已下载字节数
            total_bytes: 总字节数
            speed: 下载速度
        """
        if total_bytes > 0:
            progress = int((current_bytes / total_bytes) * 100)
            
            # 格式化字节数
            current_mb = current_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            
            message = f"下载中: {current_mb:.1f}MB/{total_mb:.1f}MB"
            
            self.update_progress("downloading", progress, message, speed)
    
    def update_inference_progress(self, current: int, total: int, current_file: str = ""):
        """更新推理进度
    
        Args:
            current: 当前处理的图片数量
            total: 总图片数量
            current_file: 当前处理的文件名
        """
        if total > 0:
            progress = int((current / total) * 100)
            
            if current_file:
                message = f"处理图片: {current_file} ({current}/{total})"
            else:
                message = f"处理进度: {current}/{total}"
            
            self.update_progress("inferring", progress, message)
    
    def set_error(self, error_message: str):
        """设置错误状态"""
        self.timer.stop()
        self.step_label.setText("错误")
        self.step_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.detail_text.append(f"[错误] {error_message}")
        self.cancel_btn.setText("关闭")
    
    def set_success(self, message: str = "操作完成"):
        """设置成功状态"""
        self.timer.stop()
        self.step_label.setText("完成")
        self.step_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self.detail_text.append(f"[完成] {message}")
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setEnabled(True)  # 重新启用按钮
    
    def cancel_operation(self):
        """取消操作"""
        # 如果操作已完成（进度100%），直接关闭对话框
        if self.progress_bar.value() >= 100:
            self.accept()
            return
        
        if self.is_cancelled:
            # 如果已经取消，则关闭对话框
            self.accept()
            return
        
        # 设置取消状态
        self.is_cancelled = True
        self.timer.stop()
        self.step_label.setText("正在取消...")
        self.step_label.setStyleSheet("font-weight: bold; color: #f39c12;")
        self.cancel_btn.setEnabled(False)
        
        # 调用取消回调
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                print(f"取消回调执行失败: {e}")
        
        # 发送取消信号
        self.cancelled.emit()
    
    def reset(self):
        """重置对话框状态"""
        self.is_cancelled = False
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.step_label.setText("准备中...")
        self.step_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.detail_text.clear()
        self.speed_label.clear()
        self.cancel_btn.setText("取消")
        self.cancel_btn.setEnabled(True)
        self.timer.stop()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果操作正在进行中，询问用户是否确认关闭
        if not self.is_cancelled and self.progress_bar.value() < 100:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "确认关闭", 
                "操作正在进行中，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # 停止定时器
        self.timer.stop()
        
        # 调用取消回调
        if self.cancel_callback and not self.is_cancelled:
            try:
                self.cancel_callback()
            except Exception as e:
                print(f"关闭时取消回调执行失败: {e}")
        
        super().closeEvent(event) 