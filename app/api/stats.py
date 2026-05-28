from flask import request, jsonify, current_app
from app.api import api_bp
from app.sessions import get_sessions

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Returns total uploads initiated (Admin protected)."""
    admin_key = current_app.config['ADMIN_KEY']
    
    # Authorize key
    if request.args.get("key") != admin_key or not admin_key:
        return jsonify({"error": "Unauthorized"}), 403
        
    sessions = get_sessions()
    total = 0
    if hasattr(sessions, 'get_stat'):
        total = sessions.get_stat("stats:total_uploads")
        
    return jsonify({
        "success": True, 
        "total_uploads_initiated": total
    })
