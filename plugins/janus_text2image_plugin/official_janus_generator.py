# 基于官方Janus实现的生图器
# 参考：https://github.com/deepseek-ai/Janus

import torch
import numpy as np
import os
import PIL.Image
from transformers import AutoModelForCausalLM
import sys
import logging

# 添加本地Janus模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'janus_official'))

try:
    from janus.models import MultiModalityCausalLM, VLChatProcessor
except ImportError as e:
    logging.error(f"无法导入Janus模块: {e}")
    logging.error("请确保Janus官方代码已复制到 janus_official 目录下")
    raise

class OfficialJanusGenerator:
    def __init__(self, model_path="deepseek-ai/Janus-1.3B", device="cuda"):
        self.model_path = model_path
        self.device = device
        self.vl_chat_processor = None
        self.vl_gpt = None
        self.tokenizer = None
        
    def load_model(self):
        """加载模型"""
        try:
            print(f"正在加载Janus模型: {self.model_path}")
            
            # 设置环境变量强制禁用FlashAttention
            import os
            os.environ["DISABLE_FLASH_ATTN"] = "1"
            os.environ["FLASH_ATTENTION_FORCE_DISABLE"] = "1"
            os.environ["TRANSFORMERS_FORCE_EAGER_ATTENTION"] = "1"
            
            # 加载处理器
            self.vl_chat_processor = VLChatProcessor.from_pretrained(self.model_path)
            self.tokenizer = self.vl_chat_processor.tokenizer
            
            # 加载配置并修改
            from transformers import AutoConfig
            config = AutoConfig.from_pretrained(self.model_path, trust_remote_code=True)
            
            # 强制设置为eager attention
            if hasattr(config, 'language_config'):
                config.language_config._attn_implementation = "eager"
                if hasattr(config.language_config, 'use_flash_attention_2'):
                    config.language_config.use_flash_attention_2 = False
                # 移除所有FlashAttention相关属性
                for attr in ['_flash_attn_2_enabled', 'flash_attn', 'use_flash_attn']:
                    if hasattr(config.language_config, attr):
                        delattr(config.language_config, attr)
            
            # 加载模型 - 使用修改后的配置
            self.vl_gpt = AutoModelForCausalLM.from_pretrained(
                self.model_path, 
                config=config,
                trust_remote_code=True,
                attn_implementation="eager"
            )
            
            # 转换数据类型并移动到设备
            self.vl_gpt = self.vl_gpt.to(torch.bfloat16)
            
            # 移动到GPU
            if torch.cuda.is_available() and self.device == "cuda":
                self.vl_gpt = self.vl_gpt.cuda()
            
            self.vl_gpt = self.vl_gpt.eval()
            
            print("模型加载完成")
            return True
            
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
    
    @torch.inference_mode()
    def generate_image(
        self,
        prompt: str,
        temperature: float = 1.0,
        parallel_size: int = 4,  # 减少并行数量以节省显存
        cfg_weight: float = 5.0,
        image_token_num_per_image: int = 576,
        img_size: int = 384,
        patch_size: int = 16,
        output_dir: str = "output"
    ):
        """生成图像"""
        if self.vl_gpt is None or self.vl_chat_processor is None:
            raise RuntimeError("模型未加载，请先调用load_model()")
        
        try:
            # 构建对话格式
            conversation = [
                {
                    "role": "User",
                    "content": prompt,
                },
                {"role": "Assistant", "content": ""},
            ]
            
            # 应用SFT模板
            sft_format = self.vl_chat_processor.apply_sft_template_for_multi_turn_prompts(
                conversations=conversation,
                sft_format=self.vl_chat_processor.sft_format,
                system_prompt="",
            )
            
            # 添加图像开始标签
            full_prompt = sft_format + self.vl_chat_processor.image_start_tag
            
            print(f"生成提示词: {full_prompt}")
            
            # 编码输入
            input_ids = self.vl_chat_processor.tokenizer.encode(full_prompt)
            input_ids = torch.LongTensor(input_ids)
            
            # 准备tokens（条件和无条件）
            tokens = torch.zeros((parallel_size*2, len(input_ids)), dtype=torch.int).to(self.device)
            for i in range(parallel_size*2):
                tokens[i, :] = input_ids
                if i % 2 != 0:  # 无条件分支
                    tokens[i, 1:-1] = self.vl_chat_processor.pad_id
            
            # 获取输入嵌入
            inputs_embeds = self.vl_gpt.language_model.get_input_embeddings()(tokens)
            
            # 生成图像tokens
            generated_tokens = torch.zeros((parallel_size, image_token_num_per_image), dtype=torch.int).to(self.device)
            
            print(f"开始生成 {image_token_num_per_image} 个图像tokens...")
            
            outputs = None
            for i in range(image_token_num_per_image):
                if i % 50 == 0:
                    print(f"生成进度: {i}/{image_token_num_per_image}")
                
                # 前向传播
                outputs = self.vl_gpt.language_model.model(
                    inputs_embeds=inputs_embeds, 
                    use_cache=True, 
                    past_key_values=outputs.past_key_values if i != 0 else None
                )
                
                hidden_states = outputs.last_hidden_state
                
                # 生成logits
                logits = self.vl_gpt.gen_head(hidden_states[:, -1, :])
                logit_cond = logits[0::2, :]      # 条件logits
                logit_uncond = logits[1::2, :]    # 无条件logits
                
                # CFG (Classifier-Free Guidance)
                logits = logit_uncond + cfg_weight * (logit_cond - logit_uncond)
                probs = torch.softmax(logits / temperature, dim=-1)
                
                # 采样下一个token
                next_token = torch.multinomial(probs, num_samples=1)
                generated_tokens[:, i] = next_token.squeeze(dim=-1)
                
                # 准备下一轮输入
                next_token = torch.cat([next_token.unsqueeze(dim=1), next_token.unsqueeze(dim=1)], dim=1).view(-1)
                img_embeds = self.vl_gpt.prepare_gen_img_embeds(next_token)
                inputs_embeds = img_embeds.unsqueeze(dim=1)
            
            print("Token生成完成，开始解码图像...")
            
            # 解码图像
            dec = self.vl_gpt.gen_vision_model.decode_code(
                generated_tokens.to(dtype=torch.int), 
                shape=[parallel_size, 8, img_size//patch_size, img_size//patch_size]
            )
            
            # 转换为numpy数组
            dec = dec.to(torch.float32).cpu().numpy().transpose(0, 2, 3, 1)
            dec = np.clip((dec + 1) / 2 * 255, 0, 255)
            
            # 创建最终图像
            visual_img = np.zeros((parallel_size, img_size, img_size, 3), dtype=np.uint8)
            visual_img[:, :, :] = dec
            
            # 保存图像
            os.makedirs(output_dir, exist_ok=True)
            saved_paths = []
            
            for i in range(parallel_size):
                save_path = os.path.join(output_dir, f"janus_generated_{i}.jpg")
                PIL.Image.fromarray(visual_img[i]).save(save_path)
                saved_paths.append(save_path)
                print(f"图像已保存: {save_path}")
            
            return saved_paths
            
        except Exception as e:
            print(f"图像生成失败: {e}")
            import traceback
            traceback.print_exc()
            return []

# 测试函数
def test_official_generator():
    generator = OfficialJanusGenerator()
    
    if generator.load_model():
        prompt = "A beautiful sunset over the ocean with golden clouds"
        paths = generator.generate_image(prompt, parallel_size=2)
        print(f"生成的图像路径: {paths}")
    else:
        print("模型加载失败")

if __name__ == "__main__":
    test_official_generator()