"""
Grayscale filter plugin for PyPhotoManager.
"""

from typing import Dict, Any, List
from pathlib import Path
from PIL import Image, ImageOps

from src.picman.plugins.base import PhotoFilterPlugin, PluginInfo


class GrayscaleFilterPlugin(PhotoFilterPlugin):
    """Plugin that applies grayscale filter to photos."""
    
    def __init__(self):
        super().__init__()
        self.settings = {
            "mode": "luminosity",  # luminosity, average, or minimum
            "contrast": 1.0
        }
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="Grayscale Filter",
            version="1.0.0",
            description="Converts photos to grayscale",
            author="PyPhotoManager Team"
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        self.logger.info("Grayscale filter plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Grayscale filter plugin shutdown")
        return True
    
    def get_filter_name(self) -> str:
        """Get the name of the filter."""
        return "Grayscale"
    
    def get_filter_params(self) -> List[Dict[str, Any]]:
        """Get filter parameters."""
        return [
            {
                "name": "mode",
                "type": "choice",
                "choices": ["luminosity", "average", "minimum"],
                "default": "luminosity",
                "label": "Grayscale Mode"
            },
            {
                "name": "contrast",
                "type": "float",
                "min": 0.5,
                "max": 2.0,
                "default": 1.0,
                "label": "Contrast"
            }
        ]
    
    def apply_filter(self, image_path: str, output_path: str, params: Dict[str, Any] = None) -> bool:
        """Apply grayscale filter to an image."""
        try:
            # Use provided params or default settings
            filter_params = params or self.settings
            
            # Open image
            with Image.open(image_path) as img:
                # Convert to grayscale based on mode
                mode = filter_params.get("mode", "luminosity")
                
                if mode == "luminosity":
                    # Weighted conversion (perceived brightness)
                    gray_img = img.convert("L")
                elif mode == "average":
                    # Simple average of RGB channels
                    gray_img = ImageOps.grayscale(img)
                elif mode == "minimum":
                    # Minimum of RGB channels
                    r, g, b = img.split()
                    gray_img = ImageOps.invert(ImageOps.invert(r).point(lambda i: min(i, ImageOps.invert(g).getpixel((0, 0)), ImageOps.invert(b).getpixel((0, 0)))))
                else:
                    gray_img = img.convert("L")
                
                # Apply contrast adjustment if specified
                contrast = filter_params.get("contrast", 1.0)
                if contrast != 1.0:
                    gray_img = ImageOps.autocontrast(gray_img, cutoff=int((1.0 - contrast) * 50))
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Save result
                gray_img.save(output_path)
            
            self.logger.info("Applied grayscale filter", 
                           input=image_path, 
                           output=output_path,
                           mode=mode)
            return True
            
        except Exception as e:
            self.logger.error("Failed to apply grayscale filter", 
                            path=image_path, 
                            error=str(e))
            return False
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions provided by this plugin."""
        return [
            {
                "menu": "Filters",
                "title": "Convert to Grayscale",
                "action": "apply_grayscale"
            }
        ]
    
    def get_settings(self) -> Dict[str, Any]:
        """Get plugin settings."""
        return self.settings
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Update plugin settings."""
        self.settings.update(settings)
        return True