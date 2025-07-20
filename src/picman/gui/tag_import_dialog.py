#!/usr/bin/env python3
"""
标签导入对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QComboBox, QPushButton, QGroupBox, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
from typing import Dict, List, Optional


class TagImportDialog(QDialog):
    """标签导入对话框"""
    
    # 信号：用户确认导入设置
    import_confirmed = pyqtSignal(dict)  # 传递导入设置
    
    def __init__(self, directory_path: str, parent=None):
        super().__init__(parent)
        self.directory_path = Path(directory_path)
        self.tag_files_found = self._scan_tag_files()
        self.init_ui()
    
    def _scan_tag_files(self) -> Dict[str, List[str]]:
        """扫描目录中的标签文件"""
        tag_files = {
            "simple": [],
            "normal": [],
            "detailed": []
        }
        
        try:
            # 扫描目录中的所有.TXT文件
            for txt_file in self.directory_path.glob("*.txt"):
                # 检查是否有对应的图片文件
                base_name = txt_file.stem
                for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']:
                    img_file = txt_file.parent / f"{base_name}{ext}"
                    if img_file.exists():
                        # 找到对应的图片文件，添加到标签文件列表
                        tag_files["normal"].append(str(txt_file))
                        break
            
            # 这里可以根据文件名模式或其他规则来分类标签文件
            # 例如：simple_*.txt, detailed_*.txt 等
            # 目前先全部归类为normal类型
            
        except Exception as e:
            print(f"扫描标签文件时出错: {e}")
        
        return tag_files
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("标签导入设置")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 目录信息
        dir_info = QLabel(f"导入目录: {self.directory_path}")
        dir_info.setWordWrap(True)
        layout.addWidget(dir_info)
        
        # 标签文件检测结果
        total_tag_files = sum(len(files) for files in self.tag_files_found.values())
        if total_tag_files > 0:
            tag_info = QLabel(f"检测到 {total_tag_files} 个标签文件")
            tag_info.setStyleSheet("color: green; font-weight: bold;")
        else:
            tag_info = QLabel("未检测到标签文件")
            tag_info.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(tag_info)
        
        # 导入选项组
        import_group = QGroupBox("导入选项")
        import_layout = QVBoxLayout(import_group)
        
        # 是否导入标签
        self.import_tags_checkbox = QCheckBox("导入标签文件")
        self.import_tags_checkbox.setChecked(total_tag_files > 0)
        self.import_tags_checkbox.toggled.connect(self.on_import_tags_toggled)
        import_layout.addWidget(self.import_tags_checkbox)
        
        # 标签类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("标签类型:"))
        
        self.tag_type_combo = QComboBox()
        self.tag_type_combo.addItems([
            "普通标签 (normal)",
            "简单标签 (simple)", 
            "详细标签 (detailed)"
        ])
        self.tag_type_combo.setCurrentText("普通标签 (normal)")
        type_layout.addWidget(self.tag_type_combo)
        type_layout.addStretch()
        
        import_layout.addLayout(type_layout)
        
        # 标签文件预览
        if total_tag_files > 0:
            preview_group = QGroupBox("标签文件预览")
            preview_layout = QVBoxLayout(preview_group)
            
            self.preview_text = QTextEdit()
            self.preview_text.setMaximumHeight(150)
            self.preview_text.setReadOnly(True)
            
            # 显示找到的标签文件
            preview_content = "找到的标签文件:\n"
            for tag_type, files in self.tag_files_found.items():
                if files:
                    preview_content += f"\n{tag_type.upper()} 标签 ({len(files)} 个):\n"
                    for file_path in files[:5]:  # 只显示前5个
                        preview_content += f"  • {Path(file_path).name}\n"
                    if len(files) > 5:
                        preview_content += f"  ... 还有 {len(files) - 5} 个文件\n"
            
            self.preview_text.setPlainText(preview_content)
            preview_layout.addWidget(self.preview_text)
            
            layout.addWidget(preview_group)
        
        layout.addWidget(import_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.confirm_button = QPushButton("确认导入")
        self.confirm_button.clicked.connect(self.confirm_import)
        self.confirm_button.setDefault(True)
        button_layout.addWidget(self.confirm_button)
        
        layout.addLayout(button_layout)
        
        # 初始状态设置
        self.on_import_tags_toggled(self.import_tags_checkbox.isChecked())
    
    def on_import_tags_toggled(self, checked: bool):
        """标签导入选项切换"""
        self.tag_type_combo.setEnabled(checked)
        self.confirm_button.setEnabled(True)
    
    def confirm_import(self):
        """确认导入设置"""
        try:
            # 获取用户设置
            import_tags = self.import_tags_checkbox.isChecked()
            tag_type_text = self.tag_type_combo.currentText()
            
            # 解析标签类型
            tag_type_map = {
                "普通标签 (normal)": "normal",
                "简单标签 (simple)": "simple", 
                "详细标签 (detailed)": "detailed"
            }
            tag_type = tag_type_map.get(tag_type_text, "normal")
            
            # 准备导入设置
            import_settings = {
                "import_tags": import_tags,
                "tag_type": tag_type,
                "tag_files_found": self.tag_files_found,
                "directory_path": str(self.directory_path)
            }
            
            # 发送确认信号
            self.import_confirmed.emit(import_settings)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置导入参数时出错: {str(e)}")
    
    def get_import_settings(self) -> Dict:
        """获取导入设置（用于外部调用）"""
        import_tags = self.import_tags_checkbox.isChecked()
        tag_type_text = self.tag_type_combo.currentText()
        
        tag_type_map = {
            "普通标签 (normal)": "normal",
            "简单标签 (simple)": "simple", 
            "详细标签 (detailed)": "detailed"
        }
        tag_type = tag_type_map.get(tag_type_text, "normal")
        
        return {
            "import_tags": import_tags,
            "tag_type": tag_type,
            "tag_files_found": self.tag_files_found,
            "directory_path": str(self.directory_path)
        } 