"""
日志工具模块
使用标准logging处理中文日志
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    logger.setLevel(level_map.get(log_level.upper(), logging.INFO))
    
    # 创建日志目录
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 创建日志文件名（按日期）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"joycaption_{today}.log"
    
    # 创建文件处理器
    file_handler = logging.FileHandler(
        log_file, 
        encoding='utf-8', 
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置格式化器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
    """
    记录函数调用
    
    Args:
        logger: 日志记录器
        func_name: 函数名称
        **kwargs: 函数参数
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"调用函数: {func_name}({params})")


def log_function_result(logger: logging.Logger, func_name: str, result=None, error=None):
    """
    记录函数结果
    
    Args:
        logger: 日志记录器
        func_name: 函数名称
        result: 函数结果
        error: 错误信息
    """
    if error:
        logger.error(f"函数 {func_name} 执行失败: {error}")
    else:
        logger.debug(f"函数 {func_name} 执行成功: {result}")


def log_progress(logger: logging.Logger, stage: str, progress: int, message: str):
    """
    记录进度信息
    
    Args:
        logger: 日志记录器
        stage: 阶段名称
        progress: 进度百分比
        message: 进度消息
    """
    logger.info(f"进度更新 - {stage}: {progress}% - {message}")


def log_model_operation(logger: logging.Logger, operation: str, model_name: str, **kwargs):
    """
    记录模型操作
    
    Args:
        logger: 日志记录器
        operation: 操作类型
        model_name: 模型名称
        **kwargs: 其他参数
    """
    extra_info = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"模型操作 - {operation}: {model_name} {extra_info}")


def log_inference(logger: logging.Logger, image_path: str, detail_level: str, result: str = None, error: str = None):
    """
    记录推理信息
    
    Args:
        logger: 日志记录器
        image_path: 图片路径
        detail_level: 详细程度
        result: 推理结果
        error: 错误信息
    """
    image_name = Path(image_path).name
    if error:
        logger.error(f"推理失败 - {image_name} ({detail_level}): {error}")
    else:
        logger.info(f"推理成功 - {image_name} ({detail_level}): {result[:100]}..." if len(result) > 100 else result) 