from app.sessions.local import LocalSessionProvider
from app.sessions.redis import RedisSessionProvider
from app.sessions.memory import InMemorySessionProvider

# Global session provider singleton instance
_session_provider = None

def init_sessions(app):
    """Initializes the configured session provider as a global singleton."""
    global _session_provider
    
    provider_name = app.config['SESSION_PROVIDER'].lower()
    
    if provider_name == "local":
        _session_provider = LocalSessionProvider()
    elif provider_name == "redis":
        _session_provider = RedisSessionProvider()
    elif provider_name == "memory":
        _session_provider = InMemorySessionProvider()
    else:
        raise ValueError(f"Unknown session provider: {provider_name}")
        
    _session_provider.init_app(app)
    app.logger.info(f"Session provider successfully initialized: {provider_name.upper()}")
    return _session_provider

def get_sessions():
    """Retrieves the active session provider singleton instance."""
    if _session_provider is None:
        raise RuntimeError("Session provider has not been initialized. Call init_sessions(app) first.")
    return _session_provider
