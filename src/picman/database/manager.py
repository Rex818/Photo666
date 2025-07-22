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
import structlog
from contextlib import contextmanager


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


class DatabaseManager:
    """Manages SQLite database operations for photo management."""
    
    def __init__(self, db_path: str, config=None):
        self.db_path = Path(db_path)
        self.config = config
        self.logger = structlog.get_logger("picman.database")
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
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
                    "tags": str,       # JSON array
                    "simple_tags": str,    # JSON array - 简单标签
                    "normal_tags": str,    # 普通标签
                    "detailed_tags": str,  # 详细标签
                    "tag_translations": str,  # 标签翻译
                    "rating": int,
                    "is_favorite": bool,
                    "thumbnail_path": str,
                    "notes": str,
                    "gps_latitude": float,
                    "gps_longitude": float,
                    "gps_altitude": float,
                    "location_text": str
                }, pk="id")
                
                # Create indexes
                db["photos"].create_index(["filepath"], unique=True)
                db["photos"].create_index(["file_hash"])
                db["photos"].create_index(["date_taken"])
                db["photos"].create_index(["rating"])
                db["photos"].create_index(["is_favorite"])
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
            
            self.logger.info("Database initialized successfully", db_path=str(self.db_path))
            
        except Exception as e:
            self.logger.error("Failed to initialize database", error=str(e))
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
                    ("gps_latitude", "REAL DEFAULT NULL"),
                    ("gps_longitude", "REAL DEFAULT NULL"),
                    ("gps_altitude", "REAL DEFAULT NULL"),
                    ("location_text", "TEXT DEFAULT NULL")
                ]
                
                for column_name, column_def in new_columns:
                    if column_name not in columns:
                        cursor.execute(f"ALTER TABLE photos ADD COLUMN {column_name} {column_def}")
                        self.logger.info(f"Added new column to photos table", column=column_name)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error("Failed to add new columns", error=str(e))
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
                "rating": photo_data.get("rating", 0),
                "is_favorite": photo_data.get("is_favorite", False),
                "thumbnail_path": photo_data.get("thumbnail_path", ""),
                "notes": photo_data.get("notes", ""),
                "gps_latitude": photo_data.get("gps_latitude"),
                "gps_longitude": photo_data.get("gps_longitude"),
                "gps_altitude": photo_data.get("gps_altitude"),
                "location_text": photo_data.get("location_text")
            }
            
            result = db["photos"].insert(photo_record)
            photo_id = result.last_pk
            
            self.logger.info("Photo added to database", 
                           photo_id=photo_id, 
                           filename=photo_data["filename"])
            
            return photo_id
            
        except Exception as e:
            self.logger.error("Failed to add photo", 
                            filename=photo_data.get("filename", "unknown"),
                            error=str(e))
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
                
                # 解析新的标签字段
                photo_dict["simple_tags"] = json.loads(photo_dict.get("simple_tags", "[]"))
                photo_dict["normal_tags"] = json.loads(photo_dict.get("normal_tags", "[]"))
                photo_dict["detailed_tags"] = json.loads(photo_dict.get("detailed_tags", "[]"))
                photo_dict["tag_translations"] = json.loads(photo_dict.get("tag_translations", "{}"))
                
                return photo_dict
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get photo", photo_id=photo_id, error=str(e))
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
            self.logger.info("Search parameters", 
                           query=query, 
                           search_terms=search_terms,
                           tags=tags,
                           rating_min=rating_min,
                           favorites_only=favorites_only,
                           min_width=min_width,
                           min_height=min_height,
                           min_size_kb=min_size_kb,
                           camera_filter=camera_filter,
                           date_from=date_from,
                           date_to=date_to)
            
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
                    # 在文件名、备注、标签中搜索，包括中英文标签
                    term_conditions.append("""
                        (filename LIKE ? OR notes LIKE ? OR 
                         simple_tags LIKE ? OR normal_tags LIKE ? OR detailed_tags LIKE ? OR
                         tag_translations LIKE ? OR
                         json_extract(tag_translations, '$.' || ?) LIKE ?)
                    """)
                    params.extend([f"%{term}%"] * 6 + [term, f"%{term}%"])
                
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
            self.logger.info("SQL query", sql=sql, params=params)
            
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
                    
                    photos.append(photo_dict)
                
                self.logger.info("Search results", count=len(photos))
                return photos
                
        except Exception as e:
            self.logger.error("Failed to search photos", error=str(e))
            return []
    
    def update_photo(self, photo_id: int, updates: Dict[str, Any]) -> bool:
        """Update photo record."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Prepare updates
            update_data = updates.copy()
            update_data["date_modified"] = datetime.now().isoformat()
            
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
            
            # gps_latitude/gps_longitude直接写入
            if "gps_latitude" in update_data:
                pass
            if "gps_longitude" in update_data:
                pass
            if "gps_altitude" in update_data:
                pass
            if "location_text" in update_data:
                pass
            
            db["photos"].update(photo_id, update_data)
            
            self.logger.info("Photo updated", photo_id=photo_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update photo", 
                            photo_id=photo_id, error=str(e))
            return False
    
    def delete_photo(self, photo_id: int) -> bool:
        """Delete photo from database."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            # Remove from albums first
            db["album_photos"].delete_where("photo_id = ?", [photo_id])
            
            # Delete photo record
            db["photos"].delete(photo_id)
            
            self.logger.info("Photo deleted", photo_id=photo_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete photo", 
                            photo_id=photo_id, error=str(e))
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
            self.logger.error("Failed to get stats", error=str(e))
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
            
            self.logger.info("Database backup created", backup_path=backup_path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create backup", error=str(e))
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
                
                # 解析新的标签字段
                photo_dict["simple_tags"] = json.loads(photo_dict.get("simple_tags", "[]"))
                photo_dict["normal_tags"] = json.loads(photo_dict.get("normal_tags", "[]"))
                photo_dict["detailed_tags"] = json.loads(photo_dict.get("detailed_tags", "[]"))
                photo_dict["tag_translations"] = json.loads(photo_dict.get("tag_translations", "{}"))
                
                result.append(photo_dict)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to get album photos", error=str(e))
            return []
    
    def create_album(self, album_data: Dict[str, Any]) -> int:
        """Create a new album."""
        try:
            db = sqlite_utils.Database(self.db_path)
            
            album_record = {
                "name": album_data["name"],
                "description": album_data.get("description", ""),
                "created_date": datetime.now().isoformat(),
                "cover_photo_id": album_data.get("cover_photo_id", 0),
                "photo_count": 0
            }
            
            result = db["albums"].insert(album_record)
            album_id = result.last_pk
            
            self.logger.info("Album created", album_id=album_id, name=album_data["name"])
            return album_id
            
        except Exception as e:
            self.logger.error("Failed to create album", error=str(e))
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
            self.logger.error("Failed to get album", album_id=album_id, error=str(e))
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
            self.logger.error("Failed to get albums", error=str(e))
            return []
    
    def update_album(self, album_id: int, updates: Dict[str, Any]) -> bool:
        """Update album information."""
        try:
            db = sqlite_utils.Database(self.db_path)
            db["albums"].update(album_id, updates)
            
            self.logger.info("Album updated", album_id=album_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update album", album_id=album_id, error=str(e))
            return False
    
    def delete_album(self, album_id: int) -> bool:
        """Delete an album."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use context manager for better connection handling
                with self.get_connection() as conn:
                    # First remove all album-photo associations
                    conn.execute("DELETE FROM album_photos WHERE album_id = ?", [album_id])
                    
                    # Then delete the album record
                    conn.execute("DELETE FROM albums WHERE id = ?", [album_id])
                    
                    conn.commit()
                
                self.logger.info("Album deleted", album_id=album_id)
                return True
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Failed to delete album (attempt {retry_count})", 
                                album_id=album_id, error=str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)  # Longer wait time
                    continue
                else:
                    break
        
        return False
    
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
                
                self.logger.info("Removed all photos from album", album_id=album_id)
                return True
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Failed to remove album photos (attempt {retry_count})", 
                                album_id=album_id, error=str(e))
                
                # If database is locked, wait and retry
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    import time
                    time.sleep(0.5 * retry_count)  # Longer wait time
                    continue
                else:
                    break
        
        return False