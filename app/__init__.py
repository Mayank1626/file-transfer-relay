from flask import Flask
from app.config import Config
from app.storage import init_storage
from app.sessions import init_sessions
from app.services.cleanup import start_cleanup_daemon
from app.middleware.security import setup_logging, init_security_middleware, init_limiter
from app.ai.database.db import init_db
from app.ai.indexing.watcher import start_screenshot_watcher

def create_app(config_class=Config):
    """Flask Application Factory.
    
    Loads settings, initiates security frameworks, configures backend providers,
    registers blueprints, and starts background cleaning threads.
    """
    # Enforce strict path resolution to subfolder elements
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    
    # Load and validate settings
    app.config.from_object(config_class)
    config_class.validate()
    
    # Configure logs
    setup_logging(app)
    
    # Register blueprints
    from app.views import views_bp
    from app.api import api_bp
    from app.events import events_bp
    from app.ai import ai_bp
    
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(ai_bp)
    
    # Initiate Security Middlewares & Limiter
    init_security_middleware(app)
    init_limiter(app)
    
    # Initiate Storage Engines & Session Providers
    init_storage(app)
    init_sessions(app)
    
    # Start ephemeral file cleaners
    start_cleanup_daemon(app)
    
    # Start AI Memory Layer subsystems
    init_db(app)
    start_screenshot_watcher(app)
    
    app.logger.info("ZapLink Application successfully booted and paired.")
    return app
