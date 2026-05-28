import os
import time
import hashlib
import threading
from flask import current_app

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.ai.database.repository import AIMemoryRepository
from app.ai.ocr.engine import extract_text
from app.ai.ocr.normalizer import normalize_text
from app.ai.retention.manager import enforce_retention, cleanup_orphans

# Thread locking for singleton management
_watcher_lock = threading.Lock()
_active_observer = None
_queue_thread = None
_stop_event = threading.Event()

def get_default_screenshots_folder():
    """Resolves Windows system Screenshots folder, falling back to local workspace."""
    # Attempt Windows pictures folder
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        windows_path = os.path.join(user_profile, "Pictures", "Screenshots")
        if os.path.exists(windows_path):
            return windows_path
            
    # Fallback to local workspace screenshots folder
    local_path = os.path.join(os.getcwd(), "data", "screenshots")
    os.makedirs(local_path, exist_ok=True)
    return local_path

def compute_file_hash(filepath):
    """Calculates SHA-256 hash of file content to prevent duplicates."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

class ScreenshotEventHandler(FileSystemEventHandler):
    """Handles directory changes and stages pending indexing requests."""
    def on_created(self, event):
        if event.is_directory:
            return

        filepath = event.src_path
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg']:
            # Wait briefly for file write locks to stabilize
            time.sleep(0.5)
            
            try:
                # Add to queue database for worker processing
                AIMemoryRepository.add_processing_job(filepath)
                # Print log safely
                print(f"AI Watcher: Registered PENDING index job for: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"AI Watcher: Error queuing job: {e}")

def run_indexing_queue_worker(app, stop_event):
    """Worker loop that pulls PENDING jobs from database and performs processing."""
    # Give the app a couple of seconds to settle
    time.sleep(2)
    
    last_orphan_check = 0

    with app.app_context():
        app.logger.info("AI Memory: Ingestion queue worker thread started successfully.")
        
        while not stop_event.is_set():
            try:
                # Fetch next pending item (changes status to PROCESSING inside atomic transaction)
                job = AIMemoryRepository.get_next_pending_job()
                if job:
                    filepath = job['filepath']
                    filename = os.path.basename(filepath)
                    
                    if not os.path.exists(filepath):
                        # File was deleted before indexing started
                        AIMemoryRepository.update_job_status(job['id'], 'FAILED', 'File missing prior to indexing')
                        AIMemoryRepository.remove_processing_job(filepath)
                        continue

                    try:
                        # 1. Compute file hash
                        file_hash = compute_file_hash(filepath)
                        filesize = os.path.getsize(filepath)

                        # 2. Check for duplicate image hash in database
                        duplicate = AIMemoryRepository.get_screenshot_by_hash(file_hash)
                        if duplicate:
                            app.logger.info(f"AI Queue: Duplicate hash detected for {filename} (ID: {duplicate['id']}). Skipping indexing.")
                            AIMemoryRepository.update_job_status(job['id'], 'COMPLETED')
                            AIMemoryRepository.remove_processing_job(filepath)
                            continue

                        # 3. Perform OCR Extraction (falls back gracefully to Metadata-only if Tesseract missing)
                        ocr_raw_text, width, height, ocr_status = extract_text(filepath)

                        # 4. Normalize text
                        normalized_text = normalize_text(ocr_raw_text)

                        # 5. Insert screenshot record
                        folder_name = os.path.basename(os.path.dirname(filepath))
                        screenshot_id = AIMemoryRepository.insert_screenshot(
                            filepath=filepath,
                            filename=filename,
                            filesize=filesize,
                            file_hash=file_hash,
                            folder=folder_name,
                            width=width,
                            height=height
                        )

                        # 6. Insert OCR result
                        AIMemoryRepository.insert_ocr_result(
                            screenshot_id=screenshot_id,
                            ocr_text=ocr_raw_text,
                            normalized_text=normalized_text,
                            status=ocr_status
                        )

                        # 7. Enforce Retention Limit policies
                        enforce_retention()

                        # 8. Clean up queue job
                        AIMemoryRepository.update_job_status(job['id'], 'COMPLETED')
                        AIMemoryRepository.remove_processing_job(filepath)
                        app.logger.info(f"AI Queue: Successfully indexed {filename} ({ocr_status}).")

                    except Exception as err:
                        retry = job['retry_count'] + 1
                        status = 'FAILED' if retry >= 3 else 'PENDING'
                        AIMemoryRepository.update_job_status(
                            job['id'], 
                            status, 
                            error_message=str(err), 
                            retry_count=retry
                        )
                        app.logger.error(f"AI Queue: Job failed for {filename} (Attempt {retry}/3): {err}")
                        
                        if status == 'FAILED':
                            # Remove so queue doesn't lock
                            AIMemoryRepository.remove_processing_job(filepath)

                # Periodically scan and clean up orphan DB entries (every 60 seconds)
                now = time.time()
                if now - last_orphan_check > 60:
                    last_orphan_check = now
                    cleanup_orphans()

            except Exception as e:
                # Top level catch to prevent worker crashes
                try:
                    app.logger.error(f"AI Queue: Worker cycle loop error: {e}")
                except Exception:
                    pass

            time.sleep(3) # Safe cooldown

def start_screenshot_watcher(app):
    """Bootstraps the folder watcher and background queue worker.
    
    Guarantees strict Singleton thread boundaries.
    """
    global _active_observer, _queue_thread, _stop_event

    # Prevent booting background threads double-times on Flask debug reloader threads
    is_debug = app.config.get('DEBUG', False)
    is_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if is_debug and not is_reloader:
        # Reloader is not active yet, skip to avoid double thread allocations
        app.logger.info("AI Watcher: Dual debug-reloader startup detected. Suppressing background observer initialization.")
        return

    with _watcher_lock:
        if _active_observer is not None or _queue_thread is not None:
            app.logger.info("AI Watcher: Background services already initialized and active (Singleton active).")
            return

        watch_path = get_default_screenshots_folder()
        app.logger.info(f"AI Watcher: Monitoring directory path: {watch_path}")

        # Start watchdog observer
        event_handler = ScreenshotEventHandler()
        observer = Observer()
        observer.schedule(event_handler, watch_path, recursive=False)
        observer.start()
        
        _active_observer = observer

        # Start queue worker
        _stop_event.clear()
        _queue_thread = threading.Thread(
            target=run_indexing_queue_worker,
            args=(app, _stop_event),
            name="ZapLink-AI-IndexingQueue",
            daemon=True
        )
        _queue_thread.start()

        app.logger.info("ZapLink Screenshot Watcher and Queue Worker started successfully.")

def stop_screenshot_watcher():
    """Performs clean graceful shutdown unlinking observer bindings."""
    global _active_observer, _queue_thread, _stop_event

    with _watcher_lock:
        # Signal queue worker to stop
        _stop_event.set()

        if _active_observer:
            try:
                _active_observer.stop()
                _active_observer.join(timeout=3)
            except Exception:
                pass
            _active_observer = None

        _queue_thread = None
