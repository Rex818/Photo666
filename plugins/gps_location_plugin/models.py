"""
GPS位置查询插件数据模型

定义插件使用的核心数据结构。
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import math


@dataclass
class GPSCoordinate:
    """GPS坐标数据类"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    
    def to_decimal_degrees(self) -> Tuple[float, float]:
        """转换为十进制度数格式"""
        return (self.latitude, self.longitude)
    
    def to_dms_string(self) -> str:
        """转换为度分秒字符串格式"""
        def decimal_to_dms(decimal_degrees: float, is_latitude: bool = True) -> str:
            """将十进制度数转换为度分秒格式"""
            abs_degrees = abs(decimal_degrees)
            degrees = int(abs_degrees)
            minutes_float = (abs_degrees - degrees) * 60
            minutes = int(minutes_float)
            seconds = (minutes_float - minutes) * 60
            
            if is_latitude:
                direction = 'N' if decimal_degrees >= 0 else 'S'
            else:
                direction = 'E' if decimal_degrees >= 0 else 'W'
            
            return f"{degrees}°{minutes}'{seconds:.1f}\"{direction}"
        
        lat_dms = decimal_to_dms(self.latitude, True)
        lon_dms = decimal_to_dms(self.longitude, False)
        
        return f"{lat_dms}, {lon_dms}"
    
    def distance_to(self, other: 'GPSCoordinate') -> float:
        """计算到另一个坐标的距离（米）
        
        使用Haversine公式计算球面距离
        """
        # 转换为弧度
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        # Haversine公式
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # 地球半径（米）
        earth_radius = 6371000
        
        return earth_radius * c
    
    def is_valid(self) -> bool:
        """验证GPS坐标是否有效"""
        return (-90 <= self.latitude <= 90 and 
                -180 <= self.longitude <= 180)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"GPS({self.latitude:.6f}, {self.longitude:.6f})"


@dataclass
class LocationInfo:
    """位置信息数据类"""
    country: str = ""
    state_province: str = ""
    city: str = ""
    district: str = ""
    street: str = ""
    full_address: str = ""
    formatted_address: str = ""
    source_api: str = ""
    query_time: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.query_time is None:
            self.query_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "country": self.country,
            "state_province": self.state_province,
            "city": self.city,
            "district": self.district,
            "street": self.street,
            "full_address": self.full_address,
            "formatted_address": self.formatted_address,
            "source_api": self.source_api,
            "query_time": self.query_time.isoformat() if self.query_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocationInfo':
        """从字典创建LocationInfo对象"""
        query_time = None
        if data.get("query_time"):
            try:
                query_time = datetime.fromisoformat(data["query_time"])
            except (ValueError, TypeError):
                query_time = datetime.now()
        
        return cls(
            country=data.get("country", ""),
            state_province=data.get("state_province", ""),
            city=data.get("city", ""),
            district=data.get("district", ""),
            street=data.get("street", ""),
            full_address=data.get("full_address", ""),
            formatted_address=data.get("formatted_address", ""),
            source_api=data.get("source_api", ""),
            query_time=query_time
        )
    
    def to_display_string(self, format_type: str = "full") -> str:
        """转换为显示字符串
        
        Args:
            format_type: 格式类型 ("full", "short", "city_only")
        """
        if format_type == "city_only":
            return self.city or self.district or "未知位置"
        elif format_type == "short":
            parts = [self.city, self.state_province, self.country]
            return ", ".join(filter(None, parts)) or "未知位置"
        else:  # full
            if self.formatted_address:
                return self.formatted_address
            elif self.full_address:
                return self.full_address
            else:
                parts = [self.street, self.district, self.city, 
                        self.state_province, self.country]
                return ", ".join(filter(None, parts)) or "未知位置"
    
    def is_empty(self) -> bool:
        """检查位置信息是否为空"""
        return not any([
            self.country, self.state_province, self.city,
            self.district, self.street, self.full_address,
            self.formatted_address
        ])
    
    def __str__(self) -> str:
        """字符串表示"""
        return self.to_display_string("short")


@dataclass
class CacheEntry:
    """缓存条目数据类"""
    coordinate: GPSCoordinate
    location: LocationInfo
    created_time: datetime
    last_used_time: datetime
    hit_count: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.created_time:
            self.created_time = datetime.now()
        if not self.last_used_time:
            self.last_used_time = datetime.now()
    
    def is_expired(self, max_age_days: int = 30) -> bool:
        """检查缓存是否过期"""
        age = datetime.now() - self.created_time
        return age.days > max_age_days
    
    def update_usage(self):
        """更新使用统计"""
        self.last_used_time = datetime.now()
        self.hit_count += 1