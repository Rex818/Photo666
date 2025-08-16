"""
Janus插件结果处理器
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image


class ResultProcessor:
    """Janus插件结果处理器"""
    
    def __init__(self, config_manager):
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.core.result_processor")
        self.config_manager = config_manager
        
        self.logger.info("Janus结果处理器初始化完成")
    
    def save_reverse_inference_result(self, image_path: str, result: str, 
                                    config: Dict[str, Any]) -> bool:
        """保存反推推理结果"""
        try:
            if not result:
                self.logger.warning(f"反推结果为空，跳过保存: {image_path}")
                return False
            
            # 获取保存配置
            save_results = config.get("save_results", True)
            result_file_suffix = config.get("result_file_suffix", ".txt")
            
            if not save_results:
                self.logger.info("配置为不保存结果，跳过保存")
                return True
            
            # 构建结果文件路径
            image_path_obj = Path(image_path)
            result_file_path = image_path_obj.parent / f"{image_path_obj.stem}{result_file_suffix}"
            
            # 保存结果文件
            with open(result_file_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            self.logger.info(f"反推结果已保存: {result_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存反推结果失败: {image_path}, 错误: {str(e)}")
            return False
    
    def save_generated_images(self, images: List[Image.Image], prompt: str,
                            output_dir: str, base_filename: str = "generated") -> List[str]:
        """保存生成的图片"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            saved_paths = []
            
            for i, image in enumerate(images):
                # 构建文件名
                if len(images) == 1:
                    filename = f"{base_filename}.png"
                else:
                    filename = f"{base_filename}_{i+1:03d}.png"
                
                file_path = output_path / filename
                
                # 保存图片
                image.save(file_path, "PNG")
                saved_paths.append(str(file_path))
                
                self.logger.info(f"生成的图片已保存: {file_path}")
            
            return saved_paths
            
        except Exception as e:
            self.logger.error(f"保存生成的图片失败: {prompt}, 错误: {str(e)}")
            return []
    
    def process_batch_reverse_inference_results(self, results: List[Dict[str, Any]], 
                                              config: Dict[str, Any]) -> Dict[str, Any]:
        """处理批量反推推理结果"""
        try:
            total_count = len(results)
            success_count = sum(1 for r in results if r.get("success", False))
            failed_count = total_count - success_count
            
            # 统计信息
            summary = {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "results": results
            }
            
            # 保存成功的结果
            saved_count = 0
            for result in results:
                if result.get("success", False):
                    image_path = result.get("image_path")
                    result_text = result.get("result")
                    if image_path and result_text:
                        if self.save_reverse_inference_result(image_path, result_text, config):
                            saved_count += 1
            
            summary["saved_count"] = saved_count
            
            self.logger.info(f"批量反推处理完成: 总计{total_count}张，成功{success_count}张，失败{failed_count}张，保存{saved_count}个结果文件")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"处理批量反推结果失败: {str(e)}")
            return {
                "total_count": len(results),
                "success_count": 0,
                "failed_count": len(results),
                "success_rate": 0,
                "error": str(e),
                "results": results
            }
    
    def process_batch_generation_results(self, results: List[Dict[str, Any]], 
                                       output_dir: str) -> Dict[str, Any]:
        """处理批量图片生成结果"""
        try:
            total_count = len(results)
            success_count = sum(1 for r in results if r.get("success", False))
            failed_count = total_count - success_count
            
            # 统计信息
            summary = {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "results": results
            }
            
            # 保存生成的图片
            total_saved = 0
            for result in results:
                if result.get("success", False):
                    prompt = result.get("prompt", "")
                    images = result.get("images", [])
                    
                    if images:
                        # 使用提示词的前20个字符作为文件名基础
                        base_filename = prompt[:20].replace(" ", "_").replace("/", "_")
                        saved_paths = self.save_generated_images(images, prompt, output_dir, base_filename)
                        total_saved += len(saved_paths)
                        
                        # 更新结果中的保存路径
                        result["saved_paths"] = saved_paths
            
            summary["total_saved_images"] = total_saved
            
            self.logger.info(f"批量图片生成处理完成: 总计{total_count}个提示词，成功{success_count}个，失败{failed_count}个，保存{total_saved}张图片")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"处理批量图片生成结果失败: {str(e)}")
            return {
                "total_count": len(results),
                "success_count": 0,
                "failed_count": len(results),
                "success_rate": 0,
                "error": str(e),
                "results": results
            }
    
    def format_result_summary(self, summary: Dict[str, Any]) -> str:
        """格式化结果摘要"""
        try:
            total = summary.get("total_count", 0)
            success = summary.get("success_count", 0)
            failed = summary.get("failed_count", 0)
            success_rate = summary.get("success_rate", 0)
            
            summary_text = f"处理完成\n"
            summary_text += f"总计: {total}\n"
            summary_text += f"成功: {success}\n"
            summary_text += f"失败: {failed}\n"
            summary_text += f"成功率: {success_rate:.1%}\n"
            
            if "saved_count" in summary:
                summary_text += f"保存结果文件: {summary['saved_count']}个\n"
            
            if "total_saved_images" in summary:
                summary_text += f"保存图片: {summary['total_saved_images']}张\n"
            
            if "error" in summary:
                summary_text += f"错误: {summary['error']}\n"
            
            return summary_text
            
        except Exception as e:
            self.logger.error(f"格式化结果摘要失败: {str(e)}")
            return "结果处理完成"
    
    def validate_image_file(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            image_path_obj = Path(image_path)
            
            # 检查文件是否存在
            if not image_path_obj.exists():
                self.logger.warning(f"图片文件不存在: {image_path}")
                return False
            
            # 检查文件扩展名
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            if image_path_obj.suffix.lower() not in valid_extensions:
                self.logger.warning(f"不支持的图片格式: {image_path}")
                return False
            
            # 尝试打开图片
            try:
                with Image.open(image_path) as img:
                    img.verify()
                return True
            except Exception as e:
                self.logger.warning(f"图片文件损坏: {image_path}, 错误: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"验证图片文件失败: {image_path}, 错误: {str(e)}")
            return False
    
    def get_image_files_from_directory(self, directory_path: str) -> List[str]:
        """从目录获取图片文件列表"""
        try:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                self.logger.error(f"目录不存在或不是目录: {directory_path}")
                return []
            
            # 支持的图片格式
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            
            image_files = []
            for file_path in directory.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                    image_files.append(str(file_path))
            
            self.logger.info(f"从目录找到{len(image_files)}个图片文件: {directory_path}")
            return image_files
            
        except Exception as e:
            self.logger.error(f"获取目录图片文件失败: {directory_path}, 错误: {str(e)}")
            return []
    
    def create_result_report(self, results: List[Dict[str, Any]], 
                           output_path: str) -> bool:
        """创建结果报告"""
        try:
            report_data = {
                "timestamp": str(Path.cwd()),
                "total_count": len(results),
                "success_count": sum(1 for r in results if r.get("success", False)),
                "failed_count": sum(1 for r in results if not r.get("success", False)),
                "results": results
            }
            
            report_path = Path(output_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"结果报告已保存: {report_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建结果报告失败: {str(e)}")
            return False
