import os

class Config:
    """Unified application configuration class.
    
    Loads configuration settings from environment variables and enforces validation.
    """
    # Flask configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "zaplink-secure-default-key-1948")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024))  # Default 2GB limit
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Domain engine choices
    STORAGE_ENGINE = os.environ.get("STORAGE_ENGINE", "local").lower()  # Options: 'local', 's3'
    SESSION_PROVIDER = os.environ.get("SESSION_PROVIDER", "local").lower()  # Options: 'local', 'redis', 'memory'

    # Local Storage & Sessions Config
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))
    SESSION_CLEANUP_INTERVAL = int(os.environ.get("SESSION_CLEANUP_INTERVAL", 600))  # 10 minutes
    SESSION_EXPIRY = int(os.environ.get("SESSION_EXPIRY", 3600))  # 1 hour

    # MinIO / S3 Configuration
    S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "admin")
    S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "supersecret")
    S3_BUCKET = os.environ.get("S3_BUCKET", "filedrop")
    S3_SIGNATURE_VERSION = os.environ.get("S3_SIGNATURE_VERSION", "s3v4")

    # Redis Configuration
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))

    # Log Settings
    LOG_DIR = os.environ.get("LOG_DIR", "logs")
    LOG_FILE = os.path.join(LOG_DIR, "filedrop.log")
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5

    # Rate Limiting
    RATELIMIT_PIN_REQUEST = os.environ.get("RATELIMIT_PIN_REQUEST", "10 per minute")
    RATELIMIT_UPLOAD_LINK = os.environ.get("RATELIMIT_UPLOAD_LINK", "20 per hour")
    RATELIMIT_CHECK_SESSION = os.environ.get("RATELIMIT_CHECK_SESSION", "5 per minute")
    RATELIMIT_DOWNLOAD_LINK = os.environ.get("RATELIMIT_DOWNLOAD_LINK", "5 per minute")

    # Admin Key
    ADMIN_KEY = os.environ.get("ADMIN_KEY", "superadminsecret")

    @classmethod
    def validate(cls):
        """Sanity checks config inputs to warn about insecure configurations."""
        if cls.STORAGE_ENGINE not in ("local", "s3"):
            raise ValueError(f"Unsupported STORAGE_ENGINE: '{cls.STORAGE_ENGINE}'. Must be 'local' or 's3'.")
        
        if cls.SESSION_PROVIDER not in ("local", "redis", "memory"):
            raise ValueError(f"Unsupported SESSION_PROVIDER: '{cls.SESSION_PROVIDER}'. Must be 'local', 'redis', or 'memory'.")
        
        if cls.STORAGE_ENGINE == "s3" and (cls.S3_ACCESS_KEY == "admin" or cls.S3_SECRET_KEY == "supersecret"):
            print("WARNING: Using default MinIO credentials in production is highly insecure!")
