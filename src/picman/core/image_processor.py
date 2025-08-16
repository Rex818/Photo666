"""
Image processing utilities.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ..config.manager import ConfigManager


class ImageProcessor:
    """Image processing and manipulation utilities."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logger
    
    def resize_image(self, image_path: str, output_path: str, 
                    size: Tuple[int, int], maintain_aspect: bool = True) -> bool:
        """Resize an image."""
        try:
            with Image.open(image_path) as img:
                if maintain_aspect:
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                else:
                    img = img.resize(size, Image.Resampling.LANCZOS)
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                img.save(output_path, quality=95, optimize=True)
                
            self.logger.info(f"Image resized: input={image_path}, output={output_path}, size={size}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resize image: path={image_path}, error={str(e)}")
            return False
    
    def rotate_image(self, image_path: str, output_path: str, angle: float) -> bool:
        """Rotate an image by specified angle."""
        try:
            with Image.open(image_path) as img:
                rotated = img.rotate(angle, expand=True)
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                rotated.save(output_path, quality=95, optimize=True)
                
            self.logger.info(f"Image rotated: input={image_path}, output={output_path}, angle={angle}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate image: path={image_path}, error={str(e)}")
            return False
    
    def adjust_brightness(self, image_path: str, output_path: str, factor: float) -> bool:
        """Adjust image brightness."""
        try:
            with Image.open(image_path) as img:
                enhancer = ImageEnhance.Brightness(img)
                enhanced = enhancer.enhance(factor)
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                enhanced.save(output_path, quality=95, optimize=True)
                
            self.logger.info(f"Image brightness adjusted: input={image_path}, output={output_path}, factor={factor}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to adjust brightness: path={image_path}, error={str(e)}")
            return False
    
    def adjust_contrast(self, image_path: str, output_path: str, factor: float) -> bool:
        """Adjust image contrast."""
        try:
            with Image.open(image_path) as img:
                enhancer = ImageEnhance.Contrast(img)
                enhanced = enhancer.enhance(factor)
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                enhanced.save(output_path, quality=95, optimize=True)
                
            self.logger.info(f"Image contrast adjusted: input={image_path}, output={output_path}, factor={factor}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to adjust contrast: path={image_path}, error={str(e)}")
            return False
    
    def convert_format(self, image_path: str, output_path: str, 
                      format: str = "JPEG", quality: int = 95) -> bool:
        """Convert image to different format."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if saving as JPEG
                if format.upper() == "JPEG" and img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                img.save(output_path, format=format, quality=quality, optimize=True)
                
            self.logger.info(f"Image format converted: input={image_path}, output={output_path}, format={format}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to convert image format: path={image_path}, error={str(e)}")
            return False
    
    def get_image_info(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed image information."""
        try:
            with Image.open(image_path) as img:
                info = {
                    "filename": Path(image_path).name,
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Add file size
                file_path = Path(image_path)
                if file_path.exists():
                    info["file_size"] = file_path.stat().st_size
                
                return info
                
        except Exception as e:
            self.logger.error(f"Failed to get image info: path={image_path}, error={str(e)}")
            return None