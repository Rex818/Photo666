"""
代理管理器
负责管理网络代理配置，支持自动检测浏览器代理和手动配置
"""

import os
import sys
import logging
import json
import winreg
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from urllib.parse import urlparse


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.proxy_config = {}
        self._load_proxy_config()
    
    def _load_proxy_config(self):
        """加载代理配置"""
        try:
            config_file = Path(__file__).parent.parent / "config" / "proxy_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.proxy_config = json.load(f)
                self.logger.info("代理配置加载成功")
            else:
                self.proxy_config = {
                    "auto_detect": True,
                    "manual_proxy": {
                        "http": "",
                        "https": "",
                        "ftp": ""
                    },
                    "use_manual": False
                }
                self._save_proxy_config()
        except Exception as e:
            self.logger.error(f"加载代理配置失败: {str(e)}")
            self.proxy_config = {
                "auto_detect": True,
                "manual_proxy": {
                    "http": "",
                    "https": "",
                    "ftp": ""
                },
                "use_manual": False
            }
    
    def _save_proxy_config(self):
        """保存代理配置"""
        try:
            config_file = Path(__file__).parent.parent / "config" / "proxy_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.proxy_config, f, ensure_ascii=False, indent=2)
            self.logger.info("代理配置保存成功")
        except Exception as e:
            self.logger.error(f"保存代理配置失败: {str(e)}")
    
    def get_browser_proxy_settings(self) -> Dict[str, str]:
        """获取浏览器代理设置"""
        proxy_settings = {}
        
        try:
            # 尝试从注册表获取IE代理设置
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                try:
                    proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
                    if proxy_enable:
                        proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                        if proxy_server:
                            # 解析代理服务器设置
                            if "=" in proxy_server:
                                # 格式: http=proxy:port;https=proxy:port
                                for part in proxy_server.split(';'):
                                    if '=' in part:
                                        protocol, server = part.split('=', 1)
                                        proxy_settings[protocol.lower()] = f"http://{server}"
                            else:
                                # 格式: proxy:port (适用于所有协议)
                                proxy_settings["http"] = f"http://{proxy_server}"
                                proxy_settings["https"] = f"http://{proxy_server}"
                except FileNotFoundError:
                    pass
        except Exception as e:
            self.logger.warning(f"获取浏览器代理设置失败: {str(e)}")
        
        return proxy_settings
    
    def get_current_proxy_settings(self) -> Dict[str, str]:
        """获取当前有效的代理设置"""
        if self.proxy_config.get("use_manual", False):
            # 使用手动配置的代理
            manual_proxy = self.proxy_config.get("manual_proxy", {})
            return {k: v for k, v in manual_proxy.items() if v.strip()}
        elif self.proxy_config.get("auto_detect", True):
            # 自动检测浏览器代理
            browser_proxy = self.get_browser_proxy_settings()
            if browser_proxy:
                self.logger.info(f"检测到浏览器代理设置: {browser_proxy}")
                return browser_proxy
        
        return {}
    
    def set_manual_proxy(self, http_proxy: str = "", https_proxy: str = "", ftp_proxy: str = ""):
        """设置手动代理配置"""
        self.proxy_config["manual_proxy"] = {
            "http": http_proxy.strip(),
            "https": https_proxy.strip(),
            "ftp": ftp_proxy.strip()
        }
        self.proxy_config["use_manual"] = True
        self._save_proxy_config()
        self.logger.info("手动代理配置已更新")
    
    def enable_auto_detect(self):
        """启用自动检测代理"""
        self.proxy_config["auto_detect"] = True
        self.proxy_config["use_manual"] = False
        self._save_proxy_config()
        self.logger.info("已启用自动代理检测")
    
    def disable_auto_detect(self):
        """禁用自动检测代理"""
        self.proxy_config["auto_detect"] = False
        self._save_proxy_config()
        self.logger.info("已禁用自动代理检测")
    
    def test_proxy_connection(self, proxy_url: str) -> bool:
        """测试代理连接"""
        try:
            proxies = {"http": proxy_url, "https": proxy_url}
            response = requests.get("https://huggingface.co", 
                                  proxies=proxies, 
                                  timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"代理连接测试失败: {str(e)}")
            return False
    
    def apply_proxy_to_environment(self):
        """将代理设置应用到环境变量"""
        proxy_settings = self.get_current_proxy_settings()
        
        # 清除现有代理环境变量
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "http_proxy", "https_proxy", "ftp_proxy"]:
            if var in os.environ:
                del os.environ[var]
        
        # 设置新的代理环境变量
        if "http" in proxy_settings:
            os.environ["HTTP_PROXY"] = proxy_settings["http"]
            os.environ["http_proxy"] = proxy_settings["http"]
        
        if "https" in proxy_settings:
            os.environ["HTTPS_PROXY"] = proxy_settings["https"]
            os.environ["https_proxy"] = proxy_settings["https"]
        
        if "ftp" in proxy_settings:
            os.environ["FTP_PROXY"] = proxy_settings["ftp"]
            os.environ["ftp_proxy"] = proxy_settings["ftp"]
        
        if proxy_settings:
            self.logger.info(f"代理环境变量已设置: {proxy_settings}")
        else:
            self.logger.info("已清除代理环境变量")
    
    def get_proxy_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        current_proxy = self.get_current_proxy_settings()
        browser_proxy = self.get_browser_proxy_settings()
        
        return {
            "current_proxy": current_proxy,
            "browser_proxy": browser_proxy,
            "auto_detect": self.proxy_config.get("auto_detect", True),
            "use_manual": self.proxy_config.get("use_manual", False),
            "manual_proxy": self.proxy_config.get("manual_proxy", {})
        } 