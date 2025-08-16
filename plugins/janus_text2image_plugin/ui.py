from __future__ import annotations

import random
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGroupBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTextEdit, QCheckBox, QComboBox, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QFont


class JanusT2IMainWidget(QWidget):
    """Janus 文生图主界面"""
    
    generate_requested = pyqtSignal(dict)  # 发出生成请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Janus 文生图插件")
        self.setMinimumSize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 上方3/4区域：图像显示
        self.create_image_display_area(layout)
        
        # 下方1/4区域：参数控制
        self.create_control_area(layout)
        
        # 设置布局比例 (3:1)
        layout.setStretch(0, 3)
        layout.setStretch(1, 1)
        
    def create_image_display_area(self, parent_layout):
        """创建图像显示区域"""
        # 图像显示组
        image_group = QGroupBox("生成图像")
        image_layout = QVBoxLayout(image_group)
        
        # 图像显示标签（滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel("点击生成按钮开始生成图像")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                background-color: #f8f8f8;
                color: #666;
                font-size: 14px;
                min-height: 200px;
            }
        """)
        scroll_area.setWidget(self.image_label)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        self.view_last_btn = QPushButton("查看最新生成")
        self.view_last_btn.clicked.connect(self.view_last_generated)
        
        self.open_output_btn = QPushButton("打开输出目录")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        
        button_layout.addWidget(self.view_last_btn)
        button_layout.addWidget(self.open_output_btn)
        button_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        image_layout.addWidget(scroll_area, 1)
        image_layout.addLayout(button_layout)
        image_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(image_group)
        
    def create_control_area(self, parent_layout):
        """创建控制区域"""
        control_group = QGroupBox("生成参数")
        control_layout = QVBoxLayout(control_group)
        
        # 第一行：提示词
        prompt_layout = QVBoxLayout()
        prompt_layout.addWidget(QLabel("提示词:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setMaximumHeight(80)
        self.prompt_edit.setPlaceholderText("输入你想要生成的图像描述...")
        prompt_layout.addWidget(self.prompt_edit)
        
        # 参数网格布局
        params_layout = QHBoxLayout()
        
        # 左列
        left_col = QVBoxLayout()
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "deepseek-ai/Janus-Pro-1B",
            "deepseek-ai/Janus-Pro-7B"
        ])
        model_layout.addWidget(self.model_combo)
        left_col.addLayout(model_layout)
        
        # 批量大小
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("批量:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 4)  # 限制最大批量大小
        self.batch_spin.setValue(1)
        self.batch_spin.setToolTip("批量生成数量，建议根据显存大小调整")
        batch_layout.addWidget(self.batch_spin)
        left_col.addLayout(batch_layout)
        
        # CFG权重
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("CFG:"))
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 10.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(5.0)
        self.cfg_spin.setToolTip("CFG权重，控制生成图像与提示词的匹配度")
        cfg_layout.addWidget(self.cfg_spin)
        left_col.addLayout(cfg_layout)
        
        # 图像尺寸
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("尺寸:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(256, 1024)
        self.size_spin.setSingleStep(64)
        self.size_spin.setValue(384)
        self.size_spin.setSuffix(" px")
        self.size_spin.setToolTip("生成图像的尺寸（正方形）")
        size_layout.addWidget(self.size_spin)
        left_col.addLayout(size_layout)
        
        params_layout.addLayout(left_col)
        
        # 右列
        right_col = QVBoxLayout()
        
        # 温度
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("温度:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.1, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(1.0)
        temp_layout.addWidget(self.temp_spin)
        right_col.addLayout(temp_layout)
        
        # Top-p
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(QLabel("Top-p:"))
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        top_p_layout.addWidget(self.top_p_spin)
        right_col.addLayout(top_p_layout)
        
        # 种子
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("种子:"))
        self.seed_edit = QLineEdit()
        self.seed_edit.setText("666666666666666")
        self.random_seed_cb = QCheckBox("随机")
        self.random_seed_cb.toggled.connect(self.on_random_seed_changed)
        seed_layout.addWidget(self.seed_edit)
        seed_layout.addWidget(self.random_seed_cb)
        right_col.addLayout(seed_layout)
        
        params_layout.addLayout(right_col)
        
        # 生成按钮
        generate_layout = QHBoxLayout()
        self.generate_btn = QPushButton("开始生成")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.generate_btn.clicked.connect(self.start_generation)
        generate_layout.addStretch()
        generate_layout.addWidget(self.generate_btn)
        generate_layout.addStretch()
        
        # 组合所有布局
        control_layout.addLayout(prompt_layout)
        control_layout.addLayout(params_layout)
        control_layout.addLayout(generate_layout)
        
        parent_layout.addWidget(control_group)
        
    def on_random_seed_changed(self, checked):
        """随机种子选项改变"""
        if checked:
            self.seed_edit.setText(str(random.randint(1, 999999999999999)))
            self.seed_edit.setEnabled(False)
        else:
            self.seed_edit.setEnabled(True)
            
    def start_generation(self):
        """开始生成"""
        # 获取参数
        params = self.get_generation_params()
        
        # 验证提示词
        if not params["prompt"].strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请输入提示词")
            return
            
        # 验证模型路径
        if not params.get("model_path", "").strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请先配置模型路径")
            return
            
        # 禁用生成按钮
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 发出生成请求信号
        self.generate_requested.emit(params)
        
    def get_generation_params(self) -> Dict[str, Any]:
        """获取生成参数"""
        # 处理种子
        if self.random_seed_cb.isChecked():
            seed = random.randint(1, 999999999999999)
            self.seed_edit.setText(str(seed))
        else:
            try:
                seed = int(self.seed_edit.text())
            except ValueError:
                seed = 666666666666666
                
        # 从配置文件读取模型路径
        model_path = ""
        try:
            import json
            from pathlib import Path
            config_file = Path("plugins/janus_text2image_plugin/config/config.json")
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                model_path = config.get("model_path", "")
        except Exception:
            pass
                
        return {
            "prompt": self.prompt_edit.toPlainText(),
            "model": self.model_combo.currentText(),
            "model_path": model_path,
            "batch_size": self.batch_spin.value(),
            "cfg_weight": self.cfg_spin.value(),
            "temperature": self.temp_spin.value(),
            "top_p": self.top_p_spin.value(),
            "img_size": self.size_spin.value(),  # 添加图像尺寸参数
            "seed": seed,
        }
        
    def update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)
        
    def show_generated_image(self, pixmap: QPixmap):
        """显示生成的图像"""
        # 缩放图像以适应显示区域
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
        # 恢复生成按钮
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("开始生成")
        self.progress_bar.setVisible(False)
        
    def view_last_generated(self):
        """查看最新生成的图像"""
        from pathlib import Path
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        output_dir = Path("output")
        if not output_dir.exists():
            QMessageBox.information(self, "提示", "输出目录不存在")
            return
            
        # 查找最新的 Janus*.png 文件
        janus_files = list(output_dir.glob("Janus*.png"))
        if not janus_files:
            QMessageBox.information(self, "提示", "没有找到生成的图像")
            return
            
        # 按修改时间排序，获取最新的
        latest_file = max(janus_files, key=lambda f: f.stat().st_mtime)
        
        # 在系统默认程序中打开
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(latest_file)))
        
    def open_output_folder(self):
        """打开输出文件夹"""
        from pathlib import Path
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir.resolve())))