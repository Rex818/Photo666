"""
Database manager for PyPhotoManager.
Handles SQLite database operations and schema management.
"""

import sqlite3
import sqlite_utils
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import json
# import structlog  # 已移除，使用标准logging
import logging
from contextlib import contextmanager
import threading
import time
from functools import lru_cache


def safe_json_dumps(obj):
    """Safely serialize object to JSON, handling non-serializable types."""
    def convert(obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif not isinstance(obj, (str, int, float, bool, list, dict, type(None))):
            return str(obj)
        return obj
    
    def recursive_convert(obj):
        if isinstance(obj, dict):
            return {k: recursive_convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [recursive_convert(item) for item in obj]
        else:
            return convert(obj)
    
    return json.dumps(recursive_convert(obj))


class UnifiedTagsAccessor:
    """统一标签访问器 - 提供智能读写统一标签字段"""
    
    @staticmethod
    def read_unified_tags(photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """智能读取标签数据 - 优先分离字段（最新数据），降级到统一字段"""
        try:
            # 首先检查分离字段是否有最新数据
            separate_fields_data = UnifiedTagsAccessor._build_from_separate_fields(photo_data)
            
            # 检查分离字段是否有中文内容（翻译结果）
            has_chinese_content = any([
                separate_fields_data["simple"]["zh"],
                separate_fields_data["normal"]["zh"], 
                separate_fields_data["detailed"]["zh"]
            ])
            
            # 如果有中文内容，说明有最新的翻译结果，优先使用分离字段
            if has_chinese_content:
                print(f"🔍 使用分离字段数据（包含最新翻译）: {has_chinese_content}")
                return separate_fields_data
            
            # 如果没有中文内容，尝试从统一字段读取
            unified_tags_str = photo_data.get("unified_tags")
            if unified_tags_str and unified_tags_str.strip():
                try:
                    unified_tags = json.loads(unified_tags_str)
                    print(f"🔍 使用统一字段数据: 无中文内容")
                    return unified_tags
                except json.JSONDecodeError:
                    pass
            
            # 最后使用分离字段
            print(f"🔍 使用分离字段数据（默认）")
            return separate_fields_data
            
        except Exception as e:
            print(f"🔍 读取统一标签失败: {e}")
            return UnifiedTagsAccessor._get_empty_structure()
    
    @staticmethod
    def _build_from_separate_fields(photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """从分离字段构建统一结构"""
        try:
            unified_tags = {
                "simple": {
                    "en": UnifiedTagsAccessor._normalize_field(photo_data.get("simple_tags_en", "")),
                    "zh": UnifiedTagsAccessor._normalize_field(photo_data.get("simple_tags_cn", ""))
                },
                "normal": {
                    "en": UnifiedTagsAccessor._normalize_field(photo_data.get("general_tags_en", "")),
                    "zh": UnifiedTagsAccessor._normalize_field(photo_data.get("general_tags_cn", ""))
                },
                "detailed": {
                    "en": UnifiedTagsAccessor._normalize_field(photo_data.get("detailed_tags_en", "")),
                    "zh": UnifiedTagsAccessor._normalize_field(photo_data.get("detailed_tags_cn", ""))
                },
                "notes": UnifiedTagsAccessor._normalize_field(photo_data.get("notes", "")),
                "metadata": {
                    "source": "separate_fields",
                    "last_updated": datetime.now().isoformat()
                }
            }
            return unified_tags
        except Exception:
            return UnifiedTagsAccessor._get_empty_structure()
    
    @staticmethod
    def _normalize_field(field_value: Any) -> str:
        """规范化字段值"""
        if not field_value:
            return ""
        
        if isinstance(field_value, str):
            # 处理JSON数组格式
            if field_value.startswith('[') and field_value.endswith(']'):
                try:
                    tag_list = json.loads(field_value)
                    if isinstance(tag_list, list):
                        return ', '.join(str(tag) for tag in tag_list if tag)
                except json.JSONDecodeError:
                    pass
            return field_value.strip()
        
        return str(field_value).strip()
    
    @staticmethod
    def _get_empty_structure() -> Dict[str, Any]:
        """获取空的统一标签结构"""
        return {
            "simple": {"en": "", "zh": ""},
            "normal": {"en": "", "zh": ""},
            "detailed": {"en": "", "zh": ""},
            "notes": "",
            "metadata": {
                "source": "empty",
                "last_updated": datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def write_unified_tags(unified_tags: Dict[str, Any]) -> Dict[str, Any]:
        """将统一标签结构转换为数据库更新字典 - 双写策略"""
        try:
            print(f"🔍 开始处理统一标签写入: {unified_tags}")
            
            # 验证和规范化统一标签结构
            normalized_tags = UnifiedTagsAccessor._validate_and_normalize(unified_tags)
            print(f"🔍 规范化后的标签: {normalized_tags}")
            
            # 构建更新字典 - 双写：统一字段 + 分离字段
            updates = {
                # 新的统一字段
                "unified_tags": json.dumps(normalized_tags, ensure_ascii=False),
                
                # 兼容的分离字段
                "simple_tags_en": normalized_tags["simple"]["en"],
                "simple_tags_cn": normalized_tags["simple"]["zh"],
                "general_tags_en": normalized_tags["normal"]["en"], 
                "general_tags_cn": normalized_tags["normal"]["zh"],
                "detailed_tags_en": normalized_tags["detailed"]["en"],
                "detailed_tags_cn": normalized_tags["detailed"]["zh"],
                "notes": normalized_tags["notes"]
            }
            
            print(f"🔍 生成的更新字典: {updates}")
            return updates
            
        except Exception as e:
            print(f"❌ 统一标签写入失败: {str(e)}")
            raise
    
    @staticmethod
    def _validate_and_normalize(unified_tags: Dict[str, Any]) -> Dict[str, Any]:
        """验证和规范化统一标签结构"""
        try:
            # 确保基本结构存在
            normalized = {
                "simple": {"en": "", "zh": ""},
                "normal": {"en": "", "zh": ""},
                "detailed": {"en": "", "zh": ""},
                "notes": "",
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "source": "unified_write"
                }
            }
            
            # 安全地复制用户数据
            if isinstance(unified_tags, dict):
                for category in ["simple", "normal", "detailed"]:
                    if category in unified_tags and isinstance(unified_tags[category], dict):
                        for lang in ["en", "zh"]:
                            if lang in unified_tags[category]:
                                content = str(unified_tags[category][lang]).strip()
                                # 验证长度限制 (2048字节)
                                if len(content.encode('utf-8')) > 2048:
                                    content_bytes = content.encode('utf-8')
                                    content = content_bytes[:2045].decode('utf-8', errors='ignore') + '...'
                                normalized[category][lang] = content
                
                # 处理备注字段
                if "notes" in unified_tags:
                    notes = str(unified_tags["notes"]).strip()
                    if len(notes.encode('utf-8')) > 2048:
                        notes_bytes = notes.encode('utf-8')
                        notes = notes_bytes[:2045].decode('utf-8', errors='ignore') + '...'
                    normalized["notes"] = notes
                
                # 保留用户元数据
                if "metadata" in unified_tags and isinstance(unified_tags["metadata"], dict):
                    normalized["metadata"].update(unified_tags["metadata"])
                    normalized["metadata"]["last_updated"] = datetime.now().isoformat()
            
            return normalized
            
        except Exception as e:
            raise


class DatabaseManager:
    """Manages SQLite database operations for photo management."""
    
    def __init__(self, db_path: str, config=None):
        self.db_path = Path(db_path)
        self.config = config
        self.logger = logging.getLogger("picman.database")
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def execute(self, query: str, params: tuple = None) -> bool:
        """Execute SQL query with unified tags compatibility layer."""
        try:
            # 检查是否是标签字段更新操作
            if query.strip().upper().startswith("UPDATE PHOTOS SET") and params:
                self.logger.debug("Checking compatibility layer for UPDATE photos SET query")
                return self._handle_compatible_update(query, params)
            
            # 普通查询执行
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to execute query: {str(e)}")
            return False
    
    def _handle_compatible_update(self, query: str, params: tuple) -> bool:
        """处理兼容性标签字段更新 - 为Florence2等插件提供支持"""
        try:
            # 解析UPDATE语句以确定更新的字段
            import re
            
            # 匹配 "UPDATE photos SET field_name = ? WHERE id = ?" 格式
            match = re.match(r'UPDATE\s+photos\s+SET\s+(\w+)\s*=\s*\?\s+WHERE\s+id\s*=\s*\?', query, re.IGNORECASE)
            
            if match and len(params) == 2:
                field_name = match.group(1)
                field_value, photo_id = params
                
                # 标签字段映射
                tag_fields = {
                    "simple_tags_en", "simple_tags_cn",
                    "general_tags_en", "general_tags_cn", 
                    "detailed_tags_en", "detailed_tags_cn",
                    "notes"
                }
                
                if field_name in tag_fields:
                    self.logger.debug(f"Intercepted tag field update for compatibility: field={field_name}, photo_id={photo_id}")
                    return self._update_tag_field_with_sync(photo_id, field_name, field_value)
            
            # 不是标签字段更新，直接执行
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to handle compatible update: {str(e)}")
            return False
    
    def _update_tag_field_with_sync(self, photo_id: int, field_name: str, field_value: str) -> bool:
        """更新标签字段并同步到统一字段"""
        try:
            # 获取当前照片数据
            photo_data = self.get_photo(photo_id)
            if not photo_data:
                self.logger.error(f"Photo not found for sync update: photo_id={photo_id}")
                return False
            
            # 获取当前统一标签
            unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_data)
            
            # 字段映射
            field_mapping = {
                "simple_tags_en": ("simple", "en"),
                "simple_tags_cn": ("simple", "zh"),
                "general_tags_en": ("normal", "en"),
                "general_tags_cn": ("normal", "zh"),
                "detailed_tags_en": ("detailed", "en"),
                "detailed_tags_cn": ("detailed", "zh"),
                "notes": ("notes", None)
            }
            
            if field_name in field_mapping:
                category, lang = field_mapping[field_name]
                
                # 更新统一结构
                if lang:
                    if category not in unified_tags:
                        unified_tags[category] = {"en": "", "zh": ""}
                    unified_tags[category][lang] = str(field_value).strip()
                else:
                    unified_tags[category] = str(field_value).strip()
                
                # 直接使用低级API更新，避免递归调用
                updates = UnifiedTagsAccessor.write_unified_tags(unified_tags)
                
                # 直接数据库更新，不通过update_photo避免递归
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 构建UPDATE语句
                    set_clauses = []
                    values = []
                    for key, value in updates.items():
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                    
                    set_clauses.append("date_modified = ?")
                    values.append(datetime.now().isoformat())
                    values.append(photo_id)
                    
                    query = f"UPDATE photos SET {', '.join(set_clauses)} WHERE id = ?"
                    cursor.execute(query, values)
                    conn.commit()
                
                self.logger.debug(f"Successfully synced tag field update: photo_id={photo_id}, field={field_name}")
                return True
            else:
                # 非标签字段，直接更新
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"UPDATE photos SET {field_name} = ? WHERE id = ?", (field_value, photo_id))
                    conn.commit()
                    return True
                
        except Exception as e:
            self.logger.error(f"Failed to update tag field with sync: photo_id={photo_id}, field={field_name}, error={str(e)}")
            return False
    
    def _init_database(self):
        """Initialize database with required tables."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Photos table
            if not db["photos"].exists():
                db["photos"].create({
                    "id": int,
                    "filename": str,
                    "filepath": str,
                    "file_size": int,
                    "file_hash": str,
                    "width": int,
                    "height": int,
                    "format": str,
                    "date_taken": str,
                    "date_added": str,
                    "date_modified": str,
                    "exif_data": str,  # JSON string
                    "ai_metadata": str,  # JSON string - AI元数据
                    "is_ai_generated": bool,  # 是否为AI生成
                    "tags": str,       # JSON array
                    "simple_tags": str,    # JSON array - 简单标签
                    "normal_tags": str,    # JSON array - 普通标签
                    "detailed_tags": str,  # JSON array - 详细标签
                    "tag_translations": str,  # JSON object - 标签翻译
                    "rating": int,
                    "is_favorite": bool,
                    "thumbnail_path": str,
                    "notes": str
                }, pk="id")
                
                # Create indexes for performance optimization
                db["photos"].create_index(["filepath"], unique=True)
                db["photos"].create_index(["file_hash"])
                db["photos"].create_index(["date_taken"])
                db["photos"].create_index(["rating"])
                db["photos"].create_index(["is_favorite"])
                # Additional performance indexes
                db["photos"].create_index(["filename"])
                db["photos"].create_index(["file_size"])
                db["photos"].create_index(["date_taken", "rating"])  # Composite index for sorting
                db["photos"].create_index(["is_favorite", "rating"])  # For favorite photos sorting
            else:
                # 检查是否需要添加新字段
                self._add_new_columns_if_needed(db)
            
            # Albums table
            if not db["albums"].exists():
                db["albums"].create({
                    "id": int,
                    "name": str,
                    "description": str,
                    "created_date": str,
                    "cover_photo_id": int,
                    "photo_count": int
                }, pk="id")
                
                db["albums"].create_index(["name"], unique=True)
            
            # Album photos junction table
            if not db["album_photos"].exists():
                db["album_photos"].create({
                    "album_id": int,
                    "photo_id": int,
                    "added_date": str
                }, pk=["album_id", "photo_id"])
                
                db["album_photos"].add_foreign_key("album_id", "albums", "id")
                db["album_photos"].add_foreign_key("photo_id", "photos", "id")
            
            # Tags table
            if not db["tags"].exists():
                db["tags"].create({
                    "id": int,
                    "name": str,
                    "color": str,
                    "usage_count": int
                }, pk="id")
                
                db["tags"].create_index(["name"], unique=True)
            
            # Settings table
            if not db["settings"].exists():
                db["settings"].create({
                    "key": str,
                    "value": str,
                    "updated_date": str
                }, pk="key")
            
            self.logger.info(f"Database initialized successfully: {str(self.db_path)}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def _add_new_columns_if_needed(self, db):
        """Add new columns to existing photos table if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查新字段是否存在
                cursor.execute("PRAGMA table_info(photos)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # 需要添加的新字段
                new_columns = [
                    ("simple_tags", "TEXT DEFAULT '[]'"),
                    ("normal_tags", "TEXT DEFAULT '[]'"),
                    ("detailed_tags", "TEXT DEFAULT '[]'"),
                    ("tag_translations", "TEXT DEFAULT '{}'"),
                    ("ai_metadata", "TEXT DEFAULT '{}'"),
                    ("is_ai_generated", "BOOLEAN DEFAULT 0"),
                    # 新的分离式标签字段
                    ("simple_tags_en", "TEXT DEFAULT ''"),
                    ("simple_tags_cn", "TEXT DEFAULT ''"),
                    ("general_tags_en", "TEXT DEFAULT ''"),
                    ("general_tags_cn", "TEXT DEFAULT ''"),
                    ("detailed_tags_en", "TEXT DEFAULT ''"),
                    ("detailed_tags_cn", "TEXT DEFAULT ''"),
                    ("positive_prompt", "TEXT DEFAULT ''"),
                    ("negative_prompt", "TEXT DEFAULT ''")
                ]
                
                for column_name, column_def in new_columns:
                    if column_name not in columns:
                        cursor.execute(f"ALTER TABLE photos ADD COLUMN {column_name} {column_def}")
                        self.logger.info(f"Added new column to photos table: {column_name}")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to add new columns: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_photo(self, photo_data: Dict[str, Any]) -> int:
        """Add a new photo to the database."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Prepare photo data
            photo_record = {
                "filename": photo_data["filename"],
                "filepath": photo_data["filepath"],
                "file_size": photo_data.get("file_size", 0),
                "file_hash": photo_data.get("file_hash", ""),
                "width": photo_data.get("width", 0),
                "height": photo_data.get("height", 0),
                "format": photo_data.get("format", ""),
                "date_taken": photo_data.get("date_taken", ""),
                "date_added": datetime.now().isoformat(),
                "date_modified": datetime.now().isoformat(),
                "exif_data": safe_json_dumps(photo_data.get("exif_data", {})),
                "tags": safe_json_dumps(photo_data.get("tags", [])),
                "simple_tags": safe_json_dumps(photo_data.get("simple_tags", [])),
                "normal_tags": safe_json_dumps(photo_data.get("normal_tags", [])),
                "detailed_tags": safe_json_dumps(photo_data.get("detailed_tags", [])),
                "tag_translations": safe_json_dumps(photo_data.get("tag_translations", {})),
                "ai_metadata": safe_json_dumps(photo_data.get("ai_metadata", {})),
                "is_ai_generated": photo_data.get("is_ai_generated", False),
                "rating": photo_data.get("rating", 0),
                "is_favorite": photo_data.get("is_favorite", False),
                "thumbnail_path": photo_data.get("thumbnail_path", ""),
                "notes": photo_data.get("notes", "")
            }
            
            result = db["photos"].insert(photo_record)
            photo_id = result.last_pk
            
            self.logger.info(f"Photo added to database: ID {photo_id}, filename {photo_data['filename']}")
            
            return photo_id
            
        except Exception as e:
            self.logger.error(f"Failed to add photo {photo_data.get('filename', 'unknown')}: {str(e)}")
            raise
    
    def get_photo(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """Get photo by ID."""
        try:
            db = sqlite_utils.Database(self.db_path)
            photo = db["photos"].get(photo_id)
            
            if photo:
                # Parse JSON fields
                photo_dict = dict(photo)
                photo_dict["exif_data"] = json.loads(photo_dict["exif_data"])
                photo_dict["tags"] = json.loads(photo_dict["tags"])
                
                # 使用统一标签系统读取标签数据
                try:
                    unified_tags = UnifiedTagsAccessor.read_unified_tags(photo_dict)
                    
                    # 为向后兼容，保持原有字段格式
                    photo_dict["unified_tags_data"] = unified_tags
                    
                    # 同时保持分离字段的访问方式（从统一数据中提取）
                    photo_dict["simple_tags_en"] = unified_tags.get("simple", {}).get("en", "")
                    photo_dict["simple_tags_cn"] = unified_tags.get("simple", {}).get("zh", "")
                    photo_dict["general_tags_en"] = unified_tags.get("normal", {}).get("en", "")
                    photo_dict["general_tags_cn"] = unified_tags.get("normal", {}).get("zh", "")
                    photo_dict["detailed_tags_en"] = unified_tags.get("detailed", {}).get("en", "")
                    photo_dict["detailed_tags_cn"] = unified_tags.get("detailed", {}).get("zh", "")
                    
                except Exception as e:
                    self.logger.error(f"Failed to read unified tags for photo {photo_dict.get('id')}: {str(e)}")
                    # 降级到传统解析方式
                    unified_tags = UnifiedTagsAccessor._get_empty_structure()
                    photo_dict["unified_tags_data"] = unified_tags
                
                # 解析传统标签字段 - 保持向后兼容
                try:
                    simple_tags_raw = photo_dict.get("simple_tags", "[]")
                    photo_dict["simple_tags"] = json.loads(simple_tags_raw) if simple_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["simple_tags"] = []
                
                try:
                    normal_tags_raw = photo_dict.get("normal_tags", "[]")
                    photo_dict["normal_tags"] = json.loads(normal_tags_raw) if normal_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["normal_tags"] = []
                
                try:
                    detailed_tags_raw = photo_dict.get("detailed_tags", "[]")
                    photo_dict["detailed_tags"] = json.loads(detailed_tags_raw) if detailed_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["detailed_tags"] = []
                
                try:
                    tag_translations_raw = photo_dict.get("tag_translations", "{}")
                    photo_dict["tag_translations"] = json.loads(tag_translations_raw) if tag_translations_raw.strip() else {}
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["tag_translations"] = {}
                
                # 解析AI元数据字段
                ai_metadata_str = photo_dict.get("ai_metadata")
                if ai_metadata_str and ai_metadata_str.strip():
                    try:
                        photo_dict["ai_metadata"] = json.loads(ai_metadata_str)
                    except (json.JSONDecodeError, TypeError):
                        self.logger.warning("Failed to parse AI metadata JSON: photo_id=%s", photo_id, 
                                          ai_metadata_str=ai_metadata_str)
                        photo_dict["ai_metadata"] = {}
                else:
                    photo_dict["ai_metadata"] = {}
                photo_dict["is_ai_generated"] = bool(photo_dict.get("is_ai_generated", False))
                
                return photo_dict
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get photo {photo_id}: {str(e)}")
            return None
    
    def search_photos(self, 
                     query: str = "",
                     search_terms: List[str] = None,
                     tags: List[str] = None,
                     rating_min: int = 0,
                     favorites_only: bool = False,
                     min_width: int = 0,
                     min_height: int = 0,
                     min_size_kb: int = 0,
                     camera_filter: str = "",
                     date_from: str = "",
                     date_to: str = "",
                     limit: int = 100,
                     offset: int = 0) -> List[Dict[str, Any]]:
        """Enhanced search photos with various filters."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # 记录搜索参数用于调试
            self.logger.info(f"Search parameters: query='{query}', search_terms={search_terms}, tags={tags}, rating_min={rating_min}, favorites_only={favorites_only}, min_width={min_width}, min_height={min_height}, min_size_kb={min_size_kb}, camera_filter='{camera_filter}', date_from='{date_from}', date_to='{date_to}'")
            
            sql_conditions = []
            params = []
            
            # 基础文本搜索（文件名、备注）
            if query:
                sql_conditions.append("(filename LIKE ? OR notes LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])
            
            # 智能关键词搜索（支持短句和单词，优化中文搜索）
            if search_terms:
                term_conditions = []
                for term in search_terms:
                    # 在文件名、备注、标签、AI元数据中搜索，包括中英文标签
                    term_conditions.append("""
                        (filename LIKE ? OR notes LIKE ? OR 
                         simple_tags LIKE ? OR normal_tags LIKE ? OR detailed_tags LIKE ? OR
                         tag_translations LIKE ? OR
                         json_extract(tag_translations, '$.' || ?) LIKE ? OR
                         ai_metadata LIKE ? OR
                         json_extract(ai_metadata, '$.positive_prompt') LIKE ? OR
                         json_extract(ai_metadata, '$.model_name') LIKE ?)
                    """)
                    params.extend([f"%{term}%"] * 6 + [term, f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"])
                
                if term_conditions:
                    sql_conditions.append(f"({' OR '.join(term_conditions)})")
            
            # 标签筛选
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("""
                        (simple_tags LIKE ? OR normal_tags LIKE ? OR detailed_tags LIKE ? OR
                         tag_translations LIKE ?)
                    """)
                    params.extend([f"%{tag}%"] * 4)
                
                if tag_conditions:
                    sql_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # 评分筛选
            if rating_min > 0:
                sql_conditions.append("rating >= ?")
                params.append(rating_min)
            
            # 收藏筛选
            if favorites_only:
                sql_conditions.append("is_favorite = 1")
            
            # 尺寸筛选
            if min_width > 0:
                sql_conditions.append("width >= ?")
                params.append(min_width)
            
            if min_height > 0:
                sql_conditions.append("height >= ?")
                params.append(min_height)
            
            # 文件大小筛选（转换为字节）
            if min_size_kb > 0:
                min_size_bytes = min_size_kb * 1024
                sql_conditions.append("file_size >= ?")
                params.append(min_size_bytes)
            
            # 相机信息筛选
            if camera_filter:
                sql_conditions.append("exif_data LIKE ?")
                params.append(f"%{camera_filter}%")
            
            # 日期范围筛选
            if date_from:
                sql_conditions.append("date_taken >= ?")
                params.append(date_from)
            
            if date_to:
                sql_conditions.append("date_taken <= ?")
                params.append(date_to)
            
            # 构建SQL查询 - 使用更灵活的OR逻辑
            sql = "SELECT * FROM photos"
            if sql_conditions:
                # 将搜索条件分组：文本搜索使用OR，其他筛选使用AND
                text_conditions = []
                filter_conditions = []
                
                for condition in sql_conditions:
                    if "LIKE" in condition and ("filename" in condition or "notes" in condition or "simple_tags" in condition or "normal_tags" in condition or "detailed_tags" in condition or "tag_translations" in condition):
                        text_conditions.append(condition)
                    else:
                        filter_conditions.append(condition)
                
                where_clauses = []
                
                # 文本搜索条件使用OR连接
                if text_conditions:
                    where_clauses.append(f"({' OR '.join(text_conditions)})")
                
                # 其他筛选条件使用AND连接
                if filter_conditions:
                    where_clauses.append(f"({' AND '.join(filter_conditions)})")
                
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
            
            sql += " ORDER BY date_taken DESC, date_added DESC"
            sql += f" LIMIT {limit} OFFSET {offset}"
            
            # 记录SQL查询用于调试
            self.logger.info(f"SQL query: {sql}, params: {params}")
            
            with self.get_connection() as conn:
                cursor = conn.execute(sql, params)
                photos = []
                
                for row in cursor.fetchall():
                    photo_dict = dict(row)
                    
                    # 安全解析JSON字段
                    try:
                        photo_dict["exif_data"] = json.loads(photo_dict.get("exif_data", "{}"))
                    except:
                        photo_dict["exif_data"] = {}
                    
                    try:
                        photo_dict["tags"] = json.loads(photo_dict.get("tags", "[]"))
                    except:
                        photo_dict["tags"] = []
                    
                    # 解析新的标签字段
                    try:
                        photo_dict["simple_tags"] = json.loads(photo_dict.get("simple_tags", "[]"))
                    except:
                        photo_dict["simple_tags"] = []
                    
                    try:
                        photo_dict["normal_tags"] = json.loads(photo_dict.get("normal_tags", "[]"))
                    except:
                        photo_dict["normal_tags"] = []
                    
                    try:
                        photo_dict["detailed_tags"] = json.loads(photo_dict.get("detailed_tags", "[]"))
                    except:
                        photo_dict["detailed_tags"] = []
                    
                    try:
                        photo_dict["tag_translations"] = json.loads(photo_dict.get("tag_translations", "{}"))
                    except:
                        photo_dict["tag_translations"] = {}
                    
                    # 解析AI元数据字段
                    try:
                        photo_dict["ai_metadata"] = json.loads(photo_dict.get("ai_metadata", "{}"))
                    except:
                        photo_dict["ai_metadata"] = {}
                    
                    try:
                        photo_dict["is_ai_generated"] = bool(photo_dict.get("is_ai_generated", False))
                    except:
                        photo_dict["is_ai_generated"] = False
                    
                    photos.append(photo_dict)
                
                self.logger.info(f"Search results: {len(photos)}")
                return photos
                
        except Exception as e:
            self.logger.error(f"Failed to search photos: {str(e)}")
            return []
    
    def update_photo(self, photo_id: int, updates: Dict[str, Any]) -> bool:
        """Update photo record with unified tags support."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Prepare updates
            update_data = updates.copy()
            update_data["date_modified"] = datetime.now().isoformat()
            
            # 检查是否包含统一标签更新
            if "unified_tags_data" in update_data:
                try:
                    # 处理统一标签更新 - 双写策略
                    print(f"🔍 检测到统一标签更新: photo_id={photo_id}")
                    unified_tags = update_data.pop("unified_tags_data")
                    print(f"🔍 统一标签数据: {unified_tags}")
                    dual_write_updates = UnifiedTagsAccessor.write_unified_tags(unified_tags)
                    print(f"🔍 双写更新字典: {dual_write_updates}")
                    update_data.update(dual_write_updates)
                    print(f"🔍 合并后的更新数据: {update_data}")
                    self.logger.info(f"Applied unified tags dual-write for photo {photo_id}")
                except Exception as e:
                    print(f"❌ 统一标签处理失败: {str(e)}")
                    self.logger.error(f"Failed to process unified tags update for photo {photo_id}: {str(e)}")
            
            # Handle JSON fields
            if "exif_data" in update_data and isinstance(update_data["exif_data"], dict):
                update_data["exif_data"] = safe_json_dumps(update_data["exif_data"])
            
            if "tags" in update_data and isinstance(update_data["tags"], list):
                update_data["tags"] = safe_json_dumps(update_data["tags"])
            
            # 处理新的标签字段
            if "simple_tags" in update_data and isinstance(update_data["simple_tags"], list):
                update_data["simple_tags"] = safe_json_dumps(update_data["simple_tags"])
            
            if "normal_tags" in update_data and isinstance(update_data["normal_tags"], list):
                update_data["normal_tags"] = safe_json_dumps(update_data["normal_tags"])
            
            if "detailed_tags" in update_data and isinstance(update_data["detailed_tags"], list):
                update_data["detailed_tags"] = safe_json_dumps(update_data["detailed_tags"])
            
            if "tag_translations" in update_data and isinstance(update_data["tag_translations"], dict):
                update_data["tag_translations"] = safe_json_dumps(update_data["tag_translations"])
            
            # 处理新的分离式标签字段（英文/中文）
            if "simple_tags_en" in update_data:
                update_data["simple_tags_en"] = str(update_data["simple_tags_en"])
            if "simple_tags_cn" in update_data:
                update_data["simple_tags_cn"] = str(update_data["simple_tags_cn"])
            if "general_tags_en" in update_data:
                update_data["general_tags_en"] = str(update_data["general_tags_en"])
            if "general_tags_cn" in update_data:
                update_data["general_tags_cn"] = str(update_data["general_tags_cn"])
            if "detailed_tags_en" in update_data:
                update_data["detailed_tags_en"] = str(update_data["detailed_tags_en"])
            if "detailed_tags_cn" in update_data:
                update_data["detailed_tags_cn"] = str(update_data["detailed_tags_cn"])
            
            # 处理其他新字段
            if "notes" in update_data:
                update_data["notes"] = str(update_data["notes"])
            if "positive_prompt" in update_data:
                update_data["positive_prompt"] = str(update_data["positive_prompt"])
            if "negative_prompt" in update_data:
                update_data["negative_prompt"] = str(update_data["negative_prompt"])
            
            # 处理AI元数据字段
            if "ai_metadata" in update_data and isinstance(update_data["ai_metadata"], dict):
                update_data["ai_metadata"] = safe_json_dumps(update_data["ai_metadata"])
            
            db["photos"].update(photo_id, update_data)
            
            self.logger.info(f"Photo updated: ID {photo_id}")
            return True
            
        except Exception as e:
            self.logger.error("Failed to update photo: photo_id=%s, error=%s", photo_id, str(e))
            return False
    
    def delete_photo(self, photo_id: int) -> bool:
        """Delete photo from database."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Remove from albums first
            db["album_photos"].delete_where("photo_id = ?", [photo_id])
            
            # Delete photo record
            db["photos"].delete(photo_id)
            
            self.logger.info(f"Photo deleted: ID {photo_id}")
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete photo: photo_id=%s, error=%s", photo_id, str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            stats = {
                "total_photos": db["photos"].count,
                "total_albums": db["albums"].count,
                "total_tags": db["tags"].count,
                "favorites_count": db["photos"].count_where("is_favorite = 1"),
                "db_size": self.db_path.stat().st_size if self.db_path.exists() else 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {str(e)}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup."""
        try:
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as source:
                backup_conn = sqlite3.connect(backup_file)
                source.backup(backup_conn)
                backup_conn.close()
            
            self.logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return False 

    def add_photo_to_album(self, photo_id: int, album_id: int) -> bool:
        """Add a photo to an album."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                db = sqlite_utils.Database(self.db_path)
                db["album_photos"].insert({
                    "album_id": album_id,
                    "photo_id": photo_id,
                    "added_date": datetime.now().isoformat()
                })
                return True
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Failed to add photo to album (attempt {retry_count})", 
                                photo_id=photo_id, 
                                album_id=album_id, 
                                error=str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                    continue
                else:
                    break
        
        return False
    
    def get_album_photos(self, album_id: int) -> List[Dict[str, Any]]:
        """Get all photos in an album."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            photos = db.query("""
                SELECT p.* FROM photos p
                INNER JOIN album_photos ap ON p.id = ap.photo_id
                WHERE ap.album_id = ?
                ORDER BY ap.added_date DESC
            """, [album_id])
            
            result = []
            for photo in photos:
                photo_dict = dict(photo)
                photo_dict["exif_data"] = json.loads(photo_dict["exif_data"])
                photo_dict["tags"] = json.loads(photo_dict["tags"])
                
                # 解析新的标签字段 - 安全处理空字符串
                try:
                    simple_tags_raw = photo_dict.get("simple_tags", "[]")
                    photo_dict["simple_tags"] = json.loads(simple_tags_raw) if simple_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["simple_tags"] = []
                
                try:
                    normal_tags_raw = photo_dict.get("normal_tags", "[]")
                    photo_dict["normal_tags"] = json.loads(normal_tags_raw) if normal_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["normal_tags"] = []
                
                try:
                    detailed_tags_raw = photo_dict.get("detailed_tags", "[]")
                    photo_dict["detailed_tags"] = json.loads(detailed_tags_raw) if detailed_tags_raw.strip() else []
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["detailed_tags"] = []
                
                try:
                    tag_translations_raw = photo_dict.get("tag_translations", "{}")
                    photo_dict["tag_translations"] = json.loads(tag_translations_raw) if tag_translations_raw.strip() else {}
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["tag_translations"] = {}
                
                # 解析AI元数据字段 - 安全处理
                try:
                    ai_metadata_raw = photo_dict.get("ai_metadata", "{}")
                    photo_dict["ai_metadata"] = json.loads(ai_metadata_raw) if ai_metadata_raw.strip() else {}
                except (json.JSONDecodeError, AttributeError):
                    photo_dict["ai_metadata"] = {}
                
                photo_dict["is_ai_generated"] = bool(photo_dict.get("is_ai_generated", False))
                
                result.append(photo_dict)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get album photos: {str(e)}")
            return []
    
    def create_album(self, album_data: Dict[str, Any]) -> int:
        """Create a new album with automatic name conflict resolution."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # 检查名称是否重复，如果重复则自动重命名
            base_name = album_data["name"]
            final_name = base_name
            counter = 1
            
            # 检查名称是否已存在
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM albums WHERE name = ?", (final_name,))
                existing_album = cursor.fetchone()
                
            while existing_album:
                final_name = f"{base_name} ({counter})"
                counter += 1
                
                # 防止无限循环
                if counter > 1000:
                    final_name = f"{base_name}_{int(time.time())}"
                    break
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM albums WHERE name = ?", (final_name,))
                    existing_album = cursor.fetchone()
            
            # 如果名称被修改，记录日志
            if final_name != base_name:
                self.logger.info(f"Album name conflict resolved: '{base_name}' -> '{final_name}'")
            
            album_record = {
                "name": final_name,
                "description": album_data.get("description", ""),
                "created_date": datetime.now().isoformat(),
                "cover_photo_id": album_data.get("cover_photo_id", 0),
                "photo_count": 0
            }
            
            result = db["albums"].insert(album_record)
            album_id = result.last_pk
            
            self.logger.info(f"Album created: ID {album_id}, name '{final_name}'")
            return album_id
            
        except Exception as e:
            self.logger.error(f"Failed to create album: {str(e)}")
            raise
    
    def get_album(self, album_id: int) -> Optional[Dict[str, Any]]:
        """Get album by ID."""
        try:
            db = sqlite_utils.Database(self.db_path)
            album = db["albums"].get(album_id)
            
            if album:
                return dict(album)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get album {album_id}: {str(e)}")
            return None
    
    def get_all_albums(self) -> List[Dict[str, Any]]:
        """Get all albums with photo count."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            albums = db.query("""
                SELECT a.*, COUNT(ap.photo_id) as photo_count
                FROM albums a
                LEFT JOIN album_photos ap ON a.id = ap.album_id
                GROUP BY a.id
                ORDER BY a.created_date DESC
            """)
            
            return [dict(album) for album in albums]
            
        except Exception as e:
            self.logger.error(f"Failed to get albums: {str(e)}")
            return []
    
    def update_album(self, album_id: int, updates: Dict[str, Any]) -> bool:
        """Update album information."""
        try:
            db = sqlite_utils.Database(self.db_path)
            db["albums"].update(album_id, updates)
            
            self.logger.info(f"Album updated: ID {album_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update album {album_id}: {str(e)}")
            return False
    
    def get_photo_albums(self, photo_id: int) -> List[Dict[str, Any]]:
        """Get all albums that contain a specific photo."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            albums = db.query("""
                SELECT a.* FROM albums a
                JOIN album_photos ap ON a.id = ap.album_id
                WHERE ap.photo_id = ?
            """, [photo_id])
            
            return [dict(album) for album in albums]
            
        except Exception as e:
            self.logger.error(f"Failed to get photo albums {photo_id}: {str(e)}")
            return []
    
    def delete_album(self, album_id: int) -> bool:
        """Delete an album and only delete photos that are exclusive to this album."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use context manager for better connection handling
                with self.get_connection() as conn:
                    # Get all photo IDs in this album first
                    photo_ids = [row[0] for row in conn.execute(
                        "SELECT photo_id FROM album_photos WHERE album_id = ?", [album_id]
                    ).fetchall()]
                    
                    # Delete tags for ALL photos in this album (regardless of other album memberships)
                    tags_deleted = 0
                    photos_deleted = 0
                    
                    for photo_id in photo_ids:
                        # Always delete photo tags for photos in this album
                        cursor = conn.execute("DELETE FROM photo_tags WHERE photo_id = ?", [photo_id])
                        tags_deleted += cursor.rowcount
                        
                        # Count how many albums this photo is in
                        album_count = conn.execute(
                            "SELECT COUNT(*) FROM album_photos WHERE photo_id = ?", [photo_id]
                        ).fetchone()[0]
                        
                        # If photo is only in this album, delete the photo record completely
                        if album_count == 1:
                            conn.execute("DELETE FROM photos WHERE id = ?", [photo_id])
                            photos_deleted += 1
                    
                    # Delete album-photo associations for this album
                    conn.execute("DELETE FROM album_photos WHERE album_id = ?", [album_id])
                    
                    # Delete the album record
                    conn.execute("DELETE FROM albums WHERE id = ?", [album_id])
                    
                    conn.commit()
                
                self.logger.info("Album deleted with complete cleanup: album_id=%s, photos_in_album=%d, tags_deleted=%d, photos_deleted=%d", 
                               album_id, len(photo_ids), tags_deleted, photos_deleted)
                return True
                
            except Exception as e:
                retry_count += 1
                self.logger.error("Failed to delete album (attempt %d): album_id=%s, error=%s", 
                                retry_count, album_id, str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)  # Longer wait time
                    continue
                else:
                    break
        
        return False
    
    def delete_multiple_albums(self, album_ids: List[int]) -> Dict[str, Any]:
        """Delete multiple albums and only delete photos that are exclusive to these albums.
        
        Args:
            album_ids: List of album IDs to delete
            
        Returns:
            Dictionary with deletion results
        """
        if not album_ids:
            return {"success": False, "error": "No album IDs provided"}
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    # Get album names for logging
                    album_names = {}
                    placeholders = ','.join(['?'] * len(album_ids))
                    cursor = conn.execute(f"SELECT id, name FROM albums WHERE id IN ({placeholders})", album_ids)
                    for row in cursor.fetchall():
                        album_names[row['id']] = row['name']
                    
                    # Get all photo IDs in these albums
                    cursor = conn.execute(f"SELECT photo_id FROM album_photos WHERE album_id IN ({placeholders})", album_ids)
                    all_photo_ids = [row[0] for row in cursor.fetchall()]
                    
                    # Count photos that will be deleted (exclusive to these albums)
                    photos_to_delete = []
                    for photo_id in set(all_photo_ids):  # Remove duplicates
                        # Count how many albums this photo is in
                        album_count = conn.execute(
                            "SELECT COUNT(*) FROM album_photos WHERE photo_id = ?", [photo_id]
                        ).fetchone()[0]
                        
                        # Count how many of those albums are in our deletion list
                        cursor = conn.execute(
                            f"SELECT COUNT(*) FROM album_photos WHERE photo_id = ? AND album_id IN ({placeholders})", 
                            [photo_id] + album_ids
                        )
                        albums_to_delete_count = cursor.fetchone()[0]
                        
                        # If photo is only in albums that we're deleting, mark for deletion
                        if album_count == albums_to_delete_count:
                            photos_to_delete.append(photo_id)
                    
                    # Delete photos that are exclusive to these albums
                    photos_deleted = 0
                    if photos_to_delete:
                        photo_placeholders = ','.join(['?'] * len(photos_to_delete))
                        conn.execute(f"DELETE FROM photos WHERE id IN ({photo_placeholders})", photos_to_delete)
                        photos_deleted = len(photos_to_delete)
                    
                    # Delete album-photo associations for these albums
                    conn.execute(f"DELETE FROM album_photos WHERE album_id IN ({placeholders})", album_ids)
                    
                    # Delete the album records
                    conn.execute(f"DELETE FROM albums WHERE id IN ({placeholders})", album_ids)
                    
                    conn.commit()
                
                result = {
                    "success": True,
                    "deleted_albums": len(album_ids),
                    "album_names": list(album_names.values()),
                    "photos_in_albums": len(all_photo_ids),
                    "photos_deleted": photos_deleted,
                    "album_ids": album_ids
                }
                
                self.logger.info("Multiple albums deleted with smart photo cleanup: deleted_albums=%s", len(album_ids),
                               album_names=list(album_names.values()),
                               photos_in_albums=len(all_photo_ids),
                               photos_deleted=photos_deleted)
                
                return result
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Failed to delete multiple albums (attempt {retry_count})", 
                                album_ids=album_ids, error=str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)
                    continue
                else:
                    break
        
        return {"success": False, "error": f"Failed to delete albums after {max_retries} attempts"}
    
    def remove_album_photos(self, album_id: int) -> bool:
        """Remove all photos from an album without deleting the photos."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use context manager for better connection handling
                with self.get_connection() as conn:
                    conn.execute("DELETE FROM album_photos WHERE album_id = ?", [album_id])
                    conn.commit()
                
                self.logger.info(f"Removed all photos from album: ID {album_id}")
                return True
                
            except Exception as e:
                retry_count += 1
                self.logger.error("Failed to remove album photos (attempt %s): album_id=%s, error=%s", 
                                retry_count, album_id, str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)  # Longer wait time
                    continue
                else:
                    break
        
        return False
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Execute a query and return a single row."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"Failed to fetch one: query='{query}', error: {str(e)}")
            return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a query and return all rows."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to fetch all: query='{query}', error: {str(e)}")
            return []
    


    def find_existing_hashes(self, hashes: List[str], batch_size: int = 1000) -> set:
        """
        批量查询已存在的文件哈希值。
        
        Args:
            hashes: 要查询的哈希值列表
            batch_size: 每批查询的大小，避免内存溢出
            
        Returns:
            已存在的哈希值集合
        """
        try:
            existing_hashes = set()
            
            # 分批查询，避免内存溢出
            for i in range(0, len(hashes), batch_size):
                batch_hashes = hashes[i:i + batch_size]
                
                # 构建查询参数
                placeholders = ','.join(['?' for _ in batch_hashes])
                query = f"SELECT file_hash FROM photos WHERE file_hash IN ({placeholders})"
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, batch_hashes)
                    results = cursor.fetchall()
                    
                    # 将结果添加到集合中
                    for row in results:
                        existing_hashes.add(row[0])
            
            self.logger.info("Found existing hashes: total_checked=%s, existing_count=%s", len(hashes), len(existing_hashes))
            
            return existing_hashes
            
        except Exception as e:
            self.logger.error(f"Failed to find existing hashes: {str(e)}")
            return set()

    def batch_add_photos_to_album(self, photo_ids: List[int], album_id: int) -> Dict[str, Any]:
        """
        批量将照片添加到相册。
        
        Args:
            photo_ids: 要添加的照片ID列表
            album_id: 目标相册ID
            
        Returns:
            操作结果统计
        """
        try:
            if not photo_ids:
                return {"success": True, "added": 0, "skipped": 0, "errors": 0}
            
            added_count = 0
            skipped_count = 0
            error_count = 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 开始事务
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # 检查相册是否存在
                    cursor.execute("SELECT id FROM albums WHERE id = ?", (album_id,))
                    if not cursor.fetchone():
                        raise ValueError(f"Album with ID {album_id} does not exist")
                    
                    # 检查哪些照片已经在相册中
                    placeholders = ','.join(['?' for _ in photo_ids])
                    cursor.execute(f"""
                        SELECT photo_id FROM album_photos 
                        WHERE album_id = ? AND photo_id IN ({placeholders})
                    """, [album_id] + photo_ids)
                    
                    existing_photo_ids = {row[0] for row in cursor.fetchall()}
                    
                    # 批量插入新照片
                    current_time = datetime.now().isoformat()
                    for photo_id in photo_ids:
                        if photo_id in existing_photo_ids:
                            skipped_count += 1
                            continue
                        
                        try:
                            cursor.execute("""
                                INSERT INTO album_photos (album_id, photo_id, added_date)
                                VALUES (?, ?, ?)
                            """, (album_id, photo_id, current_time))
                            added_count += 1
                        except Exception as e:
                            self.logger.error("Failed to add photo to album: photo_id=%s, album_id=%s, error=%s", photo_id, album_id, str(e))
                            error_count += 1
                    
                    # 更新相册照片数量
                    cursor.execute("""
                        UPDATE albums 
                        SET photo_count = (
                            SELECT COUNT(*) FROM album_photos WHERE album_id = ?
                        )
                        WHERE id = ?
                    """, (album_id, album_id))
                    
                    # 提交事务
                    cursor.execute("COMMIT")
                    
                except Exception as e:
                    # 回滚事务
                    cursor.execute("ROLLBACK")
                    raise e
            
            result = {
                "success": True,
                "added": added_count,
                "skipped": skipped_count,
                "errors": error_count,
                "total": len(photo_ids)
            }
            
            self.logger.info("Batch add photos to album completed: album_id=%s, added=%s, skipped=%s, errors=%s, total=%s", 
                           album_id, result["added"], result["skipped"], result["errors"], result["total"])
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to batch add photos to album: album_id=%s, error=%s", album_id, str(e))
            return {
                "success": False,
                "added": 0,
                "skipped": 0,
                "errors": len(photo_ids),
                "total": len(photo_ids),
                "error": str(e)
            }

    def batch_insert_photos(self, photos_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量插入照片到数据库。
        
        Args:
            photos_data: 照片数据列表
            
        Returns:
            操作结果统计
        """
        try:
            if not photos_data:
                return {"success": True, "inserted": 0, "errors": 0}
            
            inserted_count = 0
            error_count = 0
            inserted_ids = []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 开始事务
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    for photo_data in photos_data:
                        try:
                            # 准备照片数据
                            photo_record = {
                                "filename": photo_data["filename"],
                                "filepath": photo_data["filepath"],
                                "file_size": photo_data.get("file_size", 0),
                                "file_hash": photo_data.get("file_hash", ""),
                                "width": photo_data.get("width", 0),
                                "height": photo_data.get("height", 0),
                                "format": photo_data.get("format", ""),
                                "date_taken": photo_data.get("date_taken", ""),
                                "date_added": photo_data.get("date_added", datetime.now().isoformat()),
                                "date_modified": photo_data.get("date_modified", ""),
                                "exif_data": safe_json_dumps(photo_data.get("exif_data", {})),
                                "ai_metadata": safe_json_dumps(photo_data.get("ai_metadata", {})),
                                "is_ai_generated": photo_data.get("is_ai_generated", False),
                                "tags": safe_json_dumps(photo_data.get("tags", [])),
                                "simple_tags": safe_json_dumps(photo_data.get("simple_tags", [])),
                                "normal_tags": safe_json_dumps(photo_data.get("normal_tags", [])),
                                "detailed_tags": safe_json_dumps(photo_data.get("detailed_tags", [])),
                                "tag_translations": safe_json_dumps(photo_data.get("tag_translations", {})),
                                "rating": photo_data.get("rating", 0),
                                "is_favorite": photo_data.get("is_favorite", False),
                                "thumbnail_path": photo_data.get("thumbnail_path", ""),
                                "notes": photo_data.get("notes", "")
                            }
                            
                            # 插入照片
                            cursor.execute("""
                                INSERT INTO photos (
                                    filename, filepath, file_size, file_hash, width, height,
                                    format, date_taken, date_added, date_modified, exif_data,
                                    ai_metadata, is_ai_generated, tags, simple_tags, normal_tags,
                                    detailed_tags, tag_translations, rating, is_favorite,
                                    thumbnail_path, notes
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                photo_record["filename"], photo_record["filepath"],
                                photo_record["file_size"], photo_record["file_hash"],
                                photo_record["width"], photo_record["height"],
                                photo_record["format"], photo_record["date_taken"],
                                photo_record["date_added"], photo_record["date_modified"],
                                photo_record["exif_data"], photo_record["ai_metadata"],
                                photo_record["is_ai_generated"], photo_record["tags"],
                                photo_record["simple_tags"], photo_record["normal_tags"],
                                photo_record["detailed_tags"], photo_record["tag_translations"],
                                photo_record["rating"], photo_record["is_favorite"],
                                photo_record["thumbnail_path"], photo_record["notes"]
                            ))
                            
                            photo_id = cursor.lastrowid
                            inserted_ids.append(photo_id)
                            inserted_count += 1
                            
                        except Exception as e:
                            self.logger.error("Failed to insert photo: filepath=%s", photo_data.get("filepath"), error=str(e))
                            error_count += 1
                    
                    # 提交事务
                    cursor.execute("COMMIT")
                    
                except Exception as e:
                    # 回滚事务
                    cursor.execute("ROLLBACK")
                    raise e
            
            result = {
                "success": True,
                "inserted": inserted_count,
                "errors": error_count,
                "total": len(photos_data),
                "inserted_ids": inserted_ids
            }
            
            self.logger.info("Batch insert photos completed", **result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to batch insert photos: {str(e)}")
            return {
                "success": False,
                "inserted": 0,
                "errors": len(photos_data),
                "total": len(photos_data),
                "error": str(e)
            }

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT 
                        json_extract(tags.value, '$') as tag_name,
                        COUNT(*) as usage_count
                    FROM photos, json_each(photos.tags) as tags
                    WHERE photos.tags IS NOT NULL AND photos.tags != '[]'
                    GROUP BY tag_name
                    ORDER BY usage_count DESC, tag_name
                """)
                
                tags = []
                for row in cursor.fetchall():
                    tags.append({
                        "name": row[0],
                        "usage_count": row[1]
                    })
                
                return tags
                
        except Exception as e:
            self.logger.error(f"Failed to get all tags: {str(e)}")
            return []

    def save_photo_tags(self, photo_id: int, tags_data: Dict[str, Any]) -> bool:
        """保存照片标签"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 准备标签数据 - 支持新的分离式标签结构
                updates = {}
                
                # 处理分离式标签字段
                if "simple_tags_en" in tags_data:
                    updates["simple_tags_en"] = tags_data.get("simple_tags_en", "")
                if "simple_tags_cn" in tags_data:
                    updates["simple_tags_cn"] = tags_data.get("simple_tags_cn", "")
                if "general_tags_en" in tags_data:
                    updates["general_tags_en"] = tags_data.get("general_tags_en", "")
                if "general_tags_cn" in tags_data:
                    updates["general_tags_cn"] = tags_data.get("general_tags_cn", "")
                if "detailed_tags_en" in tags_data:
                    updates["detailed_tags_en"] = tags_data.get("detailed_tags_en", "")
                if "detailed_tags_cn" in tags_data:
                    updates["detailed_tags_cn"] = tags_data.get("detailed_tags_cn", "")
                if "notes" in tags_data:
                    updates["notes"] = tags_data.get("notes", "")
                
                # 处理传统的JSON格式标签（向后兼容）
                if "simple_tags" in tags_data:
                    updates["simple_tags"] = safe_json_dumps(tags_data.get("simple_tags", []))
                if "normal_tags" in tags_data:
                    updates["normal_tags"] = safe_json_dumps(tags_data.get("normal_tags", []))
                if "detailed_tags" in tags_data:
                    updates["detailed_tags"] = safe_json_dumps(tags_data.get("detailed_tags", []))
                if "tag_translations" in tags_data:
                    updates["tag_translations"] = safe_json_dumps(tags_data.get("tag_translations", {}))
                
                if not updates:
                    self.logger.warning(f"No valid tag data provided for photo {photo_id}")
                    return False
                
                # 构建动态更新查询
                set_clauses = [f"{field} = ?" for field in updates.keys()]
                values = list(updates.values()) + [photo_id]
                
                query = f"""
                    UPDATE photos 
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Successfully saved tags for photo {photo_id}")
                    return True
                else:
                    self.logger.warning(f"No photo found with id {photo_id}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Failed to save photo tags {photo_id}: {str(e)}")
            return False
    
    def update_photo_field(self, photo_id: int, field_name: str, field_value: str) -> bool:
        """更新照片的单个字段"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 验证字段名是否安全（防止SQL注入）
                allowed_fields = [
                    'simple_tags_en', 'simple_tags_cn',
                    'general_tags_en', 'general_tags_cn', 
                    'detailed_tags_en', 'detailed_tags_cn',
                    'notes', 'positive_prompt', 'negative_prompt'
                ]
                
                if field_name not in allowed_fields:
                    self.logger.error(f"Invalid field name: {field_name}")
                    return False
                
                # 使用参数化查询更新字段
                query = f"UPDATE photos SET {field_name} = ? WHERE id = ?"
                cursor.execute(query, (field_value, photo_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Updated photo {photo_id} field {field_name}")
                    return True
                else:
                    self.logger.warning(f"No photo found with id {photo_id}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Failed to update photo field {field_name} for photo {photo_id}: {str(e)}")
            return False
    
    def get_photo_albums(self, photo_id: int) -> List[Dict[str, Any]]:
        """获取照片所属的相册列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT a.id, a.name, a.description, a.created_date
                    FROM albums a
                    JOIN album_photos ap ON a.id = ap.album_id
                    WHERE ap.photo_id = ?
                    ORDER BY a.name
                """, (photo_id,))
                
                albums = []
                for row in cursor.fetchall():
                    albums.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "created_date": row[3]
                    })
                
                return albums
                
        except Exception as e:
            self.logger.error(f"Failed to get photo albums for photo {photo_id}: {str(e)}")
            return []
    
    def get_photo_by_id(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取照片信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, filename, filepath, file_size, file_hash, width, height, 
                           format, date_taken, date_added, is_ai_generated, ai_metadata,
                           simple_tags, normal_tags, detailed_tags, tag_translations,
                           simple_tags_en, simple_tags_cn, general_tags_en, general_tags_cn,
                           detailed_tags_en, detailed_tags_cn, notes,
                           positive_prompt, negative_prompt, rating, is_favorite
                    FROM photos 
                    WHERE id = ?
                """, (photo_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "filename": row[1],
                        "filepath": row[2],
                        "file_size": row[3],
                        "file_hash": row[4],
                        "width": row[5],
                        "height": row[6],
                        "format": row[7],
                        "date_taken": row[8],
                        "date_added": row[9],
                        "is_ai_generated": row[10],
                        "ai_metadata": row[11],
                        "simple_tags": row[12],
                        "normal_tags": row[13],
                        "detailed_tags": row[14],
                        "tag_translations": row[15],
                        "simple_tags_en": row[16],
                        "simple_tags_cn": row[17],
                        "general_tags_en": row[18],
                        "general_tags_cn": row[19],
                        "detailed_tags_en": row[20],
                        "detailed_tags_cn": row[21],
                        "notes": row[22],
                        "positive_prompt": row[23],
                        "negative_prompt": row[24],
                        "rating": row[25],
                        "is_favorite": row[26]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get photo by ID {photo_id}: {str(e)}")
            return None
    
    def get_recent_albums(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近使用的相册列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                     SELECT a.id, a.name, a.description, a.created_date, 
                            COUNT(ap.photo_id) as photo_count,
                            MAX(ap.added_date) as last_photo_added
                     FROM albums a
                     LEFT JOIN album_photos ap ON a.id = ap.album_id
                     GROUP BY a.id, a.name, a.description, a.created_date
                     ORDER BY last_photo_added DESC, a.created_date DESC
                     LIMIT ?
                 """, (limit,))
                
                albums = []
                for row in cursor.fetchall():
                    albums.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "created_date": row[3],
                        "photo_count": row[4],
                        "last_photo_added": row[5]
                    })
                
                return albums
                
        except Exception as e:
            self.logger.error(f"Failed to get recent albums: {str(e)}")
            return []