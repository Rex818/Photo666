"""
标签编辑面板组件
处理标签的显示和编辑功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QRadioButton,
    QCheckBox, QTextEdit, QGroupBox, QButtonGroup,
    QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont
import logging
import json


class TagEditPanel(QWidget):
    """标签编辑面板，处理标签的显示和编辑"""
    
    # 信号定义
    tags_saved = pyqtSignal(int)  # photo_id
    tags_edited = pyqtSignal(int)  # photo_id
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_photo = None
        self.is_editing = False
        
        # 配置标准logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("picman.gui.tag_edit_panel")
        
        # 标签类型选择
        self.tag_type_group = QButtonGroup()
        self.simple_radio = None
        self.normal_radio = None
        self.detailed_radio = None
        
        # 标签编辑控件
        self.simple_en_edit = None
        self.simple_cn_edit = None
        self.normal_en_edit = None
        self.normal_cn_edit = None
        self.detailed_en_edit = None
        self.detailed_cn_edit = None
        
        # 功能按钮
        self.edit_btn = None
        self.save_btn = None
        self.favorite_checkbox = None
        
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """初始化标签编辑界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标签类型选择区域（小方框）
        self.create_tag_type_selection(layout)
        
        # 功能按钮区域
        self.create_function_buttons(layout)
        
        # 双语标签显示区域（大方框）
        self.create_bilingual_tag_area(layout)
        
        # 设置初始状态
        self.set_editing_mode(False)
        
        # 设置初始标签显示状态（默认显示单标签）
        self.update_tag_display_visibility(1) # Changed from 0 to 1 for normal tag
    
    def create_tag_type_selection(self, parent_layout):
        """创建标签类型选择区域"""
        group_box = QGroupBox("标签类型选择")
        group_layout = QHBoxLayout(group_box)
        group_layout.setContentsMargins(5, 2, 5, 2)  # 减少上下边距
        group_layout.setSpacing(10)
        
        # 创建单选按钮
        self.simple_radio = QRadioButton("简单标签")
        self.normal_radio = QRadioButton("普通标签")
        self.detailed_radio = QRadioButton("详细标签")
        
        # 添加到按钮组
        self.tag_type_group.addButton(self.simple_radio, 0)
        self.tag_type_group.addButton(self.normal_radio, 1)
        self.tag_type_group.addButton(self.detailed_radio, 2)
        
        # 设置默认选择
        self.normal_radio.setChecked(True)
        
        # 添加到布局
        group_layout.addWidget(self.simple_radio)
        group_layout.addWidget(self.normal_radio)
        group_layout.addWidget(self.detailed_radio)
        group_layout.addStretch()
        
        parent_layout.addWidget(group_box)
    
    def create_function_buttons(self, parent_layout):
        """创建功能按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 2, 0, 2)  # 减少上下边距
        button_layout.setSpacing(10)
        
        # 编辑标签按钮
        self.edit_btn = QPushButton("编辑标签")
        self.edit_btn.setFixedSize(80, 25)  # 减少按钮高度
        button_layout.addWidget(self.edit_btn)
        
        # 保存标签按钮
        self.save_btn = QPushButton("保存标签")
        self.save_btn.setFixedSize(80, 25)  # 减少按钮高度
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.save_btn)
        
        # 收藏复选框
        self.favorite_checkbox = QCheckBox("收藏")
        button_layout.addWidget(self.favorite_checkbox)
        
        button_layout.addStretch()
        
        parent_layout.addLayout(button_layout)
    
    def create_bilingual_tag_area(self, parent_layout):
        """创建双语标签显示区域"""
        group_box = QGroupBox("标签内容")
        group_layout = QVBoxLayout(group_box)
        
        # 创建水平分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：英文标签
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        en_label = QLabel("英文标签:")
        en_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        left_layout.addWidget(en_label)
        
        # 英文标签编辑区域（不显示标签名称）
        self.simple_en_edit = QTextEdit()
        self.simple_en_edit.setMinimumHeight(80)  # 增加最小高度
        self.simple_en_edit.setMaximumHeight(120)  # 增加最大高度
        self.simple_en_edit.setPlaceholderText("输入简单英文标签...")
        left_layout.addWidget(self.simple_en_edit)
        
        self.normal_en_edit = QTextEdit()
        self.normal_en_edit.setMinimumHeight(80)  # 增加最小高度
        self.normal_en_edit.setMaximumHeight(120)  # 增加最大高度
        self.normal_en_edit.setPlaceholderText("输入普通英文标签...")
        left_layout.addWidget(self.normal_en_edit)
        
        self.detailed_en_edit = QTextEdit()
        self.detailed_en_edit.setMinimumHeight(80)  # 增加最小高度
        self.detailed_en_edit.setMaximumHeight(120)  # 增加最大高度
        self.detailed_en_edit.setPlaceholderText("输入详细英文标签...")
        left_layout.addWidget(self.detailed_en_edit)
        
        splitter.addWidget(left_frame)
        
        # 右侧：中文标签
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        cn_label = QLabel("中文标签:")
        cn_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        right_layout.addWidget(cn_label)
        
        # 中文标签编辑区域（不显示标签名称）
        self.simple_cn_edit = QTextEdit()
        self.simple_cn_edit.setMinimumHeight(80)  # 增加最小高度
        self.simple_cn_edit.setMaximumHeight(120)  # 增加最大高度
        self.simple_cn_edit.setPlaceholderText("输入简单中文标签...")
        right_layout.addWidget(self.simple_cn_edit)
        
        self.normal_cn_edit = QTextEdit()
        self.normal_cn_edit.setMinimumHeight(80)  # 增加最小高度
        self.normal_cn_edit.setMaximumHeight(120)  # 增加最大高度
        self.normal_cn_edit.setPlaceholderText("输入普通中文标签...")
        right_layout.addWidget(self.normal_cn_edit)
        
        self.detailed_cn_edit = QTextEdit()
        self.detailed_cn_edit.setMinimumHeight(80)  # 增加最小高度
        self.detailed_cn_edit.setMaximumHeight(120)  # 增加最大高度
        self.detailed_cn_edit.setPlaceholderText("输入详细中文标签...")
        right_layout.addWidget(self.detailed_cn_edit)
        
        splitter.addWidget(right_frame)
        
        # 设置分割器比例
        splitter.setSizes([400, 400])
        
        group_layout.addWidget(splitter)
        parent_layout.addWidget(group_box)
    
    def connect_signals(self):
        """连接信号槽"""
        # 标签类型选择变化
        self.tag_type_group.buttonClicked.connect(self.on_tag_type_changed)
        
        # 功能按钮
        if self.edit_btn:
            self.edit_btn.clicked.connect(self.on_edit_clicked)
        if self.save_btn:
            self.save_btn.clicked.connect(self.on_save_clicked)
        if self.favorite_checkbox:
            self.favorite_checkbox.stateChanged.connect(self.on_favorite_changed)
    
    def on_tag_type_changed(self, button):
        """标签类型选择变化处理"""
        try:
            button_id = self.tag_type_group.id(button)
            self.logger.info("标签类型选择变化: button_id=%s, button_text=%s", button_id, button.text())
            
            # 根据选择的标签类型，控制下方标签内容的显示
            self.update_tag_display_visibility(button_id)
            
        except Exception as e:
            self.logger.error("处理标签类型选择变化失败: %s", str(e))
    
    def update_tag_display_visibility(self, selected_type):
        """根据选择的标签类型更新标签显示区域的可见性"""
        try:
            # 隐藏所有标签编辑区域
            self.simple_en_edit.setVisible(False)
            self.simple_cn_edit.setVisible(False)
            self.normal_en_edit.setVisible(False)
            self.normal_cn_edit.setVisible(False)
            self.detailed_en_edit.setVisible(False)
            self.detailed_cn_edit.setVisible(False)
            
            # 根据选择的类型显示对应的标签编辑区域
            if selected_type == 0:  # 简单标签
                self.simple_en_edit.setVisible(True)
                self.simple_cn_edit.setVisible(True)
                self.logger.info("显示简单标签编辑区域")
            elif selected_type == 1:  # 普通标签
                self.normal_en_edit.setVisible(True)
                self.normal_cn_edit.setVisible(True)
                self.logger.info("显示普通标签编辑区域")
            elif selected_type == 2:  # 详细标签
                self.detailed_en_edit.setVisible(True)
                self.detailed_cn_edit.setVisible(True)
                self.logger.info("显示详细标签编辑区域")
            
        except Exception as e:
            self.logger.error("更新标签显示可见性失败: %s", str(e))
    
    def on_edit_clicked(self):
        """编辑标签按钮点击处理"""
        try:
            self.set_editing_mode(True)
            self.logger.info("进入编辑模式")
            
        except Exception as e:
            self.logger.error("进入编辑模式失败: %s", str(e))
    
    def on_save_clicked(self):
        """保存标签按钮点击处理"""
        try:
            if self.save_tags():
                self.set_editing_mode(False)
                self.logger.info("标签保存成功")
            else:
                self.logger.warning("标签保存失败")
                
        except Exception as e:
            self.logger.error("保存标签失败: %s", str(e))
    
    def on_favorite_changed(self, state):
        """收藏状态变化处理"""
        try:
            if self.current_photo:
                photo_id = self.current_photo.get('id')
                is_favorite = state == Qt.CheckState.Checked
                
                # 更新数据库中的收藏状态
                if self.db_manager:
                    success = self.db_manager.update_photo(photo_id, {"is_favorite": is_favorite})
                    if success:
                        # 更新内存中的照片数据
                        self.current_photo["is_favorite"] = is_favorite
                        self.logger.info("收藏状态更新成功: photo_id=%s, is_favorite=%s", photo_id, is_favorite)
                        
                        # 发送照片更新信号，通知主窗口
                        if hasattr(self, 'photo_updated'):
                            self.photo_updated.emit(photo_id)
                        
                        # 通知主窗口刷新相关显示
                        main_window = self.window()
                        if main_window and hasattr(main_window, 'refresh_current_photo_display_page'):
                            main_window.refresh_current_photo_display_page(self.current_photo)
                    else:
                        self.logger.error("收藏状态更新失败: photo_id=%s, is_favorite=%s", photo_id, is_favorite)
                        # 回退UI状态
                        self.favorite_checkbox.setChecked(not is_favorite)
                        self.current_photo["is_favorite"] = not is_favorite
                else:
                    self.logger.error("数据库管理器不可用")
                    # 回退UI状态
                    self.favorite_checkbox.setChecked(not is_favorite)
                
        except Exception as e:
            self.logger.error("更新收藏状态失败: %s", str(e))
            # 回退UI状态
            if self.current_photo:
                self.favorite_checkbox.setChecked(self.current_photo.get('is_favorite', False))
    
    def update_photo(self, photo_data):
        """更新当前显示的照片"""
        try:
            self.logger.info("标签编辑面板开始更新照片: photo_id=%s", photo_data.get('id') if photo_data else 'None')
            self.current_photo = photo_data
            
            if not photo_data:
                self.logger.warning("照片数据为空，清空显示")
                self.clear_display()
                return
            
            # 加载标签数据
            self.logger.info("开始加载标签数据")
            self.load_tag_data(photo_data)
            self.logger.info("标签数据加载完成")
            
            # 更新收藏状态
            self.logger.info("开始更新收藏状态")
            self.update_favorite_display(photo_data)
            self.logger.info("收藏状态更新完成")
            
            self.logger.info("照片标签数据更新成功: photo_id=%s", photo_data.get('id'))
            
        except Exception as e:
            self.logger.error("更新照片标签数据失败: %s", str(e))
    
    def load_tag_data(self, photo_data):
        """加载标签数据到界面"""
        try:
            photo_id = photo_data.get('id')
            if not photo_id:
                self.logger.warning("照片ID不存在")
                return
            
            self.logger.info("开始加载标签数据: photo_id=%s", photo_id)
            
            # 从照片数据中获取标签数据
            if photo_data:
                # 首先尝试从统一标签数据读取
                unified_tags = photo_data.get('unified_tags_data', {})
                
                if unified_tags and isinstance(unified_tags, dict):
                    self.logger.info("使用统一标签数据")
                    
                    # 更新简单标签
                    if self.simple_en_edit:
                        simple_en = unified_tags.get('simple', {}).get('en', '')
                        self.simple_en_edit.setPlainText(simple_en)
                        self.logger.info("简单标签英文: %s", simple_en)
                    
                    if self.simple_cn_edit:
                        simple_cn = unified_tags.get('simple', {}).get('zh', '')
                        self.simple_cn_edit.setPlainText(simple_cn)
                        self.logger.info("简单标签中文: %s", simple_cn)
                    
                    # 更新普通标签
                    if self.normal_en_edit:
                        normal_en = unified_tags.get('normal', {}).get('en', '')
                        self.normal_en_edit.setPlainText(normal_en)
                        self.logger.info("普通标签英文: %s", normal_en)
                    
                    if self.normal_cn_edit:
                        normal_cn = unified_tags.get('normal', {}).get('zh', '')
                        self.normal_cn_edit.setPlainText(normal_cn)
                        self.logger.info("普通标签中文: %s", normal_cn)
                    
                    # 更新详细标签
                    if self.detailed_en_edit:
                        detailed_en = unified_tags.get('detailed', {}).get('en', '')
                        self.detailed_en_edit.setPlainText(detailed_en)
                        self.logger.info("详细标签英文: %s", detailed_en)
                    
                    if self.detailed_cn_edit:
                        detailed_cn = unified_tags.get('detailed', {}).get('zh', '')
                        self.detailed_cn_edit.setPlainText(detailed_cn)
                        self.logger.info("详细标签中文: %s", detailed_cn)
                
                # 如果没有统一标签，尝试获取传统标签字段
                else:
                    self.logger.info("使用传统标签字段")
                    
                    if self.simple_en_edit:
                        simple_en = photo_data.get('simple_tags_en', '')
                        self.simple_en_edit.setPlainText(simple_en)
                        self.logger.info("简单标签英文: %s", simple_en)
                    
                    if self.simple_cn_edit:
                        simple_cn = photo_data.get('simple_tags_cn', '')
                        self.simple_cn_edit.setPlainText(simple_cn)
                        self.logger.info("简单标签中文: %s", simple_cn)
                    
                    if self.normal_en_edit:
                        normal_en = photo_data.get('general_tags_en', '')
                        self.normal_en_edit.setPlainText(normal_en)
                        self.logger.info("普通标签英文: %s", normal_en)
                    
                    if self.normal_cn_edit:
                        normal_cn = photo_data.get('general_tags_cn', '')
                        self.normal_cn_edit.setPlainText(normal_cn)
                        self.logger.info("普通标签中文: %s", normal_cn)
                    
                    if self.detailed_en_edit:
                        detailed_en = photo_data.get('detailed_tags_en', '')
                        self.detailed_en_edit.setPlainText(detailed_en)
                        self.logger.info("详细标签英文: %s", detailed_en)
                    
                    if self.detailed_cn_edit:
                        detailed_cn = photo_data.get('detailed_tags_cn', '')
                        self.detailed_cn_edit.setPlainText(detailed_cn)
                        self.logger.info("详细标签中文: %s", detailed_cn)
                
                self.logger.info("标签数据加载完成: photo_id=%s", photo_id)
            
        except Exception as e:
            self.logger.error("加载标签数据失败: %s", str(e))
    
    def update_favorite_display(self, photo_data):
        """更新收藏状态显示"""
        try:
            if self.favorite_checkbox:
                is_favorite = photo_data.get('is_favorite', False)
                self.favorite_checkbox.setChecked(is_favorite)
                
        except Exception as e:
            self.logger.error("更新收藏状态显示失败: %s", str(e))
    
    def clear_display(self):
        """清空显示内容"""
        try:
            # 清空所有标签编辑框
            if self.simple_en_edit:
                self.simple_en_edit.clear()
            if self.simple_cn_edit:
                self.simple_cn_edit.clear()
            if self.normal_en_edit:
                self.normal_en_edit.clear()
            if self.normal_cn_edit:
                self.normal_cn_edit.clear()
            if self.detailed_en_edit:
                self.detailed_en_edit.clear()
            if self.detailed_cn_edit:
                self.detailed_cn_edit.clear()
            
            # 重置收藏状态
            if self.favorite_checkbox:
                self.favorite_checkbox.setChecked(False)
                
        except Exception as e:
            self.logger.error("清空显示内容失败: %s", str(e))
    
    def save_tags(self):
        """保存标签数据"""
        try:
            if not self.current_photo:
                QMessageBox.warning(self, "提示", "请先选择一张照片")
                return False
            
            photo_id = self.current_photo.get('id')
            if not photo_id:
                QMessageBox.warning(self, "提示", "无效的照片ID")
                return False
            
            # 获取界面上的标签内容
            simple_en = self.simple_en_edit.toPlainText().strip() if self.simple_en_edit else ""
            simple_cn = self.simple_cn_edit.toPlainText().strip() if self.simple_cn_edit else ""
            normal_en = self.normal_en_edit.toPlainText().strip() if self.normal_en_edit else ""
            normal_cn = self.normal_cn_edit.toPlainText().strip() if self.normal_cn_edit else ""
            detailed_en = self.detailed_en_edit.toPlainText().strip() if self.detailed_en_edit else ""
            detailed_cn = self.detailed_cn_edit.toPlainText().strip() if self.detailed_cn_edit else ""
            
            # 构建统一标签数据结构
            unified_tags = {
                "simple": {
                    "en": simple_en,
                    "zh": simple_cn
                },
                "normal": {
                    "en": normal_en,
                    "zh": normal_cn
                },
                "detailed": {
                    "en": detailed_en,
                    "zh": detailed_cn
                },
                "metadata": {
                    "source": "tag_edit_panel",
                    "last_updated": "2025-01-19T00:00:00"
                }
            }
            
            # 保存到数据库（使用现有的update_photo方法）
            if self.db_manager:
                success = self.db_manager.update_photo(photo_id, {
                    "unified_tags_data": unified_tags
                })
                
                if success:
                    # 发送标签保存成功信号
                    self.tags_saved.emit(photo_id)
                    
                    # 显示成功提示
                    QMessageBox.information(self, "成功", "标签保存成功！")
                    return True
                else:
                    QMessageBox.warning(self, "保存失败", "标签保存失败，请检查数据库连接")
                    return False
            else:
                QMessageBox.warning(self, "保存失败", "数据库管理器未初始化")
                return False
                
        except Exception as e:
            self.logger.error("保存标签失败: %s", str(e))
            QMessageBox.critical(self, "错误", f"保存标签时发生错误: {str(e)}")
            return False
    
    def set_editing_mode(self, editing: bool):
        """设置编辑模式"""
        try:
            self.is_editing = editing
            
            # 更新编辑按钮状态
            if self.edit_btn:
                self.edit_btn.setEnabled(not editing)
                self.edit_btn.setText("完成编辑" if editing else "编辑标签")
            
            # 更新保存按钮状态
            if self.save_btn:
                self.save_btn.setEnabled(editing)
            
            # 更新标签编辑框状态
            self.set_text_edits_enabled(editing)
            
            self.logger.info("编辑模式设置: editing=%s", editing)
            
        except Exception as e:
            self.logger.error("设置编辑模式失败: %s", str(e))
    
    def set_text_edits_enabled(self, enabled: bool):
        """设置文本编辑框的启用状态"""
        try:
            # 设置所有标签编辑框的启用状态
            if self.simple_en_edit:
                self.simple_en_edit.setReadOnly(not enabled)
            if self.simple_cn_edit:
                self.simple_cn_edit.setReadOnly(not enabled)
            if self.normal_en_edit:
                self.normal_en_edit.setReadOnly(not enabled)
            if self.normal_cn_edit:
                self.normal_cn_edit.setReadOnly(not enabled)
            if self.detailed_en_edit:
                self.detailed_en_edit.setReadOnly(not enabled)
            if self.detailed_cn_edit:
                self.detailed_cn_edit.setReadOnly(not enabled)
                
        except Exception as e:
            self.logger.error("设置文本编辑框状态失败: %s", str(e))
