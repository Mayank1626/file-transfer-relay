from app.storage.local import LocalStorageEngine
from app.storage.s3 import S3StorageEngine

# Singleton storage engine instance
_storage_engine = None

def init_storage(app):
    """Initializes the configured storage engine as a global singleton."""
    global _storage_engine
    
    engine_name = app.config['STORAGE_ENGINE'].lower()
    
    if engine_name == "local":
        _storage_engine = LocalStorageEngine()
    elif engine_name == "s3":
        _storage_engine = S3StorageEngine()
    else:
        raise ValueError(f"Unknown storage engine: {engine_name}")
        
    _storage_engine.init_app(app)
    app.logger.info(f"Storage engine successfully initialized: {engine_name.upper()}")
    return _storage_engine

def get_storage():
    """Retrieves the active storage engine singleton instance."""
    if _storage_engine is None:
        raise RuntimeError("Storage engine has not been initialized. Call init_storage(app) first.")
    return _storage_engine
