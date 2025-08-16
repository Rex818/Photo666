# 简化版Janus生图器 - 不依赖FlashAttention
import torch
import numpy as np
import os
import PIL.Image
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
import sys
import logging

class SimpleJanusGenerator:
    def __init__(self, model_path="deepseek-ai/Janus-1.3B", device="cuda"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """加载模型"""
        try:
            print(f"正在加载Janus模型: {self.model_path}")
            
            # 先加载配置并修改
            config = AutoConfig.from_pretrained(self.model_path, trust_remote_code=True)
            
            # 强制禁用FlashAttention
            if hasattr(config, '_attn_implementation'):
                config._attn_implementation = "eager"
            if hasattr(config, 'use_flash_attention_2'):
                config.use_flash_attention_2 = False
            if hasattr(config, 'language_config'):
                if hasattr(config.language_config, '_attn_implementation'):
                    config.language_config._attn_implementation = "eager"
                if hasattr(config.language_config, 'use_flash_attention_2'):
                    config.language_config.use_flash_attention_2 = False
            
            # 设置环境变量
            os.environ["FLASH_ATTENTION_FORCE_DISABLE"] = "1"
            
            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, 
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.float16,  # 使用float16而不是bfloat16
                low_cpu_mem_usage=True
            )
            
            # 移动到GPU
            if torch.cuda.is_available() and self.device == "cuda":
                self.model = self.model.cuda()
            
            self.model = self.model.eval()
            
            print("模型加载完成")
            return True
            
        except Exception as e:
            print(f"模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_simple_text(self, prompt: str, max_length: int = 100):
        """简单的文本生成测试"""
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("模型未加载，请先调用load_model()")
        
        try:
            # 编码输入
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # 解码
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return generated_text
            
        except Exception as e:
            print(f"文本生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None

# 测试函数
def test_simple_generator():
    generator = SimpleJanusGenerator()
    
    if generator.load_model():
        prompt = "Hello, how are you?"
        result = generator.generate_simple_text(prompt)
        print(f"生成结果: {result}")
    else:
        print("模型加载失败")

if __name__ == "__main__":
    test_simple_generator()