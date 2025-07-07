#!/usr/bin/env python3
"""Database models and manager for blog automation system."""

import json
import logging
import hashlib
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from threading import local
from typing import Dict, List, Optional, Any
from sqlite3 import Connection, connect

logger = logging.getLogger(__name__)
thread_local = local()


@dataclass
class BlogPost:
    """Represents a blog post in the system."""
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    sources: str = ""  # JSON string of sources
    urls: str = ""  # JSON string of URLs
    url: str = ""  # Primary source or blog URL
    quality_score: float = 0.0
    word_count: int = 0
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    status: str = "draft"  # draft, published, archived
    tags: str = ""  # JSON string of tags
    seo_score: float = 0.0
    view_count: int = 0
    engagement_score: float = 0.0
    content_hash: str = ""  # For duplicate detection


@dataclass
class ContentMetrics:
    """Content performance metrics."""
    id: Optional[int] = None
    post_id: int = 0
    metric_name: str = ""
    metric_value: float = 0.0
    timestamp: Optional[datetime] = None
    metadata: str = ""  # JSON string


@dataclass
class SystemMetrics:
    """System performance metrics."""
    id: Optional[int] = None
    component: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    timestamp: Optional[datetime] = None
    tags: str = ""  # JSON string


class DatabaseManager:
    """Manages database connections and operations with thread safety."""
    
    def __init__(self, db_path: str = "blog_system.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> Connection:
        """Get thread-local database connection with optimizations."""
        if not hasattr(thread_local, "connection") or not thread_local.connection:
            conn = connect(self.db_path, timeout=30.0)
            
            # Apply SQLite performance optimizations
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;
                PRAGMA temp_store=MEMORY;
                PRAGMA mmap_size=134217728;
            """)
            
            conn.row_factory = sqlite3.Row
            thread_local.connection = conn
            logger.debug("Created new database connection")
        
        return thread_local.connection

    def close_connection(self):
        """Close the current thread's database connection."""
        if hasattr(thread_local, "connection") and thread_local.connection:
            try:
                thread_local.connection.close()
                thread_local.connection = None
                logger.debug("Closed database connection")
            except Exception as error:
                logger.error(f"Error closing connection: {error}")

    def init_database(self):
        """Initialize database schema with indexes and constraints."""
        conn = self.get_connection()
        try:
            with conn:
                # Create tables
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS blog_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sources TEXT DEFAULT '[]',
                        urls TEXT DEFAULT '[]',
                        url TEXT DEFAULT '',
                        quality_score REAL DEFAULT 0.0,
                        word_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        published_at TIMESTAMP,
                        status TEXT DEFAULT 'draft',
                        tags TEXT DEFAULT '[]',
                        seo_score REAL DEFAULT 0.0,
                        view_count INTEGER DEFAULT 0,
                        engagement_score REAL DEFAULT 0.0,
                        content_hash TEXT DEFAULT ''
                    );
                    
                    CREATE TABLE IF NOT EXISTS content_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}',
                        FOREIGN KEY (post_id) REFERENCES blog_posts (id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tags TEXT DEFAULT '{}'
                    );
                """)
                
                # Create indexes
                conn.executescript("""
                    CREATE INDEX IF NOT EXISTS idx_posts_status ON blog_posts(status);
                    CREATE INDEX IF NOT EXISTS idx_posts_created ON blog_posts(created_at);
                    CREATE INDEX IF NOT EXISTS idx_posts_published ON blog_posts(published_at);
                    CREATE INDEX IF NOT EXISTS idx_posts_quality ON blog_posts(quality_score);
                    CREATE INDEX IF NOT EXISTS idx_posts_url ON blog_posts(url);
                    CREATE INDEX IF NOT EXISTS idx_content_metrics_post ON content_metrics(post_id);
                    CREATE INDEX IF NOT EXISTS idx_content_metrics_name ON content_metrics(metric_name);
                    CREATE INDEX IF NOT EXISTS idx_content_metrics_time ON content_metrics(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_system_metrics_component ON system_metrics(component);
                    CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
                    CREATE INDEX IF NOT EXISTS idx_system_metrics_time ON system_metrics(timestamp);
                """)
                
                # Ensure URL column exists
                self._ensure_column_exists(
                    conn, 
                    "blog_posts", 
                    "url", 
                    "TEXT DEFAULT ''"
                )
                
                # Add unique constraints
                self._ensure_unique_constraint(
                    conn,
                    "idx_unique_title_date",
                    "blog_posts(title, date(created_at))"
                )
                
                self._ensure_unique_constraint(
                    conn,
                    "idx_unique_content_hash",
                    "blog_posts(content_hash) WHERE content_hash != ''"
                )
                
            logger.info("Database schema initialized")
        except Exception as error:
            logger.error(f"Database initialization failed: {error}")
            raise

    def _ensure_column_exists(
        self, 
        conn: Connection, 
        table: str, 
        column: str, 
        column_type: str
    ):
        """Ensure a column exists in the specified table."""
        try:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
                )
                logger.info(f"Added {column} column to {table}")
        except Exception as error:
            logger.warning(f"Column check failed for {table}.{column}: {error}")

    def _ensure_unique_constraint(
        self, 
        conn: Connection, 
        index_name: str, 
        constraint: str
    ):
        """Ensure a unique constraint exists."""
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND name = ?",
                (index_name,)
            )
            if not cursor.fetchone():
                conn.execute(
                    f"CREATE UNIQUE INDEX {index_name} ON {constraint}"
                )
                logger.info(f"Created unique constraint: {index_name}")
        except Exception as error:
            logger.warning(
                f"Constraint creation failed for {index_name}: {error}"
            )

    def save_blog_post(self, post: BlogPost) -> int:
        """
        Save a blog post to the database with duplicate prevention.
        
        Returns:
            ID of the saved post
        """
        # Generate content hash if needed
        if not post.content_hash and post.content:
            post.content_hash = hashlib.sha256(
                post.content.encode()
            ).hexdigest()

        conn = self.get_connection()
        try:
            # Check for duplicates if new post
            if not post.id:
                existing_id = self._find_duplicate_post(conn, post)
                if existing_id:
                    return existing_id

            # Execute save operation
            with conn:
                if post.id:
                    # Update existing post
                    conn.execute("""
                        UPDATE blog_posts SET 
                            title = ?, content = ?, urls = ?, url = ?,
                            quality_score = ?, word_count = ?, status = ?,
                            tags = ?, seo_score = ?, engagement_score = ?, 
                            content_hash = ?
                        WHERE id = ?
                    """, (
                        post.title, post.content, post.urls, post.url,
                        post.quality_score, post.word_count, post.status,
                        post.tags, post.seo_score, post.engagement_score,
                        post.content_hash, post.id
                    ))
                    logger.info(f"Updated blog post ID: {post.id}")
                    return post.id
                else:
                    # Insert new post
                    cursor = conn.execute("""
                        INSERT INTO blog_posts (
                            title, content, urls, url, quality_score,
                            word_count, status, tags, seo_score, 
                            engagement_score, content_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        post.title, post.content, post.urls, post.url,
                        post.quality_score, post.word_count, post.status,
                        post.tags, post.seo_score, post.engagement_score, 
                        post.content_hash
                    ))
                    post_id = cursor.lastrowid
                    logger.info(f"Created new blog post ID: {post_id}")
                    return post_id
                    
        except sqlite3.IntegrityError as error:
            if "UNIQUE constraint failed" in str(error):
                logger.warning(
                    f"Duplicate prevented by constraint: {post.title}"
                )
                existing_id = self._find_existing_post(conn, post.title)
                if existing_id:
                    return existing_id
            raise
        except Exception as error:
            logger.error(f"Error saving blog post: {error}")
            raise

    def _find_duplicate_post(
        self, 
        conn: Connection, 
        post: BlogPost
    ) -> Optional[int]:
        """Check for existing posts that might be duplicates."""
        # Check for recent posts with same title
        cursor = conn.execute(
            "SELECT id FROM blog_posts "
            "WHERE title = ? AND created_at > datetime('now', '-1 hour')",
            (post.title,)
        )
        if duplicate := cursor.fetchone():
            logger.warning(f"Duplicate title detected: {post.title}")
            return duplicate['id']
        
        # Check for matching content hash
        if post.content_hash:
            cursor = conn.execute(
                "SELECT id FROM blog_posts WHERE content_hash = ?",
                (post.content_hash,)
            )
            if duplicate := cursor.fetchone():
                logger.warning(f"Duplicate content detected: {post.title}")
                return duplicate['id']
        
        return None

    def _find_existing_post(
        self, 
        conn: Connection, 
        title: str
    ) -> Optional[int]:
        """Find existing post by title after constraint violation."""
        cursor = conn.execute(
            "SELECT id FROM blog_posts "
            "WHERE title = ? ORDER BY created_at DESC LIMIT 1",
            (title,)
        )
        if post := cursor.fetchone():
            return post['id']
        return None

    def get_blog_posts(
        self, 
        status: Optional[str] = None, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[BlogPost]:
        """Retrieve blog posts with optional status filter."""
        conn = self.get_connection()
        try:
            query = """
                SELECT * FROM blog_posts 
                {}
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            
            if status:
                query = query.format("WHERE status = ?")
                params = (status, limit, offset)
            else:
                query = query.format("")
                params = (limit, offset)
            
            cursor = conn.execute(query, params)
            return [self._row_to_blog_post(row) for row in cursor.fetchall()]
            
        except Exception as error:
            logger.error(f"Error retrieving posts: {error}")
            return []

    def _row_to_blog_post(self, row) -> BlogPost:
        """Convert database row to BlogPost object."""
        return BlogPost(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            sources=row['sources'],
            urls=row['urls'],
            url=row['url'],
            quality_score=row['quality_score'],
            word_count=row['word_count'],
            created_at=self._parse_datetime(row.get('created_at')),
            published_at=self._parse_datetime(row.get('published_at')),
            status=row['status'],
            tags=row['tags'],
            seo_score=row['seo_score'],
            view_count=row['view_count'],
            engagement_score=row['engagement_score'],
            content_hash=row.get('content_hash', '')
        )

    def _parse_datetime(
        self, 
        timestamp: Optional[str]
    ) -> Optional[datetime]:
        """Parse datetime string from database."""
        if timestamp and isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                return None
        return None

    def record_metric(
        self, 
        component: str, 
        metric_name: str, 
        value: float, 
        tags: Optional[Dict] = None
    ):
        """Record a system metric."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO system_metrics (
                        component, metric_name, metric_value, tags
                    ) VALUES (?, ?, ?, ?)
                """, (
                    component, 
                    metric_name, 
                    value, 
                    json.dumps(tags or {})
                ))
        except Exception as error:
            logger.error(f"Error recording metric: {error}")

    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Generate analytics summary for the specified period."""
        conn = self.get_connection()
        try:
            with conn:
                # Get post statistics
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) AS total_posts,
                        COUNT(CASE WHEN status = 'published' THEN 1 END) AS published_posts,
                        AVG(quality_score) AS avg_quality,
                        AVG(word_count) AS avg_word_count,
                        SUM(view_count) AS total_views
                    FROM blog_posts 
                    WHERE created_at >= datetime('now', '-{days} days')
                """)
                stats = dict(cursor.fetchone() or {})

                # Get system metrics
                cursor = conn.execute(f"""
                    SELECT 
                        component, 
                        metric_name, 
                        AVG(metric_value) AS avg_value
                    FROM system_metrics 
                    WHERE timestamp >= datetime('now', '-{days} days')
                    GROUP BY component, metric_name
                """)
                
                metrics = {}
                for row in cursor.fetchall():
                    component = row['component']
                    if component not in metrics:
                        metrics[component] = {}
                    metrics[component][row['metric_name']] = row['avg_value']

                return {
                    'post_stats': stats,
                    'system_metrics': metrics,
                    'period_days': days
                }
        except Exception as error:
            logger.error(f"Analytics summary error: {error}")
            return {
                'post_stats': {},
                'system_metrics': {},
                'period_days': days
            }

    def optimize_database(self):
        """Run database optimization routines."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            logger.info("Database optimization completed")
        except Exception as error:
            logger.error(f"Optimization failed: {error}")

    def backup_database(self, backup_path: str):
        """Create a database backup."""
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        except Exception as error:
            logger.error(f"Backup failed: {error}")

    def check_for_duplicates(self) -> Dict[str, Any]:
        """Identify duplicate blog posts by title."""
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.execute("""
                    SELECT title, COUNT(*) AS count
                    FROM blog_posts 
                    GROUP BY title 
                    HAVING count > 1 
                    ORDER BY count DESC
                """)
                duplicates = [
                    {'title': row['title'], 'count': row['count']} 
                    for row in cursor.fetchall()
                ]
                return {
                    'duplicate_count': len(duplicates),
                    'duplicates': duplicates
                }
        except Exception as error:
            logger.error(f"Duplicate check failed: {error}")
            return {'duplicate_count': 0, 'duplicates': []}

    def remove_duplicates(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Remove duplicate posts, keeping the most recent.
        
        Args:
            dry_run: If True, only report without deleting
            
        Returns:
            Dictionary with removal statistics
        """
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.execute("""
                    SELECT title, GROUP_CONCAT(id) AS ids, COUNT(*) AS count
                    FROM blog_posts 
                    GROUP BY title 
                    HAVING count > 1
                """)
                
                duplicates = cursor.fetchall()
                removed_count = 0
                
                for row in duplicates:
                    ids = [int(id_str) for id_str in row['ids'].split(',')]
                    ids_to_remove = ids[:-1]  # Keep most recent (highest ID)
                    
                    if not dry_run:
                        for post_id in ids_to_remove:
                            conn.execute(
                                "DELETE FROM blog_posts WHERE id = ?",
                                (post_id,)
                            )
                    removed_count += len(ids_to_remove)
                
                if not dry_run:
                    logger.info(f"Removed {removed_count} duplicate posts")
                else:
                    logger.info(f"DRY RUN: Found {removed_count} duplicates")
                
                return {
                    'removed_count': removed_count,
                    'duplicate_titles': len(duplicates)
                }
        except Exception as error:
            logger.error(f"Duplicate removal failed: {error}")
            return {'removed_count': 0, 'duplicate_titles': 0}


# Global database manager instance
db_manager = DatabaseManager()