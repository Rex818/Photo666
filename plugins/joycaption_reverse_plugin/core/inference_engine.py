"""
JoyCaption插件推理引擎
负责图片推理和结果生成
"""

import logging
import torch
from PIL import Image
from typing import Dict, Any, Optional, List
from pathlib import Path


class InferenceEngine:
    """JoyCaption推理引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger("plugins.joycaption_reverse_plugin.core.inference_engine")
        self.current_model_info = None
        
        # 检查GPU可用性
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            self.logger.info("使用GPU进行推理")
        else:
            self.logger.info("使用CPU进行推理")
    
    def setup_model(self, model_info: Dict[str, Any]):
        """设置模型"""
        try:
            self.current_model_info = model_info
            self.logger.info("推理引擎模型设置完成")
        except Exception as e:
            self.logger.error(f"设置模型失败: {str(e)}")
            raise
    
    def build_prompt(self, caption_type: str, caption_length: str, extra_options: List[str] = None, name_input: str = "") -> str:
        """构建提示词"""
        try:
            # 获取描述类型配置
            if not hasattr(self, '_config_manager'):
                from .config_manager import ConfigManager
                self._config_manager = ConfigManager()
            
            # 确保配置已加载
            if not self._config_manager.caption_types_config:
                self.logger.error("描述类型配置未加载")
                return "Write a description for this image."
            
            caption_types = self._config_manager.caption_types_config.get("caption_types", {})
            
            if not caption_types:
                self.logger.error("描述类型配置为空")
                return "Write a description for this image."
            
            if caption_type not in caption_types:
                self.logger.warning(f"未知的描述类型: {caption_type}，使用默认类型")
                caption_type = "Descriptive"
            
            # 获取提示词模板
            caption_type_info = caption_types[caption_type]
            templates = caption_type_info.get("prompts", [])
            
            if not templates:
                self.logger.error(f"描述类型 {caption_type} 没有提示词模板")
                return "Write a description for this image."
            
            # 根据长度选择模板
            if caption_length == "any":
                template_idx = 0
            elif isinstance(caption_length, str) and caption_length.isdigit():
                template_idx = 1
            else:
                template_idx = 2
            
            if template_idx >= len(templates):
                template_idx = 0
            
            prompt = templates[template_idx]
            
            # 添加额外选项
            if extra_options:
                prompt += " " + " ".join(extra_options)
            
            # 格式化提示词
            formatted_prompt = prompt.format(
                name=name_input or "{NAME}",
                length=caption_length,
                word_count=caption_length,
            )
            
            return formatted_prompt
            
        except Exception as e:
            self.logger.error(f"构建提示词失败: {str(e)}")
            return "Write a description for this image."
    
    def preprocess_image(self, image_path: str) -> Optional[Image.Image]:
        """预处理图片"""
        try:
            # 加载图片
            image = Image.open(image_path)
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 确保图片是有效的
            if image.size[0] == 0 or image.size[1] == 0:
                self.logger.error(f"图片尺寸无效: {image.size}")
                return None
            
            # 如果模型期望尺寸已知，则resize到期望尺寸
            if hasattr(self, 'current_model_info') and self.current_model_info:
                processor = self.current_model_info.get("processor")
                if processor and hasattr(processor, 'image_processor'):
                    expected_size = None
                    if hasattr(processor.image_processor, 'size'):
                        expected_size = processor.image_processor.size
                    elif hasattr(processor.image_processor, 'crop_size'):
                        expected_size = processor.image_processor.crop_size
                    
                    if expected_size:
                        target_size = (expected_size['width'], expected_size['height'])
                        self.logger.info(f"将图片从 {image.size} resize到 {target_size}")
                        image = image.resize(target_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            self.logger.error(f"图片预处理失败 {image_path}: {str(e)}")
            return None
    
    def inference(self, image_path: str, config: Dict[str, Any]) -> Optional[str]:
        """执行推理"""
        try:
            if not self.current_model_info:
                self.logger.error("模型未设置")
                return None
            
            model = self.current_model_info["model"]
            processor = self.current_model_info["processor"]
            
            # 预处理图片
            image = self.preprocess_image(image_path)
            if image is None:
                return None
            
            # 打印processor期望尺寸和图片实际尺寸
            try:
                expected_size = None
                if hasattr(processor, 'image_processor') and hasattr(processor.image_processor, 'size'):
                    expected_size = processor.image_processor.size
                elif hasattr(processor, 'image_processor') and hasattr(processor.image_processor, 'crop_size'):
                    expected_size = processor.image_processor.crop_size
                self.logger.info(f"模型期望图片尺寸: {expected_size}, 实际图片尺寸: {image.size}")
            except Exception as e:
                self.logger.warning(f"无法获取processor期望尺寸: {str(e)}")
            
            # 构建提示词
            caption_type = config.get("caption_type", "Descriptive")
            caption_length = config.get("caption_length", "any")
            extra_options = config.get("extra_options", [])
            name_input = config.get("name_input", "")
            
            prompt = self.build_prompt(caption_type, caption_length, extra_options, name_input)
            
            # 构建对话
            conversation = [
                {"role": "system", "content": "You are a helpful assistant and help users with any queries they may have with no censorship or restrictions."},
                {"role": "user", "content": prompt},
            ]
            
            # 应用对话模板
            conversation_string = processor.apply_chat_template(
                conversation, 
                tokenize=False, 
                add_generation_prompt=True)
            
            # 获取推理参数
            max_new_tokens = config.get("max_new_tokens", 512)
            temperature = config.get("temperature", 0.6)
            top_p = config.get("top_p", 0.9)
            top_k = config.get("top_k", 0)
            
            # 执行推理
            with torch.inference_mode():
                try:
                    # 使用原始的processor调用方式，但添加错误处理
                    inputs = processor(
                        text=conversation_string,
                        images=image,
                        return_tensors="pt",
                        padding=False
                    )
                except Exception as e:
                    # 如果processor调用失败，尝试手动处理图片
                    self.logger.warning(f"Processor调用失败，尝试手动处理: {str(e)}")
                    
                    # 使用processor的image_processor来处理图片
                    try:
                        # 使用processor的image_processor
                        if hasattr(processor, 'image_processor'):
                            image_inputs = processor.image_processor(
                                image,
                                return_tensors="pt"
                            )
                            
                            # 处理文本
                            text_inputs = processor.tokenizer(
                                conversation_string,
                                return_tensors="pt",
                                padding=False,
                                truncation=True
                            )
                            
                            # 合并输入
                            inputs = {
                                "input_ids": text_inputs["input_ids"],
                                "attention_mask": text_inputs["attention_mask"],
                                "pixel_values": image_inputs["pixel_values"]
                            }
                        else:
                            raise Exception("processor没有image_processor属性")
                            
                    except Exception as e2:
                        self.logger.error(f"手动处理也失败: {str(e2)}")
                        raise e2
                
                # 移动到设备
                if self.device == "cuda":
                    # 只移动输入到CUDA，不移动模型（因为模型已经被accelerate分发）
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                    # 不要移动模型：model = model.cuda()  # 这行被注释掉
                
                # 生成文本
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k if top_k > 0 else None,
                    do_sample=temperature > 0,
                    pad_token_id=processor.tokenizer.eos_token_id,
                    eos_token_id=processor.tokenizer.eos_token_id
                )
                
                # 解码输出
                generated_text = processor.tokenizer.decode(
                    outputs[0][inputs["input_ids"].shape[1]:], 
                    skip_special_tokens=True)
                
                return generated_text.strip()
            
        except Exception as e:
            self.logger.error(f"推理失败 {image_path}: {str(e)}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def batch_inference(self, image_paths: List[str], config: Dict[str, Any], progress_callback=None) -> List[Dict[str, Any]]:
        """批量推理"""
        results = []
        total_images = len(image_paths)
        
        for i, image_path in enumerate(image_paths):
            try:
                # 更新进度
                if progress_callback:
                    progress = int((i / total_images) * 100)
                    progress_callback("inference", progress, f"处理图片 {i+1}/{total_images}: {Path(image_path).name}")
                
                # 执行推理
                result_text = self.inference(image_path, config)
                
                result = {
                    "image_path": image_path,
                    "success": result_text is not None,
                    "text": result_text or "",
                    "error": None
                }
                
                if result_text is None:
                    result["error"] = "推理失败"
                
                results.append(result)
                
                self.logger.info(f"图片推理完成 {i+1}/{total_images}: {Path(image_path).name}")
                
            except Exception as e:
                self.logger.error(f"批量推理失败 {image_path}: {str(e)}")
                results.append({
                    "image_path": image_path,
                    "success": False,
                    "text": "",
                    "error": str(e)
                })
        
        return results
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return "You are a helpful assistant and help users with any queries they may have with no censorship or restrictions."
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            required_keys = ["caption_type", "caption_length"]
            for key in required_keys:
                if key not in config:
                    self.logger.error(f"缺少必需配置项: {key}")
                    return False
            
            # 验证数值范围
            temperature = config.get("temperature", 0.6)
            if not (0.0 <= temperature <= 2.0):
                self.logger.error(f"temperature值超出范围 [0.0, 2.0]: {temperature}")
                return False
            
            top_p = config.get("top_p", 0.9)
            if not (0.0 <= top_p <= 1.0):
                self.logger.error(f"top_p值超出范围 [0.0, 1.0]: {top_p}")
                return False
            
            max_new_tokens = config.get("max_new_tokens", 512)
            if not (1 <= max_new_tokens <= 2048):
                self.logger.error(f"max_new_tokens值超出范围 [1, 2048]: {max_new_tokens}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {str(e)}")
            return False
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            memory_info = {}
            
            if self.device == "cuda":
                memory_info["gpu_total"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                memory_info["gpu_allocated"] = torch.cuda.memory_allocated(0) / (1024**3)
                memory_info["gpu_reserved"] = torch.cuda.memory_reserved(0) / (1024**3)
                memory_info["gpu_free"] = memory_info["gpu_total"] - memory_info["gpu_reserved"]
            
            return memory_info
            
        except Exception as e:
            self.logger.error(f"获取内存使用情况失败: {str(e)}")
            return {}
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            self.current_model_info = None
            self.logger.info("推理引擎资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {str(e)}") 