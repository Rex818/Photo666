"""
Sepia filter plugin for PyPhotoManager.
"""

from typing import Dict, Any, List
from pathlib import Path
from PIL import Image, ImageOps

from src.picman.plugins.base import PhotoFilterPlugin, PluginInfo


class SepiaFilterPlugin(PhotoFilterPlugin):
    """Plugin that applies sepia filter to photos."""
    
    def __init__(self):
        super().__init__()
        self.settings = {
            "intensity": 0.8,  # 0.0 to 1.0
        }
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="Sepia Filter",
            version="1.0.0",
            description="Applies sepia tone effect to photos",
            author="PyPhotoManager Team"
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        self.logger.info("Sepia filter plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Sepia filter plugin shutdown")
        return True
    
    def get_filter_name(self) -> str:
        """Get the name of the filter."""
        return "Sepia"
    
    def get_filter_params(self) -> List[Dict[str, Any]]:
        """Get filter parameters."""
        return [
            {
                "name": "intensity",
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.8,
                "label": "Effect Intensity"
            }
        ]
    
    def apply_filter(self, image_path: str, output_path: str, params: Dict[str, Any] = None) -> bool:
        """Apply sepia filter to an image."""
        try:
            # Use provided params or default settings
            filter_params = params or self.settings
            intensity = filter_params.get("intensity", 0.8)
            
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Apply sepia filter
                sepia_img = self._apply_sepia_tone(img, intensity)
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Save result
                sepia_img.save(output_path)
            
            self.logger.info("Applied sepia filter", 
                           input=image_path, 
                           output=output_path,
                           intensity=intensity)
            return True
            
        except Exception as e:
            self.logger.error("Failed to apply sepia filter", 
                            path=image_path, 
                            error=str(e))
            return False
    
    def _apply_sepia_tone(self, img: Image.Image, intensity: float = 0.8) -> Image.Image:
        """Apply sepia tone effect to an image."""
        # Convert to grayscale
        gray_img = ImageOps.grayscale(img)
        
        # Create sepia tone
        sepia_img = Image.new("RGB", img.size)
        
        # Apply sepia palette
        for x in range(img.width):
            for y in range(img.height):
                gray_value = gray_img.getpixel((x, y))
                
                # Calculate sepia RGB values
                r = min(255, int(gray_value * 1.07))
                g = min(255, int(gray_value * 0.74))
                b = min(255, int(gray_value * 0.43))
                
                # Blend with original based on intensity
                if intensity < 1.0:
                    orig_r, orig_g, orig_b = img.getpixel((x, y))
                    r = int(r * intensity + orig_r * (1 - intensity))
                    g = int(g * intensity + orig_g * (1 - intensity))
                    b = int(b * intensity + orig_b * (1 - intensity))
                
                sepia_img.putpixel((x, y), (r, g, b))
        
        return sepia_img
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions provided by this plugin."""
        return [
            {
                "menu": "Filters",
                "title": "Apply Sepia Tone",
                "action": "apply_sepia"
            }
        ]
    
    def get_settings(self) -> Dict[str, Any]:
        """Get plugin settings."""
        return self.settings
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Update plugin settings."""
        self.settings.update(settings)
        return True