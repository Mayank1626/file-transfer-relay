import time
from app.sessions.base import SessionProvider

class InMemorySessionProvider(SessionProvider):
    """Developer-friendly pure In-Memory dict session provider."""
    
    def __init__(self):
        self._sessions = {}
        self.session_expiry = 3600
        self._stats = {}
        
    def init_app(self, app):
        self.session_expiry = app.config['SESSION_EXPIRY']
        
    def get_session(self, pin):
        if pin in self._sessions:
            data = self._sessions[pin]
            current_time = time.time()
            if current_time - data.get('timestamp', 0) > self.session_expiry:
                self.delete_session(pin)
                return None
            return data
        return None
        
    def save_session(self, pin, data, expire_seconds=None):
        self._sessions[pin] = data
        
    def exists(self, pin):
        return self.get_session(pin) is not None
        
    def delete_session(self, pin):
        self._sessions.pop(pin, None)
        
    def increment_stat(self, metric_name):
        self._stats[metric_name] = self._stats.get(metric_name, 0) + 1
        
    def get_stat(self, metric_name):
        return self._stats.get(metric_name, 0)
