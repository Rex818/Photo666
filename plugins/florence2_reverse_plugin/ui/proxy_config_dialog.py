"""
代理配置对话框
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton,
    QGroupBox, QTextEdit, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from plugins.florence2_reverse_plugin.core.proxy_manager import ProxyManager


class ProxyConfigDialog(QDialog):
    """代理配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxy_manager = ProxyManager()
        self.init_ui()
        self.load_current_settings()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("代理服务器配置")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 代理模式选择
        mode_group = QGroupBox("代理模式")
        mode_layout = QVBoxLayout()
        
        self.auto_detect_radio = QRadioButton("自动检测浏览器代理设置")
        self.manual_proxy_radio = QRadioButton("手动配置代理服务器")
        self.no_proxy_radio = QRadioButton("不使用代理")
        
        mode_layout.addWidget(self.auto_detect_radio)
        mode_layout.addWidget(self.manual_proxy_radio)
        mode_layout.addWidget(self.no_proxy_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 手动代理配置
        self.manual_group = QGroupBox("手动代理配置")
        manual_layout = QGridLayout()
        
        manual_layout.addWidget(QLabel("HTTP代理:"), 0, 0)
        self.http_proxy_edit = QLineEdit()
        self.http_proxy_edit.setPlaceholderText("http://proxy:port")
        manual_layout.addWidget(self.http_proxy_edit, 0, 1)
        
        manual_layout.addWidget(QLabel("HTTPS代理:"), 1, 0)
        self.https_proxy_edit = QLineEdit()
        self.https_proxy_edit.setPlaceholderText("http://proxy:port")
        manual_layout.addWidget(self.https_proxy_edit, 1, 1)
        
        manual_layout.addWidget(QLabel("FTP代理:"), 2, 0)
        self.ftp_proxy_edit = QLineEdit()
        self.ftp_proxy_edit.setPlaceholderText("http://proxy:port")
        manual_layout.addWidget(self.ftp_proxy_edit, 2, 1)
        
        # 测试按钮
        test_layout = QHBoxLayout()
        self.test_http_btn = QPushButton("测试HTTP代理")
        self.test_https_btn = QPushButton("测试HTTPS代理")
        test_layout.addWidget(self.test_http_btn)
        test_layout.addWidget(self.test_https_btn)
        test_layout.addStretch()
        manual_layout.addLayout(test_layout, 3, 0, 1, 2)
        
        self.manual_group.setLayout(manual_layout)
        layout.addWidget(self.manual_group)
        
        # 当前状态显示
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新状态")
        self.apply_btn = QPushButton("应用设置")
        self.cancel_btn = QPushButton("取消")
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.auto_detect_radio.toggled.connect(self.on_mode_changed)
        self.manual_proxy_radio.toggled.connect(self.on_mode_changed)
        self.no_proxy_radio.toggled.connect(self.on_mode_changed)
        
        self.test_http_btn.clicked.connect(self.test_http_proxy)
        self.test_https_btn.clicked.connect(self.test_https_proxy)
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.apply_btn.clicked.connect(self.apply_settings)
        self.cancel_btn.clicked.connect(self.reject)
    
    def load_current_settings(self):
        """加载当前设置"""
        proxy_info = self.proxy_manager.get_proxy_info()
        
        # 设置模式
        if proxy_info["use_manual"]:
            self.manual_proxy_radio.setChecked(True)
        elif proxy_info["auto_detect"]:
            self.auto_detect_radio.setChecked(True)
        else:
            self.no_proxy_radio.setChecked(True)
        
        # 设置手动代理值
        manual_proxy = proxy_info["manual_proxy"]
        self.http_proxy_edit.setText(manual_proxy.get("http", ""))
        self.https_proxy_edit.setText(manual_proxy.get("https", ""))
        self.ftp_proxy_edit.setText(manual_proxy.get("ftp", ""))
        
        # 更新状态显示
        self.refresh_status()
    
    def on_mode_changed(self):
        """模式改变时的处理"""
        self.manual_group.setEnabled(self.manual_proxy_radio.isChecked())
    
    def test_http_proxy(self):
        """测试HTTP代理"""
        proxy_url = self.http_proxy_edit.text().strip()
        if not proxy_url:
            QMessageBox.warning(self, "警告", "请输入HTTP代理地址")
            return
        
        if not proxy_url.startswith(('http://', 'https://')):
            proxy_url = f"http://{proxy_url}"
        
        self.test_http_btn.setEnabled(False)
        self.test_http_btn.setText("测试中...")
        
        try:
            success = self.proxy_manager.test_proxy_connection(proxy_url)
            if success:
                QMessageBox.information(self, "成功", "HTTP代理连接测试成功！")
            else:
                QMessageBox.warning(self, "失败", "HTTP代理连接测试失败！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试过程中发生错误：{str(e)}")
        finally:
            self.test_http_btn.setEnabled(True)
            self.test_http_btn.setText("测试HTTP代理")
    
    def test_https_proxy(self):
        """测试HTTPS代理"""
        proxy_url = self.https_proxy_edit.text().strip()
        if not proxy_url:
            QMessageBox.warning(self, "警告", "请输入HTTPS代理地址")
            return
        
        if not proxy_url.startswith(('http://', 'https://')):
            proxy_url = f"http://{proxy_url}"
        
        self.test_https_btn.setEnabled(False)
        self.test_https_btn.setText("测试中...")
        
        try:
            success = self.proxy_manager.test_proxy_connection(proxy_url)
            if success:
                QMessageBox.information(self, "成功", "HTTPS代理连接测试成功！")
            else:
                QMessageBox.warning(self, "失败", "HTTPS代理连接测试失败！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试过程中发生错误：{str(e)}")
        finally:
            self.test_https_btn.setEnabled(True)
            self.test_https_btn.setText("测试HTTPS代理")
    
    def refresh_status(self):
        """刷新状态显示"""
        proxy_info = self.proxy_manager.get_proxy_info()
        
        status_text = []
        status_text.append("=== 当前代理设置 ===")
        
        if proxy_info["use_manual"]:
            status_text.append("模式: 手动配置")
            manual_proxy = proxy_info["manual_proxy"]
            for protocol, url in manual_proxy.items():
                if url:
                    status_text.append(f"{protocol.upper()}: {url}")
                else:
                    status_text.append(f"{protocol.upper()}: 未设置")
        elif proxy_info["auto_detect"]:
            status_text.append("模式: 自动检测")
            browser_proxy = proxy_info["browser_proxy"]
            if browser_proxy:
                for protocol, url in browser_proxy.items():
                    status_text.append(f"{protocol.upper()}: {url}")
            else:
                status_text.append("未检测到浏览器代理设置")
        else:
            status_text.append("模式: 不使用代理")
        
        status_text.append("\n=== 环境变量 ===")
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY"]:
            value = os.environ.get(var, "")
            status_text.append(f"{var}: {value if value else '未设置'}")
        
        self.status_text.setPlainText("\n".join(status_text))
    
    def apply_settings(self):
        """应用设置"""
        try:
            if self.auto_detect_radio.isChecked():
                self.proxy_manager.enable_auto_detect()
            elif self.manual_proxy_radio.isChecked():
                http_proxy = self.http_proxy_edit.text().strip()
                https_proxy = self.https_proxy_edit.text().strip()
                ftp_proxy = self.ftp_proxy_edit.text().strip()
                
                self.proxy_manager.set_manual_proxy(http_proxy, https_proxy, ftp_proxy)
            else:  # no_proxy_radio
                self.proxy_manager.disable_auto_detect()
                self.proxy_manager.set_manual_proxy("", "", "")
            
            # 应用代理到环境变量
            self.proxy_manager.apply_proxy_to_environment()
            
            QMessageBox.information(self, "成功", "代理设置已应用！")
            self.refresh_status()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用设置时发生错误：{str(e)}")
    
    def accept(self):
        """确认时应用设置"""
        self.apply_settings()
        super().accept() 