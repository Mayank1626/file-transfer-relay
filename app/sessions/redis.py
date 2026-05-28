import json
import redis
from app.sessions.base import SessionProvider

class RedisSessionProvider(SessionProvider):
    """Production-grade Redis-backed pairing session provider."""
    
    def __init__(self):
        self.host = None
        self.port = None
        self.db = None
        self._redis_client = None
        self.session_expiry = 3600
        
    def init_app(self, app):
        self.host = app.config['REDIS_HOST']
        self.port = app.config['REDIS_PORT']
        self.db = app.config['REDIS_DB']
        self.session_expiry = app.config['SESSION_EXPIRY']
        
        self._redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )
        # Ping check
        try:
            self._redis_client.ping()
            app.logger.info("Successfully connected to Redis session backend.")
        except Exception as e:
            app.logger.error(f"Redis session connection failure: {e}")
            raise e
            
    def _key(self, pin):
        return f"sess:{pin}"
        
    def get_session(self, pin):
        key = self._key(pin)
        try:
            data = self._redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None
            
    def save_session(self, pin, data, expire_seconds=None):
        if expire_seconds is None:
            expire_seconds = self.session_expiry
            
        key = self._key(pin)
        try:
            self._redis_client.setex(key, expire_seconds, json.dumps(data))
        except Exception:
            pass
            
    def exists(self, pin):
        key = self._key(pin)
        try:
            return bool(self._redis_client.exists(key))
        except Exception:
            return False
            
    def delete_session(self, pin):
        key = self._key(pin)
        try:
            self._redis_client.delete(key)
        except Exception:
            pass
            
    def increment_stat(self, metric_name):
        """Helper to increment total upload metrics cleanly in Redis."""
        try:
            self._redis_client.incr(metric_name)
        except Exception:
            pass
            
    def get_stat(self, metric_name):
        """Helper to fetch metric values safely."""
        try:
            val = self._redis_client.get(metric_name)
            return int(val) if val else 0
        except Exception:
            return 0
