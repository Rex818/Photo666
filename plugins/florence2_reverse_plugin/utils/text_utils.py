"""
文本工具类
"""

import re
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class TextUtils:
    """文本处理工具类"""
    
    @staticmethod
    def parse_result_to_tags(result: str, description_level: str) -> List[str]:
        """解析推理结果为标签列表"""
        try:
            if not result or not result.strip():
                return []
            
            if description_level == 'simple':
                # 简单描述：提取关键词，通常用逗号分隔
                tags = result.split(',')
                tags = [tag.strip() for tag in tags if tag.strip()]
                # 移除引号和特殊字符
                tags = [re.sub(r'["\']', '', tag) for tag in tags]
                tags = [tag for tag in tags if len(tag) > 1]
            else:
                # 普通和详细描述：提取名词短语
                # 移除标点符号
                clean_text = re.sub(r'[^\w\s]', ' ', result)
                
                # 提取单词
                words = clean_text.split()
                
                # 过滤短词和常见停用词
                stop_words = {
                    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
                    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                    'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
                }
                
                tags = []
                for word in words:
                    word = word.lower().strip()
                    if len(word) > 2 and word not in stop_words:
                        tags.append(word)
                
                # 去重并限制数量
                tags = list(set(tags))
            
            # 限制标签数量
            tags = tags[:20]
            
            logger.info("解析标签完成", 
                       description_level=description_level,
                       original_length=len(result),
                       tag_count=len(tags))
            
            return tags
            
        except Exception as e:
            logger.error("解析标签失败", error=str(e))
            return []
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        try:
            if not text:
                return ""
            
            # 移除多余的空白字符
            text = re.sub(r'\s+', ' ', text)
            
            # 移除特殊字符
            text = re.sub(r'[^\w\s,.-]', '', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error("清理文本失败", error=str(e))
            return text
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        try:
            if not text:
                return []
            
            # 清理文本
            clean_text = TextUtils.clean_text(text)
            
            # 分词
            words = clean_text.split()
            
            # 统计词频
            word_count = {}
            for word in words:
                word = word.lower().strip()
                if len(word) > 2:
                    word_count[word] = word_count.get(word, 0) + 1
            
            # 按频率排序
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            
            # 提取前N个关键词
            keywords = [word for word, count in sorted_words[:max_keywords]]
            
            return keywords
            
        except Exception as e:
            logger.error("提取关键词失败", error=str(e))
            return []
    
    @staticmethod
    def format_description(text: str, max_length: int = 200) -> str:
        """格式化描述文本"""
        try:
            if not text:
                return ""
            
            # 清理文本
            text = TextUtils.clean_text(text)
            
            # 截断过长文本
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            return text
            
        except Exception as e:
            logger.error("格式化描述失败", error=str(e))
            return text
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """分割句子"""
        try:
            if not text:
                return []
            
            # 使用正则表达式分割句子
            sentences = re.split(r'[.!?]+', text)
            
            # 清理句子
            sentences = [s.strip() for s in sentences if s.strip()]
            
            return sentences
            
        except Exception as e:
            logger.error("分割句子失败", error=str(e))
            return [text]
    
    @staticmethod
    def count_words(text: str) -> int:
        """统计单词数量"""
        try:
            if not text:
                return 0
            
            words = text.split()
            return len(words)
            
        except Exception as e:
            logger.error("统计单词数量失败", error=str(e))
            return 0
    
    @staticmethod
    def is_chinese_text(text: str) -> bool:
        """检查是否为中文文本"""
        try:
            if not text:
                return False
            
            # 检查是否包含中文字符
            chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
            return bool(chinese_pattern.search(text))
            
        except Exception as e:
            logger.error("检查中文文本失败", error=str(e))
            return False
    
    @staticmethod
    def translate_level_to_chinese(level: str) -> str:
        """将描述级别转换为中文"""
        level_mapping = {
            'simple': '简单描述',
            'normal': '普通描述',
            'detailed': '详细描述'
        }
        return level_mapping.get(level, level)
    
    @staticmethod
    def format_file_content(image_path: str, result: str, description_level: str) -> str:
        """格式化文件内容"""
        try:
            from datetime import datetime
            
            content = f"""AI反推结果 - {TextUtils.translate_level_to_chinese(description_level)}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
图片路径: {image_path}
描述级别: {description_level}
{'='*50}

{result}

{'='*50}
"""
            return content
            
        except Exception as e:
            logger.error("格式化文件内容失败", error=str(e))
            return result 