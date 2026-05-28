import os
from flask import current_app
from app.ai.database.repository import AIMemoryRepository

# Safety limit for desktop performance
MAX_SCREENSHOTS_LIMIT = 500

def enforce_retention():
    """Prunes database index rows for the oldest screenshots when quota is exceeded."""
    try:
        stats = AIMemoryRepository.get_stats()
        total = stats.get('total_indexed', 0)
        
        if total > MAX_SCREENSHOTS_LIMIT:
            excess = total - MAX_SCREENSHOTS_LIMIT
            current_app.logger.info(f"AI Retention: Index count ({total}) exceeds quota ({MAX_SCREENSHOTS_LIMIT}). Pruning {excess} oldest records...")
            
            # Fetch the oldest items
            oldest_items = AIMemoryRepository.get_oldest_screenshots(limit=excess)
            for item in oldest_items:
                AIMemoryRepository.delete_screenshot(item['id'])
                current_app.logger.info(f"AI Retention: Safely pruned database index for oldest screenshot ID: {item['id']}")
    except Exception as e:
        current_app.logger.error(f"AI Retention: Quota enforcement failed: {e}")

def cleanup_orphans():
    """Scans all registered database filepaths and purges entries if the image was deleted on disk."""
    try:
        # Fetch screenshots from DB in batches or list all for clean validation
        conn = None
        try:
            from app.ai.database.db import get_db_connection
            conn = get_db_connection()
            rows = conn.execute("SELECT id, filepath FROM screenshots").fetchall()
            
            orphan_count = 0
            for row in rows:
                filepath = row['filepath']
                # If screenshot is deleted from user's hard drive
                if not os.path.exists(filepath):
                    AIMemoryRepository.delete_screenshot(row['id'])
                    orphan_count += 1
                    current_app.logger.info(f"AI Retention: Pruned orphan index for deleted hard drive screenshot: {filepath}")
            
            if orphan_count > 0:
                current_app.logger.info(f"AI Retention: Cleaned up {orphan_count} orphan database entries successfully.")
        finally:
            if conn:
                conn.close()
    except Exception as e:
        current_app.logger.error(f"AI Retention: Orphan scanning failed: {e}")
