#!/usr/bin/env python3
"""
标签导入对话框
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QGroupBox, QButtonGroup, QRadioButton,
    QTextEdit, QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QFont

class TagImportWorker(QThread):
    """标签导入工作线程"""
    
    progress_updated = Signal(int, str)  # progress, message
    import_finished = Signal(dict)  # results
    import_error = Signal(str)  # error message
    
    def __init__(self, photo_paths: List[str], tag_type: str, language: str, db_manager, clear_existing: bool = False, append_tags: bool = True):
        super().__init__()
        self.photo_paths = photo_paths
        self.tag_type = tag_type  # 'normal', 'simple', 'detailed'
        self.language = language  # 'chinese', 'english'
        self.db_manager = db_manager
        self.clear_existing = clear_existing
        self.append_tags = append_tags
        self.cancelled = False
        
    def run(self):
        """执行标签导入"""
        try:
            results = {
                'total_photos': len(self.photo_paths),
                'processed_photos': 0,
                'imported_tags': 0,
                'skipped_photos': 0,
                'errors': []
            }
            
            for i, photo_path in enumerate(self.photo_paths):
                if self.cancelled:
                    break
                    
                try:
                    self.progress_updated.emit(
                        int((i / len(self.photo_paths)) * 100),
                        f"处理图片: {Path(photo_path).name}"
                    )
                    
                    # 查找标签文件
                    tag_file = self.find_tag_file(photo_path)
                    if tag_file:
                        # 读取标签内容
                        tags = self.read_tag_file(tag_file)
                        if tags:
                            # 导入到数据库
                            success = self.import_tags_to_database(photo_path, tags)
                            if success:
                                results['imported_tags'] += 1
                            else:
                                results['errors'].append(f"导入失败: {Path(photo_path).name}")
                        else:
                            results['skipped_photos'] += 1
                    else:
                        results['skipped_photos'] += 1
                        
                    results['processed_photos'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"处理失败 {Path(photo_path).name}: {str(e)}")
                    results['processed_photos'] += 1
                    
            if not self.cancelled:
                self.import_finished.emit(results)
                
        except Exception as e:
            self.import_error.emit(f"导入过程出错: {str(e)}")
            
    def find_tag_file(self, photo_path: str) -> Optional[str]:
        """查找标签文件"""
        try:
            photo_dir = Path(photo_path).parent
            photo_name = Path(photo_path).stem
            
            # 可能的标签文件名
            possible_names = [
                f"{photo_name}.txt",
                f"{photo_name}_tags.txt",
                f"{photo_name}_labels.txt",
                f"{photo_name}.json",
                f"{photo_name}_tags.json",
                f"{photo_name}_labels.json"
            ]
            
            for name in possible_names:
                tag_file = photo_dir / name
                if tag_file.exists():
                    return str(tag_file)
                    
            return None
            
        except Exception as e:
            self.logger.error(f"查找标签文件失败: {str(e)}")
            return None
            
    def read_tag_file(self, tag_file: str) -> Optional[str]:
        """读取标签文件内容"""
        try:
            file_path = Path(tag_file)
            
            if file_path.suffix.lower() == '.json':
                # 读取JSON文件
                with open(tag_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 尝试不同的JSON结构
                    if isinstance(data, dict):
                        # 如果是字典，尝试常见的键名
                        for key in ['tags', 'labels', 'description', 'caption', 'text']:
                            if key in data:
                                content = data[key]
                                if isinstance(content, list):
                                    return json.dumps(content)  # 返回JSON字符串
                                elif isinstance(content, str):
                                    return content
                    elif isinstance(data, list):
                        return json.dumps(data)  # 返回JSON字符串
                    elif isinstance(data, str):
                        return data
            else:
                # 读取文本文件
                with open(tag_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        # 如果是逗号分隔的标签，转换为JSON数组
                        tags = [tag.strip() for tag in content.split(',') if tag.strip()]
                        return json.dumps(tags) if tags else None
                    return None
                    
            return None
            
        except Exception as e:
            self.logger.error(f"读取标签文件失败 {tag_file}: {str(e)}")
            return None
            
    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否为中文"""
        import re
        # 检查是否包含中文字符
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        return bool(chinese_pattern.search(text))
    
    def _separate_tags_by_language(self, tags_list: list) -> tuple:
        """将标签按语言分离"""
        chinese_tags = []
        english_tags = []
        
        for tag in tags_list:
            if isinstance(tag, str):
                if self._is_chinese_text(tag):
                    chinese_tags.append(tag)
                else:
                    english_tags.append(tag)
        
        return english_tags, chinese_tags
    
    def import_tags_to_database(self, photo_path: str, tags: str) -> bool:
        """导入标签到数据库"""
        try:
            # 解析新标签
            try:
                import json
                new_tags_list = json.loads(tags) if tags else []
            except:
                new_tags_list = [tags] if tags else []
            
            # 分离中英文标签
            english_tags, chinese_tags = self._separate_tags_by_language(new_tags_list)
            
            # 根据用户选择的标签类型确定数据库字段
            field_mapping = {
                'simple': ('simple_tags_en', 'simple_tags_cn'),
                'normal': ('general_tags_en', 'general_tags_cn'),
                'detailed': ('detailed_tags_en', 'detailed_tags_cn')
            }
            
            en_field, cn_field = field_mapping.get(self.tag_type, ('general_tags_en', 'general_tags_cn'))
            
            # 读取现有的标签数据
            query = f"SELECT {en_field}, {cn_field} FROM photos WHERE filepath = ?"
            result = self.db_manager.fetch_one(query, (photo_path,))
            
            if result:
                existing_en_tags = result[0] if result[0] else ''
                existing_cn_tags = result[1] if result[1] else ''
            else:
                existing_en_tags = ''
                existing_cn_tags = ''
            
            # 如果选择清空现有标签，先清空
            if self.clear_existing:
                existing_en_tags = ''
                existing_cn_tags = ''
            
            # 根据用户选择的语言和追加选项进行导入
            if self.language == 'chinese':
                # 用户选择中文：英文标签作为主标签，中文标签作为翻译
                if english_tags:
                    if self.append_tags and existing_en_tags.strip():
                        final_en_tags = existing_en_tags + ', ' + ', '.join(english_tags)
                    else:
                        final_en_tags = ', '.join(english_tags)
                else:
                    final_en_tags = existing_en_tags if self.append_tags else ''
                
                if chinese_tags:
                    if self.append_tags and existing_cn_tags.strip():
                        final_cn_tags = existing_cn_tags + ', ' + ', '.join(chinese_tags)
                    else:
                        final_cn_tags = ', '.join(chinese_tags)
                else:
                    final_cn_tags = existing_cn_tags if self.append_tags else ''
            else:
                # 用户选择英文：英文标签作为主标签
                if english_tags:
                    if self.append_tags and existing_en_tags.strip():
                        final_en_tags = existing_en_tags + ', ' + ', '.join(english_tags)
                    else:
                        final_en_tags = ', '.join(english_tags)
                else:
                    final_en_tags = existing_en_tags if self.append_tags else ''
                
                if chinese_tags:
                    if self.append_tags and existing_cn_tags.strip():
                        final_cn_tags = existing_cn_tags + ', ' + ', '.join(chinese_tags)
                    else:
                        final_cn_tags = ', '.join(chinese_tags)
                else:
                    final_cn_tags = existing_cn_tags if self.append_tags else ''
            
            # 使用统一标签系统更新数据库
            # 首先获取当前照片数据
            photo_query = "SELECT id FROM photos WHERE filepath = ?"
            photo_result = self.db_manager.fetch_one(photo_query, (photo_path,))
            
            if not photo_result:
                return False
            
            photo_id = photo_result[0]
            
            # 获取当前照片的统一标签数据
            photo_data = self.db_manager.get_photo(photo_id)
            if not photo_data:
                return False
            
            # 读取现有的统一标签数据
            from src.picman.database.manager import UnifiedTagsAccessor
            unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_data)
            
            # 更新对应的标签类型和语言
            category_mapping = {
                'simple': 'simple',
                'normal': 'normal', 
                'detailed': 'detailed'
            }
            
            category = category_mapping.get(self.tag_type, 'normal')
            
            # 更新统一标签结构
            if category in unified_tags:
                unified_tags[category]["en"] = final_en_tags
                unified_tags[category]["zh"] = final_cn_tags
            
            # 使用统一标签系统保存（会自动双写）
            success = self.db_manager.update_photo(photo_id, {
                "unified_tags_data": unified_tags
            })
            
            return success
            
        except Exception as e:
            self.logger.error(f"导入标签到数据库失败: {str(e)}")
            return False
            
    def cancel(self):
        """取消导入"""
        self.cancelled = True


class TagImportDialog(QDialog):
    """标签导入对话框"""
    
    def __init__(self, photo_paths: List[str], db_manager, parent=None):
        super().__init__(parent)
        self.photo_paths = photo_paths
        self.db_manager = db_manager
        self.import_worker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("导入标签")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择标签类型和语言")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 标签类型选择
        tag_type_group = QGroupBox("标签类型")
        tag_type_layout = QVBoxLayout(tag_type_group)
        
        self.tag_type_group = QButtonGroup()
        
        self.normal_tags_radio = QRadioButton("普通标签")
        self.normal_tags_radio.setChecked(True)
        self.tag_type_group.addButton(self.normal_tags_radio, 1)
        tag_type_layout.addWidget(self.normal_tags_radio)
        
        self.simple_tags_radio = QRadioButton("简单标签")
        self.tag_type_group.addButton(self.simple_tags_radio, 2)
        tag_type_layout.addWidget(self.simple_tags_radio)
        
        self.detailed_tags_radio = QRadioButton("详细标签")
        self.tag_type_group.addButton(self.detailed_tags_radio, 3)
        tag_type_layout.addWidget(self.detailed_tags_radio)
        
        layout.addWidget(tag_type_group)
        
        # 语言选择
        language_group = QGroupBox("语言")
        language_layout = QHBoxLayout(language_group)
        
        self.language_group = QButtonGroup()
        
        self.chinese_radio = QRadioButton("中文")
        self.chinese_radio.setChecked(True)
        self.language_group.addButton(self.chinese_radio, 1)
        language_layout.addWidget(self.chinese_radio)
        
        self.english_radio = QRadioButton("英文")
        self.language_group.addButton(self.english_radio, 2)
        language_layout.addWidget(self.english_radio)
        
        layout.addWidget(language_group)
        
        # 导入选项
        options_group = QGroupBox("导入选项")
        options_layout = QVBoxLayout(options_group)
        
        self.clear_existing_checkbox = QCheckBox("清空已存在照片的标签")
        self.clear_existing_checkbox.setToolTip("导入前先清空照片的所有标签信息")
        options_layout.addWidget(self.clear_existing_checkbox)
        
        self.append_tags_checkbox = QCheckBox("追加到现有标签")
        self.append_tags_checkbox.setChecked(True)
        self.append_tags_checkbox.setToolTip("将新标签追加到现有标签后面，而不是覆盖")
        options_layout.addWidget(self.append_tags_checkbox)
        
        layout.addWidget(options_group)
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel(f"待处理图片数量: {len(self.photo_paths)}")
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("开始导入")
        self.import_btn.clicked.connect(self.start_import)
        button_layout.addWidget(self.import_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def get_selected_options(self) -> Tuple[str, str]:
        """获取选择的选项"""
        # 获取标签类型
        tag_type_map = {
            1: 'normal',
            2: 'simple', 
            3: 'detailed'
        }
        tag_type = tag_type_map.get(self.tag_type_group.checkedId(), 'normal')
        
        # 获取语言
        language_map = {
            1: 'chinese',
            2: 'english'
        }
        language = language_map.get(self.language_group.checkedId(), 'chinese')
        
        return tag_type, language
        
    def start_import(self):
        """开始导入"""
        try:
            tag_type, language = self.get_selected_options()
            
            # 禁用按钮
            self.import_btn.setEnabled(False)
            self.cancel_btn.setText("取消导入")
            self.cancel_btn.clicked.disconnect()
            self.cancel_btn.clicked.connect(self.cancel_import)
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 清空日志
            self.log_text.clear()
            self.log_message("开始导入标签...")
            
            # 创建工作线程
            self.import_worker = TagImportWorker(
                self.photo_paths, tag_type, language, self.db_manager,
                clear_existing=self.clear_existing_checkbox.isChecked(),
                append_tags=self.append_tags_checkbox.isChecked()
            )
            self.import_worker.progress_updated.connect(self.update_progress)
            self.import_worker.import_finished.connect(self.import_finished)
            self.import_worker.import_error.connect(self.import_error)
            
            # 启动线程
            self.import_worker.start()
            
        except Exception as e:
            self.log_message(f"启动导入失败: {str(e)}")
            self.reset_ui()
            
    def update_progress(self, progress: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.log_message(message)
        
    def import_finished(self, results: dict):
        """导入完成"""
        self.log_message("导入完成!")
        self.log_message(f"处理图片: {results['processed_photos']}/{results['total_photos']}")
        self.log_message(f"导入标签: {results['imported_tags']}")
        self.log_message(f"跳过图片: {results['skipped_photos']}")
        
        if results['errors']:
            self.log_message(f"错误数量: {len(results['errors'])}")
            for error in results['errors'][:5]:  # 只显示前5个错误
                self.log_message(f"  - {error}")
                
        self.progress_bar.setValue(100)
        
        # 显示完成消息
        QMessageBox.information(
            self, 
            "导入完成", 
            f"标签导入完成!\n"
            f"处理图片: {results['processed_photos']}/{results['total_photos']}\n"
            f"导入标签: {results['imported_tags']}\n"
            f"跳过图片: {results['skipped_photos']}"
        )
        
        self.accept()
        
    def import_error(self, error_message: str):
        """导入错误"""
        self.log_message(f"导入错误: {error_message}")
        QMessageBox.critical(self, "导入错误", f"标签导入失败: {error_message}")
        self.reset_ui()
        
    def cancel_import(self):
        """取消导入"""
        if self.import_worker and self.import_worker.isRunning():
            self.import_worker.cancel()
            self.import_worker.wait()
            
        self.log_message("导入已取消")
        self.reset_ui()
        self.reject()
        
    def reset_ui(self):
        """重置界面"""
        self.import_btn.setEnabled(True)
        self.cancel_btn.setText("取消")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.reject)
        self.progress_bar.setVisible(False)
        
    def log_message(self, message: str):
        """记录日志消息"""
        self.log_text.append(message)
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.import_worker and self.import_worker.isRunning():
            self.import_worker.cancel()
            self.import_worker.wait()
        super().closeEvent(event) 