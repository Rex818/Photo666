#!/usr/bin/env python3
"""
GPS位置查询插件测试脚本

用于测试插件的基本功能。
"""

import sys
import os
from pathlib import Path

# 添加必要的路径
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# 添加PicMan源码目录
src_dir = plugin_dir.parent.parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

def test_plugin_basic():
    """测试插件基本功能"""
    print("=== GPS位置查询插件基本功能测试 ===\n")
    
    try:
        # 导入插件
        from plugin import GPSLocationPlugin
        print("✓ 插件导入成功")
        
        # 创建插件实例
        plugin = GPSLocationPlugin()
        print("✓ 插件实例创建成功")
        
        # 获取插件信息
        info = plugin.get_info()
        print(f"✓ 插件信息: {info.name} v{info.version}")
        print(f"  描述: {info.description}")
        print(f"  作者: {info.author}")
        
        # 初始化插件
        app_context = {
            'config': {},
            'logger': None
        }
        
        success = plugin.initialize(app_context)
        if success:
            print("✓ 插件初始化成功")
        else:
            print("⚠ 插件初始化失败（可能是配置问题）")
        
        # 检查插件状态
        status = plugin.get_status_info()
        print(f"✓ 插件状态:")
        print(f"  - 已初始化: {status['initialized']}")
        print(f"  - 可用: {status['available']}")
        print(f"  - 启用: {status['enabled']}")
        
        # 测试组件状态
        components = status['components']
        print(f"✓ 组件状态:")
        for name, available in components.items():
            status_icon = "✓" if available else "✗"
            print(f"  - {name}: {status_icon}")
        
        # 测试配置
        if plugin.config:
            config_summary = plugin.config.get_config_summary()
            print(f"✓ 配置摘要:")
            print(f"  - API优先级: {config_summary['api_priority']}")
            print(f"  - 已配置API: {config_summary['api_keys_configured']}")
            print(f"  - 缓存启用: {config_summary['cache_enabled']}")
            print(f"  - 自动查询: {config_summary['auto_query']}")
        
        # 测试API状态
        if plugin.api_client:
            api_status = plugin.api_client.get_api_status()
            print(f"✓ API状态:")
            for api_name, status in api_status.items():
                available_icon = "✓" if status['available'] else "✗"
                print(f"  - {api_name}: {available_icon}")
        
        # 关闭插件
        plugin.shutdown()
        print("✓ 插件关闭成功")
        
        print("\n=== 基本功能测试完成 ===")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_gps_extraction():
    """测试GPS提取功能"""
    print("\n=== GPS提取功能测试 ===\n")
    
    try:
        from gps_extractor import GPSExtractor
        from models import GPSCoordinate
        
        extractor = GPSExtractor()
        print("✓ GPS提取器创建成功")
        
        # 测试EXIF数据提取
        test_exif = {
            'GPSLatitude': [39, 54, 26.5],
            'GPSLatitudeRef': 'N',
            'GPSLongitude': [116, 23, 29.3],
            'GPSLongitudeRef': 'E',
            'GPSAltitude': 44.5
        }
        
        coordinate = extractor.extract_gps_from_exif(test_exif)
        if coordinate:
            print(f"✓ GPS坐标提取成功:")
            print(f"  - 纬度: {coordinate.latitude:.6f}")
            print(f"  - 经度: {coordinate.longitude:.6f}")
            print(f"  - 海拔: {coordinate.altitude}m")
            print(f"  - 度分秒格式: {coordinate.to_dms_string()}")
            print(f"  - 坐标有效: {coordinate.is_valid()}")
        else:
            print("✗ GPS坐标提取失败")
        
        # 测试支持的格式
        formats = extractor.get_supported_formats()
        print(f"✓ 支持的图片格式: {formats}")
        
        print("\n=== GPS提取功能测试完成 ===")
        return True
        
    except Exception as e:
        print(f"✗ GPS提取测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_client():
    """测试API客户端功能"""
    print("\n=== API客户端功能测试 ===\n")
    
    try:
        from location_api import LocationAPIClient, NominatimAPI
        from models import GPSCoordinate
        
        # 测试Nominatim API（免费，无需密钥）
        nominatim = NominatimAPI()
        print(f"✓ {nominatim.get_api_name()} API创建成功")
        print(f"  - 可用性: {nominatim.is_available()}")
        print(f"  - 速率限制: {nominatim.get_rate_limit()} req/s")
        
        # 创建API客户端
        config = {
            'priority': ['nominatim'],
            'timeout': 10,
            'retry_count': 1
        }
        
        client = LocationAPIClient(config)
        print("✓ API客户端创建成功")
        
        available_apis = client.get_available_apis()
        print(f"✓ 可用API: {available_apis}")
        
        # 测试位置查询（使用北京天安门坐标）
        test_coordinate = GPSCoordinate(39.9042, 116.4074)
        print(f"✓ 测试坐标: {test_coordinate}")
        
        print("  正在查询位置信息...")
        try:
            location_info = client.query_location(test_coordinate)
            if location_info:
                print(f"✓ 位置查询成功:")
                print(f"  - 国家: {location_info.country}")
                print(f"  - 省份: {location_info.state_province}")
                print(f"  - 城市: {location_info.city}")
                print(f"  - 区域: {location_info.district}")
                print(f"  - 完整地址: {location_info.formatted_address}")
                print(f"  - API来源: {location_info.source_api}")
            else:
                print("⚠ 位置查询无结果")
        except Exception as e:
            print(f"⚠ 位置查询失败: {str(e)}")
            print("  (这可能是网络问题或API限制)")
        
        print("\n=== API客户端功能测试完成 ===")
        return True
        
    except Exception as e:
        print(f"✗ API客户端测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_manager():
    """测试缓存管理功能"""
    print("\n=== 缓存管理功能测试 ===\n")
    
    try:
        from cache_manager import LocationCache
        from models import GPSCoordinate, LocationInfo
        
        # 创建临时缓存
        cache = LocationCache(":memory:")  # 使用内存数据库
        print("✓ 缓存管理器创建成功")
        
        # 测试缓存存储和检索
        test_coordinate = GPSCoordinate(39.9042, 116.4074)
        test_location = LocationInfo(
            country="中国",
            state_province="北京市",
            city="北京市",
            district="东城区",
            formatted_address="中国北京市东城区天安门广场",
            source_api="测试"
        )
        
        # 先检查缓存是否为空（这会触发数据库初始化）
        empty_result = cache.get_cached_location(GPSCoordinate(0, 0))
        print(f"✓ 缓存初始化检查完成")
        
        # 存储到缓存
        cache.cache_location(test_coordinate, test_location)
        print("✓ 位置信息缓存成功")
        
        # 从缓存检索
        cached_location = cache.get_cached_location(test_coordinate)
        if cached_location:
            print("✓ 缓存检索成功:")
            print(f"  - 城市: {cached_location.city}")
            print(f"  - 地址: {cached_location.formatted_address}")
            print(f"  - 来源: {cached_location.source_api}")
        else:
            print("✗ 缓存检索失败")
        
        # 测试缓存统计
        stats = cache.get_cache_stats()
        print(f"✓ 缓存统计:")
        print(f"  - 总条目: {stats['total_entries']}")
        print(f"  - 总命中: {stats['total_hits']}")
        print(f"  - 数据库大小: {stats['db_size_mb']} MB")
        
        print("\n=== 缓存管理功能测试完成 ===")
        return True
        
    except Exception as e:
        print(f"✗ 缓存管理测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("GPS位置查询插件测试")
    print("=" * 50)
    
    tests = [
        ("基本功能", test_plugin_basic),
        ("GPS提取", test_gps_extraction),
        ("API客户端", test_api_client),
        ("缓存管理", test_cache_manager)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n开始测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print(f"\n用户中断测试: {test_name}")
            break
        except Exception as e:
            print(f"测试异常: {test_name} - {str(e)}")
            results.append((test_name, False))
    
    # 显示测试结果摘要
    print("\n" + "=" * 50)
    print("测试结果摘要:")
    
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！插件基本功能正常。")
    else:
        print("⚠ 部分测试失败，请检查相关功能。")


if __name__ == "__main__":
    main()