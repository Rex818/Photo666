"""
Janus插件推理引擎
"""

import logging
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from .model_manager import ModelManager

# 尝试导入Janus库
try:
    from transformers import AutoModelForCausalLM
    
    # 尝试从本地janus_official模块导入
    import sys
    import os
    plugin_dir = Path(os.path.dirname(os.path.dirname(__file__)))
    janus_official_path = plugin_dir.parent / "janus_text2image_plugin" / "janus_official"
    
    if janus_official_path.exists():
        # 将janus_official路径添加到sys.path
        sys.path.insert(0, str(janus_official_path))
        try:
            from models import VLChatProcessor
            JANUS_AVAILABLE = True
            logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine").info("Janus库从本地模块导入成功")
        except ImportError as e1:
            # 如果直接导入失败，尝试从janus命名空间导入
            try:
                # 重新添加路径并尝试导入
                sys.path.insert(0, str(janus_official_path))
                from janus_official import janus
                VLChatProcessor = janus.models.VLChatProcessor
                JANUS_AVAILABLE = True
                logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine").info("Janus库从janus命名空间导入成功")
            except ImportError as e2:
                JANUS_AVAILABLE = False
                logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine").warning(f"本地Janus模块导入失败: {e1}, {e2}")
    else:
        JANUS_AVAILABLE = False
        logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine").warning(f"本地Janus模块路径不存在: {janus_official_path}")
        
except ImportError as e:
    JANUS_AVAILABLE = False
    logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine").warning(f"Janus库导入失败: {e}")


class InferenceEngine:
    """Janus插件推理引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger("plugins.janus_reverse_plugin.core.inference_engine")
        self.model_manager = None
        self.config_manager = None
        
        # 推理状态
        self.is_initialized = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Janus库可用性
        self.JANUS_AVAILABLE = JANUS_AVAILABLE
        
        self.logger.info("Janus推理引擎初始化完成")
    
    def initialize(self, config_manager, model_manager):
        """初始化推理引擎"""
        try:
            self.config_manager = config_manager
            self.model_manager = model_manager
            self.is_initialized = True
            
            self.logger.info(f"使用{self.device}进行推理")
            return True
            
        except Exception as e:
            self.logger.error(f"推理引擎初始化失败: {str(e)}")
            return False
    
    def reverse_inference(self, image_path: str, question: str, 
                         temperature: float = 0.1, top_p: float = 0.95,
                         max_new_tokens: int = 512, seed: int = 666666666666666,
                         progress_callback: Optional[Callable] = None) -> Optional[str]:
        """图片反推推理"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法执行推理")
            return "Janus库不可用，请先安装Janus库"
        try:
            # 基础校验
            if not self.model_manager or not self.model_manager.is_model_ready():
                self.logger.error("模型未加载")
                return None
            if not image_path or not Path(image_path).exists():
                self.logger.error(f"图片不存在: {image_path}")
                return None

            # 设备与随机种子
            device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                torch.manual_seed(int(seed))
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(int(seed))
            except Exception:
                pass

            model = self.model_manager.current_model
            processor = self.model_manager.current_processor
            if model is None or processor is None:
                self.logger.error("模型或处理器为空")
                return None

            if progress_callback:
                progress_callback("preparing", 5, "加载图片...")

            # 读取并规范化图像
            pil_image = Image.open(image_path).convert("RGB")

            # 构造对话
            conversation = [
                {
                    "role": "<|User|>",
                    "content": f"<image_placeholder>\n{question}",
                    "images": [pil_image],
                },
                {"role": "<|Assistant|>", "content": ""},
            ]

            if progress_callback:
                progress_callback("preparing", 20, "准备输入...")

            # 准备输入（参考ComfyUI实现）
            prepare_inputs = processor(
                conversations=conversation,
                images=[pil_image],
                force_batchify=True
            )

            # 将张量移动到模型设备
            try:
                model_device = next(model.parameters()).device
            except Exception:
                model_device = torch.device(device)
            prepare_inputs = prepare_inputs.to(model_device)

            # 工具: 递归转换dtype
            def _to_dtype(obj, dtype):
                try:
                    import torch as _t
                    if isinstance(obj, _t.Tensor):
                        return obj.to(dtype=dtype)
                    if isinstance(obj, (list, tuple)):
                        t = [ _to_dtype(x, dtype) for x in obj ]
                        return type(obj)(t)
                    if isinstance(obj, dict):
                        return {k: _to_dtype(v, dtype) for k, v in obj.items()}
                    return obj
                except Exception:
                    return obj

            # 准备embedding
            with torch.no_grad():
                inputs_embeds = model.prepare_inputs_embeds(**prepare_inputs)

                # 确保输入dtype与模型权重dtype一致，避免 Half vs BFloat16 冲突
                try:
                    expected_dtype = next(model.parameters()).dtype
                    inputs_embeds = _to_dtype(inputs_embeds, expected_dtype)
                except Exception:
                    pass

                if progress_callback:
                    progress_callback("generating", 40, "生成文本...")

                # 选择生成入口：部分实现在 model.language_model 上
                lm = getattr(model, "language_model", None)
                generate_fn = lm.generate if lm is not None else getattr(model, "generate")

                outputs = generate_fn(
                    inputs_embeds=inputs_embeds,
                    attention_mask=prepare_inputs.attention_mask,
                    pad_token_id=processor.tokenizer.eos_token_id,
                    bos_token_id=getattr(processor.tokenizer, "bos_token_id", None),
                    eos_token_id=processor.tokenizer.eos_token_id,
                    max_new_tokens=int(max_new_tokens),
                    do_sample=True,
                    temperature=float(temperature),
                    top_p=float(top_p),
                    use_cache=True,
                )

                if progress_callback:
                    progress_callback("decoding", 80, "解码结果...")

                # 有些实现返回张量，有些返回序列
                if isinstance(outputs, torch.Tensor):
                    token_ids = outputs[0].detach().cpu().tolist()
                else:
                    token_ids = list(outputs[0])

                answer = processor.tokenizer.decode(token_ids, skip_special_tokens=True)

            if progress_callback:
                progress_callback("done", 100, "完成")

            return answer

        except Exception as e:
            self.logger.error(f"反推推理失败: {str(e)}")
            return None
    
    def generate_image(self, prompt: str, seed: int = 666666666666666,
                      batch_size: int = 1, cfg_weight: float = 5.0,
                      temperature: float = 1.0, top_p: float = 0.95,
                      image_size: int = 384, progress_callback: Optional[Callable] = None) -> Optional[List[Image.Image]]:
        """生成图片"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法生成图片")
            return None
        return None
    
    def batch_reverse_inference(self, image_paths: List[str], question: str,
                              temperature: float = 0.1, top_p: float = 0.95,
                              max_new_tokens: int = 512, seed: int = 666666666666666,
                              progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量图片反推推理"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法执行批量推理")
            return [{"error": "Janus库不可用，请先安装Janus库"}]
        results: List[Dict[str, Any]] = []
        total = len(image_paths)
        for idx, path in enumerate(image_paths):
            if progress_callback:
                pct = int((idx / max(1, total)) * 100)
                progress_callback("processing", pct, f"处理: {Path(path).name}")
            text = self.reverse_inference(
                image_path=path,
                question=question,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                seed=seed,
                progress_callback=progress_callback,
            )
            results.append({
                "image_path": path,
                "result": text,
                "success": text is not None
            })
        if progress_callback:
            progress_callback("done", 100, "批量完成")
        return results
    
    def batch_generate_images(self, prompts: List[str], seed: int = 666666666666666,
                            batch_size: int = 1, cfg_weight: float = 5.0,
                            temperature: float = 1.0, top_p: float = 0.95,
                            image_size: int = 384, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量生成图片"""
        if not self.JANUS_AVAILABLE:
            self.logger.warning("Janus库不可用，无法执行批量图片生成")
            return [{"error": "Janus库不可用，请先安装Janus库"}]
        return []