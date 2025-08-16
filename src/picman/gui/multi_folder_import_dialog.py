#!/usr/bin/env python3
"""
多文件夹导入对话框
"""

import sys
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QCheckBox, QGroupBox, QFileDialog,
    QMessageBox, QProgressBar, QTextEdit, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

class MultiFolderImportDialog(QDialog):
    """多文件夹导入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.selected_folders = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("多文件夹导入")
        self.setModal(True)
        self.resize(800, 600)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("多文件夹批量导入")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # 文件夹选择区域
        folder_frame = QFrame()
        folder_layout = QVBoxLayout(folder_frame)
        
        # 文件夹选择标题和按钮
        folder_header = QHBoxLayout()
        folder_label = QLabel("选择要导入的文件夹:")
        folder_label.setStyleSheet("font-weight: bold;")
        folder_header.addWidget(folder_label)
        
        folder_header.addStretch()
        
        # 按钮组
        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.setIcon(QIcon("icons/folder-add.png") if Path("icons/folder-add.png").exists() else QIcon())
        add_folder_btn.clicked.connect(self.add_folder)
        folder_header.addWidget(add_folder_btn)
        
        remove_folder_btn = QPushButton("移除选中")
        remove_folder_btn.setIcon(QIcon("icons/folder-remove.png") if Path("icons/folder-remove.png").exists() else QIcon())
        remove_folder_btn.clicked.connect(self.remove_selected_folders)
        folder_header.addWidget(remove_folder_btn)
        
        clear_all_btn = QPushButton("清空列表")
        clear_all_btn.setIcon(QIcon("icons/clear.png") if Path("icons/clear.png").exists() else QIcon())
        clear_all_btn.clicked.connect(self.clear_all_folders)
        folder_header.addWidget(clear_all_btn)
        
        folder_layout.addLayout(folder_header)
        
        # 文件夹列表
        self.folder_list = QListWidget()
        self.folder_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.folder_list.setAlternatingRowColors(True)
        folder_layout.addWidget(self.folder_list)
        
        # 文件夹统计信息
        self.folder_stats_label = QLabel("已选择 0 个文件夹")
        self.folder_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        folder_layout.addWidget(self.folder_stats_label)
        
        splitter.addWidget(folder_frame)
        
        # 导入设置区域
        settings_group = QGroupBox("导入设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 递归扫描选项
        self.recursive_checkbox = QCheckBox("递归扫描子目录")
        self.recursive_checkbox.setChecked(True)
        self.recursive_checkbox.setToolTip("扫描选中文件夹及其所有子文件夹中的图片")
        settings_layout.addWidget(self.recursive_checkbox)
        
        # 相册创建策略
        album_strategy_layout = QVBoxLayout()
        
        # 策略选择
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        self.album_strategy_group = QButtonGroup()
        
        self.individual_albums_radio = QRadioButton("为每个文件夹创建独立相册（推荐）")
        self.individual_albums_radio.setChecked(True)
        self.individual_albums_radio.setToolTip("每个文件夹创建一个相册，便于分类管理")
        self.album_strategy_group.addButton(self.individual_albums_radio, 0)
        album_strategy_layout.addWidget(self.individual_albums_radio)
        
        self.single_album_radio = QRadioButton("所有文件夹合并到一个相册")
        self.single_album_radio.setToolTip("所有文件夹的照片导入到同一个相册中")
        self.album_strategy_group.addButton(self.single_album_radio, 1)
        album_strategy_layout.addWidget(self.single_album_radio)
        
        self.existing_album_radio = QRadioButton("添加到现有相册")
        self.existing_album_radio.setToolTip("将所有照片添加到一个已存在的相册中")
        self.album_strategy_group.addButton(self.existing_album_radio, 2)
        album_strategy_layout.addWidget(self.existing_album_radio)
        
        settings_layout.addLayout(album_strategy_layout)
        
        # 合并相册名称设置
        merged_album_layout = QHBoxLayout()
        self.merged_album_label = QLabel("合并相册名称:")
        merged_album_layout.addWidget(self.merged_album_label)
        
        from PyQt6.QtWidgets import QLineEdit
        self.merged_album_name_edit = QLineEdit()
        self.merged_album_name_edit.setPlaceholderText("输入相册名称（留空自动生成）")
        merged_album_layout.addWidget(self.merged_album_name_edit)
        
        settings_layout.addLayout(merged_album_layout)
        
        # 现有相册选择
        existing_album_layout = QHBoxLayout()
        self.existing_album_label = QLabel("选择现有相册:")
        existing_album_layout.addWidget(self.existing_album_label)
        
        from PyQt6.QtWidgets import QComboBox
        self.existing_album_combo = QComboBox()
        self.load_existing_albums()
        existing_album_layout.addWidget(self.existing_album_combo)
        
        settings_layout.addLayout(existing_album_layout)
        
        # 相册名称前缀设置（用于独立相册）
        prefix_layout = QHBoxLayout()
        self.prefix_label = QLabel("相册名称前缀:")
        prefix_layout.addWidget(self.prefix_label)
        
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("可选的前缀，如：2024年-")
        prefix_layout.addWidget(self.prefix_edit)
        
        settings_layout.addLayout(prefix_layout)
        
        # 连接信号
        self.album_strategy_group.buttonToggled.connect(self.on_album_strategy_changed)
        
        # 初始状态设置
        self.on_album_strategy_changed()
        
        splitter.addWidget(settings_group)
        
        # 进度和日志区域
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备导入...")
        self.status_label.setStyleSheet("color: #666;")
        progress_layout.addWidget(self.status_label)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setVisible(False)
        progress_layout.addWidget(self.log_text)
        
        splitter.addWidget(progress_frame)
        
        # 设置分割器比例
        splitter.setSizes([300, 150, 100])
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 显示日志按钮
        self.show_log_btn = QPushButton("显示详细日志")
        self.show_log_btn.setCheckable(True)
        self.show_log_btn.toggled.connect(self.toggle_log_visibility)
        button_layout.addWidget(self.show_log_btn)
        
        button_layout.addStretch()
        
        # 开始导入按钮
        self.import_btn = QPushButton("开始导入")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.import_btn.clicked.connect(self.start_import)
        button_layout.addWidget(self.import_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 导入线程
        self.import_thread = None
        
    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择要导入的文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            # 检查是否已经添加过
            for i in range(self.folder_list.count()):
                if self.folder_list.item(i).data(Qt.ItemDataRole.UserRole) == folder:
                    QMessageBox.information(self, "提示", f"文件夹已存在:\n{folder}")
                    return
            
            # 添加到列表
            item = QListWidgetItem(folder)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            item.setToolTip(folder)
            self.folder_list.addItem(item)
            
            self.update_folder_stats()
            self.update_import_button_state()
            
            # 如果是第一个文件夹且合并相册名为空，自动生成相册名
            if self.folder_list.count() == 1 and not self.merged_album_name_edit.text().strip():
                folder_name = Path(folder).name
                self.merged_album_name_edit.setText(f"批量导入 - {folder_name}")
    
    def remove_selected_folders(self):
        """移除选中的文件夹"""
        selected_items = self.folder_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要移除的文件夹")
            return
        
        for item in selected_items:
            row = self.folder_list.row(item)
            self.folder_list.takeItem(row)
        
        self.update_folder_stats()
        self.update_import_button_state()
    
    def clear_all_folders(self):
        """清空所有文件夹"""
        if self.folder_list.count() == 0:
            return
        
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有文件夹吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.folder_list.clear()
            self.update_folder_stats()
            self.update_import_button_state()
    
    def update_folder_stats(self):
        """更新文件夹统计信息"""
        count = self.folder_list.count()
        self.folder_stats_label.setText(f"已选择 {count} 个文件夹")
    
    def update_import_button_state(self):
        """更新导入按钮状态"""
        has_folders = self.folder_list.count() > 0
        self.import_btn.setEnabled(has_folders)
    
    def on_album_strategy_changed(self):
        """相册策略改变时的处理"""
        strategy = self.album_strategy_group.checkedId()
        
        # 独立相册模式
        individual_mode = (strategy == 0)
        self.prefix_label.setEnabled(individual_mode)
        self.prefix_edit.setEnabled(individual_mode)
        
        # 合并相册模式
        merged_mode = (strategy == 1)
        self.merged_album_label.setEnabled(merged_mode)
        self.merged_album_name_edit.setEnabled(merged_mode)
        
        # 现有相册模式
        existing_mode = (strategy == 2)
        self.existing_album_label.setEnabled(existing_mode)
        self.existing_album_combo.setEnabled(existing_mode)
    
    def load_existing_albums(self):
        """加载现有相册"""
        try:
            if hasattr(self.parent_window, 'db_manager'):
                albums = self.parent_window.db_manager.get_all_albums()
                self.existing_album_combo.clear()
                self.existing_album_combo.addItem("选择相册...", None)
                
                for album in albums:
                    self.existing_album_combo.addItem(album['name'], album['id'])
        except Exception as e:
            self.logger.error(f"加载相册列表失败: {e}")
    
    def toggle_log_visibility(self, visible):
        """切换日志显示"""
        self.log_text.setVisible(visible)
        self.show_log_btn.setText("隐藏详细日志" if visible else "显示详细日志")
    
    def get_selected_folders(self) -> List[str]:
        """获取选中的文件夹列表"""
        folders = []
        for i in range(self.folder_list.count()):
            item = self.folder_list.item(i)
            folder = item.data(Qt.ItemDataRole.UserRole)
            folders.append(folder)
        return folders
    
    def get_import_settings(self) -> dict:
        """获取导入设置"""
        strategy = self.album_strategy_group.checkedId()
        
        settings = {
            'recursive': self.recursive_checkbox.isChecked(),
            'strategy': strategy,  # 0: 独立相册, 1: 合并相册, 2: 现有相册
            'prefix': self.prefix_edit.text().strip(),
            'merged_album_name': self.merged_album_name_edit.text().strip(),
            'existing_album_id': None
        }
        
        if strategy == 2:  # 现有相册
            current_data = self.existing_album_combo.currentData()
            if current_data:
                settings['existing_album_id'] = current_data
        
        return settings
    
    def start_import(self):
        """开始导入"""
        folders = self.get_selected_folders()
        settings = self.get_import_settings()
        
        # 验证设置
        if not folders:
            QMessageBox.warning(self, "警告", "请至少选择一个文件夹")
            return
        
        strategy = settings['strategy']
        
        # 验证合并相册模式的设置
        if strategy == 1:  # 合并相册模式
            if not settings['merged_album_name']:
                # 自动生成相册名
                settings['merged_album_name'] = f"多文件夹导入 - {len(folders)}个文件夹"
        
        # 验证现有相册模式的设置
        elif strategy == 2:  # 现有相册模式
            if not settings['existing_album_id']:
                QMessageBox.warning(self, "警告", "请选择一个现有相册")
                return
        
        # 禁用界面
        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在导入...")
        
        # 创建并启动导入线程
        self.import_thread = MultiFolderImportThread(
            folders, settings, self.parent_window, self
        )
        self.import_thread.progress_updated.connect(self.on_progress_updated)
        self.import_thread.status_updated.connect(self.on_status_updated)
        self.import_thread.log_updated.connect(self.on_log_updated)
        self.import_thread.import_completed.connect(self.on_import_completed)
        self.import_thread.start()
    
    def on_progress_updated(self, value, maximum):
        """进度更新"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
    
    def on_status_updated(self, status):
        """状态更新"""
        self.status_label.setText(status)
    
    def on_log_updated(self, log_message):
        """日志更新"""
        self.log_text.append(log_message)
    
    def on_import_completed(self, success, result):
        """导入完成"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("导入完成！")
            
            # 显示结果
            message = f"""导入完成！
            
总目录数: {result['total_directories']}
成功目录数: {result['successful_directories']}
失败目录数: {result['failed_directories']}
总导入数: {result['total_imported']}
总跳过数: {result['total_skipped']}
总错误数: {result['total_errors']}"""
            
            QMessageBox.information(self, "导入完成", message)
            
            # 刷新主界面
            if hasattr(self.parent_window, 'refresh_albums'):
                self.parent_window.refresh_albums()
            
            self.accept()
        else:
            self.status_label.setText("导入失败")
            QMessageBox.critical(self, "导入失败", f"导入过程中发生错误:\n{result}")


class MultiFolderImportThread(QThread):
    """多文件夹导入线程"""
    
    progress_updated = pyqtSignal(int, int)
    status_updated = pyqtSignal(str)
    log_updated = pyqtSignal(str)
    import_completed = pyqtSignal(bool, object)
    
    def __init__(self, folders, settings, parent_window, dialog):
        super().__init__()
        self.folders = folders
        self.settings = settings
        self.parent_window = parent_window
        self.dialog = dialog
    
    def run(self):
        """执行导入"""
        try:
            # 获取photo_manager
            if not hasattr(self.parent_window, 'photo_manager'):
                self.import_completed.emit(False, "无法获取照片管理器")
                return
            
            photo_manager = self.parent_window.photo_manager
            db_manager = self.parent_window.db_manager
            
            strategy = self.settings['strategy']
            
            if strategy == 0:  # 独立相册模式
                self.import_individual_albums(photo_manager, db_manager)
            elif strategy == 1:  # 合并相册模式
                self.import_merged_album(photo_manager, db_manager)
            elif strategy == 2:  # 现有相册模式
                self.import_to_existing_album(photo_manager, db_manager)
            else:
                self.import_completed.emit(False, "未知的导入策略")
                
        except Exception as e:
            self.log_updated.emit(f"导入过程中发生异常: {str(e)}")
            self.import_completed.emit(False, str(e))
    
    def import_individual_albums(self, photo_manager, db_manager):
        """为每个文件夹创建独立相册"""
        self.status_updated.emit("正在为每个文件夹创建独立相册...")
        self.log_updated.emit(f"开始为 {len(self.folders)} 个文件夹创建独立相册")
        
        total_imported = 0
        total_skipped = 0
        total_errors = 0
        successful_albums = []
        failed_folders = []
        
        for i, folder in enumerate(self.folders):
            try:
                folder_name = Path(folder).name
                prefix = self.settings['prefix']
                album_name = f"{prefix}{folder_name}" if prefix else folder_name
                
                self.status_updated.emit(f"正在处理文件夹 {i+1}/{len(self.folders)}: {folder_name}")
                self.log_updated.emit(f"创建相册: {album_name}")
                
                # 创建相册
                album_data = {
                    'name': album_name,
                    'description': f"从文件夹导入: {folder}"
                }
                album_id = db_manager.create_album(album_data)
                
                if album_id:
                    # 导入文件夹到相册
                    result = photo_manager.import_directory(
                        directory_path=folder,
                        recursive=self.settings['recursive'],
                        album_id=album_id
                    )
                    
                    if result['success']:
                        total_imported += result['imported']
                        total_skipped += result['skipped']
                        total_errors += result['errors']
                        successful_albums.append({
                            'name': album_name,
                            'id': album_id,
                            'folder': folder,
                            'imported': result['imported'],
                            'skipped': result['skipped'],
                            'errors': result['errors']
                        })
                        self.log_updated.emit(f"✅ {album_name}: 导入 {result['imported']}, 跳过 {result['skipped']}, 错误 {result['errors']}")
                    else:
                        failed_folders.append({'folder': folder, 'error': result.get('error', '导入失败')})
                        self.log_updated.emit(f"❌ {album_name}: 导入失败 - {result.get('error', '未知错误')}")
                else:
                    failed_folders.append({'folder': folder, 'error': '无法创建相册'})
                    self.log_updated.emit(f"❌ {folder_name}: 无法创建相册")
                
                # 更新进度
                self.progress_updated.emit(i + 1, len(self.folders))
                
            except Exception as e:
                failed_folders.append({'folder': folder, 'error': str(e)})
                self.log_updated.emit(f"❌ {Path(folder).name}: 处理失败 - {str(e)}")
        
        # 构建结果
        result = {
            'success': True,
            'strategy': 'individual',
            'total_directories': len(self.folders),
            'successful_directories': len(successful_albums),
            'failed_directories': len(failed_folders),
            'total_imported': total_imported,
            'total_skipped': total_skipped,
            'total_errors': total_errors,
            'successful_albums': successful_albums,
            'failed_folders': failed_folders
        }
        
        self.log_updated.emit("独立相册导入完成！")
        self.import_completed.emit(True, result)
    
    def import_merged_album(self, photo_manager, db_manager):
        """合并到一个相册"""
        album_name = self.settings['merged_album_name']
        if not album_name:
            album_name = f"多文件夹导入 - {len(self.folders)}个文件夹"
        
        self.status_updated.emit(f"正在创建合并相册: {album_name}")
        self.log_updated.emit(f"创建合并相册: {album_name}")
        
        # 创建相册
        album_data = {
            'name': album_name,
            'description': f"多文件夹导入 - {len(self.folders)} 个文件夹"
        }
        album_id = db_manager.create_album(album_data)
        
        if not album_id:
            self.import_completed.emit(False, "无法创建合并相册")
            return
        
        # 执行多文件夹导入
        result = photo_manager.import_multiple_directories(
            directory_paths=self.folders,
            recursive=self.settings['recursive'],
            album_id=album_id
        )
        
        if result['success']:
            result['strategy'] = 'merged'
            result['album_name'] = album_name
            result['album_id'] = album_id
            self.log_updated.emit("合并相册导入完成！")
            self.import_completed.emit(True, result)
        else:
            self.log_updated.emit(f"合并相册导入失败: {result.get('error', '未知错误')}")
            self.import_completed.emit(False, result.get('error', '未知错误'))
    
    def import_to_existing_album(self, photo_manager, db_manager):
        """导入到现有相册"""
        album_id = self.settings['existing_album_id']
        
        if not album_id:
            self.import_completed.emit(False, "未选择现有相册")
            return
        
        self.status_updated.emit("正在导入到现有相册...")
        self.log_updated.emit(f"导入到现有相册 ID: {album_id}")
        
        # 执行多文件夹导入
        result = photo_manager.import_multiple_directories(
            directory_paths=self.folders,
            recursive=self.settings['recursive'],
            album_id=album_id
        )
        
        if result['success']:
            result['strategy'] = 'existing'
            result['album_id'] = album_id
            self.log_updated.emit("现有相册导入完成！")
            self.import_completed.emit(True, result)
        else:
            self.log_updated.emit(f"现有相册导入失败: {result.get('error', '未知错误')}")
            self.import_completed.emit(False, result.get('error', '未知错误'))


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = MultiFolderImportDialog()
    dialog.show()
    sys.exit(app.exec())