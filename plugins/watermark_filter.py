"""
Watermark filter plugin for PyPhotoManager.
Allows adding text watermarks to photos.
"""

from typing import Dict, Any, List
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

from src.picman.plugins.base import PhotoFilterPlugin, PluginInfo


class WatermarkFilterPlugin(PhotoFilterPlugin):
    """Plugin that applies text watermark to photos."""
    
    def __init__(self):
        super().__init__()
        self.settings = {
            "text": "© PyPhotoManager",
            "position": "bottom-right",  # top-left, top-right, bottom-left, bottom-right, center
            "font_size": 24,
            "opacity": 0.7,  # 0.0 to 1.0
            "color": "#ffffff",  # white
            "padding": 10  # padding from edge
        }
    
    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name="Watermark Filter",
            version="1.0.0",
            description="Adds text watermark to photos",
            author="PyPhotoManager Team"
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        self.logger.info("Watermark filter plugin initialized")
        return True
    
    def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Watermark filter plugin shutdown")
        return True
    
    def get_filter_name(self) -> str:
        """Get the name of the filter."""
        return "Watermark"
    
    def get_filter_params(self) -> List[Dict[str, Any]]:
        """Get filter parameters."""
        return [
            {
                "name": "text",
                "type": "string",
                "default": "© PyPhotoManager",
                "label": "Watermark Text"
            },
            {
                "name": "position",
                "type": "choice",
                "choices": ["top-left", "top-right", "bottom-left", "bottom-right", "center"],
                "default": "bottom-right",
                "label": "Position"
            },
            {
                "name": "font_size",
                "type": "int",
                "min": 8,
                "max": 72,
                "default": 24,
                "label": "Font Size"
            },
            {
                "name": "opacity",
                "type": "float",
                "min": 0.1,
                "max": 1.0,
                "default": 0.7,
                "label": "Opacity"
            },
            {
                "name": "color",
                "type": "color",
                "default": "#ffffff",
                "label": "Text Color"
            },
            {
                "name": "padding",
                "type": "int",
                "min": 0,
                "max": 100,
                "default": 10,
                "label": "Padding"
            }
        ]
    
    def apply_filter(self, image_path: str, output_path: str, params: Dict[str, Any] = None) -> bool:
        """Apply watermark filter to an image."""
        try:
            # Use provided params or default settings
            filter_params = params or self.settings
            
            # Extract parameters
            text = filter_params.get("text", "© PyPhotoManager")
            position = filter_params.get("position", "bottom-right")
            font_size = filter_params.get("font_size", 24)
            opacity = filter_params.get("opacity", 0.7)
            color = filter_params.get("color", "#ffffff")
            padding = filter_params.get("padding", 10)
            
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGBA if needed
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                
                # Create transparent overlay for watermark
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # Try to use a system font
                try:
                    # Try to find a suitable font
                    font_paths = [
                        # Windows fonts
                        "C:/Windows/Fonts/arial.ttf",
                        "C:/Windows/Fonts/calibri.ttf",
                        # macOS fonts
                        "/System/Library/Fonts/Helvetica.ttc",
                        "/System/Library/Fonts/Arial.ttf",
                        # Linux fonts
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/TTF/Arial.ttf"
                    ]
                    
                    font = None
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            font = ImageFont.truetype(font_path, font_size)
                            break
                    
                    # If no system font found, use default
                    if font is None:
                        font = ImageFont.load_default()
                        self.logger.warning("Could not find system font, using default")
                        
                except Exception as e:
                    self.logger.warning(f"Error loading font: {str(e)}, using default")
                    font = ImageFont.load_default()
                
                # Calculate text size
                text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else (font.getsize(text) if hasattr(font, 'getsize') else (font_size * len(text) * 0.6, font_size * 1.2))
                
                # Calculate position
                if position == "top-left":
                    pos = (padding, padding)
                elif position == "top-right":
                    pos = (img.width - text_width - padding, padding)
                elif position == "bottom-left":
                    pos = (padding, img.height - text_height - padding)
                elif position == "bottom-right":
                    pos = (img.width - text_width - padding, img.height - text_height - padding)
                else:  # center
                    pos = ((img.width - text_width) // 2, (img.height - text_height) // 2)
                
                # Convert color from hex to RGB
                if color.startswith('#'):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    color_rgb = (r, g, b)
                else:
                    color_rgb = (255, 255, 255)  # default to white
                
                # Add alpha channel for opacity
                color_rgba = color_rgb + (int(255 * opacity),)
                
                # Draw text on overlay
                try:
                    # For newer Pillow versions
                    draw.text(pos, text, font=font, fill=color_rgba)
                except TypeError:
                    # For older Pillow versions that don't support RGBA fill
                    draw.text(pos, text, font=font, fill=color_rgb)
                
                # Composite the overlay with the original image
                watermarked = Image.alpha_composite(img, overlay)
                
                # Convert back to RGB if the output format doesn't support alpha
                output_ext = os.path.splitext(output_path)[1].lower()
                if output_ext in ['.jpg', '.jpeg', '.bmp']:
                    watermarked = watermarked.convert('RGB')
                
                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Save result
                watermarked.save(output_path)
            
            self.logger.info("Applied watermark filter", 
                           input=image_path, 
                           output=output_path,
                           text=text,
                           position=position)
            return True
            
        except Exception as e:
            self.logger.error("Failed to apply watermark filter", 
                            path=image_path, 
                            error=str(e))
            return False
    
    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions provided by this plugin."""
        return [
            {
                "menu": "Filters",
                "title": "Add Watermark",
                "action": "apply_watermark"
            }
        ]
    
    def get_settings(self) -> Dict[str, Any]:
        """Get plugin settings."""
        return self.settings
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Update plugin settings."""
        self.settings.update(settings)
        return True