"""
JoyCaption插件适配器
将JoyCaption插件适配到主程序的插件接口
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加插件目录到Python路径
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

from .main import JoyCaptionPlugin
from .core.config_manager import ConfigManager


class JoyCaptionAdapter:
    """JoyCaption插件适配器"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.plugin = JoyCaptionPlugin(self.config_manager)
        self.app_context = {}
    
    def get_info(self):
        """获取插件信息"""
        from src.picman.plugins.base import PluginInfo
        
        plugin_info = self.plugin.get_plugin_info()
        return PluginInfo(
            name=plugin_info["name"],
            version=plugin_info["version"],
            description=plugin_info["description"],
            author=plugin_info["author"]
        )
    
    def initialize(self, app_context: Dict[str, Any] = None) -> bool:
        """初始化插件"""
        try:
            if app_context:
                self.app_context = app_context
            return True
        except Exception as e:
            print(f"JoyCaption插件初始化失败: {e}")
            return False
    
    def shutdown(self) -> bool:
        """关闭插件"""
        try:
            self.plugin.shutdown()
            return True
        except Exception as e:
            print(f"JoyCaption插件关闭失败: {e}")
            return False
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """获取菜单动作"""
        return [
            {
                "name": "JoyCaption图片反推",
                "action": self.show_dialog,
                "menu": "AI工具",
                "shortcut": "Ctrl+Shift+J",
                "description": "使用JoyCaption模型进行图片信息反向推导"
            }
        ]
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        return [
            {
                "name": "JoyCaption反推",
                "action": self.show_dialog,
                "icon": "ai_caption",
                "tooltip": "JoyCaption图片反推"
            }
        ]
    
    def show_dialog(self):
        """显示对话框"""
        try:
            # 获取主窗口
            main_window = self.app_context.get("main_window")
            if not main_window:
                print("无法找到主窗口")
                return
            
            # 显示对话框
            self.plugin.show_dialog()
            
        except Exception as e:
            print(f"显示JoyCaption对话框失败: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """获取插件设置"""
        return {
            "selected_model": self.config_manager.get("selected_model", "joycaption-v1.5"),
            "memory_mode": self.config_manager.get("memory_mode", "Balanced (8-bit)"),
            "detail_level": self.config_manager.get("detail_level", "normal"),
            "caption_type": self.config_manager.get("caption_type", "Descriptive"),
            "temperature": self.config_manager.get("temperature", 0.7),
            "top_p": self.config_manager.get("top_p", 0.9),
            "max_tokens": self.config_manager.get("max_tokens", 512)
        }
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """更新插件设置"""
        try:
            for key, value in settings.items():
                self.config_manager.set(key, value)
            self.config_manager.save_user_config()
            return True
        except Exception as e:
            print(f"更新JoyCaption设置失败: {e}")
            return False


# 创建适配器实例
joycaption_adapter = JoyCaptionAdapter() 