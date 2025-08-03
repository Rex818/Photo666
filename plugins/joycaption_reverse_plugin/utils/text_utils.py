"""
JoyCaption插件文本工具类
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime


class TextUtils:
    """文本工具类"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        try:
            if not text:
                return ""
            
            # 移除多余的空白字符
            text = re.sub(r'\s+', ' ', text.strip())
            
            # 移除特殊字符
            text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]', '', text)
            
            return text
            
        except Exception as e:
            logging.error(f"清理文本失败: {str(e)}")
            return text
    
    @staticmethod
    def extract_tags(text: str) -> List[str]:
        """从文本中提取标签"""
        try:
            if not text:
                return []
            
            # 分割文本
            tags = []
            
            # 按逗号分割
            comma_tags = [tag.strip() for tag in text.split(',') if tag.strip()]
            tags.extend(comma_tags)
            
            # 按空格分割
            space_tags = [tag.strip() for tag in text.split() if tag.strip()]
            tags.extend(space_tags)
            
            # 去重并清理
            unique_tags = []
            for tag in tags:
                clean_tag = TextUtils.clean_text(tag)
                if clean_tag and clean_tag not in unique_tags:
                    unique_tags.append(clean_tag)
            
            return unique_tags
            
        except Exception as e:
            logging.error(f"提取标签失败: {str(e)}")
            return []
    
    @staticmethod
    def format_caption(text: str, max_length: int = 0) -> str:
        """格式化描述文本"""
        try:
            if not text:
                return ""
            
            # 清理文本
            text = TextUtils.clean_text(text)
            
            # 限制长度
            if max_length > 0 and len(text) > max_length:
                text = text[:max_length] + "..."
            
            return text
            
        except Exception as e:
            logging.error(f"格式化描述失败: {str(e)}")
            return text
    
    @staticmethod
    def split_text_by_sentences(text: str) -> List[str]:
        """按句子分割文本"""
        try:
            if not text:
                return []
            
            # 使用正则表达式分割句子
            sentences = re.split(r'[.!?]+', text)
            
            # 清理句子
            cleaned_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    cleaned_sentences.append(sentence)
            
            return cleaned_sentences
            
        except Exception as e:
            logging.error(f"分割句子失败: {str(e)}")
            return [text]
    
    @staticmethod
    def count_words(text: str) -> int:
        """计算单词数量"""
        try:
            if not text:
                return 0
            
            # 按空格分割并计算
            words = text.split()
            return len(words)
            
        except Exception as e:
            logging.error(f"计算单词数量失败: {str(e)}")
            return 0
    
    @staticmethod
    def count_characters(text: str) -> int:
        """计算字符数量"""
        try:
            if not text:
                return 0
            
            return len(text)
            
        except Exception as e:
            logging.error(f"计算字符数量失败: {str(e)}")
            return 0
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """截断文本"""
        try:
            if not text or len(text) <= max_length:
                return text
            
            return text[:max_length - len(suffix)] + suffix
            
        except Exception as e:
            logging.error(f"截断文本失败: {str(e)}")
            return text
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """标准化文本"""
        try:
            if not text:
                return ""
            
            # 转换为小写
            text = text.lower()
            
            # 移除多余的空白字符
            text = re.sub(r'\s+', ' ', text.strip())
            
            # 标准化标点符号
            text = re.sub(r'[，。！？；：]', lambda m: {
                '，': ',', '。': '.', '！': '!', '？': '?', '；': ';', '：': ':'
            }[m.group()], text)
            
            return text
            
        except Exception as e:
            logging.error(f"标准化文本失败: {str(e)}")
            return text
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        try:
            if not text:
                return []
            
            # 清理文本
            text = TextUtils.clean_text(text)
            
            # 按空格分割
            words = text.split()
            
            # 过滤短词和常见词
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            keywords = [word for word in words if len(word) > 2 and word.lower() not in stop_words]
            
            # 去重
            unique_keywords = []
            for keyword in keywords:
                if keyword not in unique_keywords:
                    unique_keywords.append(keyword)
            
            # 限制数量
            return unique_keywords[:max_keywords]
            
        except Exception as e:
            logging.error(f"提取关键词失败: {str(e)}")
            return []
    
    @staticmethod
    def format_timestamp(timestamp: Optional[datetime] = None) -> str:
        """格式化时间戳"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            logging.error(f"格式化时间戳失败: {str(e)}")
            return ""
    
    @staticmethod
    def create_summary(text: str, max_sentences: int = 3) -> str:
        """创建文本摘要"""
        try:
            if not text:
                return ""
            
            # 分割句子
            sentences = TextUtils.split_text_by_sentences(text)
            
            # 选择前几个句子作为摘要
            summary_sentences = sentences[:max_sentences]
            
            return ". ".join(summary_sentences) + "."
            
        except Exception as e:
            logging.error(f"创建摘要失败: {str(e)}")
            return text
    
    @staticmethod
    def validate_text(text: str, min_length: int = 0, max_length: int = 0) -> bool:
        """验证文本"""
        try:
            if not text:
                return min_length == 0
            
            text_length = len(text)
            
            if min_length > 0 and text_length < min_length:
                return False
            
            if max_length > 0 and text_length > max_length:
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"验证文本失败: {str(e)}")
            return False
    
    @staticmethod
    def extract_metadata(text: str) -> Dict[str, Any]:
        """提取文本元数据"""
        try:
            metadata = {
                "length": len(text),
                "word_count": TextUtils.count_words(text),
                "sentence_count": len(TextUtils.split_text_by_sentences(text)),
                "keyword_count": len(TextUtils.extract_keywords(text)),
                "has_numbers": bool(re.search(r'\d', text)),
                "has_special_chars": bool(re.search(r'[^\w\s]', text)),
                "language": TextUtils.detect_language(text)
            }
            
            return metadata
            
        except Exception as e:
            logging.error(f"提取元数据失败: {str(e)}")
            return {}
    
    @staticmethod
    def detect_language(text: str) -> str:
        """检测语言"""
        try:
            if not text:
                return "unknown"
            
            # 简单的语言检测
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            
            if chinese_chars > english_chars:
                return "chinese"
            elif english_chars > chinese_chars:
                return "english"
            else:
                return "mixed"
                
        except Exception as e:
            logging.error(f"检测语言失败: {str(e)}")
            return "unknown"
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        try:
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
                
        except Exception as e:
            logging.error(f"格式化文件大小失败: {str(e)}")
            return "0 B"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        try:
            if not filename:
                return "untitled"
            
            # 移除或替换非法字符
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # 移除多余的空格和点
            filename = re.sub(r'\s+', ' ', filename.strip())
            filename = re.sub(r'\.+$', '', filename)
            
            # 限制长度
            if len(filename) > 255:
                filename = filename[:255]
            
            return filename if filename else "untitled"
            
        except Exception as e:
            logging.error(f"清理文件名失败: {str(e)}")
            return "untitled" 