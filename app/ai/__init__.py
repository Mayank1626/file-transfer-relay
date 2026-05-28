import os
from flask import Blueprint, request, jsonify, current_app

from app.ai.database.repository import AIMemoryRepository
from app.ai.search.engine import AISearchEngine
from app.ai.indexing.watcher import get_default_screenshots_folder
from app.ai.clipboard import (
    AIClipboardRepository,
    set_paused_until,
    get_pause_status
)

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai/search', methods=['POST'])
def search_memory():
    """Queries indexed screenshots and clipboard history, returning highlighted term matches."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        limit = int(data.get('limit', 15))
        offset = int(data.get('offset', 0))
        source = data.get('source', 'all').strip().lower()

        results = AISearchEngine.search(query, limit, offset, source)
        
        return jsonify({
            'success': True,
            'query': query,
            'source': source,
            'results': results
        })
    except Exception as e:
        current_app.logger.error(f"AI Routes: Unified search failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/stats', methods=['GET'])
def get_memory_stats():
    """Returns status tickers representing screenshots, worker queues, and clipboard tracking states."""
    try:
        stats = AIMemoryRepository.get_stats()
        stats['screenshots_folder'] = get_default_screenshots_folder()
        
        # Append Clipboard statistics
        conn = None
        try:
            from app.ai.database.db import get_db_connection
            conn = get_db_connection()
            total_clip = conn.execute("SELECT COUNT(*) FROM clipboard_entries").fetchone()[0]
            fav_clip = conn.execute("SELECT COUNT(*) FROM clipboard_entries WHERE is_favorite = 1").fetchone()[0]
            excl_clip = conn.execute("SELECT COUNT(*) FROM excluded_hashes").fetchone()[0]
        except Exception:
            total_clip = 0
            fav_clip = 0
            excl_clip = 0
        finally:
            if conn:
                conn.close()

        is_paused, remaining = get_pause_status()

        stats.update({
            'total_clipboard': total_clip,
            'favorite_clipboard': fav_clip,
            'excluded_hashes_count': excl_clip,
            'is_tracking_paused': is_paused,
            'pause_remaining_seconds': remaining
        })

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/clipboard/favorite', methods=['POST'])
def toggle_clipboard_favorite():
    """Toggles favorite/star badge status for a clipboard history row."""
    try:
        data = request.get_json() or {}
        entry_id = data.get('id')
        if not entry_id:
            return jsonify({'success': False, 'error': 'Entry ID is required'}), 400

        success = AIClipboardRepository.toggle_favorite(entry_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/clipboard/delete', methods=['POST'])
def delete_clipboard_entry():
    """Deletes a clipboard entry from DB, optionally adding its hash to permanent excluded index."""
    try:
        data = request.get_json() or {}
        entry_id = data.get('id')
        exclude = bool(data.get('exclude', False))
        if not entry_id:
            return jsonify({'success': False, 'error': 'Entry ID is required'}), 400

        success = AIClipboardRepository.delete_entry(entry_id, exclude)
        return jsonify({'success': success, 'excluded': exclude})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/clipboard/clear', methods=['POST'])
def clear_clipboard_history():
    """Clears all non-favorited clipboard records from storage."""
    try:
        success = AIClipboardRepository.clear_history()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/clipboard/toggle-tracking', methods=['POST'])
def toggle_clipboard_tracking():
    """Handles manual/timed pauses: duration in seconds (-1 for permanent pause, 0 for active resume)."""
    try:
        data = request.get_json() or {}
        duration = int(data.get('duration', 0))
        
        set_paused_until(duration)
        is_paused, remaining = get_pause_status()
        
        return jsonify({
            'success': True,
            'is_tracking_paused': is_paused,
            'pause_remaining_seconds': remaining
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/index/mock', methods=['POST'])
def bootstrap_mock_screenshots():
    """Injects high-fidelity mock screenshots and clipboard entries for immediate demo feedback."""
    try:
        screenshots_dir = get_default_screenshots_folder()
        os.makedirs(screenshots_dir, exist_ok=True)

        # 3 Mock screenshots
        mock_screenshots = [
            {
                'filename': 'react_context_error.png',
                'size': 142050,
                'hash': 'mock_sha_react_context_error_12345',
                'ocr': 'React Context Auth Provider Error: Type mismatch at useContext Hook. Line 45 in login.js. TypeError: Cannot read properties of null (reading "useContext")',
                'norm': 'react context auth provider error type mismatch usecontext hook line 45 login.js typeerror cannot read properties null reading'
            },
            {
                'filename': 'leetcode_dp_solution.png',
                'size': 98200,
                'hash': 'mock_sha_leetcode_dp_solution_67890',
                'ocr': 'Leetcode Dynamic Programming. Top-down memoization: class Solution: def longestCommonSubsequence(self, text1: str, text2: str) -> int: dp = [[0]*(len(text2)+1) for _ in range(len(text1)+1)]',
                'norm': 'leetcode dynamic programming top-down memoization class solution def longestcommonsubsequence text1 str text2 int dp len range'
            },
            {
                'filename': 'mayank_resume.png',
                'size': 204310,
                'hash': 'mock_sha_mayank_resume_24680',
                'ocr': 'Mayank Software Engineer CV. Tech Stack: Python, Flask, Redis, React, SQL. Projects: ZapLink Frictionless File Transfer Platform and AI Cognitive Memory Orchestrator.',
                'norm': 'mayank software engineer cv tech stack python flask redis react sql projects zaplink frictionless file transfer platform ai cognitive memory orchestrator'
            }
        ]

        inserted_scr = 0
        for item in mock_screenshots:
            filepath = os.path.join(screenshots_dir, item['filename'])
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 100)

            dup = AIMemoryRepository.get_screenshot_by_hash(item['hash'])
            if not dup:
                screenshot_id = AIMemoryRepository.insert_screenshot(
                    filepath=filepath,
                    filename=item['filename'],
                    filesize=item['size'],
                    file_hash=item['hash'],
                    folder=os.path.basename(screenshots_dir),
                    width=1920,
                    height=1080
                )
                
                AIMemoryRepository.insert_ocr_result(
                    screenshot_id=screenshot_id,
                    ocr_text=item['ocr'],
                    normalized_text=item['norm'],
                    status='COMPLETE'
                )
                inserted_scr += 1

        # 3 Mock clipboard entries
        mock_clipboards = [
            {
                'content': 'npm run dev',
                'hash': 'mock_clip_sha_npm_run_dev_1',
                'type': 'COMMAND',
                'app': 'cmd.exe',
                'chars': 11
            },
            {
                'content': 'SELECT * FROM users WHERE email = \'test@example.com\';',
                'hash': 'mock_clip_sha_sql_select_2',
                'type': 'SQL',
                'app': 'TablePlus.exe',
                'chars': 53
            },
            {
                'content': 'https://github.com/Mayank1626/file-transfer-relay',
                'hash': 'mock_clip_sha_git_url_3',
                'type': 'URL',
                'app': 'chrome.exe',
                'chars': 49
            }
        ]

        inserted_clip = 0
        import uuid
        mock_session = str(uuid.uuid4())
        for item in mock_clipboards:
            dup = AIClipboardRepository.get_entry_by_hash(item['hash'])
            if not dup:
                AIClipboardRepository.insert_entry(
                    content=item['content'],
                    content_hash=item['hash'],
                    content_type=item['type'],
                    source_app=item['app'],
                    character_count=item['chars'],
                    session_id=mock_session
                )
                inserted_clip += 1

        # Run quota check
        from app.ai.retention.manager import enforce_retention
        enforce_retention()

        return jsonify({
            'success': True,
            'message': f"Bootstrapped {inserted_scr} mock screenshots and {inserted_clip} mock clipboard entries successfully.",
            'monitored_folder': screenshots_dir
        })
    except Exception as e:
        current_app.logger.error(f"AI Routes: Ingestion mock bootstrap error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/debug/sessions', methods=['GET'])
def debug_sessions():
    """Diagnostic route that exposes active session keys and statuses (safe/non-sensitive)."""
    try:
        from app.sessions import get_sessions
        sessions = get_sessions()
        
        session_list = {}
        # 1. Redis check
        if hasattr(sessions, '_redis_client') and sessions._redis_client:
            keys = sessions._redis_client.keys("sess:*")
            for key in keys:
                pin = key.split(":")[-1]
                data = sessions.get_session(pin)
                if data:
                    session_list[pin] = data
        # 2. Local File check
        elif hasattr(sessions, 'upload_folder') and sessions.upload_folder:
            import os
            for filename in os.listdir(sessions.upload_folder):
                if filename.startswith("sess_") and filename.endswith(".json"):
                    pin = filename[5:-5]
                    data = sessions.get_session(pin)
                    if data:
                        session_list[pin] = data
                        
        return jsonify({
            'success': True,
            'provider': sessions.__class__.__name__,
            'active_sessions': session_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
