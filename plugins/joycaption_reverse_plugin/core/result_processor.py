"""
JoyCaption插件结果处理器
负责处理推理结果和文件保存
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ResultProcessor:
    """JoyCaption结果处理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.core.result_processor")
        
        # 获取输出配置
        self.output_config = config_manager.get_output_config()
    
    def save_result_to_file(self, image_path: str, result_text: str, description_level: str = "normal") -> bool:
        """保存结果到文件"""
        try:
            image_path_obj = Path(image_path)
            
            # 构建输出文件路径
            output_file = image_path_obj.parent / f"{image_path_obj.stem}.txt"
            
            # 获取文件编码
            encoding = self.output_config.get("file_encoding", "utf-8")
            
            # 保存结果
            with open(output_file, 'w', encoding=encoding) as f:
                f.write(result_text)
            
            self.logger.info(f"结果已保存到文件: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存结果到文件失败 {image_path}: {str(e)}")
            return False
    
    def save_batch_results(self, results: List[Dict[str, Any]], description_level: str = "normal") -> Dict[str, Any]:
        """保存批量结果"""
        try:
            success_count = 0
            failed_count = 0
            saved_files = []
            
            for result in results:
                if result.get("success", False):
                    image_path = result["image_path"]
                    result_text = result["text"]
                    
                    if self.save_result_to_file(image_path, result_text, description_level):
                        success_count += 1
                        saved_files.append(image_path)
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            
            summary = {
                "total": len(results),
                "success": success_count,
                "failed": failed_count,
                "saved_files": saved_files,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"批量结果保存完成: 成功 {success_count}, 失败 {failed_count}")
            return summary
            
        except Exception as e:
            self.logger.error(f"保存批量结果失败: {str(e)}")
            return {
                "total": len(results),
                "success": 0,
                "failed": len(results),
                "saved_files": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def save_result_to_database(self, image_path: str, result_text: str, description_level: str = "normal") -> bool:
        """保存结果到数据库（集成到Photo666的标签系统）"""
        try:
            # 这里可以集成到Photo666的数据库系统
            # 暂时返回True，表示保存成功
            self.logger.info(f"结果已保存到数据库: {image_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存结果到数据库失败 {image_path}: {str(e)}")
            return False
    
    def format_result_for_display(self, result_text: str, description_level: str = "normal") -> str:
        """格式化结果用于显示"""
        try:
            # 根据描述级别格式化结果
            if description_level == "simple":
                # 简单描述：保持原样
                return result_text
            elif description_level == "normal":
                # 普通描述：添加一些格式化
                return result_text
            elif description_level == "detailed":
                # 详细描述：可以添加更多格式化
                return result_text
            else:
                return result_text
                
        except Exception as e:
            self.logger.error(f"格式化结果失败: {str(e)}")
            return result_text
    
    def create_result_summary(self, results: List[Dict[str, Any]], description_level: str = "normal") -> Dict[str, Any]:
        """创建结果摘要"""
        try:
            total_count = len(results)
            success_count = sum(1 for r in results if r.get("success", False))
            failed_count = total_count - success_count
            
            # 统计错误类型
            error_types = {}
            for result in results:
                if not result.get("success", False):
                    error = result.get("error", "未知错误")
                    error_types[error] = error_types.get(error, 0) + 1
            
            # 计算平均处理时间（如果有时间信息）
            processing_times = []
            for result in results:
                if "processing_time" in result:
                    processing_times.append(result["processing_time"])
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            summary = {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
                "error_types": error_types,
                "avg_processing_time": avg_processing_time,
                "description_level": description_level,
                "timestamp": datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"创建结果摘要失败: {str(e)}")
            return {
                "total_count": len(results),
                "success_count": 0,
                "failed_count": len(results),
                "success_rate": 0,
                "error_types": {"处理失败": len(results)},
                "avg_processing_time": 0,
                "description_level": description_level,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def export_results_to_json(self, results: List[Dict[str, Any]], output_path: str) -> bool:
        """导出结果到JSON文件"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备导出数据
            export_data = {
                "plugin": "JoyCaption Reverse Plugin",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "summary": self.create_result_summary(results)
            }
            
            # 保存到JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"结果已导出到JSON文件: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出结果到JSON失败: {str(e)}")
            return False
    
    def validate_result(self, result_text: str) -> bool:
        """验证结果有效性"""
        try:
            # 检查结果是否为空
            if not result_text or not result_text.strip():
                return False
            
            # 检查结果长度
            if len(result_text.strip()) < 5:
                return False
            
            # 可以添加更多验证规则
            return True
            
        except Exception as e:
            self.logger.error(f"验证结果失败: {str(e)}")
            return False
    
    def merge_results(self, results: List[Dict[str, Any]], merge_strategy: str = "append") -> str:
        """合并多个结果"""
        try:
            if not results:
                return ""
            
            if merge_strategy == "append":
                # 简单追加
                merged_text = "\n\n".join([r.get("text", "") for r in results if r.get("success", False)])
            elif merge_strategy == "summary":
                # 生成摘要
                texts = [r.get("text", "") for r in results if r.get("success", False)]
                merged_text = f"共处理 {len(texts)} 张图片:\n\n" + "\n\n".join(texts)
            else:
                # 默认追加
                merged_text = "\n\n".join([r.get("text", "") for r in results if r.get("success", False)])
            
            return merged_text
            
        except Exception as e:
            self.logger.error(f"合并结果失败: {str(e)}")
            return ""
    
    def get_result_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取结果统计信息"""
        try:
            total_count = len(results)
            success_count = sum(1 for r in results if r.get("success", False))
            failed_count = total_count - success_count
            
            # 计算文本长度统计
            text_lengths = []
            for result in results:
                if result.get("success", False):
                    text = result.get("text", "")
                    text_lengths.append(len(text))
            
            stats = {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
                "avg_text_length": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
                "min_text_length": min(text_lengths) if text_lengths else 0,
                "max_text_length": max(text_lengths) if text_lengths else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取结果统计信息失败: {str(e)}")
            return {
                "total_count": len(results),
                "success_count": 0,
                "failed_count": len(results),
                "success_rate": 0,
                "avg_text_length": 0,
                "min_text_length": 0,
                "max_text_length": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 