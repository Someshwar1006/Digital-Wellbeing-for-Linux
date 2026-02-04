"""
Database module for ZenScreen - SQLite-based storage for usage data.
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import appdirs

APP_NAME = "zenscreen"
APP_AUTHOR = "zenscreen"


def get_data_dir() -> Path:
    """Get the application data directory."""
    data_dir = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """Get the database file path."""
    return get_data_dir() / "zenscreen.db"


class Database:
    """SQLite database manager for ZenScreen."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        self.db_path = db_path or get_db_path()
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # App usage records - tracks each window focus session
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    date TEXT NOT NULL,
                    category TEXT DEFAULT 'uncategorized'
                )
            """)
            
            # Create index for faster date-based queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_app_usage_date 
                ON app_usage(date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_app_usage_app_name 
                ON app_usage(app_name)
            """)
            
            # Daily summaries for quick dashboard access
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    date TEXT PRIMARY KEY,
                    total_screen_time INTEGER DEFAULT 0,
                    total_active_time INTEGER DEFAULT 0,
                    total_idle_time INTEGER DEFAULT 0,
                    app_breakdown TEXT,
                    first_activity TEXT,
                    last_activity TEXT,
                    updated_at TEXT
                )
            """)
            
            # Focus sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    planned_duration INTEGER,
                    actual_duration INTEGER DEFAULT 0,
                    blocked_apps TEXT,
                    completed INTEGER DEFAULT 0,
                    interrupted INTEGER DEFAULT 0
                )
            """)
            
            # Settings/Configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            # App categories (for better organization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_categories (
                    app_name TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    icon TEXT,
                    is_productive INTEGER DEFAULT 0
                )
            """)
            
            # Initialize default settings
            self._init_default_settings(cursor)
            
            conn.commit()
    
    def _init_default_settings(self, cursor):
        """Initialize default settings if not present."""
        defaults = {
            'idle_threshold': '300',  # 5 minutes
            'break_reminder_interval': '3600',  # 1 hour
            'daily_goal_minutes': '480',  # 8 hours
            'enable_notifications': 'true',
            'theme': 'system',
            'start_on_login': 'true',
            'track_window_titles': 'true',
            'focus_default_duration': '1500',  # 25 minutes (Pomodoro)
        }
        
        for key, value in defaults.items():
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # =========== App Usage Methods ===========
    
    def start_app_session(self, app_name: str, window_title: str = "") -> int:
        """Record the start of an app usage session."""
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_usage (app_name, window_title, start_time, date)
                VALUES (?, ?, ?, ?)
            """, (app_name, window_title, now.isoformat(), now.date().isoformat()))
            conn.commit()
            return cursor.lastrowid
    
    def end_app_session(self, session_id: int) -> None:
        """End an app usage session and calculate duration."""
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the start time
            cursor.execute("SELECT start_time FROM app_usage WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = int((now - start_time).total_seconds())
                
                cursor.execute("""
                    UPDATE app_usage 
                    SET end_time = ?, duration_seconds = ?
                    WHERE id = ?
                """, (now.isoformat(), duration, session_id))
                conn.commit()
    
    def get_usage_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get all app usage records for a specific date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM app_usage 
                WHERE date = ?
                ORDER BY start_time
            """, (target_date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_app_usage_summary(self, target_date: date) -> List[Dict[str, Any]]:
        """Get aggregated app usage for a date, sorted by duration."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    app_name,
                    SUM(duration_seconds) as total_duration,
                    COUNT(*) as session_count,
                    MIN(start_time) as first_use,
                    MAX(end_time) as last_use
                FROM app_usage 
                WHERE date = ? AND duration_seconds > 0
                GROUP BY app_name
                ORDER BY total_duration DESC
            """, (target_date.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_total_screen_time(self, target_date: date) -> int:
        """Get total screen time in seconds for a date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(duration_seconds), 0) as total
                FROM app_usage 
                WHERE date = ?
            """, (target_date.isoformat(),))
            return cursor.fetchone()['total']
    
    def get_weekly_summary(self, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get daily totals for the past 7 days."""
        if end_date is None:
            end_date = date.today()
        
        start_date = end_date - timedelta(days=6)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    date,
                    SUM(duration_seconds) as total_duration,
                    COUNT(DISTINCT app_name) as unique_apps
                FROM app_usage 
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date
            """, (start_date.isoformat(), end_date.isoformat()))
            
            results = {row['date']: dict(row) for row in cursor.fetchall()}
            
            # Fill in missing days with zero values
            weekly_data = []
            current = start_date
            while current <= end_date:
                date_str = current.isoformat()
                if date_str in results:
                    weekly_data.append(results[date_str])
                else:
                    weekly_data.append({
                        'date': date_str,
                        'total_duration': 0,
                        'unique_apps': 0
                    })
                current += timedelta(days=1)
            
            return weekly_data
    
    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly usage statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get daily breakdown
            cursor.execute("""
                SELECT 
                    date,
                    SUM(duration_seconds) as total_duration
                FROM app_usage 
                WHERE date LIKE ?
                GROUP BY date
                ORDER BY date
            """, (f"{year:04d}-{month:02d}-%",))
            
            daily_data = [dict(row) for row in cursor.fetchall()]
            
            # Get top apps
            cursor.execute("""
                SELECT 
                    app_name,
                    SUM(duration_seconds) as total_duration
                FROM app_usage 
                WHERE date LIKE ?
                GROUP BY app_name
                ORDER BY total_duration DESC
                LIMIT 10
            """, (f"{year:04d}-{month:02d}-%",))
            
            top_apps = [dict(row) for row in cursor.fetchall()]
            
            total_time = sum(d['total_duration'] for d in daily_data)
            
            return {
                'year': year,
                'month': month,
                'total_screen_time': total_time,
                'daily_breakdown': daily_data,
                'top_apps': top_apps,
                'days_tracked': len(daily_data),
                'average_daily': total_time // len(daily_data) if daily_data else 0
            }
    
    # =========== Focus Session Methods ===========
    
    def start_focus_session(self, duration_minutes: int, blocked_apps: List[str]) -> int:
        """Start a new focus session."""
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO focus_sessions 
                (start_time, planned_duration, blocked_apps)
                VALUES (?, ?, ?)
            """, (now.isoformat(), duration_minutes * 60, json.dumps(blocked_apps)))
            conn.commit()
            return cursor.lastrowid
    
    def end_focus_session(self, session_id: int, completed: bool = True) -> None:
        """End a focus session."""
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get start time
            cursor.execute("SELECT start_time FROM focus_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                actual_duration = int((now - start_time).total_seconds())
                
                cursor.execute("""
                    UPDATE focus_sessions 
                    SET end_time = ?, actual_duration = ?, completed = ?, interrupted = ?
                    WHERE id = ?
                """, (now.isoformat(), actual_duration, int(completed), int(not completed), session_id))
                conn.commit()
    
    def get_active_focus_session(self) -> Optional[Dict[str, Any]]:
        """Get the currently active focus session, if any."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM focus_sessions 
                WHERE end_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['blocked_apps'] = json.loads(result['blocked_apps'] or '[]')
                return result
            return None
    
    def get_focus_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get focus session history for the past N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM focus_sessions 
                WHERE start_time >= ?
                ORDER BY start_time DESC
            """, (cutoff,))
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data['blocked_apps'] = json.loads(data['blocked_apps'] or '[]')
                results.append(data)
            return results
    
    # =========== Settings Methods ===========
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
    
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in cursor.fetchall()}
    
    # =========== App Categories Methods ===========
    
    def set_app_category(self, app_name: str, category: str, is_productive: bool = False) -> None:
        """Set the category for an application."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO app_categories (app_name, category, is_productive)
                VALUES (?, ?, ?)
            """, (app_name, category, int(is_productive)))
            conn.commit()
    
    def get_app_category(self, app_name: str) -> Optional[str]:
        """Get the category for an application."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category FROM app_categories WHERE app_name = ?", (app_name,))
            row = cursor.fetchone()
            return row['category'] if row else None
    
    # =========== Utility Methods ===========
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Remove data older than specified days."""
        cutoff = (date.today() - timedelta(days=days_to_keep)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM app_usage WHERE date < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get the currently active (unclosed) app session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM app_usage 
                WHERE end_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def close_stale_sessions(self) -> int:
        """Close any sessions that were left open (e.g., from crashes)."""
        now = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all unclosed sessions
            cursor.execute("""
                SELECT id, start_time FROM app_usage 
                WHERE end_time IS NULL
            """)
            
            closed = 0
            for row in cursor.fetchall():
                start_time = datetime.fromisoformat(row['start_time'])
                duration = int((now - start_time).total_seconds())
                
                # Cap duration at 1 hour for stale sessions
                duration = min(duration, 3600)
                
                cursor.execute("""
                    UPDATE app_usage 
                    SET end_time = ?, duration_seconds = ?
                    WHERE id = ?
                """, (now.isoformat(), duration, row['id']))
                closed += 1
            
            conn.commit()
            return closed
