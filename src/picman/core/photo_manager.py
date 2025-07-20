"""
Core photo management functionality.
"""

import hashlib
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import structlog
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS

from ..database.manager import DatabaseManager
from ..config.manager import ConfigManager
from .thumbnail_generator import ThumbnailGenerator
from .directory_scanner import DirectoryScanner


class PhotoManager:
    """Core photo management class."""
    
    def __init__(self, config_manager: ConfigManager, db_manager: DatabaseManager):
        self.config = config_manager
        self.db = db_manager
        self.thumbnail_gen = ThumbnailGenerator(config_manager)
        self.directory_scanner = DirectoryScanner(config_manager)
        self.logger = structlog.get_logger("picman.core.photo_manager")
        
    def import_photo(self, file_path: str) -> Optional[int]:
        """Import a single photo into the database."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.error("File not found", path=str(file_path))
                return None
            
            # Check if file is supported
            if not self._is_supported_format(file_path):
                self.logger.warning("Unsupported file format", path=str(file_path))
                return None
            
            # Check for duplicates
            file_hash = self._calculate_file_hash(file_path)
            existing_photo = self._find_by_hash(file_hash)
            
            if existing_photo:
                # 检查文件路径是否发生变化
                current_filepath = str(file_path.absolute())
                stored_filepath = existing_photo["filepath"]
                
                if current_filepath != stored_filepath:
                    # 文件路径发生变化，更新数据库中的路径
                    self.logger.info("Photo file moved, updating path", 
                                   old_path=stored_filepath,
                                   new_path=current_filepath,
                                   photo_id=existing_photo["id"])
                    
                    # 更新文件路径和文件大小
                    update_data = {
                        "filepath": current_filepath,
                        "file_size": file_path.stat().st_size,
                        "date_modified": datetime.now().isoformat()
                    }
                    
                    # 如果缩略图不存在，重新生成
                    if not existing_photo.get("thumbnail_path") or not Path(existing_photo["thumbnail_path"]).exists():
                        if self.config.get("thumbnail.generate_on_import", True):
                            thumbnail_path = self.thumbnail_gen.generate_thumbnail(file_path)
                            if thumbnail_path:
                                update_data["thumbnail_path"] = thumbnail_path
                                self.logger.info("Regenerated thumbnail for moved file", 
                                               photo_id=existing_photo["id"])
                    
                    # 更新数据库
                    if self.db.update_photo(existing_photo["id"], update_data):
                        self.logger.info("Successfully updated photo path", 
                                       photo_id=existing_photo["id"])
                    else:
                        self.logger.error("Failed to update photo path", 
                                        photo_id=existing_photo["id"])
                else:
                    self.logger.info("Photo already exists at same location", path=str(file_path))
                
                return existing_photo["id"]
            
            # Extract image metadata
            metadata = self._extract_metadata(file_path)
            
            # Generate thumbnail
            thumbnail_path = None
            if self.config.get("thumbnail.generate_on_import", True):
                thumbnail_path = self.thumbnail_gen.generate_thumbnail(file_path)
            
            # Prepare photo data
            photo_data = {
                "filename": file_path.name,
                "filepath": str(file_path.absolute()),
                "file_size": file_path.stat().st_size,
                "file_hash": file_hash,
                "width": metadata.get("width", 0),
                "height": metadata.get("height", 0),
                "format": metadata.get("format", ""),
                "date_taken": metadata.get("date_taken", ""),
                "exif_data": metadata.get("exif_data", {}),
                "thumbnail_path": thumbnail_path or "",
                "rating": 0,
                "is_favorite": False,
                "tags": [],
                "notes": ""
            }
            
            # Add to database
            photo_id = self.db.add_photo(photo_data)
            
            self.logger.info("Photo imported successfully", 
                           photo_id=photo_id, 
                           filename=file_path.name)
            
            return photo_id
            
        except Exception as e:
            self.logger.error("Failed to import photo", 
                            path=str(file_path), 
                            error=str(e))
            return None
    
    def import_directory(self, directory_path: str, recursive: bool = True, album_id: Optional[int] = None, tag_settings: Optional[dict] = None) -> Dict[str, Any]:
        """Import all photos from a directory."""
        try:
            directory = Path(directory_path)
            
            if not directory.exists() or not directory.is_dir():
                self.logger.error("Directory not found", path=str(directory))
                return {"success": False, "error": "Directory not found"}
            
            imported_count = 0
            skipped_count = 0
            error_count = 0
            imported_photo_ids = []
            
            # Use directory scanner to find image files
            for file_path in self.directory_scanner.scan_directory(directory_path, recursive):
                if tag_settings and tag_settings.get("import_tags", False):
                    # 使用带标签的导入方法
                    result = self.import_photo_with_tags(str(file_path), tag_settings)
                else:
                    # 使用普通导入方法
                    result = self.import_photo(str(file_path))
                
                if result:
                    imported_count += 1
                    imported_photo_ids.append(result)
                elif result is None:
                    error_count += 1
                else:
                    skipped_count += 1
            
            # Associate imported photos with album if album_id is provided
            if album_id and imported_photo_ids:
                for photo_id in imported_photo_ids:
                    self.db.add_photo_to_album(photo_id, album_id)
                self.logger.info("Associated photos with album", 
                               album_id=album_id, 
                               photo_count=len(imported_photo_ids))
            
            result = {
                "success": True,
                "imported": imported_count,
                "skipped": skipped_count,
                "errors": error_count,
                "total_processed": imported_count + skipped_count + error_count
            }
            
            self.logger.info("Directory import completed", **result)
            return result
            
        except Exception as e:
            self.logger.error("Failed to import directory", 
                            path=str(directory_path), 
                            error=str(e))
            return {"success": False, "error": str(e)}
    
    def import_photos_from_directory(self, directory_path: str, recursive: bool = True, album_id: int = None) -> int:
        """Import photos from directory and return the count of imported photos.
        
        Args:
            directory_path: Path to the directory containing photos
            recursive: Whether to scan subdirectories recursively
            album_id: Optional album ID to associate photos with
            
        Returns:
            Number of successfully imported photos
        """
        result = self.import_directory(directory_path, recursive)
        if result["success"]:
            imported_count = result["imported"]
            
            # If album_id is provided, associate imported photos with the album
            if album_id and imported_count > 0:
                self._associate_photos_with_album(album_id, directory_path)
            
            return imported_count
        else:
            self.logger.error("Failed to import photos from directory", 
                            directory=directory_path, 
                            error=result.get("error"))
            return 0
    
    def _associate_photos_with_album(self, album_id: int, directory_path: str):
        """Associate photos from a directory with an album.
        
        Args:
            album_id: Album ID to associate photos with
            directory_path: Directory path to find photos
        """
        try:
            # Get photos from the directory
            photos = self.search_photos(directory_path=directory_path)
            
            # Associate each photo with the album
            for photo in photos:
                self.db.add_photo_to_album(photo["id"], album_id)
            
            self.logger.info("Photos associated with album", 
                           album_id=album_id, 
                           photo_count=len(photos))
            
        except Exception as e:
            self.logger.error("Failed to associate photos with album", 
                            album_id=album_id, 
                            directory=directory_path, 
                            error=str(e))
    
    def get_photo_info(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed photo information."""
        return self.db.get_photo(photo_id)
    
    def update_photo_rating(self, photo_id: int, rating: int) -> bool:
        """Update photo rating (0-5 stars)."""
        if not 0 <= rating <= 5:
            self.logger.error("Invalid rating value", rating=rating)
            return False
        
        return self.db.update_photo(photo_id, {"rating": rating})
    
    def toggle_favorite(self, photo_id: int) -> bool:
        """Toggle photo favorite status."""
        photo = self.db.get_photo(photo_id)
        if not photo:
            return False
        
        new_status = not photo["is_favorite"]
        return self.db.update_photo(photo_id, {"is_favorite": new_status})
    
    def add_tags(self, photo_id: int, tags: List[str]) -> bool:
        """Add tags to a photo."""
        photo = self.db.get_photo(photo_id)
        if not photo:
            return False
        
        current_tags = set(photo["tags"])
        current_tags.update(tags)
        
        return self.db.update_photo(photo_id, {"tags": list(current_tags)})
    
    def remove_tags(self, photo_id: int, tags: List[str]) -> bool:
        """Remove tags from a photo."""
        photo = self.db.get_photo(photo_id)
        if not photo:
            return False
        
        current_tags = set(photo["tags"])
        current_tags.difference_update(tags)
        
        return self.db.update_photo(photo_id, {"tags": list(current_tags)})
    
    def search_photos(self, **kwargs) -> List[Dict[str, Any]]:
        """Search photos with various filters.
        
        Args:
            **kwargs: Various search parameters including:
                - query: Text search
                - tags: List of tags
                - rating_min: Minimum rating
                - favorites_only: Only favorites
                - directory_path: Photos from specific directory
                - limit: Maximum number of results
                - offset: Results offset
        
        Returns:
            List of matching photos
        """
        # Special handling for directory_path
        directory_path = kwargs.pop("directory_path", None)
        if directory_path:
            # Convert to consistent format for comparison
            directory_path = str(Path(directory_path))
            
            # Get all photos
            all_photos = self.db.search_photos(**kwargs)
            
            # Filter by directory
            return [photo for photo in all_photos 
                   if photo["filepath"].startswith(directory_path)]
        else:
            # Standard search
            return self.db.search_photos(**kwargs)
    
    def delete_photo(self, photo_id: int, delete_file: bool = False) -> bool:
        """Delete photo from database and optionally from disk."""
        try:
            photo = self.db.get_photo(photo_id)
            if not photo:
                return False
            
            # Delete from database
            if not self.db.delete_photo(photo_id):
                return False
            
            # Delete file from disk if requested
            if delete_file:
                file_path = Path(photo["filepath"])
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info("Photo file deleted", path=str(file_path))
                
                # Delete thumbnail
                if photo["thumbnail_path"]:
                    thumb_path = Path(photo["thumbnail_path"])
                    if thumb_path.exists():
                        thumb_path.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete photo", 
                            photo_id=photo_id, 
                            error=str(e))
            return False
    
    def _is_supported_format(self, file_path: Path) -> bool:
        """Check if file format is supported."""
        supported_formats = self.config.get("import_settings.supported_formats",
                                           ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'])
        return file_path.suffix.lower() in supported_formats
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _find_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Find photo by file hash."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM photos WHERE file_hash = ?", [file_hash])
                row = cursor.fetchone()
                if row:
                    photo_dict = dict(row)
                    photo_dict["exif_data"] = json.loads(photo_dict["exif_data"])
                    photo_dict["tags"] = json.loads(photo_dict["tags"])
                    return photo_dict
            return None
        except Exception as e:
            self.logger.error("Failed to find photo by hash", file_hash=file_hash, error=str(e))
            return None
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image file."""
        metadata = {
            "width": 0,
            "height": 0,
            "format": "",
            "date_taken": "",
            "exif_data": {}
        }
        
        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format or ""
                
                # Extract EXIF data
                if hasattr(img, '_getexif') and img._getexif():
                    exif_dict = {}
                    exif = img._getexif()
                    
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        # Convert non-serializable types for JSON serialization
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except UnicodeDecodeError:
                                value = str(value)
                        elif isinstance(value, (datetime, date)):
                            value = value.isoformat()
                        elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            value = str(value)
                        
                        exif_dict[tag] = value
                    
                    metadata["exif_data"] = exif_dict
                    
                    # Extract date taken
                    date_taken = exif_dict.get("DateTime") or exif_dict.get("DateTimeOriginal")
                    if date_taken:
                        try:
                            # Convert to ISO format
                            dt = datetime.strptime(date_taken, "%Y:%m:%d %H:%M:%S")
                            metadata["date_taken"] = dt.isoformat()
                        except ValueError:
                            pass
                
        except Exception as e:
            self.logger.warning("Failed to extract metadata", 
                              path=str(file_path), 
                              error=str(e))
        
        return metadata
    
    def find_original_image_by_hash(self, file_hash: str) -> Optional[str]:
        """Find original image file path by hash.
        
        Args:
            file_hash: SHA256 hash of the image file
            
        Returns:
            Original file path if found, None otherwise
        """
        try:
            # First check if we have this hash in database
            photo = self._find_by_hash(file_hash)
            if photo:
                file_path = photo["filepath"]
                # Check if file still exists
                if Path(file_path).exists():
                    return file_path
                else:
                    self.logger.warning("Original image file not found", 
                                      file_path=file_path, 
                                      file_hash=file_hash)
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to find original image by hash", 
                            file_hash=file_hash, 
                            error=str(e))
            return None
    
    def get_photo_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get photo information by hash, even if original file is missing.
        
        Args:
            file_hash: SHA256 hash of the image file
            
        Returns:
            Photo information dictionary or None if not found
        """
        return self._find_by_hash(file_hash)
    
    def update_photo_filepath(self, photo_id: int, new_filepath: str) -> bool:
        """Update photo filepath in database.
        
        Args:
            photo_id: Photo ID to update
            new_filepath: New file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            new_path = Path(new_filepath)
            if not new_path.exists():
                self.logger.error("New file path does not exist", path=new_filepath)
                return False
            
            # 验证文件哈希值是否匹配
            file_hash = self._calculate_file_hash(new_path)
            photo = self.db.get_photo(photo_id)
            if not photo:
                self.logger.error("Photo not found", photo_id=photo_id)
                return False
            
            if photo["file_hash"] != file_hash:
                self.logger.error("File hash mismatch", 
                                photo_id=photo_id,
                                expected_hash=photo["file_hash"],
                                actual_hash=file_hash)
                return False
            
            # 更新文件路径和相关信息
            update_data = {
                "filepath": str(new_path.absolute()),
                "file_size": new_path.stat().st_size,
                "date_modified": datetime.now().isoformat()
            }
            
            # 如果缩略图不存在，重新生成
            if not photo.get("thumbnail_path") or not Path(photo["thumbnail_path"]).exists():
                if self.config.get("thumbnail.generate_on_import", True):
                    thumbnail_path = self.thumbnail_gen.generate_thumbnail(new_path)
                    if thumbnail_path:
                        update_data["thumbnail_path"] = thumbnail_path
            
            # 更新数据库
            success = self.db.update_photo(photo_id, update_data)
            if success:
                self.logger.info("Successfully updated photo filepath", 
                               photo_id=photo_id,
                               new_path=str(new_path.absolute()))
            else:
                self.logger.error("Failed to update photo filepath", photo_id=photo_id)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to update photo filepath", 
                            photo_id=photo_id,
                            new_filepath=new_filepath,
                            error=str(e))
            return False
    
    def find_and_fix_missing_files(self) -> Dict[str, Any]:
        """Find photos with missing files and attempt to fix them.
        
        Returns:
            Dictionary with results of the operation
        """
        try:
            all_photos = self.db.search_photos(limit=10000)  # Get all photos
            missing_files = []
            fixed_files = []
            errors = []
            
            for photo in all_photos:
                file_path = Path(photo["filepath"])
                if not file_path.exists():
                    missing_files.append(photo)
                    
                    # 尝试通过文件名查找文件
                    found_file = self._find_file_by_name(photo["filename"], photo["file_hash"])
                    if found_file:
                        # 更新文件路径
                        if self.update_photo_filepath(photo["id"], str(found_file)):
                            fixed_files.append({
                                "photo_id": photo["id"],
                                "old_path": photo["filepath"],
                                "new_path": str(found_file)
                            })
                        else:
                            errors.append({
                                "photo_id": photo["id"],
                                "error": "Failed to update filepath"
                            })
            
            result = {
                "total_photos": len(all_photos),
                "missing_files": len(missing_files),
                "fixed_files": len(fixed_files),
                "errors": len(errors),
                "missing_photos": missing_files,
                "fixed_details": fixed_files,
                "error_details": errors
            }
            
            self.logger.info("File path check completed", **result)
            return result
            
        except Exception as e:
            self.logger.error("Failed to check missing files", error=str(e))
            return {
                "total_photos": 0,
                "missing_files": 0,
                "fixed_files": 0,
                "errors": 1,
                "error_details": [{"error": str(e)}]
            }
    
    def _find_file_by_name(self, filename: str, expected_hash: str) -> Optional[Path]:
        """Find a file by name and verify its hash.
        
        Args:
            filename: Name of the file to find
            expected_hash: Expected SHA256 hash of the file
            
        Returns:
            Path to the found file if hash matches, None otherwise
        """
        try:
            # 搜索常见的照片目录
            search_dirs = [
                Path.home() / "Pictures",
                Path.home() / "Photos", 
                Path.home() / "Images",
                Path.home() / "Desktop",
                Path.home() / "Downloads"
            ]
            
            # 添加用户配置的搜索目录
            user_dirs = self.config.get("file_search.directories", [])
            for user_dir in user_dirs:
                if Path(user_dir).exists():
                    search_dirs.append(Path(user_dir))
            
            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                
                # 递归搜索文件
                for file_path in search_dir.rglob(filename):
                    if file_path.is_file():
                        # 验证文件哈希值
                        try:
                            file_hash = self._calculate_file_hash(file_path)
                            if file_hash == expected_hash:
                                self.logger.info("Found missing file", 
                                               filename=filename,
                                               path=str(file_path))
                                return file_path
                        except Exception as e:
                            self.logger.warning("Failed to calculate hash for found file", 
                                              path=str(file_path),
                                              error=str(e))
                            continue
            
            self.logger.warning("Could not find file", filename=filename)
            return None
            
        except Exception as e:
            self.logger.error("Failed to search for file", 
                            filename=filename,
                            error=str(e))
            return None
    
    def import_photo_with_tags(self, file_path: str, tag_settings: dict = None) -> Optional[int]:
        """Import a photo with optional tag import.
        
        Args:
            file_path: Path to the photo file
            tag_settings: Tag import settings
            
        Returns:
            Photo ID if successful, None otherwise
        """
        try:
            # 首先导入照片
            photo_id = self.import_photo(file_path)
            if not photo_id:
                return None
            
            # 如果提供了标签设置，导入标签
            if tag_settings and tag_settings.get("import_tags", False):
                self._import_tags_for_photo(photo_id, file_path, tag_settings)
            
            return photo_id
            
        except Exception as e:
            self.logger.error("Failed to import photo with tags", 
                            path=str(file_path), 
                            error=str(e))
            return None
    
    def _import_tags_for_photo(self, photo_id: int, photo_path: str, tag_settings: dict):
        """Import tags for a specific photo.
        
        Args:
            photo_id: Photo ID
            photo_path: Path to the photo file
            tag_settings: Tag import settings
        """
        try:
            photo_path = Path(photo_path)
            tag_type = tag_settings.get("tag_type", "normal")
            
            # 查找对应的标签文件
            tag_file_path = self._find_tag_file(photo_path)
            if not tag_file_path:
                self.logger.info("No tag file found for photo", 
                               photo_id=photo_id,
                               photo_path=str(photo_path))
                return
            
            # 读取标签文件
            tags = self._read_tag_file(tag_file_path)
            if not tags:
                self.logger.warning("Tag file is empty or invalid", 
                                  tag_file=str(tag_file_path))
                return
            
            # 翻译标签（这里可以集成翻译服务）
            translated_tags = self._translate_tags(tags)
            
            # 准备标签数据
            tag_data = {
                "simple_tags": [],
                "normal_tags": [],
                "detailed_tags": []
            }
            
            # 根据标签类型分配标签
            if tag_type == "simple":
                tag_data["simple_tags"] = tags
            elif tag_type == "detailed":
                tag_data["detailed_tags"] = tags
            else:  # normal
                tag_data["normal_tags"] = tags
            
            # 更新照片的标签信息
            self._update_photo_tags(photo_id, tag_data, translated_tags)
            
            self.logger.info("Tags imported successfully", 
                           photo_id=photo_id,
                           tag_count=len(tags),
                           tag_type=tag_type)
            
        except Exception as e:
            self.logger.error("Failed to import tags for photo", 
                            photo_id=photo_id,
                            error=str(e))
    
    def _find_tag_file(self, photo_path: Path) -> Optional[Path]:
        """Find the corresponding tag file for a photo.
        
        Args:
            photo_path: Path to the photo file
            
        Returns:
            Path to the tag file if found, None otherwise
        """
        try:
            # 标签文件与照片文件同名，扩展名为.txt
            base_name = photo_path.stem
            tag_file = photo_path.parent / f"{base_name}.txt"
            
            if tag_file.exists():
                return tag_file
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to find tag file", 
                            photo_path=str(photo_path),
                            error=str(e))
            return None
    
    def _read_tag_file(self, tag_file_path: Path) -> List[str]:
        """Read tags from a tag file.
        
        Args:
            tag_file_path: Path to the tag file
            
        Returns:
            List of tags
        """
        try:
            tags = []
            with open(tag_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):  # 忽略空行和注释
                        tags.append(line)
            
            return tags
            
        except Exception as e:
            self.logger.error("Failed to read tag file", 
                            tag_file=str(tag_file_path),
                            error=str(e))
            return []
    
    def _translate_tags(self, tags: List[str]) -> Dict[str, str]:
        """翻译标签列表 - 使用插件系统"""
        try:
            translations = {}
            
            # 尝试使用Google翻译插件
            try:
                from ..plugins.google_translate_plugin import plugin_instance
                if plugin_instance.api_key:
                    translations = plugin_instance.translate_tags(tags)
                    self.logger.info("Tags translated using Google Translate plugin", count=len(tags))
                    return translations
            except Exception as e:
                self.logger.warning("Google Translate plugin not available", error=str(e))
            
            # 如果没有插件，使用内置翻译映射
            tag_translations = {
                "portrait": "人像",
                "landscape": "风景",
                "nature": "自然",
                "city": "城市",
                "architecture": "建筑",
                "street": "街道",
                "people": "人物",
                "animal": "动物",
                "flower": "花朵",
                "tree": "树木",
                "mountain": "山脉",
                "sea": "海洋",
                "sky": "天空",
                "sunset": "日落",
                "sunrise": "日出",
                "night": "夜晚",
                "day": "白天",
                "colorful": "彩色",
                "black_and_white": "黑白",
                "vintage": "复古",
                "modern": "现代",
                "abstract": "抽象",
                "minimalist": "极简",
                "artistic": "艺术",
                "professional": "专业",
                "amateur": "业余",
                "high_quality": "高质量",
                "low_quality": "低质量",
                "blur": "模糊",
                "sharp": "清晰",
                "bright": "明亮",
                "dark": "黑暗",
                "warm": "温暖",
                "cool": "冷色调",
                "happy": "快乐",
                "sad": "悲伤",
                "peaceful": "宁静",
                "energetic": "充满活力",
                "calm": "平静",
                "dynamic": "动态",
                "static": "静态"
            }
            
            for tag in tags:
                # 尝试直接匹配
                if tag in tag_translations:
                    translations[tag] = tag_translations[tag]
                else:
                    # 尝试匹配部分关键词
                    translated = None
                    for key, value in tag_translations.items():
                        if key in tag.lower() or tag.lower() in key:
                            translated = value
                            break
                    
                    if translated:
                        translations[tag] = translated
                    else:
                        # 如果没有找到翻译，使用原文
                        translations[tag] = tag
            
            self.logger.info("Tags translated using built-in mapping", count=len(tags))
            return translations
            
        except Exception as e:
            self.logger.error("Failed to translate tags", error=str(e))
            # 返回原标签作为翻译
            return {tag: tag for tag in tags}
    
    def _update_photo_tags(self, photo_id: int, tag_data: dict, translated_tags: dict):
        """Update photo with tag information.
        
        Args:
            photo_id: Photo ID
            tag_data: Tag data organized by type
            translated_tags: Dictionary of tag translations
        """
        try:
            # 获取现有照片信息
            photo = self.db.get_photo(photo_id)
            if not photo:
                return
            
            # 准备更新数据
            update_data = {}
            
            # 更新标签数据
            if tag_data.get("simple_tags"):
                update_data["simple_tags"] = tag_data["simple_tags"]
            if tag_data.get("normal_tags"):
                update_data["normal_tags"] = tag_data["normal_tags"]
            if tag_data.get("detailed_tags"):
                update_data["detailed_tags"] = tag_data["detailed_tags"]
            
            # 更新翻译数据
            update_data["tag_translations"] = translated_tags
            
            # 更新数据库
            if update_data:
                self.db.update_photo(photo_id, update_data)
                self.logger.info("Photo tags updated", 
                               photo_id=photo_id,
                               update_data=update_data)
            
        except Exception as e:
            self.logger.error("Failed to update photo tags", 
                            photo_id=photo_id,
                            error=str(e))
    
    def get_photo_tags(self, photo_id: int) -> dict:
        """Get all tags for a photo.
        
        Args:
            photo_id: Photo ID
            
        Returns:
            Dictionary containing all tag information
        """
        try:
            photo = self.db.get_photo(photo_id)
            if not photo:
                return {}
            
            return {
                "simple_tags": photo.get("simple_tags", []),
                "normal_tags": photo.get("normal_tags", []),
                "detailed_tags": photo.get("detailed_tags", []),
                "tag_translations": photo.get("tag_translations", {}),
                "tags": photo.get("tags", [])  # 原有的标签系统
            }
            
        except Exception as e:
            self.logger.error("Failed to get photo tags", 
                            photo_id=photo_id,
                            error=str(e))
            return {}