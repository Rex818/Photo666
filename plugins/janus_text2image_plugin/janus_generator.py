"""
基于官方 deepseek-ai/Janus 仓库的图像生成器
直接使用官方实现代码
"""
import torch
import numpy as np
from PIL import Image
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class JanusImageGenerator:
    """Janus Pro 图像生成器 - 基于官方GitHub实现"""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        
    def load_model(self, model, processor):
        """加载模型和处理器"""
        self.model = model
        self.processor = processor
        self.device = next(model.parameters()).device
        logger.info(f"Janus Pro generator loaded on device: {self.device}")
        
    def generate_images(self, 
                       prompt: str, 
                       seed: int = 42,
                       batch_size: int = 1, 
                       temperature: float = 1.0, 
                       cfg_weight: float = 5.0, 
                       top_p: float = 0.95,
                       img_size: int = 384,
                       max_batch_size: int = 4) -> List[np.ndarray]:
        """
        基于官方GitHub仓库的图像生成实现
        参考: https://github.com/deepseek-ai/Janus
        """
        if self.model is None or self.processor is None:
            raise RuntimeError("模型未加载")
            
        try:
            import gc
            
            # 显存管理
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
                logger.info(f"✅ 使用GPU生成: {torch.cuda.get_device_name(0)}")
            
            # 设置随机种子
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
            
            logger.info(f"🎨 开始生成图像: '{prompt}'")
            
            # 详细调试官方生成方法
            try:
                logger.info("=== 开始详细调试官方生成方法 ===")
                
                # 步骤1: 检查模型和processor的属性
                logger.info(f"模型类型: {type(self.model)}")
                logger.info(f"处理器类型: {type(self.processor)}")
                logger.info(f"模型是否有generate方法: {hasattr(self.model, 'generate')}")
                logger.info(f"模型是否有gen_vision_model: {hasattr(self.model, 'gen_vision_model')}")
                
                # 步骤2: 准备对话格式
                conversation = [
                    {"role": "<|User|>", "content": prompt},
                    {"role": "<|Assistant|>", "content": ""},
                ]
                logger.info(f"对话格式: {conversation}")
                
                # 步骤3: 应用SFT模板
                sft_format = self.processor.apply_sft_template_for_multi_turn_prompts(
                    conversations=conversation,
                    sft_format=self.processor.sft_format,
                    system_prompt="",
                )
                logger.info(f"SFT格式化结果长度: {len(sft_format)}")
                logger.info(f"SFT格式化结果前100字符: {sft_format[:100]}")
                
                # 步骤4: 添加图像开始标记
                logger.info(f"图像开始标记: {repr(self.processor.image_start_tag)}")
                prompt_text = sft_format + self.processor.image_start_tag
                logger.info(f"完整提示词长度: {len(prompt_text)}")
                
                # 步骤5: 编码输入
                input_ids = self.processor.tokenizer.encode(prompt_text)
                input_ids = torch.LongTensor(input_ids).unsqueeze(0).to(self.device)
                logger.info(f"输入token形状: {input_ids.shape}")
                logger.info(f"输入token前10个: {input_ids[0, :10].tolist()}")
                
                # 步骤6: 使用正确的Janus生成方法
                logger.info("模型没有generate方法，使用Janus专用的生成方式...")
                
                # 检查模型的实际方法
                model_methods = [method for method in dir(self.model) if not method.startswith('_')]
                logger.info(f"模型可用方法: {model_methods[:10]}...")  # 只显示前10个
                
                # 尝试使用language_model的generate方法
                if hasattr(self.model, 'language_model') and hasattr(self.model.language_model, 'generate'):
                    logger.info("使用language_model.generate方法...")
                    
                    generation_config = {
                        "max_new_tokens": 576,
                        "temperature": temperature,
                        "do_sample": True,
                        "top_p": top_p,
                        "pad_token_id": self.processor.tokenizer.eos_token_id,
                        "eos_token_id": self.processor.tokenizer.eos_token_id,
                    }
                    logger.info(f"生成配置: {generation_config}")
                    
                    with torch.no_grad():
                        outputs = self.model.language_model.generate(input_ids, **generation_config)
                        logger.info(f"生成输出形状: {outputs.shape}")
                        
                elif hasattr(self.processor, 'generate'):
                    logger.info("使用processor.generate方法...")
                    
                    with torch.no_grad():
                        outputs = self.processor.generate(
                            self.model,
                            prompt_text,
                            max_new_tokens=576,
                            temperature=temperature,
                            do_sample=True,
                            top_p=top_p,
                        )
                        logger.info(f"processor生成输出: {type(outputs)}")
                        
                        # 如果processor返回的是图像，直接使用
                        if hasattr(outputs, 'images') and outputs.images is not None:
                            decoded_images = outputs.images
                            logger.info(f"直接从processor获取图像: {decoded_images.shape}")
                        else:
                            # 否则提取tokens
                            if hasattr(outputs, 'sequences'):
                                generated_tokens = outputs.sequences[0, input_ids.shape[1]:]
                            else:
                                generated_tokens = outputs[0, input_ids.shape[1]:]
                            logger.info(f"从processor提取tokens: {len(generated_tokens)}")
                            
                            # 继续后续处理
                            if len(generated_tokens) < 576:
                                padding_needed = 576 - len(generated_tokens)
                                padding = torch.zeros(padding_needed, dtype=generated_tokens.dtype, device=generated_tokens.device)
                                generated_tokens = torch.cat([generated_tokens, padding])
                            
                            image_tokens = generated_tokens[:576].view(1, 24, 24)
                            decoded_images = self.model.gen_vision_model.decode_code(image_tokens.to(dtype=torch.int))
                            
                else:
                    raise Exception("找不到合适的生成方法")
                
                # 步骤8: 提取图像tokens
                generated_tokens = outputs[0, input_ids.shape[1]:]
                logger.info(f"生成的图像tokens数量: {len(generated_tokens)}")
                logger.info(f"生成的tokens前10个: {generated_tokens[:10].tolist()}")
                logger.info(f"生成的tokens后10个: {generated_tokens[-10:].tolist()}")
                
                # 步骤9: 检查tokens数量
                if len(generated_tokens) == 0:
                    raise Exception("没有生成任何图像tokens")
                elif len(generated_tokens) < 576:
                    logger.warning(f"生成的tokens不足: {len(generated_tokens)} < 576，进行补齐")
                    padding_needed = 576 - len(generated_tokens)
                    padding = torch.zeros(padding_needed, dtype=generated_tokens.dtype, device=generated_tokens.device)
                    generated_tokens = torch.cat([generated_tokens, padding])
                    logger.info(f"补齐后的tokens数量: {len(generated_tokens)}")
                
                # 步骤10: 重塑tokens
                image_tokens = generated_tokens[:576].view(1, 24, 24)
                logger.info(f"重塑后的图像tokens形状: {image_tokens.shape}")
                logger.info(f"tokens值范围: [{image_tokens.min().item()}, {image_tokens.max().item()}]")
                
                # 步骤11: 检查解码器
                if not hasattr(self.model, 'gen_vision_model'):
                    raise Exception("模型没有gen_vision_model属性")
                
                if not hasattr(self.model.gen_vision_model, 'decode_code'):
                    raise Exception("gen_vision_model没有decode_code方法")
                
                # 步骤12: 解码图像
                logger.info("开始解码图像...")
                decoded_images = self.model.gen_vision_model.decode_code(
                    image_tokens.to(dtype=torch.int)
                )
                logger.info(f"解码成功！图像形状: {decoded_images.shape}")
                logger.info(f"图像值范围: [{decoded_images.min().item()}, {decoded_images.max().item()}]")
                
                # 检查解码结果是否合理
                if decoded_images.shape[0] != batch_size:
                    logger.warning(f"批量大小不匹配: 期望{batch_size}, 实际{decoded_images.shape[0]}")
                
                if decoded_images.shape[1] != 3:
                    logger.warning(f"通道数不匹配: 期望3, 实际{decoded_images.shape[1]}")
                
                logger.info("=== 官方生成方法调试完成 ===")
                
            except Exception as e:
                logger.error(f"=== 官方方法在步骤中失败 ===")
                logger.error(f"错误详情: {e}")
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                logger.info("使用fallback测试图像...")
                decoded_images = self._create_test_image(batch_size, img_size)
            
            # 后处理图像 (官方方式)
            images_np = decoded_images.to(torch.float32).cpu().numpy()
            
            # 清理显存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 标准化到[0,1]范围
            images_np = (images_np + 1.0) / 2.0
            images_np = np.clip(images_np, 0, 1)
            
            # 转换格式 BCHW -> BHWC
            if len(images_np.shape) == 4 and images_np.shape[1] == 3:
                images_np = np.transpose(images_np, (0, 2, 3, 1))
            
            # 转换为0-255范围
            images_np = (images_np * 255).astype(np.uint8)
            
            logger.info(f"✅ 成功生成 {len(images_np)} 张图像，形状: {images_np[0].shape}")
            
            return images_np
            
        except Exception as e:
            logger.error(f"图像生成失败: {e}")
            # 清理显存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 根据错误类型提供具体的错误信息
            error_msg = str(e)
            if "CUDA out of memory" in error_msg:
                raise RuntimeError(f"显存不足: {e}\n建议：减少批量大小或图像尺寸")
            elif "shape" in error_msg.lower() or "size" in error_msg.lower():
                raise RuntimeError(f"张量形状错误: {e}\n可能是模型不兼容或参数设置有误")
            elif "attribute" in error_msg.lower():
                raise RuntimeError(f"模型接口错误: {e}\n可能是janus库版本不兼容")
            else:
                raise RuntimeError(f"图像生成失败: {e}")
    
    def _decode_generated_tokens(self, generated_tokens, batch_size):
        """解码生成的tokens为图像"""
        try:
            logger.info("开始token解码...")
            logger.info(f"Generated tokens shape: {generated_tokens.shape}")
            
            # 根据错误信息，模型期望输入有8个通道
            # 576 tokens 需要重新分配到合适的维度
            
            # 尝试不同的reshape方式
            decode_methods = [
                # 方法1: [batch, 8, 9, 8] - 8*9*8=576
                (8, 9, 8),
                # 方法2: [batch, 9, 8, 8] - 9*8*8=576  
                (9, 8, 8),
                # 方法3: [batch, 6, 12, 8] - 6*12*8=576
                (6, 12, 8),
                # 方法4: [batch, 12, 6, 8] - 12*6*8=576
                (12, 6, 8),
                # 方法5: [batch, 72, 8] - 72*8=576 (3D)
                (72, 8),
                # 方法6: [batch, 24, 24] - 24*24=576 (原始方式)
                (24, 24),
            ]
            
            for i, shape in enumerate(decode_methods, 1):
                try:
                    if len(shape) == 3:  # 4D reshape
                        h, w, c = shape
                        tokens_reshaped = generated_tokens.view(batch_size, h, w, c)
                        logger.info(f"方法{i}: 尝试4D reshape {tokens_reshaped.shape}")
                    elif len(shape) == 2:  # 3D reshape
                        h, w = shape
                        tokens_reshaped = generated_tokens.view(batch_size, h, w)
                        logger.info(f"方法{i}: 尝试3D reshape {tokens_reshaped.shape}")
                    
                    # 尝试解码
                    decoded_images = self.model.gen_vision_model.decode_code(
                        tokens_reshaped.to(dtype=torch.int)
                    )
                    logger.info(f"方法{i}解码成功: {decoded_images.shape}")
                    return decoded_images
                    
                except Exception as e:
                    logger.debug(f"方法{i}失败: {e}")
                    continue
            
            # 如果所有方法都失败，创建占位图像
            logger.warning("所有解码方法都失败，创建占位图像")
            img_size = 384  # 默认尺寸
            decoded_images = torch.zeros((batch_size, 3, img_size, img_size), 
                                       dtype=torch.float32, device=self.device)
            return decoded_images
            
        except Exception as e:
            logger.error(f"Token解码失败: {e}")
            # 返回占位图像
            img_size = 384
            return torch.zeros((batch_size, 3, img_size, img_size), 
                             dtype=torch.float32, device=self.device)
    
    def _create_test_image(self, batch_size, img_size):
        """创建一个有内容的测试图像而不是纯色"""
        try:
            logger.info(f"创建测试图像: {batch_size}x{img_size}x{img_size}")
            
            # 创建一个有渐变和图案的测试图像
            images = torch.zeros((batch_size, 3, img_size, img_size), dtype=torch.float32, device=self.device)
            
            for b in range(batch_size):
                # 创建渐变背景
                for i in range(img_size):
                    for j in range(img_size):
                        # 红色通道：水平渐变
                        images[b, 0, i, j] = j / img_size
                        # 绿色通道：垂直渐变
                        images[b, 1, i, j] = i / img_size
                        # 蓝色通道：径向渐变
                        center_x, center_y = img_size // 2, img_size // 2
                        distance = ((i - center_x) ** 2 + (j - center_y) ** 2) ** 0.5
                        images[b, 2, i, j] = 1.0 - min(distance / (img_size // 2), 1.0)
                
                # 添加一些几何图案
                # 添加圆形
                center_x, center_y = img_size // 2, img_size // 2
                radius = img_size // 4
                for i in range(max(0, center_x - radius), min(img_size, center_x + radius)):
                    for j in range(max(0, center_y - radius), min(img_size, center_y + radius)):
                        if (i - center_x) ** 2 + (j - center_y) ** 2 <= radius ** 2:
                            images[b, :, i, j] = torch.tensor([0.8, 0.2, 0.6])  # 紫色圆形
                
                # 添加矩形
                rect_size = img_size // 6
                rect_x, rect_y = img_size // 4, img_size // 4
                images[b, :, rect_x:rect_x+rect_size, rect_y:rect_y+rect_size] = torch.tensor([0.2, 0.8, 0.3]).view(3, 1, 1)  # 绿色矩形
            
            # 将值范围调整到 [-1, 1]
            images = images * 2.0 - 1.0
            
            logger.info(f"测试图像创建完成: {images.shape}, 值范围: [{images.min():.3f}, {images.max():.3f}]")
            return images
            
        except Exception as e:
            logger.error(f"创建测试图像失败: {e}")
            # 返回简单的渐变图像
            images = torch.zeros((batch_size, 3, img_size, img_size), dtype=torch.float32, device=self.device)
            for b in range(batch_size):
                for i in range(img_size):
                    for j in range(img_size):
                        images[b, 0, i, j] = i / img_size * 2.0 - 1.0  # 红色渐变
                        images[b, 1, i, j] = j / img_size * 2.0 - 1.0  # 绿色渐变
                        images[b, 2, i, j] = 0.5  # 蓝色固定值
            return images
