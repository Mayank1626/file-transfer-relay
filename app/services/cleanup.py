import os
import time
import json
import threading

def cleanup_old_sessions(app):
    """Prunes expired file payloads and JSON sessions from local disk storage.
    
    This function runs inside a background daemon thread.
    """
    upload_folder = app.config['UPLOAD_FOLDER']
    cleanup_interval = app.config['SESSION_CLEANUP_INTERVAL']
    session_expiry = app.config['SESSION_EXPIRY']
    
    # Give the server a few seconds to fully boot
    time.sleep(5)
    
    while True:
        current_time = time.time()
        try:
            if os.path.exists(upload_folder):
                for filename in os.listdir(upload_folder):
                    # Only target JSON session files
                    if filename.startswith("sess_") and filename.endswith(".json"):
                        path = os.path.join(upload_folder, filename)
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            # Check if session age exceeds 1 hour limit
                            if current_time - data.get('timestamp', 0) > session_expiry:
                                filepath = data.get('filepath')
                                # Unlink file payload
                                if filepath and os.path.exists(filepath):
                                    os.remove(filepath)
                                    
                                # Unlink JSON session state
                                os.remove(path)
                                app.logger.info(f"Background Clean: Successfully pruned expired session PIN: {filename[5:-5]}")
                        except Exception as e:
                            app.logger.error(f"Error clean item {filename}: {e}")
        except Exception as ex:
            app.logger.error(f"Error list uploads directory in cleanup: {ex}")
            
        time.sleep(cleanup_interval)

def start_cleanup_daemon(app):
    """Starts the background cleanup daemon if local filesystem storage is active."""
    # Only boot the cleanup loop if using local session providers
    provider = app.config['SESSION_PROVIDER'].lower()
    engine = app.config['STORAGE_ENGINE'].lower()
    
    if provider == "local" or engine == "local":
        daemon = threading.Thread(
            target=cleanup_old_sessions,
            args=(app,),
            name="ZapLink-CleanupDaemon",
            daemon=True
        )
        daemon.start()
        app.logger.info("Local Background Cleanup Daemon started successfully.")
    else:
        app.logger.info("Using Redis/S3 storage. Relying on native S3 Bucket Lifecycle & Redis Key TTLs.")
