"""
结果处理器
处理Florence2推理结果，保存到文件和数据库
"""

import os
import json
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultProcessor:
    """结果处理器"""
    
    def __init__(self):
        self.config_manager = None
        self.app_context = None
        self.is_initialized = False
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """初始化结果处理器"""
        try:
            self.app_context = app_context
            self.is_initialized = True
            logger.info("结果处理器初始化完成")
            return True
        except Exception as e:
            logger.error(f"结果处理器初始化失败: {str(e)}")
            return False
    
    def _save_to_file(self, result: Dict[str, Any], output_config: Dict[str, Any]) -> bool:
        """保存结果到文件"""
        try:
            image_path = Path(result["image_path"])
            image_dir = image_path.parent
            image_name = image_path.stem
            
            # 获取文件前缀和后缀
            file_prefix = output_config.get("file_prefix", "")
            file_suffix = output_config.get("file_suffix", ".txt")
            
            # 生成输出文件名
            output_filename = f"{file_prefix}{image_name}{file_suffix}"
            output_path = image_dir / output_filename
            
            # 只保存纯文本结果
            if result["success"]:
                content = result["result"]
            else:
                content = f"推理失败: {result.get('error', '未知错误')}"
            
            # 保存为纯文本格式
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"结果已保存到文件: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return False
    
    def _save_to_database(self, result: Dict[str, Any]) -> bool:
        """保存结果到数据库"""
        try:
            if not self.app_context or "database" not in self.app_context:
                logger.warning("数据库上下文不可用，跳过数据库保存")
                return False
            
            database = self.app_context["database"]
            
            # 检查是否已存在记录
            image_path = result["image_path"]
            model_name = result["model_name"]
            description_level = result["description_level"]
            
            # 查询现有记录
            existing = database.execute(
                "SELECT id FROM reverse_inference_results WHERE image_path = ? AND model_name = ? AND description_level = ?",
                (image_path, model_name, description_level)
            ).fetchone()
            
            if existing:
                # 更新现有记录
                database.execute(
                    """UPDATE reverse_inference_results 
                       SET result = ?, success = ?, error = ?, updated_at = ?, model_path = ?
                       WHERE image_path = ? AND model_name = ? AND description_level = ?""",
                    (
                        result["result"],
                        result["success"],
                        result.get("error", ""),
                        datetime.now().isoformat(),
                        result.get("model_path", ""),
                        image_path,
                        model_name,
                        description_level
                    )
                )
                logger.info(f"更新数据库记录: {image_path}")
            else:
                # 插入新记录
                database.execute(
                    """INSERT INTO reverse_inference_results 
                       (image_path, model_name, description_level, result, success, error, created_at, updated_at, model_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        image_path,
                        model_name,
                        description_level,
                        result["result"],
                        result["success"],
                        result.get("error", ""),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        result.get("model_path", "")
                    )
                )
                logger.info(f"插入数据库记录: {image_path}")
            
            database.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {str(e)}")
            return False
    
    def _update_ui_tags(self, result: Dict[str, Any]) -> bool:
        """更新UI标签显示"""
        try:
            if not self.app_context or "main_window" not in self.app_context:
                logger.warning("主窗口上下文不可用，跳过UI更新")
                return False
            
            main_window = self.app_context["main_window"]
            
            # 获取图片路径
            image_path = result["image_path"]
            
            # 查找对应的照片ID
            database = self.app_context["database"]
            photo = database.execute(
                "SELECT id FROM photos WHERE file_path = ?",
                (image_path,)
            ).fetchone()
            
            if not photo:
                logger.warning(f"未找到照片记录: {image_path}")
                return False
            
            photo_id = photo[0]
            
            # 根据描述级别更新对应的标签
            description_level = result["description_level"]
            result_text = result["result"]
            
            if result["success"]:
                # 更新标签
                if description_level == "simple":
                    # 更新简单标签
                    self._update_photo_tags(photo_id, "simple_tags", result_text)
                elif description_level == "normal":
                    # 更新普通标签
                    self._update_photo_tags(photo_id, "normal_tags", result_text)
                elif description_level == "detailed":
                    # 更新详细标签
                    self._update_photo_tags(photo_id, "detailed_tags", result_text)
                
                logger.info(f"更新UI标签: {image_path} - {description_level}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新UI标签失败: {str(e)}")
            return False
    
    def _update_photo_tags(self, photo_id: int, tag_field: str, tag_content: str):
        """更新照片标签"""
        try:
            database = self.app_context["database"]
            
            # 更新照片标签
            database.execute(
                f"UPDATE photos SET {tag_field} = ? WHERE id = ?",
                (tag_content, photo_id)
            )
            
            database.commit()
            
        except Exception as e:
            logger.error(f"更新照片标签失败: {str(e)}")
    
    def process_results(self, results: List[Dict[str, Any]], 
                       description_level: str, config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """处理推理结果"""
        try:
            logger.info(f"开始处理推理结果 - 结果数量: {len(results)}, 描述级别: {description_level}")
            
            # 获取输出配置
            output_config = self.config_manager.get_output_config() if self.config_manager else {}
            
            # 从配置中获取保存选项
            save_to_file = config.get("save_to_file", True) if config else True
            save_to_database = config.get("save_to_database", True) if config else True
            
            processed_results = []
            for result in results:
                try:
                    # 根据配置决定保存方式
                    file_saved = False
                    db_saved = False
                    
                    if save_to_file:
                        file_saved = self._save_to_file(result, output_config)
                    
                    if save_to_database:
                        db_saved = self._update_ui_tags(result)
                    
                    # 更新结果状态
                    processed_result = {
                        **result,
                        "processed": True,
                        "file_saved": file_saved,
                        "database_saved": db_saved
                    }
                    processed_results.append(processed_result)
                    
                    logger.info(f"结果处理完成: {Path(result['image_path']).name}")
                    
                except Exception as e:
                    logger.error(f"处理单个结果失败: {str(e)}")
                    processed_results.append({
                        **result,
                        "processed": False,
                        "file_saved": False,
                        "database_saved": False,
                        "processing_error": str(e)
                    })
            
            logger.info(f"结果处理完成 - 处理数量: {len(processed_results)}")
            return processed_results
            
        except Exception as e:
            logger.error(f"结果处理失败: {str(e)}")
            return []
    
    def get_result_from_file(self, image_path: str, description_level: str) -> Optional[str]:
        """从文件读取结果"""
        try:
            image_path_obj = Path(image_path)
            image_dir = image_path_obj.parent
            image_name = image_path_obj.stem
            
            # 获取输出配置
            output_config = self.config_manager.get_output_config() if self.config_manager else {}
            file_prefix = output_config.get("file_prefix", "")
            file_suffix = output_config.get("file_suffix", ".txt")
            
            # 生成文件路径
            result_file = image_dir / f"{file_prefix}{image_name}{file_suffix}"
            
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                # 检查描述级别是否匹配
                if content.get("description_level") == description_level:
                    return content.get("result", "")
            
            return None
            
        except Exception as e:
            logger.error(f"从文件读取结果失败: {str(e)}")
            return None
    
    def get_result_from_database(self, image_path: str, description_level: str) -> Optional[str]:
        """从数据库读取结果"""
        try:
            if not self.app_context or "database" not in self.app_context:
                return None
            
            database = self.app_context["database"]
            
            result = database.execute(
                """SELECT result FROM reverse_inference_results 
                   WHERE image_path = ? AND description_level = ? AND success = 1
                   ORDER BY updated_at DESC LIMIT 1""",
                (image_path, description_level)
            ).fetchone()
            
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"从数据库读取结果失败: {str(e)}")
            return None 