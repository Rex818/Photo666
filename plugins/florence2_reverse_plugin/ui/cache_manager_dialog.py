#!/usr/bin/env python3
"""
缓存管理对话框
"""

import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QSpinBox, QGroupBox,
    QProgressBar, QTextEdit, QSplitter, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

class CacheManagerDialog(QDialog):
    """缓存管理对话框"""
    
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("Florence2 缓存管理")
        self.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：缓存信息和控制
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)
        
        # 右侧：缓存详情
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 500])
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        main_layout.addLayout(bottom_layout)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_cache_info)
        bottom_layout.addWidget(self.refresh_btn)
        
        # 清理过期缓存按钮
        self.cleanup_btn = QPushButton("清理过期缓存")
        self.cleanup_btn.clicked.connect(self.cleanup_expired_cache)
        bottom_layout.addWidget(self.cleanup_btn)
        
        # 清除所有缓存按钮
        self.clear_all_btn = QPushButton("清除所有缓存")
        self.clear_all_btn.clicked.connect(self.clear_all_cache)
        bottom_layout.addWidget(self.clear_all_btn)
        
        bottom_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        # 初始化数据
        self.refresh_cache_info()
        
    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QGroupBox("缓存配置")
        layout = QVBoxLayout(left_widget)
        
        # 缓存统计
        stats_group = QGroupBox("缓存统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.total_models_label = QLabel("缓存模型数量: 0")
        stats_layout.addWidget(self.total_models_label)
        
        self.max_cache_label = QLabel("最大缓存数量: 2")
        stats_layout.addWidget(self.max_cache_label)
        
        self.timeout_label = QLabel("缓存超时时间: 3600秒")
        stats_layout.addWidget(self.timeout_label)
        
        layout.addWidget(stats_group)
        
        # 缓存配置
        config_group = QGroupBox("缓存配置")
        config_layout = QVBoxLayout(config_group)
        
        # 最大缓存数量
        max_cache_layout = QHBoxLayout()
        max_cache_layout.addWidget(QLabel("最大缓存数量:"))
        self.max_cache_spinbox = QSpinBox()
        self.max_cache_spinbox.setRange(1, 10)
        self.max_cache_spinbox.setValue(2)
        max_cache_layout.addWidget(self.max_cache_spinbox)
        config_layout.addLayout(max_cache_layout)
        
        # 超时时间
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("超时时间(秒):"))
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(300, 7200)
        self.timeout_spinbox.setValue(3600)
        self.timeout_spinbox.setSingleStep(300)
        timeout_layout.addWidget(self.timeout_spinbox)
        config_layout.addLayout(timeout_layout)
        
        # 应用配置按钮
        self.apply_config_btn = QPushButton("应用配置")
        self.apply_config_btn.clicked.connect(self.apply_cache_config)
        config_layout.addWidget(self.apply_config_btn)
        
        layout.addWidget(config_group)
        
        # 内存使用情况
        memory_group = QGroupBox("内存使用")
        memory_layout = QVBoxLayout(memory_group)
        
        self.memory_label = QLabel("GPU内存使用: 未知")
        memory_layout.addWidget(self.memory_label)
        
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_progress.setValue(0)
        memory_layout.addWidget(self.memory_progress)
        
        layout.addWidget(memory_group)
        
        layout.addStretch()
        
        return left_widget
        
    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QGroupBox("缓存详情")
        layout = QVBoxLayout(right_widget)
        
        # 缓存模型表格
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(5)
        self.cache_table.setHorizontalHeaderLabels([
            "模型名称", "加载时间", "使用次数", "最后使用", "状态"
        ])
        
        # 设置表格属性
        header = self.cache_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.cache_table)
        
        # 日志显示
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        return right_widget
        
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_cache_info)
        self.timer.start(5000)  # 每5秒刷新一次
        
    def refresh_cache_info(self):
        """刷新缓存信息"""
        try:
            cache_info = self.plugin.get_cache_info()
            
            # 更新统计信息
            self.total_models_label.setText(f"缓存模型数量: {cache_info.get('total_models', 0)}")
            self.max_cache_label.setText(f"最大缓存数量: {cache_info.get('max_cache_size', 2)}")
            self.timeout_label.setText(f"缓存超时时间: {cache_info.get('cache_timeout', 3600)}秒")
            
            # 更新配置控件
            self.max_cache_spinbox.setValue(cache_info.get('max_cache_size', 2))
            self.timeout_spinbox.setValue(cache_info.get('cache_timeout', 3600))
            
            # 更新缓存表格
            self.update_cache_table(cache_info)
            
            # 更新内存使用情况
            self.update_memory_info()
            
        except Exception as e:
            self.log_message(f"刷新缓存信息失败: {str(e)}")
            
    def update_cache_table(self, cache_info):
        """更新缓存表格"""
        try:
            cached_models = cache_info.get('cached_models', {})
            self.cache_table.setRowCount(len(cached_models))
            
            for row, (model_name, info) in enumerate(cached_models.items()):
                # 模型名称
                self.cache_table.setItem(row, 0, QTableWidgetItem(model_name))
                
                # 加载时间
                loaded_at = info.get('loaded_at', 'unknown')
                if isinstance(loaded_at, datetime):
                    loaded_at = loaded_at.strftime('%H:%M:%S')
                self.cache_table.setItem(row, 1, QTableWidgetItem(str(loaded_at)))
                
                # 使用次数
                use_count = info.get('use_count', 0)
                self.cache_table.setItem(row, 2, QTableWidgetItem(str(use_count)))
                
                # 最后使用时间
                last_used = info.get('last_used', 'unknown')
                if isinstance(last_used, datetime):
                    last_used = last_used.strftime('%H:%M:%S')
                self.cache_table.setItem(row, 3, QTableWidgetItem(str(last_used)))
                
                # 状态
                is_expired = info.get('is_expired', False)
                status = "已过期" if is_expired else "正常"
                status_item = QTableWidgetItem(status)
                if is_expired:
                    status_item.setBackground(Qt.GlobalColor.red)
                else:
                    status_item.setBackground(Qt.GlobalColor.green)
                self.cache_table.setItem(row, 4, status_item)
                
        except Exception as e:
            self.log_message(f"更新缓存表格失败: {str(e)}")
            
    def update_memory_info(self):
        """更新内存使用情况"""
        try:
            # 这里可以添加GPU内存监控逻辑
            # 暂时显示模拟数据
            import torch
            if torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                memory_reserved = torch.cuda.memory_reserved() / 1024**3   # GB
                self.memory_label.setText(f"GPU内存使用: {memory_allocated:.2f}GB / {memory_reserved:.2f}GB")
                
                # 计算使用百分比
                if memory_reserved > 0:
                    usage_percent = (memory_allocated / memory_reserved) * 100
                    self.memory_progress.setValue(int(usage_percent))
            else:
                self.memory_label.setText("GPU内存使用: 未使用GPU")
                self.memory_progress.setValue(0)
                
        except Exception as e:
            self.memory_label.setText("GPU内存使用: 获取失败")
            self.memory_progress.setValue(0)
            
    def apply_cache_config(self):
        """应用缓存配置"""
        try:
            max_cache_size = self.max_cache_spinbox.value()
            cache_timeout = self.timeout_spinbox.value()
            
            self.plugin.set_cache_config(max_cache_size, cache_timeout)
            self.log_message(f"缓存配置已更新: 最大数量={max_cache_size}, 超时时间={cache_timeout}秒")
            
            # 刷新显示
            self.refresh_cache_info()
            
        except Exception as e:
            self.log_message(f"应用缓存配置失败: {str(e)}")
            
    def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            self.plugin.cleanup_expired_cache()
            self.log_message("过期缓存清理完成")
            
            # 刷新显示
            self.refresh_cache_info()
            
        except Exception as e:
            self.log_message(f"清理过期缓存失败: {str(e)}")
            
    def clear_all_cache(self):
        """清除所有缓存"""
        try:
            self.plugin.clear_cache()
            self.log_message("所有缓存已清除")
            
            # 刷新显示
            self.refresh_cache_info()
            
        except Exception as e:
            self.log_message(f"清除所有缓存失败: {str(e)}")
            
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        super().closeEvent(event) 