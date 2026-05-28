import sqlite3
import time
from app.ai.database.db import get_db_connection

class AIClipboardRepository:
    """Interfaces our SQLite tables for clipboard data and exclusion rules."""

    @staticmethod
    def is_hash_excluded(content_hash):
        """Returns True if the content hash is in the excluded list."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM excluded_hashes WHERE hash = ?",
                (content_hash,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    @staticmethod
    def exclude_hash(content_hash):
        """Registers a hash in the permanent exclusion list."""
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO excluded_hashes (hash) VALUES (?)",
                (content_hash,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_entry_by_hash(content_hash):
        """Retrieves a clipboard entry matching SHA-256 hash."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM clipboard_entries WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_latest_entry_from_app(source_app):
        """Retrieves the latest clipboard entry captured from a specific app."""
        if not source_app:
            return None
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM clipboard_entries WHERE source_app = ? ORDER BY created_at DESC LIMIT 1",
                (source_app,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def insert_entry(content, content_hash, content_type, source_app, character_count, session_id=None):
        """Registers a clipboard entry. Excludes duplicates and ignored hashes."""
        if AIClipboardRepository.is_hash_excluded(content_hash):
            return None
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO clipboard_entries (content, content_hash, content_type, source_app, character_count, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (content, content_hash, content_type, source_app, character_count, session_id)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def delete_entry(entry_id, exclude=False):
        """Removes a clipboard entry. If exclude is True, its hash is permanently ignored."""
        conn = get_db_connection()
        try:
            if exclude:
                row = conn.execute("SELECT content_hash FROM clipboard_entries WHERE id = ?", (entry_id,)).fetchone()
                if row:
                    AIClipboardRepository.exclude_hash(row['content_hash'])
            conn.execute("DELETE FROM clipboard_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def toggle_favorite(entry_id):
        """Toggles the favorited state of a clipboard entry."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute("SELECT is_favorite FROM clipboard_entries WHERE id = ?", (entry_id,)).fetchone()
            if row:
                new_fav = 1 if row['is_favorite'] == 0 else 0
                cursor.execute("UPDATE clipboard_entries SET is_favorite = ? WHERE id = ?", (new_fav, entry_id))
                conn.commit()
                return True
            return False
        finally:
            conn.close()

    @staticmethod
    def clear_history():
        """Clears all clipboard history, keeping favorited entries intact."""
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM clipboard_entries WHERE is_favorite = 0")
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_recent_entries(limit=15, offset=0):
        """Fetches latest clipboard history rows in chronological order."""
        conn = get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM clipboard_entries ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def prune_older_than_30_days():
        """Auto-deletes entries older than 30 days (excluding favorited ones)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM clipboard_entries WHERE is_favorite = 0 AND created_at < datetime('now', '-30 days')"
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    @staticmethod
    def enforce_limit(max_limit=2000):
        """Limits clipboard index rows to prevent database bloat, keeping oldest favorites."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*) FROM clipboard_entries").fetchone()[0]
            if total > max_limit:
                excess = total - max_limit
                # Fetch IDs of the oldest non-favorited entries to delete
                old_rows = cursor.execute(
                    "SELECT id FROM clipboard_entries WHERE is_favorite = 0 ORDER BY created_at ASC LIMIT ?",
                    (excess,)
                ).fetchall()
                ids_to_del = [r['id'] for r in old_rows]
                if ids_to_del:
                    cursor.execute(
                        f"DELETE FROM clipboard_entries WHERE id IN ({','.join(['?']*len(ids_to_del))})",
                        tuple(ids_to_del)
                    )
                    conn.commit()
                    return len(ids_to_del)
            return 0
        finally:
            conn.close()
