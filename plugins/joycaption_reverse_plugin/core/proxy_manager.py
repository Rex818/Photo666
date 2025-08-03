"""
JoyCaption插件代理管理器
负责处理网络代理配置
"""

import os
import requests
from typing import Dict, Optional, Any
from pathlib import Path

from ..utils.logger import setup_logger


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.logger = setup_logger("proxy_manager")
        self.proxy_config = self._load_proxy_config()
        self.logger.info("代理配置加载成功")
    
    def _load_proxy_config(self) -> Dict[str, str]:
        """加载代理配置"""
        try:
            # 检查环境变量
            http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
            
            if http_proxy or https_proxy:
                proxy_config = {}
                if http_proxy:
                    proxy_config['http'] = http_proxy
                if https_proxy:
                    proxy_config['https'] = https_proxy
                
                self.logger.info(f"从环境变量加载代理配置: {proxy_config}")
                return proxy_config
            
            # 检查浏览器代理设置
            browser_proxy = self._detect_browser_proxy()
            if browser_proxy:
                self.logger.info(f"检测到浏览器代理设置: {browser_proxy}")
                return browser_proxy
            
            # 检查系统代理设置
            system_proxy = self._detect_system_proxy()
            if system_proxy:
                self.logger.info(f"检测到系统代理设置: {system_proxy}")
                return system_proxy
            
            self.logger.info("未检测到代理设置")
            return {}
            
        except Exception as e:
            self.logger.error(f"加载代理配置失败: {e}")
            return {}
    
    def _detect_browser_proxy(self) -> Optional[Dict[str, str]]:
        """检测浏览器代理设置"""
        try:
            # 常见的代理端口
            common_ports = [7890, 7891, 1080, 8080, 3128, 8888]
            
            for port in common_ports:
                proxy_url = f"http://127.0.0.1:{port}"
                try:
                    # 测试代理连接
                    response = requests.get(
                        "http://www.google.com", 
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=5
                    )
                    if response.status_code == 200:
                        return {"http": proxy_url, "https": proxy_url}
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"检测浏览器代理失败: {e}")
            return None
    
    def _detect_system_proxy(self) -> Optional[Dict[str, str]]:
        """检测系统代理设置"""
        try:
            # Windows系统代理检测
            import winreg
            
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                    proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    if proxy_enable:
                        proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                        if proxy_server:
                            return {"http": f"http://{proxy_server}", "https": f"http://{proxy_server}"}
            except:
                pass
            
            return None
            
        except Exception as e:
            self.logger.debug(f"检测系统代理失败: {e}")
            return None
    
    def get_proxy_config(self) -> Dict[str, str]:
        """获取代理配置"""
        return self.proxy_config
    
    def set_proxy_config(self, proxy_config: Dict[str, str]):
        """设置代理配置"""
        self.proxy_config = proxy_config
        self.logger.info(f"代理配置已更新: {proxy_config}")
    
    def set_proxy_environment(self):
        """设置代理环境变量"""
        try:
            if self.proxy_config:
                for protocol, proxy_url in self.proxy_config.items():
                    os.environ[f"{protocol.upper()}_PROXY"] = proxy_url
                self.logger.info(f"代理环境变量已设置: {self.proxy_config}")
            else:
                # 清除代理环境变量
                for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                    if var in os.environ:
                        del os.environ[var]
                self.logger.info("代理环境变量已清除")
                
        except Exception as e:
            self.logger.error(f"设置代理环境变量失败: {e}")
    
    def test_proxy_connection(self, test_url: str = "https://huggingface.co") -> bool:
        """测试代理连接"""
        try:
            if not self.proxy_config:
                self.logger.info("无代理设置，使用直接连接")
                return True
            
            response = requests.get(
                test_url,
                proxies=self.proxy_config,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"代理连接测试成功: {test_url}")
                return True
            else:
                self.logger.warning(f"代理连接测试失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"代理连接测试失败: {e}")
            return False
    
    def get_proxy_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "proxy_config": self.proxy_config,
            "has_proxy": bool(self.proxy_config),
            "proxy_count": len(self.proxy_config)
        }
    
    def clear_proxy(self):
        """清除代理设置"""
        self.proxy_config = {}
        self.set_proxy_environment()
        self.logger.info("代理设置已清除")
    
    def is_proxy_enabled(self) -> bool:
        """检查是否启用代理"""
        return bool(self.proxy_config) 