"""
Janus 图像生成页面。

布局要求：
- 上方 3/4 显示生成结果图片（可滚动、可自适应居中）。
- 下方 1/4 放置 Janus 模型选择与基础配置（模型、提示词、尺寸、步数等）与生成按钮。

说明：
- 生成逻辑留出接口，后续可对接 ComfyUI Janus-Pro 节点（参考 example/ComfyUI-Janus-Pro/nodes）。
"""

from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGroupBox,
    QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton,
    QProgressBar, QSplitter, QCheckBox, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap


class JanusGeneratePage(QWidget):
    """Janus 生图页面组件。"""

    # 发起生成信号，外部可连接实际生成流程
    request_generate = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self.load_model_config()  # 初始化时加载默认配置

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上部：结果图显示（占 3/4）
        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.result_label = QLabel("未生成")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("border: 1px solid #ccc; background:#f8f8f8;")
        self.result_label.setMinimumSize(400, 300)
        self.result_scroll.setWidget(self.result_label)

        # 下部：配置与操作（占 1/4）
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        config_group = QGroupBox("生图配置")
        form = QFormLayout(config_group)

        # 模型配置组
        model_config_group = QGroupBox("模型配置")
        model_config_layout = QVBoxLayout(model_config_group)
        
        # 模型选择
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-ai/Janus-Pro-1B", "deepseek-ai/Janus-Pro-7B"])
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_select_layout.addWidget(self.model_combo, 1)
        model_config_layout.addLayout(model_select_layout)
        
        # 模型路径配置
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("模型路径:"))
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("请选择模型文件夹路径...")
        path_layout.addWidget(self.model_path_edit, 1)
        
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.browse_model_path)
        path_layout.addWidget(self.browse_button)
        
        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.save_model_config)
        path_layout.addWidget(self.save_config_button)
        
        model_config_layout.addLayout(path_layout)
        
        # 模型性能提示
        self.model_info_label = QLabel()
        self.model_info_label.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        self.model_info_label.setWordWrap(True)
        model_config_layout.addWidget(self.model_info_label)
        
        form.addRow(model_config_group)
        
        # 更新模型信息
        self._on_model_changed()

        # 提示词
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Prompt（提示词）…")
        self.prompt_edit.setFixedHeight(60)
        form.addRow("提示词", self.prompt_edit)

        # 反向提示词
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setPlaceholderText("Negative Prompt（反向提示词）…")
        self.negative_prompt_edit.setFixedHeight(40)
        form.addRow("反向提示", self.negative_prompt_edit)

        # 尺寸与步数等基础参数
        size_row = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 4096)
        self.width_spin.setValue(1024)
        self.width_spin.setSuffix(" px")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 4096)
        self.height_spin.setValue(1024)
        self.height_spin.setSuffix(" px")
        size_row.addWidget(QLabel("宽"))
        size_row.addWidget(self.width_spin)
        size_row.addWidget(QLabel("高"))
        size_row.addWidget(self.height_spin)
        form.addRow("尺寸", self._wrap_row(size_row))

        steps_row = QHBoxLayout()
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 200)
        self.steps_spin.setValue(30)
        self.guidance_spin = QDoubleSpinBox()
        self.guidance_spin.setRange(0.0, 50.0)
        self.guidance_spin.setSingleStep(0.1)
        self.guidance_spin.setValue(7.0)
        steps_row.addWidget(QLabel("步数"))
        steps_row.addWidget(self.steps_spin)
        steps_row.addWidget(QLabel("CFG Weight"))
        steps_row.addWidget(self.guidance_spin)
        form.addRow("采样", self._wrap_row(steps_row))

        # 额外生成参数（参考示例图）
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.01)
        self.temperature_spin.setValue(1.0)
        form.addRow("Temperature", self.temperature_spin)

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.01)
        self.top_p_spin.setValue(0.95)
        form.addRow("Top P", self.top_p_spin)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 32)
        self.batch_size_spin.setValue(1)
        form.addRow("Batch Size", self.batch_size_spin)

        # Image Size 单一尺寸（用于方图便捷设置）
        self.image_size_spin = QSpinBox()
        self.image_size_spin.setRange(256, 1024)
        self.image_size_spin.setSingleStep(64)
        self.image_size_spin.setValue(384)
        self.image_size_spin.setSuffix(" px")
        self.image_size_spin.valueChanged.connect(self._on_image_size_changed)
        form.addRow("Image Size", self.image_size_spin)

        # 种子
        seed_row = QHBoxLayout()
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2_147_483_647)
        self.seed_spin.setValue(12345)
        self.random_seed_checkbox = QCheckBox("随机")
        self.random_seed_checkbox.setToolTip("选中时使用随机种子（等价于 seed = -1）")
        self.random_seed_checkbox.stateChanged.connect(self._on_random_seed_changed)
        seed_row.addWidget(self.seed_spin)
        seed_row.addWidget(self.random_seed_checkbox)
        form.addRow("Seed", self._wrap_row(seed_row))

        # 生成按钮与进度
        actions_row = QHBoxLayout()
        self.generate_btn = QPushButton("开始生成")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        actions_row.addWidget(self.generate_btn)
        actions_row.addWidget(self.progress)
        form.addRow("操作", self._wrap_row(actions_row))

        config_layout.addWidget(config_group)
        config_layout.addStretch()

        splitter.addWidget(self.result_scroll)
        splitter.addWidget(config_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _wrap_row(self, row_layout: QHBoxLayout) -> QWidget:
        wrapper = QWidget()
        wrapper.setLayout(row_layout)
        return wrapper

    def set_available_models(self, models: list[str]) -> None:
        self.model_combo.clear()
        self.model_combo.addItems(models)

    def show_generated_image(self, pixmap: QPixmap) -> None:
        if pixmap and not pixmap.isNull():
            self.result_label.setPixmap(pixmap)
            self.result_label.setText("")
        else:
            self.result_label.setPixmap(QPixmap())
            self.result_label.setText("生成失败或无图片")

    def set_progress(self, value: int) -> None:
        self.progress.setValue(max(0, min(100, value)))

    def _on_generate_clicked(self) -> None:
        # 检查模型路径
        model_path = self.model_path_edit.text().strip()
        if not model_path:
            QMessageBox.warning(self, "配置错误", "请先配置模型路径")
            return
            
        payload: Dict[str, Any] = {
            "model": self.model_combo.currentText(),
            "model_path": model_path,
            "prompt": self.prompt_edit.toPlainText().strip(),
            "negative_prompt": self.negative_prompt_edit.toPlainText().strip(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "steps": self.steps_spin.value(),
            "cfg_weight": self.guidance_spin.value(),
            "temperature": self.temperature_spin.value(),
            "top_p": self.top_p_spin.value(),
            "batch_size": self.batch_size_spin.value(),
            "img_size": self.image_size_spin.value(),  # 使用img_size参数名
            "seed": (-1 if self.random_seed_checkbox.isChecked() else self.seed_spin.value()),
        }
        self.request_generate.emit(payload)

    def _on_image_size_changed(self, value: int) -> None:
        # 若当前宽高相等，视为方图，同步为该尺寸；否则不干预
        if self.width_spin.value() == self.height_spin.value():
            self.width_spin.setValue(value)
            self.height_spin.setValue(value)

    def _on_random_seed_changed(self) -> None:
        if self.random_seed_checkbox.isChecked():
            self.seed_spin.setEnabled(False)
        else:
            self.seed_spin.setEnabled(True)
    
    def browse_model_path(self) -> None:
        """浏览模型路径"""
        current_path = self.model_path_edit.text().strip()
        if not current_path:
            current_path = ""
            
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if current_path:
            dialog.setDirectory(current_path)
            
        if dialog.exec():
            selected_path = dialog.selectedFiles()[0]
            self.model_path_edit.setText(selected_path)
    
    def save_model_config(self) -> None:
        """保存模型配置为默认配置"""
        try:
            import json
            from pathlib import Path
            
            model_path = self.model_path_edit.text().strip()
            if not model_path:
                QMessageBox.warning(self, "配置错误", "请先选择模型路径")
                return
                
            config = {
                "model": self.model_combo.currentText(),
                "model_path": model_path
            }
            
            # 创建配置目录
            config_dir = Path("plugins/janus_text2image_plugin/config")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存配置
            config_file = config_dir / "config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
            QMessageBox.information(self, "保存成功", "模型配置已保存为默认配置")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置失败: {e}")
    
    def load_model_config(self) -> None:
        """加载默认模型配置"""
        try:
            import json
            from pathlib import Path
            
            config_file = Path("plugins/janus_text2image_plugin/config/config.json")
            if not config_file.exists():
                return
                
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            # 应用配置
            model = config.get("model", "")
            if model:
                index = self.model_combo.findText(model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                    
            model_path = config.get("model_path", "")
            if model_path:
                self.model_path_edit.setText(model_path)
                
        except Exception:
            # 静默失败，不影响界面初始化
            pass
    
    def _on_model_changed(self):
        """模型选择改变时的处理"""
        model_name = self.model_combo.currentText()
        if "1B" in model_name:
            self.model_info_label.setText(
                "⚠️ 注意：Janus-Pro-1B 模型在图像生成方面存在质量限制。\n"
                "建议使用 Janus-Pro-7B 模型以获得更好的生成效果。"
            )
            self.model_info_label.setStyleSheet("color: #ff6b35; font-size: 12px; margin: 5px;")
        else:
            self.model_info_label.setText(
                "✅ Janus-Pro-7B 模型具有更好的图像生成质量。\n"
                "需要更多显存（建议24GB+）但生成效果更佳。"
            )
            self.model_info_label.setStyleSheet("color: #28a745; font-size: 12px; margin: 5px;")


