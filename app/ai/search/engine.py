from datetime import datetime, timezone
from app.ai.database.repository import AIMemoryRepository
from app.ai.clipboard.repository import AIClipboardRepository
from app.ai.database.db import get_db_connection

class AISearchEngine:
    """Governs combined search token logic across screenshots and clipboard memories."""

    @staticmethod
    def search_clipboard(query_string, limit=15, offset=0):
        """Keyword term matching on clipboard content, source process, or content type."""
        if not query_string:
            return AIClipboardRepository.get_recent_entries(limit, offset)

        tokens = [t.lower().strip() for t in query_string.split() if t.strip()]
        if not tokens:
            return AIClipboardRepository.get_recent_entries(limit, offset)

        conn = get_db_connection()
        try:
            where_clauses = []
            params = []
            for token in tokens:
                where_clauses.append("(content LIKE ? OR source_app LIKE ? OR content_type LIKE ?)")
                wildcard = f"%{token}%"
                params.extend([wildcard, wildcard, wildcard])

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT * FROM clipboard_entries
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def search(query, limit=15, offset=0, source='all'):
        """Searches indexed screenshots and clipboard history with custom scoring and source filters."""
        query = query.strip() if query else ""

        screenshots = []
        clipboards = []

        # 1. Query Screenshots if applicable
        if source in ['all', 'screenshots']:
            raw_scr = AIMemoryRepository.search_screenshots(query, limit + offset, 0)
            for row in raw_scr:
                screenshots.append({
                    'id': row['id'],
                    'type': 'screenshot',
                    'filepath': row['filepath'],
                    'filename': row['filename'],
                    'filesize': row['filesize'],
                    'width': row['width'],
                    'height': row['height'],
                    'folder': row['folder'],
                    'created_at': row['created_at'],
                    'ocr_status': row.get('ocr_status', 'METADATA_ONLY'),
                    'ocr_text': row.get('ocr_text', ''),
                    'is_favorite': 0,
                    'highlights': AISearchEngine._generate_highlights(row.get('ocr_text', ''), query)
                })

        # 2. Query Clipboard entries if applicable
        if source in ['all', 'clipboard']:
            raw_clip = AISearchEngine.search_clipboard(query, limit + offset, 0)
            for row in raw_clip:
                clipboards.append({
                    'id': row['id'],
                    'type': 'clipboard',
                    'content': row['content'],
                    'content_type': row['content_type'],
                    'source_app': row['source_app'],
                    'character_count': row['character_count'],
                    'is_favorite': row['is_favorite'],
                    'session_id': row['session_id'],
                    'created_at': row['created_at'],
                    'highlights': AISearchEngine._generate_highlights(row['content'], query)
                })

        # 3. Merge both lists
        merged = screenshots + clipboards

        # 4. Score results for Option B ranking
        # score = created_at_epoch + (is_favorite * 3 days) + (exact_match * 5 days)
        def parse_dt(dt_str):
            try:
                # Handle SQLite standard format 'YYYY-MM-DD HH:MM:SS'
                # If there's a T or other formats, try parsing gracefully
                dt_str = dt_str.replace('T', ' ')
                # Remove timezone offset representation if present
                if '.' in dt_str:
                    dt_str = dt_str.split('.')[0]
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                return 0.0

        scored_results = []
        for item in merged:
            created_time = parse_dt(item['created_at'])
            score = created_time

            # A: Favorite Boost (3 days = 259,200 seconds)
            if item.get('is_favorite', 0) == 1:
                score += 259200.0

            # B: Exact substring match Boost (5 days = 432,000 seconds)
            if query:
                query_lower = query.lower()
                is_exact = False
                if item['type'] == 'screenshot':
                    is_exact = query_lower in item['filename'].lower() or query_lower in item['ocr_text'].lower()
                elif item['type'] == 'clipboard':
                    is_exact = query_lower in item['content'].lower() or query_lower in item.get('source_app', '').lower()

                if is_exact:
                    score += 432000.0

            scored_results.append((score, item))

        # 5. Sort descending by score
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # 6. Apply pagination offset & limit
        paginated = [item for _, item in scored_results[offset : offset + limit]]
        return paginated

    @staticmethod
    def _generate_highlights(text, query):
        """Lightweight snippet extractor highlighting matching search tokens."""
        if not text or not query:
            return ""

        words = [w.lower().strip() for w in query.split() if w.strip()]
        if not words:
            # Return snippet of text
            snippet_len = 120
            return text[:snippet_len] + (" ..." if len(text) > snippet_len else "")

        lower_text = text.lower()
        snippet_len = 120

        for word in words:
            idx = lower_text.find(word)
            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(text), idx + snippet_len)
                snippet = text[start:end]
                
                prefix = "... " if start > 0 else ""
                suffix = " ..." if end < len(text) else ""
                return f"{prefix}{snippet}{suffix}"

        return text[:snippet_len] + (" ..." if len(text) > snippet_len else "")
