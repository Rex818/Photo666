"""
GPS提取器模块测试

测试GPS坐标提取功能。
"""

import unittest
import sys
import os
from pathlib import Path

# 添加插件目录到Python路径
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

from gps_extractor import GPSExtractor
from models import GPSCoordinate
from exceptions import GPSExtractionError, InvalidCoordinateError


class TestGPSExtractor(unittest.TestCase):
    """GPS提取器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.extractor = GPSExtractor()
    
    def test_convert_coordinate_to_decimal(self):
        """测试坐标转换为十进制度数"""
        # 测试度分秒格式
        coord_dms = [39, 54, 26.5]  # 39°54'26.5"
        result = self.extractor._convert_coordinate_to_decimal(coord_dms, 'N')
        expected = 39 + 54/60 + 26.5/3600
        self.assertAlmostEqual(result, expected, places=6)
        
        # 测试南纬（负数）
        result_s = self.extractor._convert_coordinate_to_decimal(coord_dms, 'S')
        self.assertAlmostEqual(result_s, -expected, places=6)
        
        # 测试度分格式
        coord_dm = [116, 23.5]  # 116°23.5'
        result = self.extractor._convert_coordinate_to_decimal(coord_dm, 'E')
        expected = 116 + 23.5/60
        self.assertAlmostEqual(result, expected, places=6)
        
        # 测试西经（负数）
        result_w = self.extractor._convert_coordinate_to_decimal(coord_dm, 'W')
        self.assertAlmostEqual(result_w, -expected, places=6)
    
    def test_parse_rational(self):
        """测试有理数解析"""
        # 测试分数字符串
        self.assertEqual(self.extractor._parse_rational("39/1"), 39.0)
        self.assertEqual(self.extractor._parse_rational("54/1"), 54.0)
        self.assertAlmostEqual(self.extractor._parse_rational("265/10"), 26.5)
        
        # 测试数字
        self.assertEqual(self.extractor._parse_rational(39), 39.0)
        self.assertEqual(self.extractor._parse_rational(39.5), 39.5)
        
        # 测试异常情况
        self.assertEqual(self.extractor._parse_rational("invalid"), 0.0)
    
    def test_extract_gps_from_exif(self):
        """测试从EXIF数据提取GPS"""
        # 测试完整的GPS数据
        exif_data = {
            'GPSLatitude': [39, 54, 26.5],
            'GPSLatitudeRef': 'N',
            'GPSLongitude': [116, 23, 29.3],
            'GPSLongitudeRef': 'E',
            'GPSAltitude': 44.5
        }
        
        coordinate = self.extractor.extract_gps_from_exif(exif_data)
        self.assertIsNotNone(coordinate)
        self.assertIsInstance(coordinate, GPSCoordinate)
        self.assertAlmostEqual(coordinate.latitude, 39.907361, places=5)
        self.assertAlmostEqual(coordinate.longitude, 116.391472, places=5)
        self.assertEqual(coordinate.altitude, 44.5)
        
        # 测试无GPS数据
        empty_exif = {}
        coordinate = self.extractor.extract_gps_from_exif(empty_exif)
        self.assertIsNone(coordinate)
        
        # 测试部分GPS数据（缺少经度）
        partial_exif = {
            'GPSLatitude': [39, 54, 26.5],
            'GPSLatitudeRef': 'N'
        }
        coordinate = self.extractor.extract_gps_from_exif(partial_exif)
        self.assertIsNone(coordinate)
    
    def test_extract_gps_from_nested_exif(self):
        """测试从嵌套EXIF数据提取GPS"""
        # 测试GPSInfo嵌套格式
        exif_data = {
            'GPSInfo': {
                'GPSLatitude': [39, 54, 26.5],
                'GPSLatitudeRef': 'N',
                'GPSLongitude': [116, 23, 29.3],
                'GPSLongitudeRef': 'E'
            }
        }
        
        coordinate = self.extractor.extract_gps_from_exif(exif_data)
        self.assertIsNotNone(coordinate)
        self.assertAlmostEqual(coordinate.latitude, 39.907361, places=5)
        self.assertAlmostEqual(coordinate.longitude, 116.391472, places=5)
    
    def test_extract_gps_from_json_string(self):
        """测试从JSON字符串提取GPS"""
        import json
        
        exif_dict = {
            'GPSLatitude': [39, 54, 26.5],
            'GPSLatitudeRef': 'N',
            'GPSLongitude': [116, 23, 29.3],
            'GPSLongitudeRef': 'E'
        }
        exif_json = json.dumps(exif_dict)
        
        coordinate = self.extractor.extract_gps_from_exif(exif_json)
        self.assertIsNotNone(coordinate)
        self.assertAlmostEqual(coordinate.latitude, 39.907361, places=5)
        self.assertAlmostEqual(coordinate.longitude, 116.391472, places=5)
    
    def test_validate_coordinates(self):
        """测试坐标验证"""
        # 有效坐标
        self.assertTrue(self.extractor._validate_coordinates(39.9, 116.4))
        self.assertTrue(self.extractor._validate_coordinates(-90, -180))
        self.assertTrue(self.extractor._validate_coordinates(90, 180))
        
        # 无效坐标
        self.assertFalse(self.extractor._validate_coordinates(91, 116.4))  # 纬度超范围
        self.assertFalse(self.extractor._validate_coordinates(39.9, 181))  # 经度超范围
        self.assertFalse(self.extractor._validate_coordinates(-91, 116.4))  # 纬度超范围
        self.assertFalse(self.extractor._validate_coordinates(39.9, -181))  # 经度超范围
    
    def test_extract_gps_from_picman_data(self):
        """测试从PicMan数据提取GPS"""
        # 测试包含EXIF数据的照片数据
        photo_data = {
            'id': 1,
            'filepath': '/nonexistent/path.jpg',  # 文件不存在，会回退到EXIF数据
            'exif_data': {
                'GPSLatitude': [39, 54, 26.5],
                'GPSLatitudeRef': 'N',
                'GPSLongitude': [116, 23, 29.3],
                'GPSLongitudeRef': 'E'
            }
        }
        
        coordinate = self.extractor.extract_gps_from_picman_data(photo_data)
        self.assertIsNotNone(coordinate)
        self.assertAlmostEqual(coordinate.latitude, 39.907361, places=5)
        
        # 测试无GPS数据的照片
        photo_data_no_gps = {
            'id': 2,
            'filepath': '/nonexistent/path.jpg',
            'exif_data': {}
        }
        
        coordinate = self.extractor.extract_gps_from_picman_data(photo_data_no_gps)
        self.assertIsNone(coordinate)
    
    def test_get_supported_formats(self):
        """测试获取支持的格式"""
        formats = self.extractor.get_supported_formats()
        self.assertIsInstance(formats, list)
        
        # 如果PIL可用，应该有支持的格式
        try:
            import PIL
            self.assertGreater(len(formats), 0)
            self.assertIn('.jpg', formats)
            self.assertIn('.jpeg', formats)
        except ImportError:
            # PIL不可用时，应该返回空列表
            self.assertEqual(len(formats), 0)
    
    def test_is_file_supported(self):
        """测试文件格式支持检查"""
        try:
            import PIL
            # PIL可用时
            self.assertTrue(self.extractor.is_file_supported('test.jpg'))
            self.assertTrue(self.extractor.is_file_supported('test.jpeg'))
            self.assertTrue(self.extractor.is_file_supported('test.tiff'))
            self.assertFalse(self.extractor.is_file_supported('test.txt'))
        except ImportError:
            # PIL不可用时
            self.assertFalse(self.extractor.is_file_supported('test.jpg'))


if __name__ == '__main__':
    unittest.main()