import os
import json
import time
from app.sessions.base import SessionProvider

class LocalSessionProvider(SessionProvider):
    """Disk-backed JSON file session provider (similar to original app.py)."""
    
    def __init__(self):
        self.upload_folder = None
        self.session_expiry = 3600
        
    def init_app(self, app):
        self.upload_folder = app.config['UPLOAD_FOLDER']
        self.session_expiry = app.config['SESSION_EXPIRY']
        os.makedirs(self.upload_folder, exist_ok=True)
        
    def _get_path(self, pin):
        return os.path.join(self.upload_folder, f"sess_{pin}.json")
        
    def get_session(self, pin):
        path = self._get_path(pin)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Validate manual expiry limit for file-backed sessions
                current_time = time.time()
                if current_time - data.get('timestamp', 0) > self.session_expiry:
                    self.delete_session(pin)
                    return None
                return data
            except Exception:
                pass
        return None
        
    def save_session(self, pin, data, expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.session_expiry
            
        path = self._get_path(pin)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass
            
    def exists(self, pin):
        return self.get_session(pin) is not None
        
    def delete_session(self, pin):
        path = self._get_path(pin)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
