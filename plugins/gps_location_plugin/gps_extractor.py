"""
GPS坐标提取模块

从照片EXIF数据中提取GPS坐标信息，并转换为标准格式。
"""

import os
import json
from typing import Optional, Dict, Any, Union, List, Tuple
from pathlib import Path
import logging

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from .models import GPSCoordinate
    from .exceptions import GPSExtractionError, InvalidCoordinateError
except ImportError:
    from models import GPSCoordinate
    from exceptions import GPSExtractionError, InvalidCoordinateError


class GPSExtractor:
    """GPS坐标提取器
    
    负责从照片文件或EXIF数据中提取GPS坐标信息，
    并转换为标准的十进制度数格式。
    """
    
    def __init__(self):
        self.logger = logging.getLogger("gps_location_plugin.gps_extractor")
        
        if not PIL_AVAILABLE:
            self.logger.warning("PIL/Pillow not available, GPS extraction may be limited")
    
    def extract_gps_from_file(self, image_path: str) -> Optional[GPSCoordinate]:
        """从图片文件中提取GPS坐标
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            GPSCoordinate对象，如果没有GPS信息则返回None
            
        Raises:
            GPSExtractionError: GPS提取失败时抛出
        """
        try:
            if not os.path.exists(image_path):
                raise GPSExtractionError(f"文件不存在: {image_path}", image_path)
            
            if not PIL_AVAILABLE:
                self.logger.warning("PIL not available, cannot extract GPS from file")
                return None
            
            # 使用PIL读取EXIF数据
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                
                if not exif_data:
                    self.logger.debug("No EXIF data found: %s", image_path)
                    return None
                
                # 转换EXIF数据为可读格式
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                
                # 提取GPS信息
                gps_info = exif_dict.get('GPSInfo')
                if not gps_info:
                    self.logger.debug("No GPS info found in EXIF: %s", image_path)
                    return None
                
                # 转换GPS信息为可读格式
                gps_data = {}
                for gps_tag_id, value in gps_info.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_data[gps_tag] = value
                
                return self.extract_gps_from_exif(gps_data)
                
        except Exception as e:
            if isinstance(e, GPSExtractionError):
                raise
            raise GPSExtractionError(f"从文件提取GPS失败: {str(e)}", image_path)
    
    def extract_gps_from_exif(self, exif_data: Dict[str, Any]) -> Optional[GPSCoordinate]:
        """从EXIF数据字典中提取GPS坐标
        
        Args:
            exif_data: EXIF数据字典或GPS数据字典
            
        Returns:
            GPSCoordinate对象，如果没有GPS信息则返回None
            
        Raises:
            GPSExtractionError: GPS提取失败时抛出
        """
        try:
            # 处理字符串格式的EXIF数据（从数据库读取的情况）
            if isinstance(exif_data, str):
                try:
                    exif_data = json.loads(exif_data)
                except json.JSONDecodeError:
                    self.logger.warning("Invalid EXIF JSON data")
                    return None
            
            if not isinstance(exif_data, dict):
                return None
            
            # 尝试直接从GPS字段获取
            gps_lat = exif_data.get('GPSLatitude')
            gps_lon = exif_data.get('GPSLongitude')
            gps_lat_ref = exif_data.get('GPSLatitudeRef', 'N')
            gps_lon_ref = exif_data.get('GPSLongitudeRef', 'E')
            gps_alt = exif_data.get('GPSAltitude')
            
            # 如果没有直接的GPS字段，尝试从GPSInfo中获取
            if not gps_lat and 'GPSInfo' in exif_data:
                gps_info = exif_data['GPSInfo']
                if isinstance(gps_info, dict):
                    gps_lat = gps_info.get('GPSLatitude')
                    gps_lon = gps_info.get('GPSLongitude')
                    gps_lat_ref = gps_info.get('GPSLatitudeRef', 'N')
                    gps_lon_ref = gps_info.get('GPSLongitudeRef', 'E')
                    gps_alt = gps_info.get('GPSAltitude')
            
            if not gps_lat or not gps_lon:
                self.logger.debug("No GPS coordinates found in EXIF data")
                return None
            
            # 转换坐标为十进制度数
            try:
                lat_decimal = self._convert_coordinate_to_decimal(gps_lat, gps_lat_ref)
                lon_decimal = self._convert_coordinate_to_decimal(gps_lon, gps_lon_ref)
                
                # 转换海拔（如果有）
                alt_decimal = None
                if gps_alt:
                    alt_decimal = self._convert_altitude_to_decimal(gps_alt)
                
                # 创建GPS坐标对象
                coordinate = GPSCoordinate(
                    latitude=lat_decimal,
                    longitude=lon_decimal,
                    altitude=alt_decimal
                )
                
                # 验证坐标有效性
                if not coordinate.is_valid():
                    raise InvalidCoordinateError(lat_decimal, lon_decimal)
                
                self.logger.debug("GPS coordinates extracted successfully: latitude=%s, longitude=%s", lat_decimal, lon_decimal)
                return coordinate
                
            except Exception as e:
                raise GPSExtractionError(f"GPS坐标转换失败: {str(e)}")
                
        except Exception as e:
            if isinstance(e, (GPSExtractionError, InvalidCoordinateError)):
                raise
            raise GPSExtractionError(f"从EXIF提取GPS失败: {str(e)}")
    
    def _convert_coordinate_to_decimal(self, coord: Any, ref: str) -> float:
        """将GPS坐标转换为十进制度数格式
        
        Args:
            coord: GPS坐标数据（可能是度分秒格式的列表或元组）
            ref: 方向参考（N/S/E/W）
            
        Returns:
            十进制度数格式的坐标
        """
        try:
            # 如果已经是数字，直接返回
            if isinstance(coord, (int, float)):
                decimal = float(coord)
            elif isinstance(coord, (list, tuple)) and len(coord) >= 3:
                # 度分秒格式：[度, 分, 秒]
                degrees, minutes, seconds = coord[:3]
                
                # 处理分数格式（如 "39/1"）
                degrees = self._parse_rational(degrees)
                minutes = self._parse_rational(minutes)
                seconds = self._parse_rational(seconds)
                
                # 转换为十进制度数
                decimal = degrees + minutes / 60.0 + seconds / 3600.0
            elif isinstance(coord, (list, tuple)) and len(coord) == 2:
                # 度分格式：[度, 分]
                degrees, minutes = coord
                degrees = self._parse_rational(degrees)
                minutes = self._parse_rational(minutes)
                decimal = degrees + minutes / 60.0
            elif isinstance(coord, (list, tuple)) and len(coord) == 1:
                # 只有度
                degrees = self._parse_rational(coord[0])
                decimal = degrees
            else:
                # 尝试直接转换
                decimal = float(coord)
            
            # 根据方向参考调整符号
            if ref in ['S', 'W']:
                decimal = -decimal
            
            return decimal
            
        except Exception as e:
            raise GPSExtractionError(f"坐标转换失败: {coord}, ref: {ref}, error: {str(e)}")
    
    def _parse_rational(self, value: Any) -> float:
        """解析有理数格式的值
        
        Args:
            value: 可能是分数字符串（如"39/1"）或数字
            
        Returns:
            浮点数值
        """
        if isinstance(value, str) and '/' in value:
            try:
                numerator, denominator = value.split('/')
                return float(numerator) / float(denominator)
            except (ValueError, ZeroDivisionError):
                return float(value.split('/')[0])  # 如果分母为0，只取分子
        elif isinstance(value, (int, float)):
            return float(value)
        else:
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
    
    def _convert_altitude_to_decimal(self, altitude: Any) -> Optional[float]:
        """转换海拔数据为十进制格式
        
        Args:
            altitude: 海拔数据
            
        Returns:
            海拔值（米），如果转换失败返回None
        """
        try:
            if isinstance(altitude, str) and '/' in altitude:
                numerator, denominator = altitude.split('/')
                return float(numerator) / float(denominator)
            elif isinstance(altitude, (int, float)):
                return float(altitude)
            else:
                return float(altitude)
        except (ValueError, TypeError, ZeroDivisionError):
            self.logger.warning("Failed to convert altitude: altitude=%s", altitude)
            return None
    
    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """验证GPS坐标是否有效
        
        Args:
            lat: 纬度
            lon: 经度
            
        Returns:
            坐标是否有效
        """
        return (-90 <= lat <= 90) and (-180 <= lon <= 180)
    
    def extract_gps_from_picman_data(self, photo_data: Dict[str, Any]) -> Optional[GPSCoordinate]:
        """从PicMan照片数据中提取GPS坐标
        
        这是一个便利方法，用于从PicMan的照片数据结构中提取GPS信息。
        
        Args:
            photo_data: PicMan照片数据字典
            
        Returns:
            GPSCoordinate对象，如果没有GPS信息则返回None
        """
        try:
            # 首先尝试从文件路径提取
            filepath = photo_data.get('filepath')
            if filepath and os.path.exists(filepath):
                coordinate = self.extract_gps_from_file(filepath)
                if coordinate:
                    return coordinate
            
            # 如果文件提取失败，尝试从EXIF数据提取
            exif_data = photo_data.get('exif_data')
            if exif_data:
                return self.extract_gps_from_exif(exif_data)
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to extract GPS from PicMan data: photo_id=%s, error=%s", photo_data.get('id'), str(e))
            return None
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的图片格式列表
        
        Returns:
            支持的文件扩展名列表
        """
        if PIL_AVAILABLE:
            return ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.bmp', '.gif']
        else:
            return []  # 没有PIL时无法直接读取文件
    
    def is_file_supported(self, file_path: str) -> bool:
        """检查文件是否支持GPS提取
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        if not PIL_AVAILABLE:
            return False
        
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.get_supported_formats()