"""
标签编辑页面组件
包含图片显示和标签编辑功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QRadioButton,
    QCheckBox, QTextEdit, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont
import logging

from .photo_viewer import PhotoViewer
from .tag_edit_panel import TagEditPanel


class TagEditPage(QWidget):
    """标签编辑页面，包含图片显示和标签编辑功能"""
    
    # 信号定义
    photo_updated = pyqtSignal(int)  # photo_id
    previous_photo_requested = pyqtSignal()  # 请求上一张图片
    next_photo_requested = pyqtSignal()  # 请求下一张图片
    
    def __init__(self, db_manager, photo_manager):
        super().__init__()
        
        self.db_manager = db_manager
        self.photo_manager = photo_manager
        self.current_photo = None
        
        # 配置标准logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("picman.gui.tag_edit_page")
        
        self.logger.info("标签编辑页开始初始化")
        
        try:
            self.init_ui()
            self.logger.info("UI初始化完成")
        except Exception as e:
            self.logger.error("UI初始化失败: %s", str(e))
            raise
        
        try:
            self.connect_signals()
            self.logger.info("信号连接完成")
        except Exception as e:
            self.logger.error("信号连接失败: %s", str(e))
            raise
        
        self.logger.info("标签编辑页初始化完成")
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建分割器，上半部分图片显示，下半部分标签编辑
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部分：图片显示区域（复用PhotoViewer）
        self.photo_viewer = PhotoViewer()
        # 在标签编辑页中隐藏元数据面板，只显示图片和工具栏
        # 但是保留收藏复选框，因为收藏功能很重要
        self.photo_viewer.set_info_panel_visible(False)
        
        # 创建一个简化的收藏复选框，添加到标签编辑页中
        # 这个复选框会直接调用PhotoViewer的收藏功能，保持完全一致
        self.create_simple_favorite_checkbox()
        
        splitter.addWidget(self.photo_viewer)
        
        # 下半部分：标签编辑面板
        self.tag_edit_panel = TagEditPanel(self.db_manager)
        splitter.addWidget(self.tag_edit_panel)
        
        # 设置分割器比例（图片显示区域占70%，标签编辑区域占30%）
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
    
    def create_simple_favorite_checkbox(self):
        """创建一个简化的收藏复选框，添加到标签编辑页中"""
        try:
            from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QWidget
            
            # 创建一个简单的容器来放置收藏复选框
            favorite_container = QWidget()
            favorite_layout = QHBoxLayout(favorite_container)
            favorite_layout.setContentsMargins(10, 5, 10, 5)
            
            # 创建收藏复选框
            self.simple_favorite_checkbox = QCheckBox("收藏")
            self.simple_favorite_checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 14px;
                    font-weight: bold;
                    color: #333;
                    padding: 5px;
                }
                QCheckBox:hover {
                    color: #0066cc;
                }
            """)
            
            # 连接信号
            self.simple_favorite_checkbox.stateChanged.connect(self.on_simple_favorite_changed)
            
            # 添加到布局
            favorite_layout.addWidget(self.simple_favorite_checkbox)
            favorite_layout.addStretch()
            
            # 将收藏容器添加到主布局的顶部
            self.layout().insertWidget(0, favorite_container)
            
            self.logger.info("简化收藏复选框创建成功")
            
        except Exception as e:
            self.logger.error("创建简化收藏复选框失败: %s", str(e))
    
    def on_simple_favorite_changed(self, state):
        """简化收藏复选框状态变化处理 - 直接调用PhotoViewer的收藏功能"""
        try:
            if self.current_photo and hasattr(self.photo_viewer, 'toggle_favorite'):
                # 直接调用PhotoViewer的收藏功能，保持完全一致
                self.photo_viewer.toggle_favorite(state)
                self.logger.info("通过PhotoViewer更新收藏状态: state=%s", state)
            else:
                self.logger.warning("无法通过PhotoViewer更新收藏状态")
                
        except Exception as e:
            self.logger.error("更新收藏状态失败: %s", str(e))
            # 回退UI状态
            if self.current_photo:
                self.simple_favorite_checkbox.setChecked(self.current_photo.get('is_favorite', False))
    
    def sync_simple_favorite_checkbox(self, state):
        """同步简化收藏复选框的状态，防止循环调用"""
        try:
            # 暂时断开信号，防止循环调用
            self.simple_favorite_checkbox.stateChanged.disconnect(self.on_simple_favorite_changed)
            
            # 同步状态
            self.simple_favorite_checkbox.setChecked(state == 2)  # Qt.CheckState.Checked.value
            
            # 重新连接信号
            self.simple_favorite_checkbox.stateChanged.connect(self.on_simple_favorite_changed)
            
            self.logger.info("简化收藏复选框状态同步完成: state=%s", state)
            
        except Exception as e:
            self.logger.error("同步简化收藏复选框状态失败: %s", str(e))
            # 重新连接信号
            try:
                self.simple_favorite_checkbox.stateChanged.connect(self.on_simple_favorite_changed)
            except:
                pass
    
    def connect_signals(self):
        """连接信号槽"""
        # 连接PhotoViewer的信号
        self.photo_viewer.photo_updated.connect(self.photo_updated.emit)
        self.photo_viewer.previous_photo_requested.connect(self.previous_photo_requested.emit)
        self.photo_viewer.next_photo_requested.connect(self.next_photo_requested.emit)
        
        # 连接PhotoViewer的收藏状态变化，同步简化收藏复选框
        if hasattr(self.photo_viewer, 'favorite_checkbox') and self.photo_viewer.favorite_checkbox:
            self.photo_viewer.favorite_checkbox.stateChanged.connect(self.sync_simple_favorite_checkbox)
        
        # 连接标签编辑面板的信号
        if hasattr(self.tag_edit_panel, 'tags_saved'):
            self.tag_edit_panel.tags_saved.connect(self.on_tags_saved)
    
    def update_photo(self, photo_data: dict):
        """更新当前显示的照片"""
        try:
            # 数据有效性检查
            if not photo_data:
                self.logger.warning("照片数据为空")
                return
            
            photo_id = photo_data.get('id')
            if not photo_id:
                self.logger.warning("照片ID不存在")
                return
            
            self.logger.info("标签编辑页开始更新照片: photo_id=%s", photo_id)
            self.current_photo = photo_data
            
            # 更新图片显示区域 - 使用PhotoViewer的display_photo方法
            if self.photo_viewer:
                self.logger.info("正在更新PhotoViewer")
                try:
                    # 强制刷新PhotoViewer，确保图片能正确显示
                    self.photo_viewer.display_photo(photo_data)
                    self.logger.info("PhotoViewer更新完成")
                except Exception as e:
                    self.logger.error("PhotoViewer更新失败: %s", str(e))
            else:
                self.logger.warning("PhotoViewer不存在")
            
            # 更新标签编辑面板
            if self.tag_edit_panel:
                self.logger.info("正在更新标签编辑面板")
                try:
                    self.tag_edit_panel.update_photo(photo_data)
                    self.logger.info("标签编辑面板更新完成")
                except Exception as e:
                    self.logger.error("标签编辑面板更新失败: %s", str(e))
            else:
                self.logger.warning("标签编辑面板不存在")
            
            # 同步简化收藏复选框的状态
            if hasattr(self, 'simple_favorite_checkbox') and self.simple_favorite_checkbox:
                is_favorite = photo_data.get('is_favorite', False)
                self.simple_favorite_checkbox.setChecked(is_favorite)
                self.logger.info("简化收藏复选框状态同步完成: is_favorite=%s", is_favorite)
            
            self.logger.info("标签编辑页照片更新成功: photo_id=%s", photo_id)
            
        except Exception as e:
            self.logger.error("更新照片失败: %s", str(e))
    
    def force_refresh_photo_display(self, photo_data: dict):
        """强制刷新照片显示 - 用于解决图片不显示的问题"""
        try:
            self.logger.info("强制刷新照片显示: photo_id=%s", photo_data.get('id'))
            
            # 强制重新设置PhotoViewer的照片数据
            if self.photo_viewer:
                # 清除当前显示
                self.photo_viewer.clear_display()
                
                # 重新显示照片
                self.photo_viewer.display_photo(photo_data)
                self.logger.info("强制刷新PhotoViewer完成")
            
            # 强制更新标签编辑面板
            if self.tag_edit_panel:
                self.tag_edit_panel.update_photo(photo_data)
                self.logger.info("强制刷新标签编辑面板完成")
            
        except Exception as e:
            self.logger.error("强制刷新照片显示失败: %s", str(e))
    
    def on_photo_selected(self, photo_data: dict):
        """处理照片选择事件 - 与主窗口的照片选择逻辑保持一致"""
        try:
            self.logger.info("标签编辑页收到照片选择事件: photo_id=%s", photo_data.get('id'))
            self.update_photo(photo_data)
        except Exception as e:
            self.logger.error("处理照片选择事件失败: %s", str(e))
    
    def on_tags_saved(self, photo_id):
        """标签保存成功后的处理"""
        try:
            # 通知主窗口标签已更新
            self.photo_updated.emit(photo_id)
            self.logger.info("标签保存成功: photo_id=%s", photo_id)
            
        except Exception as e:
            self.logger.error("处理标签保存信号失败: %s", str(e))
    
    def get_current_photo(self):
        """获取当前显示的照片数据"""
        return self.current_photo
    
    def set_editing_mode(self, editing: bool):
        """设置编辑模式"""
        try:
            if self.tag_edit_panel:
                self.tag_edit_panel.set_editing_mode(editing)
            self.logger.info("编辑模式设置: editing=%s", editing)
            
        except Exception as e:
            self.logger.error("设置编辑模式失败: %s", str(e))
    
    def get_photo_viewer(self):
        """获取PhotoViewer实例，供外部调用"""
        return self.photo_viewer
