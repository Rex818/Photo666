"""
Directory scanner for automatically finding and importing images.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Set, Generator
import structlog


class DirectoryScanner:
    """Scans directories for image files."""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = structlog.get_logger("picman.core.directory_scanner")
        
        # Default supported formats if not specified in config
        self.supported_formats = self.config.get("import_settings.supported_formats", 
                                               ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'])
    
    def scan_directory(self, directory_path: str, recursive: bool = True) -> Generator[Path, None, None]:
        """
        Scan a directory for image files.
        
        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Generator yielding paths to image files
        """
        try:
            directory = Path(directory_path)
            
            if not directory.exists() or not directory.is_dir():
                self.logger.error("Directory not found", path=str(directory))
                return
            
            # Walk through directory
            if recursive:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = Path(root) / file
                        if self._is_supported_file(file_path):
                            yield file_path
            else:
                # Non-recursive scan
                for item in directory.iterdir():
                    if item.is_file() and self._is_supported_file(item):
                        yield item
                        
            self.logger.info("Directory scan completed", path=str(directory))
            
        except Exception as e:
            self.logger.error("Error scanning directory", 
                            path=str(directory_path), 
                            error=str(e))
    
    def find_image_directories(self, root_path: str, min_images: int = 5) -> List[Dict[str, Any]]:
        """
        Find directories containing images.
        
        Args:
            root_path: Root directory to start search
            min_images: Minimum number of images required to consider a directory
            
        Returns:
            List of dictionaries with directory info
        """
        try:
            root = Path(root_path)
            if not root.exists() or not root.is_dir():
                self.logger.error("Root directory not found", path=str(root))
                return []
            
            result = []
            
            for dir_path, _, files in os.walk(root):
                dir_obj = Path(dir_path)
                
                # Skip hidden directories
                if dir_obj.name.startswith('.'):
                    continue
                
                # Count image files
                image_count = sum(1 for f in files if self._is_supported_extension(Path(f).suffix))
                
                if image_count >= min_images:
                    result.append({
                        "path": dir_path,
                        "name": dir_obj.name,
                        "image_count": image_count,
                        "parent": str(dir_obj.parent)
                    })
            
            # Sort by image count (descending)
            result.sort(key=lambda x: x["image_count"], reverse=True)
            
            self.logger.info("Found image directories", 
                           count=len(result), 
                           root=str(root))
            
            return result
            
        except Exception as e:
            self.logger.error("Error finding image directories", 
                            path=str(root_path), 
                            error=str(e))
            return []
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        return file_path.is_file() and self._is_supported_extension(file_path.suffix)
    
    def _is_supported_extension(self, extension: str) -> bool:
        """Check if file extension is supported."""
        return extension.lower() in self.supported_formats