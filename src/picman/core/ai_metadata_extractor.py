"""
AI Metadata Extractor for PyPhotoManager.
Extracts AI generation metadata from various AI-generated image formats.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from PIL import Image
import structlog


@dataclass
class AIMetadata:
    """AI生成图片的元数据结构"""
    # 基本信息
    is_ai_generated: bool = False
    generation_software: str = ""  # WebUI, ComfyUI, Midjourney, etc.
    generation_date: str = ""
    
    # 模型信息
    model_name: str = ""
    model_version: str = ""
    lora_name: str = ""
    lora_weight: float = 0.0
    
    # 生成参数
    positive_prompt: str = ""
    negative_prompt: str = ""
    sampler: str = ""
    steps: int = 0
    cfg_scale: float = 0.0
    seed: int = 0
    size: str = ""  # "1024x1024"
    
    # 其他参数
    clip_skip: int = 0
    denoising_strength: float = 0.0
    
    # Midjourney特有参数
    mj_job_id: str = ""  # Midjourney任务ID
    mj_stylize: int = 0  # Midjourney风格化参数
    mj_quality: int = 0  # Midjourney质量参数
    mj_aspect_ratio: str = ""  # Midjourney宽高比
    mj_version: str = ""  # Midjourney版本
    mj_raw_mode: bool = False  # Midjourney原始模式
    mj_chaos: int = 0  # Midjourney混乱度参数
    mj_tile: bool = False  # Midjourney平铺模式
    mj_niji: bool = False  # Midjourney Niji模式
    mj_weird: int = 0  # Midjourney怪异度参数
    
    # 原始数据
    raw_metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        if self.raw_metadata is None:
            result['raw_metadata'] = {}
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIMetadata':
        """从字典创建实例"""
        if data.get('raw_metadata') is None:
            data['raw_metadata'] = {}
        return cls(**data)


class AIMetadataExtractor:
    """AI元数据提取器"""
    
    def __init__(self):
        self.logger = structlog.get_logger("picman.core.ai_metadata_extractor")
        
        # 支持的AI软件标识
        self.ai_software_patterns = {
            'webui': [
                r'parameters',
                r'Steps: \d+',
                r'Sampler: \w+',
                r'CFG scale: \d+\.?\d*',
                r'Seed: \d+',
                r'Model: \w+'
            ],
            'comfyui': [
                r'prompt',
                r'workflow',
                r'ComfyUI',
                r'seed',
                r'steps'
            ],
            'midjourney': [
                r'Midjourney',
                r'ImageDescription',
                r'--ar \d+:\d+',
                r'--v \d+',
                r'--q \d+'
            ]
        }
    
    def extract_metadata(self, image_path: str) -> AIMetadata:
        """从图片中提取AI元数据"""
        try:
            metadata = AIMetadata()
            image_path = Path(image_path)
            
            if not image_path.exists():
                self.logger.warning("Image file not found", path=str(image_path))
                return metadata
            
            # 打开图片
            with Image.open(image_path) as img:
                # 检查PNG文本块
                if img.format == 'PNG':
                    metadata = self._extract_png_metadata(img, metadata)
                
                # 检查EXIF数据
                if hasattr(img, 'getexif') and img.getexif():
                    metadata = self._extract_exif_metadata(img, metadata)
                
                # 检查文件名中的信息
                metadata = self._extract_filename_metadata(image_path.name, metadata)
            
            # 判断是否为AI生成图片
            metadata.is_ai_generated = self._is_ai_generated(metadata)
            
            self.logger.info("AI metadata extracted", 
                           path=str(image_path),
                           is_ai_generated=metadata.is_ai_generated,
                           software=metadata.generation_software)
            
            return metadata
            
        except Exception as e:
            self.logger.error("Failed to extract AI metadata", 
                            path=str(image_path),
                            error=str(e))
            return AIMetadata()
    
    def _extract_png_metadata(self, img: Image.Image, metadata: AIMetadata) -> AIMetadata:
        """从PNG文本块中提取元数据"""
        try:
            if hasattr(img, 'info') and img.info:
                # 检查WebUI格式
                if 'parameters' in img.info:
                    metadata = self._parse_webui_parameters(img.info['parameters'], metadata)
                
                # 检查ComfyUI格式
                if 'prompt' in img.info:
                    metadata = self._parse_comfyui_metadata(img.info, metadata)
                
                # 检查Midjourney格式 - 检查Description字段
                if 'Description' in img.info:
                    description = img.info['Description']
                    if isinstance(description, str) and self._is_midjourney_description(description):
                        metadata = self._parse_midjourney_metadata(description, metadata)
                
                # 检查ImageDescription字段（备用）
                if 'ImageDescription' in img.info and not metadata.generation_software:
                    description = img.info['ImageDescription']
                    if isinstance(description, str) and self._is_midjourney_description(description):
                        metadata = self._parse_midjourney_metadata(description, metadata)
                
                # 保存原始元数据
                metadata.raw_metadata = dict(img.info)
        
        except Exception as e:
            self.logger.error("Failed to extract PNG metadata", error=str(e))
        
        return metadata
    
    def _extract_exif_metadata(self, img: Image.Image, metadata: AIMetadata) -> AIMetadata:
        """从EXIF数据中提取元数据"""
        try:
            exif = img.getexif()
            
            # 检查UserComment字段
            if 37510 in exif:  # UserComment
                user_comment = exif[37510]
                if isinstance(user_comment, bytes):
                    user_comment = user_comment.decode('utf-8', errors='ignore')
                
                # 尝试解析UserComment中的AI信息
                metadata = self._parse_user_comment(user_comment, metadata)
            
            # 检查ImageDescription字段
            if 270 in exif:  # ImageDescription
                image_desc = exif[270]
                if isinstance(image_desc, str):
                    metadata = self._parse_image_description(image_desc, metadata)
        
        except Exception as e:
            self.logger.error("Failed to extract EXIF metadata", error=str(e))
        
        return metadata
    
    def _extract_filename_metadata(self, filename: str, metadata: AIMetadata) -> AIMetadata:
        """从文件名中提取元数据"""
        try:
            # 检查文件名中的种子号
            seed_match = re.search(r'(\d{10,})', filename)
            if seed_match and metadata.seed == 0:
                metadata.seed = int(seed_match.group(1))
            
            # 检查文件名中的尺寸信息
            size_match = re.search(r'(\d+)x(\d+)', filename)
            if size_match and not metadata.size:
                width, height = size_match.groups()
                metadata.size = f"{width}x{height}"
        
        except Exception as e:
            self.logger.error("Failed to extract filename metadata", error=str(e))
        
        return metadata
    
    def _parse_webui_parameters(self, parameters: str, metadata: AIMetadata) -> AIMetadata:
        """解析WebUI格式的参数"""
        try:
            metadata.generation_software = "Stable Diffusion WebUI"
            
            # 解析基本参数
            steps_match = re.search(r'Steps: (\d+)', parameters)
            if steps_match:
                metadata.steps = int(steps_match.group(1))
            
            sampler_match = re.search(r'Sampler: ([^,]+)', parameters)
            if sampler_match:
                metadata.sampler = sampler_match.group(1).strip()
            
            cfg_match = re.search(r'CFG scale: ([\d.]+)', parameters)
            if cfg_match:
                metadata.cfg_scale = float(cfg_match.group(1))
            
            seed_match = re.search(r'Seed: (\d+)', parameters)
            if seed_match:
                metadata.seed = int(seed_match.group(1))
            
            # 解析模型信息
            model_match = re.search(r'Model: ([^,]+)', parameters)
            if model_match:
                metadata.model_name = model_match.group(1).strip()
            
            # 解析提示词
            lines = parameters.split('\n')
            positive_prompt = ""
            negative_prompt = ""
            in_negative = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('Negative prompt:'):
                    in_negative = True
                    negative_prompt = line.replace('Negative prompt:', '').strip()
                elif line and not line.startswith('Steps:') and not line.startswith('Sampler:') and not line.startswith('CFG scale:') and not line.startswith('Seed:') and not line.startswith('Model:'):
                    if in_negative:
                        negative_prompt += ' ' + line
                    else:
                        positive_prompt += ' ' + line
            
            if positive_prompt.strip():
                metadata.positive_prompt = positive_prompt.strip()
            if negative_prompt.strip():
                metadata.negative_prompt = negative_prompt.strip()
            
            # 解析尺寸
            size_match = re.search(r'Size: (\d+)x(\d+)', parameters)
            if size_match:
                width, height = size_match.groups()
                metadata.size = f"{width}x{height}"
            
            # 解析其他参数
            clip_skip_match = re.search(r'Clip skip: (\d+)', parameters)
            if clip_skip_match:
                metadata.clip_skip = int(clip_skip_match.group(1))
            
            denoising_match = re.search(r'Denoising strength: ([\d.]+)', parameters)
            if denoising_match:
                metadata.denoising_strength = float(denoising_match.group(1))
        
        except Exception as e:
            self.logger.error("Failed to parse WebUI parameters", error=str(e))
        
        return metadata
    
    def _parse_comfyui_metadata(self, info: Dict[str, Any], metadata: AIMetadata) -> AIMetadata:
        """解析ComfyUI格式的元数据"""
        try:
            metadata.generation_software = "ComfyUI"
            
            # 解析prompt字段
            if 'prompt' in info:
                prompt_data = info['prompt']
                if isinstance(prompt_data, str):
                    try:
                        prompt_json = json.loads(prompt_data)
                        metadata = self._extract_comfyui_prompt_data(prompt_json, metadata)
                    except json.JSONDecodeError:
                        pass
            
            # 解析workflow字段
            if 'workflow' in info:
                workflow_data = info['workflow']
                if isinstance(workflow_data, str):
                    try:
                        workflow_json = json.loads(workflow_data)
                        metadata = self._extract_comfyui_workflow_data(workflow_json, metadata)
                    except json.JSONDecodeError:
                        pass
        
        except Exception as e:
            self.logger.error("Failed to parse ComfyUI metadata", error=str(e))
        
        return metadata
    
    def _extract_comfyui_prompt_data(self, prompt_data: Dict[str, Any], metadata: AIMetadata) -> AIMetadata:
        """从ComfyUI prompt数据中提取信息"""
        try:
            # 遍历所有节点
            for node_id, node_data in prompt_data.items():
                if isinstance(node_data, dict):
                    # 检查KSampler节点
                    if node_data.get('class_type') == 'KSampler':
                        if 'inputs' in node_data:
                            inputs = node_data['inputs']
                            if 'seed' in inputs:
                                metadata.seed = int(inputs['seed'])
                            if 'steps' in inputs:
                                metadata.steps = int(inputs['steps'])
                            if 'cfg' in inputs:
                                metadata.cfg_scale = float(inputs['cfg'])
                            if 'sampler_name' in inputs:
                                metadata.sampler = str(inputs['sampler_name'])
                    
                    # 检查CheckpointLoaderSimple节点
                    elif node_data.get('class_type') == 'CheckpointLoaderSimple':
                        if 'inputs' in node_data and 'ckpt_name' in node_data['inputs']:
                            metadata.model_name = str(node_data['inputs']['ckpt_name'])
                    
                    # 检查CLIPTextEncode节点（正面提示词）
                    elif node_data.get('class_type') == 'CLIPTextEncode':
                        if 'inputs' in node_data and 'text' in node_data['inputs']:
                            text = node_data['inputs']['text']
                            if isinstance(text, str) and text.strip():
                                metadata.positive_prompt = text.strip()
        
        except Exception as e:
            self.logger.error("Failed to extract ComfyUI prompt data", error=str(e))
        
        return metadata
    
    def _extract_comfyui_workflow_data(self, workflow_data: Dict[str, Any], metadata: AIMetadata) -> AIMetadata:
        """从ComfyUI workflow数据中提取信息"""
        try:
            # 提取工作流基本信息
            if isinstance(workflow_data, dict):
                # 提取节点信息
                nodes = workflow_data.get('nodes', {})
                if isinstance(nodes, dict):
                    # 查找关键节点类型
                    for node_id, node_data in nodes.items():
                        if isinstance(node_data, dict):
                            class_type = node_data.get('class_type', '')
                            
                            # KSampler节点 - 采样参数
                            if class_type == 'KSampler':
                                inputs = node_data.get('inputs', {})
                                if not metadata.sampler and 'sampler_name' in inputs:
                                    metadata.sampler = str(inputs['sampler_name'])
                                if not metadata.steps and 'steps' in inputs:
                                    metadata.steps = int(inputs['steps'])
                                if not metadata.cfg_scale and 'cfg' in inputs:
                                    metadata.cfg_scale = float(inputs['cfg'])
                                if not metadata.seed and 'seed' in inputs:
                                    metadata.seed = int(inputs['seed'])
                                if not metadata.denoising_strength and 'denoise' in inputs:
                                    metadata.denoising_strength = float(inputs['denoise'])
                            
                            # CheckpointLoaderSimple节点 - 模型信息
                            elif class_type == 'CheckpointLoaderSimple':
                                inputs = node_data.get('inputs', {})
                                if not metadata.model_name and 'ckpt_name' in inputs:
                                    metadata.model_name = str(inputs['ckpt_name'])
                            
                            # CLIPLoader节点 - CLIP模型
                            elif class_type == 'CLIPLoader':
                                inputs = node_data.get('inputs', {})
                                if 'clip_name' in inputs:
                                    clip_name = str(inputs['clip_name'])
                                    if not metadata.model_version:
                                        metadata.model_version = f"CLIP: {clip_name}"
                            
                            # VAE节点 - VAE模型
                            elif class_type == 'VAELoader':
                                inputs = node_data.get('inputs', {})
                                if 'vae_name' in inputs:
                                    vae_name = str(inputs['vae_name'])
                                    if not metadata.model_version:
                                        metadata.model_version = f"VAE: {vae_name}"
                            
                            # LoraLoader节点 - Lora模型
                            elif class_type == 'LoraLoader':
                                inputs = node_data.get('inputs', {})
                                if not metadata.lora_name and 'lora_name' in inputs:
                                    metadata.lora_name = str(inputs['lora_name'])
                                if not metadata.lora_weight and 'strength_model' in inputs:
                                    metadata.lora_weight = float(inputs['strength_model'])
                            
                            # CLIPTextEncode节点 - 提示词
                            elif class_type == 'CLIPTextEncode':
                                inputs = node_data.get('inputs', {})
                                if not metadata.positive_prompt and 'text' in inputs:
                                    text = inputs['text']
                                    if isinstance(text, str) and text.strip():
                                        metadata.positive_prompt = text.strip()
                            
                            # CLIPTextEncode (negative) 节点 - 负面提示词
                            elif class_type == 'CLIPTextEncode' and 'negative' in str(node_data).lower():
                                inputs = node_data.get('inputs', {})
                                if not metadata.negative_prompt and 'text' in inputs:
                                    text = inputs['text']
                                    if isinstance(text, str) and text.strip():
                                        metadata.negative_prompt = text.strip()
                            
                            # EmptyLatentImage节点 - 图片尺寸
                            elif class_type == 'EmptyLatentImage':
                                inputs = node_data.get('inputs', {})
                                if not metadata.size and 'width' in inputs and 'height' in inputs:
                                    width = inputs['width']
                                    height = inputs['height']
                                    metadata.size = f"{width}x{height}"
                
                # 确保raw_metadata不为None
                if metadata.raw_metadata is None:
                    metadata.raw_metadata = {}
                
                # 提取工作流元数据
                metadata.raw_metadata['workflow_info'] = {
                    'node_count': len(workflow_data.get('nodes', {})),
                    'connection_count': len(workflow_data.get('connections', {})),
                    'workflow_version': workflow_data.get('version', 'unknown')
                }
                
                # 生成工作流摘要
                workflow_summary = self._generate_workflow_summary(workflow_data)
                if workflow_summary:
                    metadata.raw_metadata['workflow_summary'] = workflow_summary
        
        except Exception as e:
            self.logger.error("Failed to extract ComfyUI workflow data", error=str(e))
        
        return metadata
    
    def _generate_workflow_summary(self, workflow_data: Dict[str, Any]) -> str:
        """生成工作流摘要信息"""
        try:
            summary_parts = []
            
            if isinstance(workflow_data, dict):
                nodes = workflow_data.get('nodes', {})
                if isinstance(nodes, dict):
                    # 统计节点类型
                    node_types = {}
                    for node_id, node_data in nodes.items():
                        if isinstance(node_data, dict):
                            class_type = node_data.get('class_type', '')
                            node_types[class_type] = node_types.get(class_type, 0) + 1
                    
                    # 生成摘要
                    if node_types:
                        summary_parts.append(f"节点类型: {', '.join([f'{k}({v})' for k, v in node_types.items()])}")
                    
                    # 检查是否有特殊节点
                    special_nodes = []
                    for node_id, node_data in nodes.items():
                        if isinstance(node_data, dict):
                            class_type = node_data.get('class_type', '')
                            if class_type in ['ControlNetLoader', 'IPAdapterLoader', 'UpscaleModelLoader']:
                                special_nodes.append(class_type)
                    
                    if special_nodes:
                        summary_parts.append(f"特殊节点: {', '.join(special_nodes)}")
            
            return ' | '.join(summary_parts) if summary_parts else ""
            
        except Exception as e:
            self.logger.error("Failed to generate workflow summary", error=str(e))
            return ""
    
    def _parse_midjourney_metadata(self, image_description: str, metadata: AIMetadata) -> AIMetadata:
        """解析Midjourney格式的元数据"""
        try:
            metadata.generation_software = "Midjourney"
            
            # 解析Job ID
            job_id_match = re.search(r'Job ID: ([a-f0-9-]+)', image_description)
            if job_id_match:
                metadata.mj_job_id = job_id_match.group(1)
            
            # 解析版本
            version_match = re.search(r'--v (\d+)', image_description)
            if version_match:
                metadata.mj_version = f"v{version_match.group(1)}"
                metadata.model_version = f"v{version_match.group(1)}"
            
            # 解析风格化参数
            stylize_match = re.search(r'--stylize (\d+)', image_description)
            if stylize_match:
                metadata.mj_stylize = int(stylize_match.group(1))
            
            # 解析质量参数
            quality_match = re.search(r'--q (\d+)', image_description)
            if quality_match:
                metadata.mj_quality = int(quality_match.group(1))
            
            # 解析宽高比
            ar_match = re.search(r'--ar (\d+):(\d+)', image_description)
            if ar_match:
                width, height = ar_match.groups()
                metadata.mj_aspect_ratio = f"{width}:{height}"
                metadata.size = f"{width}x{height}"
            
            # 解析原始模式
            if '--raw' in image_description:
                metadata.mj_raw_mode = True
            
            # 解析混乱度参数
            chaos_match = re.search(r'--c (\d+)', image_description)
            if chaos_match:
                metadata.mj_chaos = int(chaos_match.group(1))
            
            # 解析平铺模式
            if '--tile' in image_description:
                metadata.mj_tile = True
            
            # 解析Niji模式
            if '--niji' in image_description:
                metadata.mj_niji = True
            
            # 解析怪异度参数
            weird_match = re.search(r'--weird (\d+)', image_description)
            if weird_match:
                metadata.mj_weird = int(weird_match.group(1))
            
            # 解析提示词 - 提取主要提示词部分
            prompt_parts = image_description.split('--')
            if prompt_parts:
                main_prompt = prompt_parts[0].strip()
                if main_prompt:
                    metadata.positive_prompt = main_prompt
            
            # 保存Midjourney特有参数到原始元数据
            if metadata.raw_metadata is None:
                metadata.raw_metadata = {}
            
            metadata.raw_metadata['midjourney_params'] = {
                'job_id': metadata.mj_job_id,
                'version': metadata.mj_version,
                'stylize': metadata.mj_stylize,
                'quality': metadata.mj_quality,
                'aspect_ratio': metadata.mj_aspect_ratio,
                'raw_mode': metadata.mj_raw_mode,
                'chaos': metadata.mj_chaos,
                'tile': metadata.mj_tile,
                'niji': metadata.mj_niji,
                'weird': metadata.mj_weird
            }
        
        except Exception as e:
            self.logger.error("Failed to parse Midjourney metadata", error=str(e))
        
        return metadata
    
    def _parse_user_comment(self, user_comment: str, metadata: AIMetadata) -> AIMetadata:
        """解析UserComment中的AI信息"""
        try:
            # 尝试解析JSON格式
            try:
                comment_data = json.loads(user_comment)
                if isinstance(comment_data, dict):
                    # 检查常见的AI软件标识
                    if 'software' in comment_data:
                        metadata.generation_software = comment_data['software']
                    if 'model' in comment_data:
                        metadata.model_name = comment_data['model']
                    if 'prompt' in comment_data:
                        metadata.positive_prompt = comment_data['prompt']
            except json.JSONDecodeError:
                # 如果不是JSON，尝试正则匹配
                pass
        
        except Exception as e:
            self.logger.error("Failed to parse user comment", error=str(e))
        
        return metadata
    
    def _parse_image_description(self, image_desc: str, metadata: AIMetadata) -> AIMetadata:
        """解析ImageDescription中的AI信息"""
        try:
            # 检查是否包含AI相关信息
            if any(keyword in image_desc.lower() for keyword in ['stable diffusion', 'webui', 'comfyui', 'midjourney']):
                metadata.positive_prompt = image_desc.strip()
        
        except Exception as e:
            self.logger.error("Failed to parse image description", error=str(e))
        
        return metadata
    
    def _is_midjourney_description(self, description: str) -> bool:
        """判断是否为Midjourney描述"""
        if not description:
            return False
        
        # 检查Midjourney特有标识
        midjourney_indicators = [
            'Job ID:',
            '--v ',
            '--stylize',
            '--raw',
            '--ar ',
            '--q ',
            '--c ',
            '--tile',
            '--niji',
            '--weird'
        ]
        
        return any(indicator in description for indicator in midjourney_indicators)
    
    def _is_ai_generated(self, metadata: AIMetadata) -> bool:
        """判断是否为AI生成的图片"""
        # 检查是否有AI软件标识
        if metadata.generation_software:
            return True
        
        # 检查是否有AI相关的参数
        if metadata.model_name or metadata.positive_prompt or metadata.sampler:
            return True
        
        # 检查Midjourney特有参数
        if metadata.mj_job_id or metadata.mj_version:
            return True
        
        # 检查原始元数据中是否有AI相关信息
        if metadata.raw_metadata:
            raw_text = str(metadata.raw_metadata).lower()
            ai_keywords = ['stable diffusion', 'webui', 'comfyui', 'midjourney', 'dall-e', 'gpt']
            if any(keyword in raw_text for keyword in ai_keywords):
                return True
        
        return False 