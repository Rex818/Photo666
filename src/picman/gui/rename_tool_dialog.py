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
        self.setWindowTitle("淇敼鏂囦欢鍚嶅伐鍏?)
        self.setMinimumWidth(600)
        self.photo_manager = photo_manager  # 鐢ㄤ簬鏌ユ暟鎹簱
        self.init_ui()
        self.file_list = []  # 鐪熷疄鍥剧墖鏂囦欢鍒楄〃
        self.preview_map = {}  # {old: new}
        self.skip_files = set()  # 闇€璺宠繃鐨勬枃浠?

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 鐩綍閫夋嫨
        dir_group = QGroupBox("閫夋嫨鍥剧墖鐩綍")
        dir_layout = QHBoxLayout(dir_group)
        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setPlaceholderText("璇烽€夋嫨鍥剧墖鐩綍...")
        dir_layout.addWidget(self.dir_line_edit)
        self.dir_browse_btn = QPushButton("娴忚...")
        self.dir_browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.dir_browse_btn)
        layout.addWidget(dir_group)

        # 鏂囦欢鍚嶆牸寮忛€夐」
        format_group = QGroupBox("鏂囦欢鍚嶆牸寮忚缃?)
        format_layout = QHBoxLayout(format_group)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("鍓嶇紑鍚?)
        format_layout.addWidget(QLabel("鍓嶇紑:"))
        format_layout.addWidget(self.prefix_edit)
        self.sep_edit = QLineEdit("_")
        self.sep_edit.setMaximumWidth(40)
        format_layout.addWidget(QLabel("鍒嗛殧绗?"))
        format_layout.addWidget(self.sep_edit)
        self.numbering_checkbox = QCheckBox("缂栧彿")
        self.numbering_checkbox.setChecked(True)
        format_layout.addWidget(self.numbering_checkbox)
        self.date_checkbox = QCheckBox("鏃ユ湡")
        format_layout.addWidget(self.date_checkbox)
        self.geo_checkbox = QCheckBox("鍦扮悊浣嶇疆")
        format_layout.addWidget(self.geo_checkbox)
        self.tags_checkbox = QCheckBox("鏍囩淇℃伅")
        format_layout.addWidget(self.tags_checkbox)
        format_layout.addStretch()
        layout.addWidget(format_group)

        # 淇濈暀鍘熸枃浠跺悕閫夐」
        retain_group = QGroupBox("淇濈暀鍘熸枃浠跺悕")
        retain_layout = QHBoxLayout(retain_group)
        self.retain_combo = QComboBox()
        self.retain_combo.addItems(["鍏ㄩ儴淇濈暀", "浠呬繚鐣欐墿灞曞悕", "涓嶄繚鐣?])
        retain_layout.addWidget(QLabel("淇濈暀鏂瑰紡:"))
        retain_layout.addWidget(self.retain_combo)
        retain_layout.addStretch()
        layout.addWidget(retain_group)

        # 棰勮鍖?
        preview_group = QGroupBox("閲嶅懡鍚嶉瑙?)
        preview_layout = QVBoxLayout(preview_group)
        self.preview_list = QListWidget()
        preview_layout.addWidget(self.preview_list)
        layout.addWidget(preview_group)

        # 鎿嶄綔鎸夐挳
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("棰勮")
        self.preview_btn.clicked.connect(self.preview_rename)
        btn_layout.addWidget(self.preview_btn)
        self.rename_btn = QPushButton("鎵ц閲嶅懡鍚?)
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.execute_rename)
        btn_layout.addWidget(self.rename_btn)
        self.cancel_btn = QPushButton("鍙栨秷")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "閫夋嫨鍥剧墖鐩綍")
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
        """杩斿洖鎴柇鍚庡畨鍏ㄧ殑鏂版枃浠跺悕锛屼繚璇佺粷瀵硅矾寰勪笉瓒呴暱锛岃嫢鎴柇鍚庝粛瓒呴暱鍒欒繑鍥濶one銆?""
        max_path_len = 260
        dir_abs = os.path.abspath(os.path.normpath(dir_path))
        old_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, old_name)))
        new_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, new_name)))
        if old_name == new_name:
            return new_name, False, False  # 鏈噸鍛藉悕
        if len(new_path) <= max_path_len:
            return new_name, False, False  # 涓嶉渶瑕佹埅鏂?
        # 闇€瑕佹埅鏂?
        base, ext = os.path.splitext(new_name)
        # 璁＄畻鍙敤闀垮害锛堢粷瀵圭洰褰?鍒嗛殧绗?鎵╁睍鍚嶏級
        available = max_path_len - len(os.path.abspath(os.path.normpath(os.path.join(dir_abs, ext))))
        if available <= 0:
            return None, False, True  # 鎴柇鍚庝粛瓒呴暱
        # 鎴柇base
        base = base[:available]
        safe_name = base + ext
        safe_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, safe_name)))
        if len(safe_path) > max_path_len:
            return None, False, True  # 鎴柇鍚庝粛瓒呴暱
        return safe_name, True, False  # 鎴柇鍚庡畨鍏?

    def preview_rename(self):
        self.preview_list.clear()
        self.preview_map.clear()
        self.skip_files = set()
        dir_path = self.dir_line_edit.text().strip()
        dir_abs = os.path.abspath(os.path.normpath(dir_path))
        if not dir_path or not os.path.isdir(dir_path):
            QMessageBox.warning(self, "鎻愮ず", "璇峰厛閫夋嫨鏈夋晥鐨勫浘鐗囩洰褰曪紒")
            return
        # 鐩綍鏈韩瓒呴暱鐩存帴鍏ㄧ孩鎻愮ず
        if len(dir_abs) > 240:
            item = QListWidgetItem("[鐩綍璺緞杩囬暱锛屾墍鏈夋枃浠舵棤娉曢噸鍛藉悕]")
            item.setForeground(Qt.GlobalColor.red)
            self.preview_list.addItem(item)
            self.rename_btn.setEnabled(False)
            return
        self.file_list = self.get_image_files(dir_path)
        if not self.file_list:
            QMessageBox.warning(self, "鎻愮ず", "璇ョ洰褰曚笅娌℃湁鍥剧墖鏂囦欢锛?)
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
                item = QListWidgetItem(f"{fname}  鈫? [鏈鍏ワ紝鏃犳硶鑾峰彇鍦扮悊浣嶇疆/鏍囩淇℃伅锛岃烦杩嘳")
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
            if retain_mode == "鍏ㄩ儴淇濈暀":
                parts.append(name)
            elif retain_mode == "浠呬繚鐣欐墿灞曞悕":
                pass
            elif retain_mode == "涓嶄繚鐣?:
                pass
            new_name = sep.join(parts) + ext
            safe_name, truncated, too_long = self._safe_new_name(dir_abs, new_name, fname)
            if too_long:
                text = f"{fname}  鈫? [璺緞杩囬暱锛屾棤娉曢噸鍛藉悕锛岃烦杩嘳"
                item = QListWidgetItem(text)
                item.setForeground(Qt.GlobalColor.red)
                self.preview_list.addItem(item)
                self.skip_files.add(fname)
                continue
            self.preview_map[fname] = safe_name
            if fname != safe_name:
                text = f"{fname}  鈫? {safe_name}"
                if truncated:
                    text += "  [宸茶嚜鍔ㄦ埅鏂枃浠跺悕]"
            else:
                text = f"{fname}  (鏈噸鍛藉悕)"
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
            QMessageBox.warning(self, "鎻愮ず", "璇峰厛閫夋嫨鏈夋晥鐨勫浘鐗囩洰褰曪紒")
            return
        if len(dir_abs) > 240:
            QMessageBox.warning(self, "鎻愮ず", "鐩綍璺緞杩囬暱锛屾墍鏈夋枃浠舵棤娉曢噸鍛藉悕锛?)
            return
        if not self.preview_map:
            QMessageBox.warning(self, "鎻愮ず", "璇峰厛鐐瑰嚮棰勮鐢熸垚鏂版枃浠跺悕锛?)
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
                continue  # 鏈噸鍛藉悕锛岃烦杩?
            safe_name, truncated, too_long = self._safe_new_name(dir_abs, new, old)
            if too_long:
                msg = f"{old} 鈫?[璺緞杩囬暱锛屾棤娉曢噸鍛藉悕锛岃烦杩嘳"
                errors.append(msg)
                if logger:
                    logger.error(f"閲嶅懡鍚嶅け璐? {old} 鈫?{new}锛屽師鍥狅細璺緞杩囬暱锛屾棤娉曢噸鍛藉悕")
                continue
            old_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, old)))
            new_path = os.path.abspath(os.path.normpath(os.path.join(dir_abs, safe_name)))
            try:
                if os.path.exists(new_path):
                    msg = f"鐩爣鏂囦欢宸插瓨鍦? {safe_name}"
                    errors.append(msg)
                    if logger:
                        logger.error(f"閲嶅懡鍚嶅け璐? {old} 鈫?{safe_name}锛屽師鍥狅細鐩爣鏂囦欢宸插瓨鍦?)
                    continue
                os.rename(old_path, new_path)
                renamed += 1
            except OSError as e:
                reason = str(e)
                if hasattr(e, 'winerror') and e.winerror == 206:
                    reason = "璺緞鎴栨枃浠跺悕杩囬暱"
                msg = f"{old} 鈫?{safe_name}: {reason}"
                errors.append(msg)
                if logger:
                    logger.error(f"閲嶅懡鍚嶅け璐? {old} 鈫?{safe_name}锛屽師鍥狅細{reason}")
            except Exception as e:
                msg = f"{old} 鈫?{safe_name}: {e}"
                errors.append(msg)
                if logger:
                    logger.error(f"閲嶅懡鍚嶅け璐? {old} 鈫?{safe_name}锛屽師鍥狅細{e}")
        msg = f"鎴愬姛閲嶅懡鍚?{renamed} 涓枃浠躲€?
        if errors:
            msg += "\n閮ㄥ垎鏂囦欢鏈垚鍔燂細\n" + "\n".join(errors)
        QMessageBox.information(self, "閲嶅懡鍚嶇粨鏋?, msg)
        # self.accept()  # 涓嶈嚜鍔ㄥ叧闂?
