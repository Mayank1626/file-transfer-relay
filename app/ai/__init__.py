import os
from flask import Blueprint, request, jsonify, current_app

from app.ai.database.repository import AIMemoryRepository
from app.ai.search.engine import AISearchEngine
from app.ai.indexing.watcher import get_default_screenshots_folder

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai/search', methods=['POST'])
def search_memory():
    """Queries indexed screenshots and returns highlighted keyword matches."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        limit = int(data.get('limit', 10))
        offset = int(data.get('offset', 0))

        # Retrieve matches using token keyword search
        results = AISearchEngine.search(query, limit, offset)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results
        })
    except Exception as e:
        current_app.logger.error(f"AI Routes: Search failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/stats', methods=['GET'])
def get_memory_stats():
    """Returns tickers representing the active index and background worker states."""
    try:
        stats = AIMemoryRepository.get_stats()
        # Append screenshots folder path to statistics
        stats['screenshots_folder'] = get_default_screenshots_folder()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/ai/index/mock', methods=['POST'])
def bootstrap_mock_screenshots():
    """Injects high-fidelity mock screenshots on disk and in the DB for instant demo capability."""
    try:
        screenshots_dir = get_default_screenshots_folder()
        os.makedirs(screenshots_dir, exist_ok=True)

        # 3 Mock targets
        mock_data = [
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

        inserted = 0
        for item in mock_data:
            filepath = os.path.join(screenshots_dir, item['filename'])
            
            # Create physical mock files on disk to prevent missing file unlinks
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    # Write dummy bytes representing a simulated small png
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 100)

            # Check if this hash is already present in DB
            dup = AIMemoryRepository.get_screenshot_by_hash(item['hash'])
            if not dup:
                # Direct SQL Injection bypassing heavy Watchdog queue loops
                screenshot_id = AIMemoryRepository.insert_screenshot(
                    filepath=filepath,
                    filename=item['filename'],
                    filesize=item['size'],
                    file_hash=item['hash'],
                    folder=os.path.basename(screenshots_dir),
                    width=1920,
                    height=1080
                )
                
                # Insert mock OCR result
                AIMemoryRepository.insert_ocr_result(
                    screenshot_id=screenshot_id,
                    ocr_text=item['ocr'],
                    normalized_text=item['norm'],
                    status='COMPLETE'
                )
                inserted += 1

        # Triggers quota check just in case
        from app.ai.retention.manager import enforce_retention
        enforce_retention()

        return jsonify({
            'success': True,
            'message': f"Successfully bootstrapped {inserted} mock screenshots into memory index.",
            'monitored_folder': screenshots_dir
        })
    except Exception as e:
        current_app.logger.error(f"AI Routes: Ingestion bootstrap error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
