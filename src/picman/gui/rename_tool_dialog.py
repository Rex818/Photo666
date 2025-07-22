import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QLineEdit, QComboBox, QCheckBox, QListWidget, QListWidgetItem, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from pathlib import Path

class RenameToolDialog(QDialog):
    def __init__(self, parent=None, photo_manager=None):
        super().__init__(parent)
        self.setWindowTitle("修改文件名工具")
        self.setMinimumWidth(600)
        self.photo_manager = photo_manager  # 用于查数据库
        self.init_ui()
        self.file_list = []  # 真实图片文件列表
        self.preview_map = {}  # {old: new}
        self.skip_files = set()  # 需跳过的文件

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 目录选择
        dir_group = QGroupBox("选择图片目录")
        dir_layout = QHBoxLayout(dir_group)
        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setPlaceholderText("请选择图片目录...")
        dir_layout.addWidget(self.dir_line_edit)
        self.dir_browse_btn = QPushButton("浏览...")
        self.dir_browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.dir_browse_btn)
        layout.addWidget(dir_group)

        # 文件名格式选项
        format_group = QGroupBox("文件名格式设置")
        format_layout = QHBoxLayout(format_group)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("前缀名")
        format_layout.addWidget(QLabel("前缀:"))
        format_layout.addWidget(self.prefix_edit)
        self.sep_edit = QLineEdit("_")
        self.sep_edit.setMaximumWidth(40)
        format_layout.addWidget(QLabel("分隔符:"))
        format_layout.addWidget(self.sep_edit)
        self.numbering_checkbox = QCheckBox("编号")
        self.numbering_checkbox.setChecked(True)
        format_layout.addWidget(self.numbering_checkbox)
        self.date_checkbox = QCheckBox("日期")
        format_layout.addWidget(self.date_checkbox)
        self.geo_checkbox = QCheckBox("地理位置")
        format_layout.addWidget(self.geo_checkbox)
        self.tags_checkbox = QCheckBox("标签信息")
        format_layout.addWidget(self.tags_checkbox)
        format_layout.addStretch()
        layout.addWidget(format_group)

        # 保留原文件名选项
        retain_group = QGroupBox("保留原文件名")
        retain_layout = QHBoxLayout(retain_group)
        self.retain_combo = QComboBox()
        self.retain_combo.addItems(["全部保留", "仅保留扩展名", "不保留"])
        retain_layout.addWidget(QLabel("保留方式:"))
        retain_layout.addWidget(self.retain_combo)
        retain_layout.addStretch()
        layout.addWidget(retain_group)

        # 预览区
        preview_group = QGroupBox("重命名预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_list = QListWidget()
        preview_layout.addWidget(self.preview_list)
        layout.addWidget(preview_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self.preview_rename)
        btn_layout.addWidget(self.preview_btn)
        self.rename_btn = QPushButton("执行重命名")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.execute_rename)
        btn_layout.addWidget(self.rename_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择图片目录")
        if dir_path:
            self.dir_line_edit.setText(dir_path)

    def get_image_files(self, dir_path):
        exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        files = []
        for fname in os.listdir(dir_path):
            if os.path.splitext(fname)[1].lower() in exts:
                files.append(fname)
        return files

    def get_db_info(self, abs_path):
        if not self.photo_manager:
            return None
        try:
            file_hash = self.photo_manager._calculate_file_hash(abs_path)
            info = self.photo_manager.get_photo_by_hash(file_hash)
            return info
        except Exception:
            return None

    def _safe_new_name(self, dir_path, new_name, old_name):
        """返回截断后安全的新文件名，保证绝对路径不超长，若截断后仍超长则返回None。"""
        max_path_len = 260
        dir_abs = os.path.abspath(os.path.normpath(dir_path))
        old_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, old_name)))
        new_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, new_name)))
        if old_name == new_name:
            return new_name, False, False  # 未重命名
        if len(new_path) <= max_path_len:
            return new_name, False, False  # 不需要截断
        # 需要截断
        base, ext = os.path.splitext(new_name)
        # 计算可用长度（绝对目录+分隔符+扩展名）
        available = max_path_len - len(os.path.abspath(os.path.normpath(os.path.join(dir_abs, ext))))
        if available <= 0:
            return None, False, True  # 截断后仍超长
        # 截断base
        base = base[:available]
        safe_name = base + ext
        safe_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, safe_name)))
        if len(safe_path) > max_path_len:
            return None, False, True  # 截断后仍超长
        return safe_name, True, False  # 截断后安全

    def preview_rename(self):
        self.preview_list.clear()
        self.preview_map.clear()
        self.skip_files = set()
        dir_path = self.dir_line_edit.text().strip()
        dir_abs = os.path.abspath(os.path.normpath(dir_path))
        if not dir_path or not os.path.isdir(dir_path):
            QMessageBox.warning(self, "提示", "请先选择有效的图片目录！")
            return
        # 目录本身超长直接全红提示
        if len(dir_abs) > 240:
            item = QListWidgetItem("[目录路径过长，所有文件无法重命名]")
            item.setForeground(Qt.GlobalColor.red)
            self.preview_list.addItem(item)
            self.rename_btn.setEnabled(False)
            return
        self.file_list = self.get_image_files(dir_path)
        if not self.file_list:
            QMessageBox.warning(self, "提示", "该目录下没有图片文件！")
            return
        prefix = self.prefix_edit.text().strip()
        sep = self.sep_edit.text().strip() or "_"
        numbering = self.numbering_checkbox.isChecked()
        date = self.date_checkbox.isChecked()
        geo = self.geo_checkbox.isChecked()
        tags = self.tags_checkbox.isChecked()
        retain_mode = self.retain_combo.currentText()
        for idx, fname in enumerate(self.file_list, 1):
            abs_path = os.path.abspath(os.path.join(dir_abs, fname))
            db_info = self.get_db_info(abs_path)
            if (geo or tags) and not db_info:
                item = QListWidgetItem(f"{fname}  →  [未导入，无法获取地理位置/标签信息，跳过]")
                item.setForeground(Qt.GlobalColor.red)
                self.preview_list.addItem(item)
                self.skip_files.add(fname)
                continue
            parts = []
            if prefix:
                parts.append(prefix)
            if numbering:
                parts.append(f"{idx:03d}")
            if date:
                date_str = ""
                if db_info and db_info.get("date_taken"):
                    date_str = db_info["date_taken"][:10].replace("-", "")
                else:
                    try:
                        stat = os.stat(abs_path)
                        date_str = str(self._get_file_date(stat))
                    except Exception:
                        date_str = ""
                if date_str:
                    parts.append(date_str)
            if geo:
                geo_str = ""
                if db_info and db_info.get("location_text"):
                    geo_str = db_info["location_text"]
                if geo_str:
                    parts.append(geo_str)
            if tags:
                tag_str = ""
                if db_info:
                    tag_list = db_info.get("tags") or []
                    if isinstance(tag_list, str):
                        import json
                        try:
                            tag_list = json.loads(tag_list)
                        except Exception:
                            tag_list = []
                    if tag_list:
                        tag_str = ",".join([str(t) for t in tag_list])
                if tag_str:
                    parts.append(tag_str)
            name, ext = os.path.splitext(fname)
            if retain_mode == "全部保留":
                parts.append(name)
            elif retain_mode == "仅保留扩展名":
                pass
            elif retain_mode == "不保留":
                pass
            new_name = sep.join(parts) + ext
            safe_name, truncated, too_long = self._safe_new_name(dir_abs, new_name, fname)
            if too_long:
                text = f"{fname}  →  [路径过长，无法重命名，跳过]"
                item = QListWidgetItem(text)
                item.setForeground(Qt.GlobalColor.red)
                self.preview_list.addItem(item)
                self.skip_files.add(fname)
                continue
            self.preview_map[fname] = safe_name
            if fname != safe_name:
                text = f"{fname}  →  {safe_name}"
                if truncated:
                    text += "  [已自动截断文件名]"
            else:
                text = f"{fname}  (未重命名)"
            item = QListWidgetItem(text)
            self.preview_list.addItem(item)
        self.rename_btn.setEnabled(len(self.preview_map) > 0)

    def _get_file_date(self, stat):
        import datetime
        t = stat.st_mtime
        return datetime.datetime.fromtimestamp(t).strftime("%Y%m%d")

    def execute_rename(self):
        dir_path = self.dir_line_edit.text().strip()
        dir_abs = os.path.abspath(os.path.normpath(dir_path))
        if not dir_path or not os.path.isdir(dir_path):
            QMessageBox.warning(self, "提示", "请先选择有效的图片目录！")
            return
        if len(dir_abs) > 240:
            QMessageBox.warning(self, "提示", "目录路径过长，所有文件无法重命名！")
            return
        if not self.preview_map:
            QMessageBox.warning(self, "提示", "请先点击预览生成新文件名！")
            return
        errors = []
        renamed = 0
        logger = None
        if self.photo_manager and hasattr(self.photo_manager, 'logger'):
            logger = self.photo_manager.logger
        for old, new in self.preview_map.items():
            if old in self.skip_files:
                continue
            if old == new:
                continue  # 未重命名，跳过
            safe_name, truncated, too_long = self._safe_new_name(dir_abs, new, old)
            if too_long:
                msg = f"{old} → [路径过长，无法重命名，跳过]"
                errors.append(msg)
                if logger:
                    logger.error(f"重命名失败: {old} → {new}，原因：路径过长，无法重命名")
                continue
            old_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, old)))
            new_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, safe_name)))
            try:
                if os.path.exists(new_path):
                    msg = f"目标文件已存在: {safe_name}"
                    errors.append(msg)
                    if logger:
                        logger.error(f"重命名失败: {old} → {safe_name}，原因：目标文件已存在")
                    continue
                os.rename(old_path, new_path)
                renamed += 1
            except OSError as e:
                reason = str(e)
                if hasattr(e, 'winerror') and e.winerror == 206:
                    reason = "路径或文件名过长"
                msg = f"{old} → {safe_name}: {reason}"
                errors.append(msg)
                if logger:
                    logger.error(f"重命名失败: {old} → {safe_name}，原因：{reason}")
            except Exception as e:
                msg = f"{old} → {safe_name}: {e}"
                errors.append(msg)
                if logger:
                    logger.error(f"重命名失败: {old} → {safe_name}，原因：{e}")
        msg = f"成功重命名 {renamed} 个文件。"
        if errors:
            msg += "\n部分文件未成功：\n" + "\n".join(errors)
        QMessageBox.information(self, "重命名结果", msg)
        # self.accept()  # 不自动关闭 