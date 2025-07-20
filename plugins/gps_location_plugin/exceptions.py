"""
GPS位置查询插件异常定义

定义插件使用的各种异常类型。
"""


class GPSLocationError(Exception):
    """GPS位置查询插件基础异常"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (错误代码: {self.error_code}, 详情: {self.details})"
        return f"{self.message} (错误代码: {self.error_code})"


class GPSExtractionError(GPSLocationError):
    """GPS坐标提取异常"""
    
    def __init__(self, message: str, file_path: str = None, details: dict = None):
        error_code = "GPS_EXTRACTION_ERROR"
        if details is None:
            details = {}
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, error_code, details)


class InvalidCoordinateError(GPSExtractionError):
    """无效GPS坐标异常"""
    
    def __init__(self, latitude: float = None, longitude: float = None):
        details = {}
        if latitude is not None:
            details["latitude"] = latitude
        if longitude is not None:
            details["longitude"] = longitude
        
        message = f"无效的GPS坐标: 纬度={latitude}, 经度={longitude}"
        super().__init__(message, error_code="INVALID_COORDINATE", details=details)


class APIQueryError(GPSLocationError):
    """API查询异常"""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None, details: dict = None):
        error_code = "API_QUERY_ERROR"
        if details is None:
            details = {}
        if api_name:
            details["api_name"] = api_name
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, error_code, details)


class NetworkError(APIQueryError):
    """网络连接异常"""
    
    def __init__(self, message: str = "网络连接失败", api_name: str = None, details: dict = None):
        super().__init__(message, api_name, error_code="NETWORK_ERROR", details=details)


class APIKeyError(APIQueryError):
    """API密钥异常"""
    
    def __init__(self, message: str = "API密钥无效或缺失", api_name: str = None):
        super().__init__(message, api_name, error_code="API_KEY_ERROR")


class APIRateLimitError(APIQueryError):
    """API速率限制异常"""
    
    def __init__(self, message: str = "API调用频率超限", api_name: str = None, retry_after: int = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, api_name, error_code="API_RATE_LIMIT", details=details)


class APIResponseError(APIQueryError):
    """API响应解析异常"""
    
    def __init__(self, message: str = "API响应格式错误", api_name: str = None, response_data: str = None):
        details = {}
        if response_data:
            details["response_data"] = response_data[:500]  # 限制长度
        super().__init__(message, api_name, error_code="API_RESPONSE_ERROR", details=details)


class CacheError(GPSLocationError):
    """缓存操作异常"""
    
    def __init__(self, message: str, operation: str = None, details: dict = None):
        error_code = "CACHE_ERROR"
        if details is None:
            details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code, details)


class CacheDatabaseError(CacheError):
    """缓存数据库异常"""
    
    def __init__(self, message: str = "缓存数据库操作失败", db_path: str = None, sql_error: str = None):
        details = {}
        if db_path:
            details["db_path"] = db_path
        if sql_error:
            details["sql_error"] = sql_error
        super().__init__(message, "database", details)


class ConfigurationError(GPSLocationError):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None):
        error_code = "CONFIGURATION_ERROR"
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value:
            details["config_value"] = config_value
        super().__init__(message, error_code, details)


class PluginInitializationError(GPSLocationError):
    """插件初始化异常"""
    
    def __init__(self, message: str = "插件初始化失败", component: str = None, details: dict = None):
        error_code = "PLUGIN_INIT_ERROR"
        if details is None:
            details = {}
        if component:
            details["component"] = component
        super().__init__(message, error_code, details)


class PluginNotAvailableError(GPSLocationError):
    """插件不可用异常"""
    
    def __init__(self, message: str = "插件当前不可用", reason: str = None):
        error_code = "PLUGIN_NOT_AVAILABLE"
        details = {}
        if reason:
            details["reason"] = reason
        super().__init__(message, error_code, details)


# 错误代码映射
ERROR_MESSAGES = {
    "UNKNOWN_ERROR": "未知错误",
    "GPS_EXTRACTION_ERROR": "GPS坐标提取失败",
    "INVALID_COORDINATE": "GPS坐标无效",
    "API_QUERY_ERROR": "API查询失败",
    "NETWORK_ERROR": "网络连接失败",
    "API_KEY_ERROR": "API密钥错误",
    "API_RATE_LIMIT": "API调用频率超限",
    "API_RESPONSE_ERROR": "API响应解析失败",
    "CACHE_ERROR": "缓存操作失败",
    "CONFIGURATION_ERROR": "配置错误",
    "PLUGIN_INIT_ERROR": "插件初始化失败",
    "PLUGIN_NOT_AVAILABLE": "插件不可用"
}


def get_error_message(error_code: str) -> str:
    """获取错误代码对应的中文消息"""
    return ERROR_MESSAGES.get(error_code, "未知错误")


def format_error_for_user(error: GPSLocationError) -> str:
    """格式化错误信息供用户查看"""
    base_message = get_error_message(error.error_code)
    
    if error.message != base_message:
        return f"{base_message}: {error.message}"
    
    return base_message