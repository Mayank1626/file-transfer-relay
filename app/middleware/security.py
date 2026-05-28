import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from flask import request, jsonify, has_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

# Global limiter instance placeholder
limiter = None

class RequestIDFilter(logging.Filter):
    """Logging filter that injects the current request context's ID and endpoint."""
    def filter(self, record):
        if has_request_context():
            record.request_id = request.environ.get('request_id', 'N/A')
            record.endpoint = request.endpoint or 'N/A'
        else:
            record.request_id = 'N/A'
            record.endpoint = 'N/A'
        return True

def setup_logging(app):
    """Configures rotating file logging with unique Request ID context matching."""
    log_dir = app.config['LOG_DIR']
    os.makedirs(log_dir, exist_ok=True)
    
    handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(request_id)s] %(endpoint)s: %(message)s'
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

def init_security_middleware(app):
    """Registers before/after request middleware and centralized error handlers."""
    
    @app.before_request
    def before_request():
        # Inject unique 8-character request ID trace
        request.environ['request_id'] = uuid.uuid4().hex[:8]
        
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response
        
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
            
        req_id = request.environ.get('request_id', 'N/A')
        app.logger.error(
            f"Server Error: {str(e)}", 
            extra={'request_id': req_id, 'endpoint': request.endpoint}
        )
        return jsonify({"success": False, "error": "Internal server error"}), 500
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"success": False, "error": "Too many requests. Please slow down."}), 429
        
    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"success": False, "error": "File size exceeds the configured upload limit."}), 413

def init_limiter(app):
    """Sets up the global rate limiter using either Redis URI or local memory."""
    global limiter
    
    session_provider = app.config['SESSION_PROVIDER'].lower()
    
    if session_provider == "redis":
        redis_host = app.config['REDIS_HOST']
        redis_port = app.config['REDIS_PORT']
        storage_uri = f"redis://{redis_host}:{redis_port}"
    else:
        # In-memory storage fallback for local development
        storage_uri = "memory://"
        
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri=storage_uri,
        strategy="fixed-window"
    )
    return limiter

def get_limiter():
    """Retrieves the globally initialized rate limiter."""
    return limiter
