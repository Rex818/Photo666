#!/usr/bin/env python3
"""
插件配置对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGroupBox, QCheckBox, QMessageBox,
    QFormLayout, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt
import json
import structlog
from pathlib import Path


class PluginConfigDialog(QDialog):
    """插件配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = structlog.get_logger("picman.gui.plugin_config")
        self.config_file = Path("config/plugins/google_translate_plugin.json")
        self.config = self.load_config()
        
        self.init_ui()
        self.load_config_to_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Google翻译插件配置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QFormLayout(info_group)
        
        self.plugin_name = QLabel("Google翻译插件")
        self.plugin_version = QLabel("1.0.0")
        self.plugin_description = QLabel("使用免费的googletrans库进行标签翻译")
        self.plugin_author = QLabel("PicMan Team")
        
        info_layout.addRow("名称:", self.plugin_name)
        info_layout.addRow("版本:", self.plugin_version)
        info_layout.addRow("描述:", self.plugin_description)
        info_layout.addRow("作者:", self.plugin_author)
        
        layout.addWidget(info_group)
        
        # 配置选项
        config_group = QGroupBox("配置选项")
        config_layout = QFormLayout(config_group)
        
        # 启用插件
        self.enable_plugin = QCheckBox("启用插件")
        config_layout.addRow("状态:", self.enable_plugin)
        
        # 源语言
        self.source_language = QComboBox()
        self.source_language.addItems([
            "en", "zh-CN", "zh-TW", "ja", "ko", "fr", "de", "es", "ru", "auto"
        ])
        # 添加标签说明
        source_labels = {
            "en": "英语",
            "zh-CN": "中文（简体）",
            "zh-TW": "中文（繁体）",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语",
            "auto": "自动检测"
        }
        for i in range(self.source_language.count()):
            code = self.source_language.itemText(i)
            label = source_labels.get(code, code)
            self.source_language.setItemText(i, f"{code} - {label}")
        config_layout.addRow("源语言:", self.source_language)
        
        # 目标语言
        self.target_language = QComboBox()
        self.target_language.addItems([
            "zh-CN", "zh-TW", "en", "ja", "ko", "fr", "de", "es", "ru"
        ])
        # 添加标签说明
        target_labels = {
            "en": "英语",
            "zh-CN": "中文（简体）",
            "zh-TW": "中文（繁体）",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语"
        }
        for i in range(self.target_language.count()):
            code = self.target_language.itemText(i)
            label = target_labels.get(code, code)
            self.target_language.setItemText(i, f"{code} - {label}")
        config_layout.addRow("目标语言:", self.target_language)
        
        layout.addWidget(config_group)
        
        # 说明文本
        help_group = QGroupBox("使用说明")
        help_layout = QVBoxLayout(help_group)
        
        help_text = QTextEdit()
        help_text.setMaximumHeight(120)
        help_text.setPlainText("""
使用免费的googletrans库：

1. 无需申请API密钥
2. 无需付费
3. 直接使用Google翻译服务
4. 支持多种语言翻译
5. 自动缓存翻译结果

注意：googletrans库使用非官方的Google翻译接口，可能会有请求限制。
建议合理使用，避免过于频繁的翻译请求。
        """)
        help_text.setReadOnly(True)
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试翻译")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建默认配置
                default_config = {
                    "name": "Google翻译插件",
                    "version": "1.0.0",
                    "description": "使用免费的googletrans库进行标签翻译",
                    "author": "PicMan Team",
                    "enabled": False,
                    "config": {
                        "source_language": "en",
                        "target_language": "zh-CN"
                    }
                }
                self.save_config_file(default_config)
                return default_config
        except Exception as e:
            self.logger.error("Failed to load config", error=str(e))
            return {}
    
    def save_config_file(self, config: dict):
        """保存配置文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.error("Failed to save config", error=str(e))
    
    def load_config_to_ui(self):
        """将配置加载到UI"""
        try:
            # 启用状态
            self.enable_plugin.setChecked(self.config.get("enabled", False))
            
            # 源语言
            source_lang = self.config.get("config", {}).get("source_language", "en")
            # 查找包含该语言代码的项
            for i in range(self.source_language.count()):
                if self.source_language.itemText(i).startswith(source_lang + " -"):
                    self.source_language.setCurrentIndex(i)
                    break
            
            # 目标语言
            target_lang = self.config.get("config", {}).get("target_language", "zh-CN")
            # 查找包含该语言代码的项
            for i in range(self.target_language.count()):
                if self.target_language.itemText(i).startswith(target_lang + " -"):
                    self.target_language.setCurrentIndex(i)
                    break
                
        except Exception as e:
            self.logger.error("Failed to load config to UI", error=str(e))
    
    def save_config(self):
        """保存配置"""
        try:
            # 更新配置
            self.config["enabled"] = self.enable_plugin.isChecked()
            
            # 提取语言代码（去掉标签说明）
            source_text = self.source_language.currentText()
            source_lang = source_text.split(" - ")[0] if " - " in source_text else source_text
            self.config["config"]["source_language"] = source_lang
            
            target_text = self.target_language.currentText()
            target_lang = target_text.split(" - ")[0] if " - " in target_text else target_text
            self.config["config"]["target_language"] = target_lang
            
            # 保存到文件
            self.save_config_file(self.config)
            
            QMessageBox.information(self, "保存成功", "配置已保存！\n重启应用程序后生效。")
            self.accept()
            
        except Exception as e:
            self.logger.error("Failed to save config", error=str(e))
            QMessageBox.critical(self, "保存失败", f"保存配置失败：{str(e)}")
    
    def test_connection(self):
        """测试翻译功能"""
        try:
            # 测试googletrans库
            try:
                from googletrans import Translator
                translator = Translator()
                
                # 测试翻译
                result = translator.translate("Hello", src="en", dest="zh-CN")
                
                if result and result.text:
                    QMessageBox.information(self, "测试成功", f"翻译功能正常！\n测试翻译：Hello -> {result.text}")
                else:
                    QMessageBox.warning(self, "测试失败", "翻译结果为空")
                    
            except ImportError:
                QMessageBox.critical(self, "测试失败", "googletrans库未安装，请运行：pip install googletrans==4.0.0rc1")
            except Exception as e:
                QMessageBox.critical(self, "测试失败", f"翻译测试失败：{str(e)}")
                
        except Exception as e:
            self.logger.error("Translation test failed", error=str(e))
            QMessageBox.critical(self, "测试失败", f"测试失败：{str(e)}") 