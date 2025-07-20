"""
地理位置API查询模块

提供多种地理位置API服务的统一接口。
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import structlog

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from .models import GPSCoordinate, LocationInfo
    from .exceptions import (
        APIQueryError, NetworkError, APIKeyError, 
        APIRateLimitError, APIResponseError
    )
except ImportError:
    from models import GPSCoordinate, LocationInfo
    from exceptions import (
        APIQueryError, NetworkError, APIKeyError, 
        APIRateLimitError, APIResponseError
    )


class BaseLocationAPI(ABC):
    """位置查询API基类
    
    定义所有位置查询API的统一接口。
    """
    
    def __init__(self, api_key: str = None, timeout: int = 10):
        """初始化API客户端
        
        Args:
            api_key: API密钥（如果需要）
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.timeout = timeout
        self.logger = structlog.get_logger(f"gps_location_plugin.{self.get_api_name().lower()}")
        self.last_request_time = 0
        
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requests library not available")
    
    @abstractmethod
    def get_api_name(self) -> str:
        """获取API服务名称"""
        pass
    
    @abstractmethod
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息
        
        Args:
            coordinate: GPS坐标
            
        Returns:
            位置信息，查询失败返回None
            
        Raises:
            APIQueryError: API查询相关异常
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查API是否可用"""
        pass
    
    def get_rate_limit(self) -> Optional[int]:
        """获取速率限制（每秒请求数）
        
        Returns:
            每秒最大请求数，None表示无限制
        """
        return None
    
    def get_required_config(self) -> List[str]:
        """获取必需的配置项
        
        Returns:
            必需配置项的键名列表
        """
        return []
    
    def _enforce_rate_limit(self):
        """执行速率限制"""
        rate_limit = self.get_rate_limit()
        if rate_limit is None:
            return
        
        min_interval = 1.0 / rate_limit
        elapsed = time.time() - self.last_request_time
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            self.logger.debug("Rate limiting", sleep_time=sleep_time)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict[str, Any] = None, 
                     headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发起HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            headers: 请求头
            
        Returns:
            响应JSON数据
            
        Raises:
            NetworkError: 网络错误
            APIResponseError: 响应解析错误
        """
        if not REQUESTS_AVAILABLE:
            raise NetworkError("requests库不可用", self.get_api_name())
        
        try:
            self._enforce_rate_limit()
            
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            
            # 检查HTTP状态码
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise APIRateLimitError(
                    "API调用频率超限", 
                    self.get_api_name(),
                    int(retry_after) if retry_after else None
                )
            elif response.status_code == 401:
                raise APIKeyError("API密钥无效", self.get_api_name())
            elif response.status_code != 200:
                raise APIQueryError(
                    f"API请求失败: HTTP {response.status_code}",
                    self.get_api_name(),
                    response.status_code
                )
            
            # 解析JSON响应
            try:
                return response.json()
            except json.JSONDecodeError as e:
                raise APIResponseError(
                    f"响应JSON解析失败: {str(e)}",
                    self.get_api_name(),
                    response.text[:500]
                )
                
        except requests.exceptions.Timeout:
            raise NetworkError(f"请求超时（{self.timeout}秒）", self.get_api_name())
        except requests.exceptions.ConnectionError:
            raise NetworkError("网络连接失败", self.get_api_name())
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"网络请求异常: {str(e)}", self.get_api_name())


class NominatimAPI(BaseLocationAPI):
    """OpenStreetMap Nominatim API实现
    
    免费的地理编码服务，无需API密钥。
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        super().__init__(timeout=timeout)
        self.base_url = "https://nominatim.openstreetmap.org/reverse"
        self.user_agent = user_agent or "PicMan GPS Location Plugin/1.0.0"
    
    def get_api_name(self) -> str:
        return "Nominatim"
    
    def get_rate_limit(self) -> Optional[int]:
        return 1  # 每秒1次请求
    
    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息"""
        try:
            params = {
                'lat': coordinate.latitude,
                'lon': coordinate.longitude,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'zh-CN,zh,en'
            }
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            self.logger.debug("Querying Nominatim", 
                            lat=coordinate.latitude, lon=coordinate.longitude)
            
            response_data = self._make_request(self.base_url, params, headers)
            
            if not response_data:
                self.logger.warning("Empty response from Nominatim")
                return None
            
            return self._parse_nominatim_response(response_data)
            
        except Exception as e:
            if isinstance(e, (APIQueryError, NetworkError)):
                raise
            raise APIQueryError(f"Nominatim查询失败: {str(e)}", self.get_api_name())
    
    def _parse_nominatim_response(self, response: Dict[str, Any]) -> LocationInfo:
        """解析Nominatim响应数据"""
        try:
            address = response.get('address', {})
            
            # 提取地址组件
            country = address.get('country', '')
            state = (address.get('state') or 
                    address.get('province') or 
                    address.get('region', ''))
            city = (address.get('city') or 
                   address.get('town') or 
                   address.get('village') or 
                   address.get('municipality', ''))
            district = (address.get('suburb') or 
                       address.get('district') or 
                       address.get('neighbourhood', ''))
            street = (address.get('road') or 
                     address.get('street', ''))
            
            # 完整地址
            display_name = response.get('display_name', '')
            
            location_info = LocationInfo(
                country=country,
                state_province=state,
                city=city,
                district=district,
                street=street,
                full_address=display_name,
                formatted_address=display_name,
                source_api=self.get_api_name()
            )
            
            self.logger.debug("Nominatim response parsed", 
                            location=location_info.to_display_string("short"))
            return location_info
            
        except Exception as e:
            raise APIResponseError(
                f"Nominatim响应解析失败: {str(e)}",
                self.get_api_name(),
                str(response)[:500]
            )


class GoogleMapsAPI(BaseLocationAPI):
    """Google Maps Geocoding API实现
    
    需要API密钥，提供高质量的地理编码服务。
    """
    
    def __init__(self, api_key: str, timeout: int = 10):
        super().__init__(api_key=api_key, timeout=timeout)
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def get_api_name(self) -> str:
        return "Google Maps"
    
    def get_required_config(self) -> List[str]:
        return ['api_key']
    
    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE and bool(self.api_key)
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息"""
        if not self.api_key:
            raise APIKeyError("Google Maps API密钥未配置", self.get_api_name())
        
        try:
            params = {
                'latlng': f"{coordinate.latitude},{coordinate.longitude}",
                'key': self.api_key,
                'language': 'zh-CN'
            }
            
            self.logger.debug("Querying Google Maps", 
                            lat=coordinate.latitude, lon=coordinate.longitude)
            
            response_data = self._make_request(self.base_url, params)
            
            if response_data.get('status') != 'OK':
                error_message = response_data.get('error_message', 
                                                response_data.get('status', 'Unknown error'))
                raise APIQueryError(f"Google Maps API错误: {error_message}", self.get_api_name())
            
            results = response_data.get('results', [])
            if not results:
                self.logger.warning("No results from Google Maps")
                return None
            
            return self._parse_google_response(results[0])
            
        except Exception as e:
            if isinstance(e, (APIQueryError, NetworkError, APIKeyError)):
                raise
            raise APIQueryError(f"Google Maps查询失败: {str(e)}", self.get_api_name())
    
    def _parse_google_response(self, result: Dict[str, Any]) -> LocationInfo:
        """解析Google Maps响应数据"""
        try:
            components = result.get('address_components', [])
            formatted_address = result.get('formatted_address', '')
            
            # 解析地址组件
            country = ''
            state = ''
            city = ''
            district = ''
            street = ''
            
            for component in components:
                types = component.get('types', [])
                name = component.get('long_name', '')
                
                if 'country' in types:
                    country = name
                elif 'administrative_area_level_1' in types:
                    state = name
                elif any(t in types for t in ['locality', 'administrative_area_level_2']):
                    city = name
                elif any(t in types for t in ['sublocality', 'neighborhood']):
                    district = name
                elif 'route' in types:
                    street = name
            
            location_info = LocationInfo(
                country=country,
                state_province=state,
                city=city,
                district=district,
                street=street,
                full_address=formatted_address,
                formatted_address=formatted_address,
                source_api=self.get_api_name()
            )
            
            self.logger.debug("Google Maps response parsed", 
                            location=location_info.to_display_string("short"))
            return location_info
            
        except Exception as e:
            raise APIResponseError(
                f"Google Maps响应解析失败: {str(e)}",
                self.get_api_name(),
                str(result)[:500]
            )


class BaiduMapsAPI(BaseLocationAPI):
    """百度地图API实现
    
    需要API密钥，对中国地区支持较好。
    """
    
    def __init__(self, api_key: str, timeout: int = 10):
        super().__init__(api_key=api_key, timeout=timeout)
        self.base_url = "https://api.map.baidu.com/reverse_geocoding/v3/"
    
    def get_api_name(self) -> str:
        return "百度地图"
    
    def get_required_config(self) -> List[str]:
        return ['api_key']
    
    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE and bool(self.api_key)
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息"""
        if not self.api_key:
            raise APIKeyError("百度地图API密钥未配置", self.get_api_name())
        
        try:
            params = {
                'ak': self.api_key,
                'location': f"{coordinate.latitude},{coordinate.longitude}",
                'output': 'json',
                'coordtype': 'wgs84ll'  # WGS84坐标系
            }
            
            self.logger.debug("Querying Baidu Maps", 
                            lat=coordinate.latitude, lon=coordinate.longitude)
            
            response_data = self._make_request(self.base_url, params)
            
            if response_data.get('status') != 0:
                error_message = response_data.get('message', f"错误代码: {response_data.get('status')}")
                raise APIQueryError(f"百度地图API错误: {error_message}", self.get_api_name())
            
            result = response_data.get('result')
            if not result:
                self.logger.warning("No result from Baidu Maps")
                return None
            
            return self._parse_baidu_response(result)
            
        except Exception as e:
            if isinstance(e, (APIQueryError, NetworkError, APIKeyError)):
                raise
            raise APIQueryError(f"百度地图查询失败: {str(e)}", self.get_api_name())
    
    def _parse_baidu_response(self, result: Dict[str, Any]) -> LocationInfo:
        """解析百度地图响应数据"""
        try:
            addressComponent = result.get('addressComponent', {})
            formatted_address = result.get('formatted_address', '')
            
            location_info = LocationInfo(
                country=addressComponent.get('country', ''),
                state_province=addressComponent.get('province', ''),
                city=addressComponent.get('city', ''),
                district=addressComponent.get('district', ''),
                street=addressComponent.get('street', ''),
                full_address=formatted_address,
                formatted_address=formatted_address,
                source_api=self.get_api_name()
            )
            
            self.logger.debug("Baidu Maps response parsed", 
                            location=location_info.to_display_string("short"))
            return location_info
            
        except Exception as e:
            raise APIResponseError(
                f"百度地图响应解析失败: {str(e)}",
                self.get_api_name(),
                str(result)[:500]
            )


class AmapAPI(BaseLocationAPI):
    """高德地图API实现
    
    需要API密钥，对中国地区支持较好。
    """
    
    def __init__(self, api_key: str, timeout: int = 10):
        super().__init__(api_key=api_key, timeout=timeout)
        self.base_url = "https://restapi.amap.com/v3/geocode/regeo"
    
    def get_api_name(self) -> str:
        return "高德地图"
    
    def get_required_config(self) -> List[str]:
        return ['api_key']
    
    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE and bool(self.api_key)
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息"""
        if not self.api_key:
            raise APIKeyError("高德地图API密钥未配置", self.get_api_name())
        
        try:
            params = {
                'key': self.api_key,
                'location': f"{coordinate.longitude},{coordinate.latitude}",  # 注意：高德是经度在前
                'output': 'json',
                'extensions': 'all'
            }
            
            self.logger.debug("Querying Amap", 
                            lat=coordinate.latitude, lon=coordinate.longitude)
            
            response_data = self._make_request(self.base_url, params)
            
            if response_data.get('status') != '1':
                error_message = response_data.get('info', f"错误代码: {response_data.get('infocode')}")
                raise APIQueryError(f"高德地图API错误: {error_message}", self.get_api_name())
            
            regeocode = response_data.get('regeocode')
            if not regeocode:
                self.logger.warning("No regeocode from Amap")
                return None
            
            return self._parse_amap_response(regeocode)
            
        except Exception as e:
            if isinstance(e, (APIQueryError, NetworkError, APIKeyError)):
                raise
            raise APIQueryError(f"高德地图查询失败: {str(e)}", self.get_api_name())
    
    def _parse_amap_response(self, regeocode: Dict[str, Any]) -> LocationInfo:
        """解析高德地图响应数据"""
        try:
            addressComponent = regeocode.get('addressComponent', {})
            formatted_address = regeocode.get('formatted_address', '')
            
            location_info = LocationInfo(
                country=addressComponent.get('country', ''),
                state_province=addressComponent.get('province', ''),
                city=addressComponent.get('city', ''),
                district=addressComponent.get('district', ''),
                street=addressComponent.get('streetNumber', {}).get('street', ''),
                full_address=formatted_address,
                formatted_address=formatted_address,
                source_api=self.get_api_name()
            )
            
            self.logger.debug("Amap response parsed", 
                            location=location_info.to_display_string("short"))
            return location_info
            
        except Exception as e:
            raise APIResponseError(
                f"高德地图响应解析失败: {str(e)}",
                self.get_api_name(),
                str(regeocode)[:500]
            )


class LocationAPIClient:
    """位置查询API客户端管理器
    
    管理多个API服务，提供统一的查询接口和自动切换功能。
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化API客户端管理器
        
        Args:
            config: 配置字典
        """
        self.logger = structlog.get_logger("gps_location_plugin.api_client")
        self.config = config or {}
        
        # 初始化API服务
        self.apis: Dict[str, BaseLocationAPI] = {}
        self._init_apis()
        
        # 设置优先级
        self.priority = self.config.get('priority', ['nominatim', 'google', 'baidu', 'amap'])
        
        self.logger.info("Location API client initialized", 
                        available_apis=list(self.apis.keys()),
                        priority=self.priority)
    
    def _init_apis(self):
        """初始化API服务实例"""
        timeout = self.config.get('timeout', 10)
        user_agent = self.config.get('user_agent', 'PicMan GPS Location Plugin/1.0.0')
        
        # Nominatim (免费，无需密钥)
        self.apis['nominatim'] = NominatimAPI(timeout=timeout, user_agent=user_agent)
        
        # Google Maps (需要密钥)
        google_key = self.config.get('google_api_key')
        if google_key:
            self.apis['google'] = GoogleMapsAPI(google_key, timeout=timeout)
        
        # 百度地图 (需要密钥)
        baidu_key = self.config.get('baidu_api_key')
        if baidu_key:
            self.apis['baidu'] = BaiduMapsAPI(baidu_key, timeout=timeout)
        
        # 高德地图 (需要密钥)
        amap_key = self.config.get('amap_api_key')
        if amap_key:
            self.apis['amap'] = AmapAPI(amap_key, timeout=timeout)
    
    def query_location(self, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """查询位置信息
        
        按照优先级顺序尝试各个API服务，直到成功或全部失败。
        
        Args:
            coordinate: GPS坐标
            
        Returns:
            位置信息，如果所有API都失败则返回None
        """
        last_error = None
        
        for api_name in self.priority:
            api = self.apis.get(api_name)
            if not api or not api.is_available():
                self.logger.debug("API not available", api=api_name)
                continue
            
            try:
                result = self._try_api(api, coordinate)
                if result and not result.is_empty():
                    self.logger.info("Location query successful", 
                                   api=api_name, 
                                   location=result.to_display_string("short"))
                    return result
                else:
                    self.logger.debug("API returned empty result", api=api_name)
                    
            except Exception as e:
                last_error = e
                self.logger.warning("API query failed", 
                                  api=api_name, error=str(e))
                continue
        
        # 所有API都失败了
        if last_error:
            self.logger.error("All APIs failed", last_error=str(last_error))
        else:
            self.logger.error("No available APIs")
        
        return None
    
    def _try_api(self, api: BaseLocationAPI, coordinate: GPSCoordinate) -> Optional[LocationInfo]:
        """尝试使用指定API查询位置
        
        Args:
            api: API实例
            coordinate: GPS坐标
            
        Returns:
            位置信息
        """
        retry_count = self.config.get('retry_count', 3)
        
        for attempt in range(retry_count):
            try:
                return api.query_location(coordinate)
            except APIRateLimitError as e:
                # 速率限制错误，等待后重试
                retry_after = e.details.get('retry_after', 60)
                if attempt < retry_count - 1:
                    self.logger.info("Rate limited, retrying", 
                                   api=api.get_api_name(),
                                   retry_after=retry_after,
                                   attempt=attempt + 1)
                    time.sleep(min(retry_after, 60))  # 最多等待60秒
                    continue
                raise
            except (NetworkError, APIResponseError) as e:
                # 网络或响应错误，短暂等待后重试
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.info("Retrying after error", 
                                   api=api.get_api_name(),
                                   error=str(e),
                                   wait_time=wait_time,
                                   attempt=attempt + 1)
                    time.sleep(wait_time)
                    continue
                raise
            except APIKeyError:
                # API密钥错误，不重试
                raise
    
    def set_api_priority(self, priority_list: List[str]):
        """设置API优先级
        
        Args:
            priority_list: API名称的优先级列表
        """
        # 验证API名称
        valid_apis = []
        for api_name in priority_list:
            if api_name in self.apis:
                valid_apis.append(api_name)
            else:
                self.logger.warning("Unknown API in priority list", api=api_name)
        
        self.priority = valid_apis
        self.logger.info("API priority updated", priority=self.priority)
    
    def get_available_apis(self) -> List[str]:
        """获取可用的API列表
        
        Returns:
            可用API名称列表
        """
        return [name for name, api in self.apis.items() if api.is_available()]
    
    def get_api_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有API的状态信息
        
        Returns:
            API状态信息字典
        """
        status = {}
        for name, api in self.apis.items():
            status[name] = {
                'available': api.is_available(),
                'rate_limit': api.get_rate_limit(),
                'required_config': api.get_required_config()
            }
        return status