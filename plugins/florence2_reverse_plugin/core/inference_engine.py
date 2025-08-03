"""
Florence2推理引擎
实现Florence2模型的图片反推功能
"""

import os
import torch
from typing import Dict, Any, List, Optional, Callable
import logging
from pathlib import Path
from PIL import Image
import numpy as np

# 导入transformers库
try:
    from transformers import AutoModelForCausalLM, AutoProcessor
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("transformers库未安装，推理功能将不可用")

logger = logging.getLogger(__name__)


class InferenceEngine:
    """Florence2推理引擎"""
    
    def __init__(self):
        self.config_manager = None
        self.model_manager = None
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.is_initialized = False
        self.device = None
        self.progress_callback = None
    
    def initialize(self, config_manager, model_manager) -> bool:
        """初始化推理引擎"""
        try:
            self.config_manager = config_manager
            self.model_manager = model_manager
            
            # 设置设备
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info("使用GPU进行推理")
            else:
                self.device = torch.device("cpu")
                logger.info("使用CPU进行推理")
            
            self.is_initialized = True
            logger.info("Florence2推理引擎初始化完成")
            return True
        except Exception as e:
            logger.error(f"推理引擎初始化失败: {str(e)}")
            return False
    
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _update_progress(self, step: str, progress: int, message: str):
        """更新进度"""
        if self.progress_callback:
            try:
                self.progress_callback(step, progress, message)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {str(e)}")
    
    def load_model(self, model_name: str) -> bool:
        """从ModelManager获取已加载的模型"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("transformers库未安装")
            
            self._update_progress("loading", 0, f"正在获取模型: {model_name}")
            
            # 检查模型是否已加载
            if not self.model_manager.is_model_loaded():
                raise RuntimeError("模型未加载，请先通过ModelManager加载模型")
            
            # 获取已加载的模型和处理器
            self.model = self.model_manager.model
            self.processor = self.model_manager.processor
            
            if self.model is None or self.processor is None:
                raise RuntimeError("模型或处理器未正确加载")
            
            self._update_progress("loading", 100, "模型获取完成")
            logger.info(f"Florence2模型获取成功: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"模型获取失败: {str(e)}")
            self._update_progress("loading", 0, f"模型获取失败: {str(e)}")
            return False
    
    def _preprocess_image(self, image_path: str) -> Optional[torch.Tensor]:
        """预处理图片"""
        try:
            # 加载图片
            image = Image.open(image_path).convert('RGB')
            
            # 对于Florence2模型，我们直接返回PIL图像，让_generate_description方法处理
            # 这样可以避免重复的processor调用导致的缓存问题
            return image
                
        except Exception as e:
            logger.error(f"图片预处理失败 {image_path}: {str(e)}")
            return None
    
    def _generate_prompt(self, description_level: str) -> str:
        """根据描述级别生成提示词 - 基于ComfyUI-Florence2的任务提示词"""
        prompts = {
            "simple": "<CAPTION>",  # 简单描述
            "normal": "<DETAILED_CAPTION>",  # 普通描述
            "detailed": "<MORE_DETAILED_CAPTION>"  # 详细描述
        }
        return prompts.get(description_level, prompts["normal"])
    
    def _generate_description(self, image_input, description_level: str) -> str:
        """生成图片描述"""
        try:
            # 检查是否为GIT模型
            is_git_model = hasattr(self.model, 'git') or 'git' in str(type(self.model)).lower()
            
            if is_git_model:
                # GIT模型使用不同的输入格式
                # 直接使用图片输入，不需要文本提示
                inputs = {
                    'pixel_values': image_input
                }
                
                # 获取推理配置
                inference_config = self.config_manager.get_inference_config()
                
                # 生成描述
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=inference_config.get("max_new_tokens", 50),
                        num_beams=inference_config.get("num_beams", 3),
                        do_sample=inference_config.get("do_sample", True),
                        temperature=inference_config.get("temperature", 0.7),
                        top_p=inference_config.get("top_p", 0.9),
                    )
                
                # 解码输出 - 使用processor的tokenizer
                if hasattr(self.processor, 'tokenizer'):
                    generated_text = self.processor.tokenizer.decode(
                        outputs[0],
                        skip_special_tokens=True
                    )
                else:
                    # 如果没有tokenizer，直接返回原始输出
                    generated_text = str(outputs[0])
                
                return generated_text.strip()
            else:
                # Florence2模型 - 使用AutoProcessor处理输入
                # 生成提示词
                prompt = self._generate_prompt(description_level)
                
                # 检查输入类型
                if isinstance(image_input, torch.Tensor):
                    # 如果是tensor，转换为PIL图像
                    from PIL import Image
                    import torchvision.transforms.functional as F
                    
                    if image_input.dim() == 4:
                        image_input = image_input.squeeze(0)
                    
                    # 确保数据类型正确
                    model_dtype = next(self.model.parameters()).dtype
                    image_input = image_input.to(self.device)
                    if model_dtype == torch.float16:
                        image_input = image_input.half()
                    else:
                        image_input = image_input.float()
                    
                    image_pil = F.to_pil_image(image_input)
                else:
                    # 如果已经是PIL图像，直接使用
                    image_pil = image_input
                
                # 使用processor处理输入 - 只处理一次，避免缓存问题
                inputs = self.processor(
                    text=prompt,
                    images=image_pil,
                    return_tensors="pt",
                    do_rescale=False
                )
                
                # 确保所有输入都使用正确的数据类型和设备
                model_dtype = next(self.model.parameters()).dtype
                inputs = {
                    'input_ids': inputs['input_ids'].to(self.device, dtype=torch.long),
                    'attention_mask': inputs['attention_mask'].to(self.device, dtype=torch.long),
                    'pixel_values': inputs['pixel_values'].to(self.device, dtype=model_dtype)
                }
                
                # 获取推理配置
                inference_config = self.config_manager.get_inference_config()
                
                # 生成描述 - 使用简化的generate方法
                with torch.no_grad():
                    # 确保input_ids不为None
                    if inputs['input_ids'] is None or inputs['input_ids'].numel() == 0:
                        # 如果没有input_ids，创建一个空的input_ids
                        inputs['input_ids'] = torch.zeros((1, 1), dtype=torch.long, device=self.device)
                        inputs['attention_mask'] = torch.ones((1, 1), dtype=torch.long, device=self.device)
                    
                    # 使用generate方法，使用原始工作参数
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=inference_config.get("max_new_tokens", 50),
                        do_sample=False,  # 使用贪婪解码
                        num_beams=1,  # 不使用beam search
                        pad_token_id=self.processor.tokenizer.eos_token_id if hasattr(self.processor, 'tokenizer') else None,
                        eos_token_id=self.processor.tokenizer.eos_token_id if hasattr(self.processor, 'tokenizer') else None,
                        use_cache=False,  # 禁用缓存避免问题
                    )
                
                # 解码输出
                if hasattr(self.processor, 'tokenizer'):
                    results = self.processor.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
                else:
                    results = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                # 清理特殊标记
                clean_results = str(results)
                clean_results = clean_results.replace('</s>', '')
                clean_results = clean_results.replace('<s>', '')
                
                return clean_results.strip()
            
        except Exception as e:
            logger.error(f"生成描述失败: {str(e)}")
            return f"描述生成失败: {str(e)}"
    
    def infer_images(self, image_paths: List[str], 
                    model_name: str,
                    description_level: str = "normal",
                    progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """推理图片"""
        try:
            if progress_callback:
                self.set_progress_callback(progress_callback)
            
            logger.info(f"开始推理图片 - 图片数量: {len(image_paths)}, 模型: {model_name}, 描述级别: {description_level}")
            
            # 加载模型
            if not self.load_model(model_name):
                raise RuntimeError("模型加载失败")
            
            results = []
            total_images = len(image_paths)
            
            for i, image_path in enumerate(image_paths):
                try:
                    self._update_progress("inference", int((i / total_images) * 100), f"正在处理: {Path(image_path).name}")
                    
                    # 预处理图片
                    image_tensor = self._preprocess_image(image_path)
                    if image_tensor is None:
                        results.append({
                            "image_path": image_path,
                            "success": False,
                            "error": "图片预处理失败",
                            "model_name": model_name,
                            "description_level": description_level
                        })
                        continue
                    
                    # 生成描述
                    description = self._generate_description(image_tensor, description_level)
                    
                    # 保存结果
                    result = {
                        "image_path": image_path,
                        "success": True,
                        "result": description,
                        "model_name": model_name,
                        "description_level": description_level,
                        "processed": True
                    }
                    results.append(result)
                    
                    logger.info(f"图片推理完成: {Path(image_path).name}")
                    
                except Exception as e:
                    logger.error(f"图片推理失败 {image_path}: {str(e)}")
                    results.append({
                        "image_path": image_path,
                        "success": False,
                        "error": str(e),
                        "model_name": model_name,
                        "description_level": description_level
                    })
            
            self._update_progress("inference", 100, "推理完成")
            logger.info(f"推理完成 - 成功: {sum(1 for r in results if r['success'])}, 失败: {sum(1 for r in results if not r['success'])}")
            return results
            
        except Exception as e:
            logger.error(f"推理失败: {str(e)}")
            return []
    
    def shutdown(self) -> bool:
        """关闭推理引擎"""
        try:
            # 清理模型
            if self.model:
                del self.model
                self.model = None
            
            if self.processor:
                del self.processor
                self.processor = None
            
            if self.tokenizer:
                del self.tokenizer
                self.tokenizer = None
            
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.is_initialized = False
            logger.info("Florence2推理引擎关闭完成")
            return True
        except Exception as e:
            logger.error(f"推理引擎关闭失败: {str(e)}")
            return False 