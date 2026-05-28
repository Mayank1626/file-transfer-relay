import time
import sqlite3
from app.ai.database.db import get_db_connection

class AIMemoryRepository:
    """Provides structured data access routines interfacing our SQLite tables."""

    @staticmethod
    def get_screenshot_by_hash(file_hash):
        """Returns screenshot row if hash already exists in database."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM screenshots WHERE hash = ?", 
                (file_hash,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_screenshot_by_path(filepath):
        """Returns screenshot row matching absolute filepath."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM screenshots WHERE filepath = ?", 
                (filepath,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def insert_screenshot(filepath, filename, filesize, file_hash, folder, width=0, height=0):
        """Registers a new screenshot in database, returning its primary ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO screenshots (filepath, filename, filesize, hash, folder, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (filepath, filename, filesize, file_hash, folder, width, height)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Handle collision gracefully
            row = cursor.execute("SELECT id FROM screenshots WHERE hash = ?", (file_hash,)).fetchone()
            return row['id'] if row else None
        finally:
            conn.close()

    @staticmethod
    def insert_ocr_result(screenshot_id, ocr_text, normalized_text, status='COMPLETE'):
        """Registers an OCR text processing result mapping it to a screenshot ID."""
        conn = get_db_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO ocr_results (screenshot_id, ocr_text, normalized_text, status)
                VALUES (?, ?, ?, ?)
                """,
                (screenshot_id, ocr_text, normalized_text, status)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def add_processing_job(filepath):
        """Registers a new indexing request path in the queue."""
        conn = get_db_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO processing_jobs (filepath, status)
                VALUES (?, 'PENDING')
                """,
                (filepath,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_next_pending_job():
        """Fetches the oldest PENDING job row in a worker-safe queue transaction."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                """
                SELECT * FROM processing_jobs 
                WHERE status = 'PENDING' 
                ORDER BY created_at ASC LIMIT 1
                """
            ).fetchone()
            
            if row:
                job = dict(row)
                # Transition status immediately to prevent dual processing
                cursor.execute(
                    "UPDATE processing_jobs SET status = 'PROCESSING', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (job['id'],)
                )
                conn.commit()
                return job
            return None
        finally:
            conn.close()

    @staticmethod
    def update_job_status(job_id, status, error_message=None, retry_count=None):
        """Updates a processing job status."""
        conn = get_db_connection()
        try:
            query = "UPDATE processing_jobs SET status = ?, updated_at = CURRENT_TIMESTAMP"
            params = [status]

            if error_message is not None:
                query += ", error_message = ?"
                params.append(error_message)

            if retry_count is not None:
                query += ", retry_count = ?"
                params.append(retry_count)

            query += " WHERE id = ?"
            params.append(job_id)

            conn.execute(query, tuple(params))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def remove_processing_job(filepath):
        """Removes a finished job from queue."""
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM processing_jobs WHERE filepath = ?", (filepath,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_screenshot(screenshot_id):
        """Deletes a screenshot record and cascades associated OCR rows."""
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_oldest_screenshots(limit=50):
        """Retrieves list of the oldest indexed screenshots for retention prunes."""
        conn = get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM screenshots ORDER BY created_at ASC LIMIT ?", 
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_stats():
        """Aggregates active indexing tickers for status reports."""
        conn = get_db_connection()
        try:
            total_scr = conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
            pending_jobs = conn.execute("SELECT COUNT(*) FROM processing_jobs WHERE status IN ('PENDING', 'PROCESSING')").fetchone()[0]
            success_ocr = conn.execute("SELECT COUNT(*) FROM ocr_results WHERE status = 'COMPLETE'").fetchone()[0]
            failed_jobs = conn.execute("SELECT COUNT(*) FROM processing_jobs WHERE status = 'FAILED'").fetchone()[0]
            
            return {
                'total_indexed': total_scr,
                'pending_queue': pending_jobs,
                'ocr_complete': success_ocr,
                'failed_jobs': failed_jobs
            }
        finally:
            conn.close()

    @staticmethod
    def get_recent_screenshots(limit=10, offset=0):
        """Fetches the latest indexed files coupled with their OCR result details."""
        conn = get_db_connection()
        try:
            rows = conn.execute(
                """
                SELECT s.*, o.ocr_text, o.status as ocr_status 
                FROM screenshots s
                LEFT JOIN ocr_results o ON s.id = o.screenshot_id
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def search_screenshots(query_string, limit=10, offset=0):
        """Multi-token keyword matching with SQL filters and recency sorting."""
        if not query_string:
            return AIMemoryRepository.get_recent_screenshots(limit, offset)

        # Tokenize query string
        tokens = [t.lower().strip() for t in query_string.split() if t.strip()]
        if not tokens:
            return AIMemoryRepository.get_recent_screenshots(limit, offset)

        conn = get_db_connection()
        try:
            # Build query combining match rules for all tokens
            where_clauses = []
            params = []

            for token in tokens:
                # Require each token to match either filename or normalized search texts
                where_clauses.append("(s.filename LIKE ? OR o.normalized_text LIKE ?)")
                wildcard = f"%{token}%"
                params.extend([wildcard, wildcard])

            where_sql = " AND ".join(where_clauses)
            
            # Recency ranking
            sql = f"""
                SELECT s.*, o.ocr_text, o.status as ocr_status
                FROM screenshots s
                LEFT JOIN ocr_results o ON s.id = o.screenshot_id
                WHERE {where_sql}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
