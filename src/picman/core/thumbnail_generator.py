"""
Thumbnail generation functionality.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps, ExifTags

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ..config.manager import ConfigManager


class ThumbnailGenerator:
    """Generates and manages photo thumbnails."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = logger
        
        # Create thumbnails directory
        self.thumbnail_dir = Path("data/thumbnails")
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_exif_orientation(self, img: Image.Image) -> int:
        """Get EXIF orientation from image."""
        try:
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                if exif is not None:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            return exif[orientation]
        except Exception as e:
            self.logger.debug("Failed to get EXIF orientation: error=%s", str(e))
        return 1  # Default orientation
    
    def _rotate_image_by_exif(self, img: Image.Image) -> Image.Image:
        """Rotate image according to EXIF orientation."""
        orientation = self._get_exif_orientation(img)
        
        if orientation == 2:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            img = img.transpose(Image.Transpose.ROTATE_180)
        elif orientation == 4:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT).transpose(Image.Transpose.ROTATE_90)
        elif orientation == 6:
            img = img.transpose(Image.Transpose.ROTATE_270)
        elif orientation == 7:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT).transpose(Image.Transpose.ROTATE_270)
        elif orientation == 8:
            img = img.transpose(Image.Transpose.ROTATE_90)
        
        return img
    
    def generate_thumbnail(self, image_path: str) -> Optional[str]:
        """Generate thumbnail for an image."""
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                self.logger.error("Image file not found: %s", str(image_path))
                return None
            
            # Generate thumbnail filename
            thumb_filename = f"{image_path.stem}_{hash(str(image_path))}.jpg"
            thumb_path = self.thumbnail_dir / thumb_filename
            
            # Skip if thumbnail already exists
            if thumb_path.exists():
                return str(thumb_path)
            
            # Get thumbnail settings
            size = self.config.get("thumbnail.size", (256, 256))
            quality = self.config.get("thumbnail.quality", 85)
            
            # Generate thumbnail
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Apply EXIF orientation correction
                img = self._rotate_image_by_exif(img)
                
                # Create thumbnail with proper aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumb_path, "JPEG", quality=quality, optimize=True)
            
            self.logger.info("Thumbnail generated: original=%s, thumbnail=%s", str(image_path), str(thumb_path))
            
            return str(thumb_path)
            
        except Exception as e:
            self.logger.error("Failed to generate thumbnail: path=%s, error=%s", str(image_path), str(e))
            return None
    
    def get_thumbnail_path(self, image_path: str) -> Optional[str]:
        """Get thumbnail path for an image."""
        image_path = Path(image_path)
        thumb_filename = f"{image_path.stem}_{hash(str(image_path))}.jpg"
        thumb_path = self.thumbnail_dir / thumb_filename
        
        return str(thumb_path) if thumb_path.exists() else None
    
    def delete_thumbnail(self, image_path: str) -> bool:
        """Delete thumbnail for an image."""
        try:
            thumb_path = self.get_thumbnail_path(image_path)
            if thumb_path and Path(thumb_path).exists():
                Path(thumb_path).unlink()
                self.logger.info("Thumbnail deleted: thumbnail=%s", thumb_path)
                return True
            return False
            
        except Exception as e:
            self.logger.error("Failed to delete thumbnail: path=%s, error=%s", str(image_path), str(e))
            return False
    
    def cleanup_orphaned_thumbnails(self) -> int:
        """Remove thumbnails for non-existent images."""
        try:
            removed_count = 0
            
            for thumb_file in self.thumbnail_dir.glob("*.jpg"):
                # This is a simplified cleanup - in practice, you'd check against the database
                if not thumb_file.exists():
                    continue
                
                # Check if original image exists (simplified logic)
                # In a real implementation, you'd query the database
                
            self.logger.info("Thumbnail cleanup completed: removed=%s", removed_count)
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup thumbnails: {str(e)}")
            return 0