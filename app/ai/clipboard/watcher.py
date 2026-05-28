import sys
import os
import time
import threading
import uuid
import ctypes
import hashlib
from datetime import datetime, timezone

from app.ai.clipboard.repository import AIClipboardRepository
from app.ai.clipboard.normalizer import normalize_clipboard_text
from app.ai.clipboard.classifier import classify_content
from app.ai.retention.manager import enforce_retention

_clipboard_lock = threading.Lock()
_watcher_thread = None
_stop_event = threading.Event()

# Timed pause target (in epoch time)
# 0.0 means tracking is active, float('inf') means paused indefinitely
_paused_until = 0.0

def set_paused_until(duration):
    """Sets timed pause duration. 
    duration=0 means resume.
    duration=-1 means infinite pause.
    otherwise, duration in seconds.
    """
    global _paused_until
    if duration == 0:
        _paused_until = 0.0
    elif duration == -1:
        _paused_until = float('inf')
    else:
        _paused_until = time.time() + duration

def get_pause_status():
    """Returns (is_paused, remaining_seconds)."""
    global _paused_until
    now = time.time()
    if _paused_until == float('inf'):
        return True, -1
    elif _paused_until > now:
        return True, int(_paused_until - now)
    return False, 0

def get_process_name(pid):
    """Resolves Windows executable filename from process ID using pure ctypes."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_process:
        return None
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = ctypes.c_ulong(512)
        if kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return None
    finally:
        kernel32.CloseHandle(h_process)

def get_active_window_title(hwnd):
    """Gets text title of a window HWND handle."""
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    return ""

def get_clipboard_text():
    """Safely retrieves current text on system clipboard."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    if not user32.OpenClipboard(None):
        return None
        
    CF_UNICODETEXT = 13
    try:
        h_data = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data:
            return None
            
        p_data = kernel32.GlobalLock(h_data)
        if not p_data:
            return None
            
        try:
            text = ctypes.c_wchar_p(p_data).value
            return text
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()

def get_or_create_session(source_app):
    """Checks the latest entry from this app and groups copies within 3 minutes into a session."""
    latest = AIClipboardRepository.get_latest_entry_from_app(source_app)
    if latest:
        try:
            created_dt = datetime.strptime(latest['created_at'], '%Y-%m-%d %H:%M:%S')
            created_dt = created_dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            diff = (now_utc - created_dt).total_seconds()
            if diff < 180.0:  # 3 minutes
                return latest['session_id']
        except Exception:
            pass
    return str(uuid.uuid4())

def run_clipboard_watcher_loop(app, stop_event):
    """Singleton background watcher thread polling the system clipboard."""
    global _paused_until
    
    last_processed_hash = None
    last_processed_time = 0.0
    
    # Wait briefly for server boot-up settled states
    time.sleep(2.0)
    
    with app.app_context():
        app.logger.info("AI Memory: Clipboard Watcher background daemon started successfully.")
        
        while not stop_event.is_set():
            try:
                # 1. Skip if system tracking is paused (either permanent or timed)
                now = time.time()
                if _paused_until > now:
                    time.sleep(1.5)
                    continue
                    
                # 2. Get active window handle & process details
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                
                if not hwnd:
                    time.sleep(1.5)
                    continue
                
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                source_app = get_process_name(pid.value) or "Unknown"
                window_title = get_active_window_title(hwnd) or ""
                
                # 3. Privacy Guard Check: "Do Not Track While Typing Password"
                source_app_lower = source_app.lower()
                window_title_lower = window_title.lower()
                
                # Ignore vault tools
                if any(x in source_app_lower for x in ['1password', 'bitwarden', 'keepass', 'keychain']):
                    time.sleep(1.5)
                    continue
                
                # Ignore password focused or sensitive title windows
                sensitive_keywords = ['login', 'sign-in', 'signin', 'sign in', 'password', 'passcode', 'credential', 'credentials', 'bank', 'auth']
                if any(x in window_title_lower for x in sensitive_keywords):
                    time.sleep(1.5)
                    continue
                
                # 4. Fetch clipboard text
                text = get_clipboard_text()
                if not text:
                    time.sleep(1.5)
                    continue
                
                text_stripped = text.strip()
                if not text_stripped:
                    time.sleep(1.5)
                    continue
                
                # 5. Temporal Debouncer (deduplication check within 30s)
                text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                if text_hash == last_processed_hash and (now - last_processed_time) < 30.0:
                    time.sleep(1.5)
                    continue
                
                # 6. Normalize and perform regex privacy scrubbing
                normalized = normalize_clipboard_text(text)
                if not normalized:
                    time.sleep(1.5)
                    continue
                    
                norm_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
                
                # Check if hash was permanently excluded
                if AIClipboardRepository.is_hash_excluded(norm_hash):
                    time.sleep(1.5)
                    continue
                
                # Check database duplication
                duplicate = AIClipboardRepository.get_entry_by_hash(norm_hash)
                if duplicate:
                    last_processed_hash = text_hash
                    last_processed_time = now
                    time.sleep(1.5)
                    continue
                
                # 7. Classify Content
                content_type = classify_content(normalized)
                
                # 8. Compute Session block identifier (3-minute grouped session)
                session_id = get_or_create_session(source_app)
                
                # 9. Write to database
                char_count = len(normalized)
                AIClipboardRepository.insert_entry(
                    content=normalized,
                    content_hash=norm_hash,
                    content_type=content_type,
                    source_app=source_app,
                    character_count=char_count,
                    session_id=session_id
                )
                
                # 10. Enforce retention limits
                enforce_retention()
                
                # Update debounce tracking
                last_processed_hash = text_hash
                last_processed_time = now
                app.logger.info(f"AI Clipboard Watcher: Indexed new copy entry from {source_app} ({content_type}, session: {session_id[:8]})")
                
            except Exception as e:
                try:
                    app.logger.error(f"AI Clipboard Watcher: Error in cycle: {e}")
                except Exception:
                    pass
            
            time.sleep(1.5)

def start_clipboard_watcher(app):
    """Starts the clipboard polling background worker.
    
    Aborts gracefully on non-win32 platforms.
    """
    global _watcher_thread, _stop_event
    
    if sys.platform != 'win32':
        app.logger.info("AI Clipboard Watcher: Platform is not Win32. Deactivating background daemon gracefully.")
        return
        
    is_debug = app.config.get('DEBUG', False)
    is_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    if is_debug and not is_reloader:
        app.logger.info("AI Clipboard Watcher: RELOADER not running, skipping dual thread spawn.")
        return

    with _clipboard_lock:
        if _watcher_thread is not None:
            app.logger.info("AI Clipboard Watcher: Singleton thread is already running.")
            return
            
        _stop_event.clear()
        _watcher_thread = threading.Thread(
            target=run_clipboard_watcher_loop,
            args=(app, _stop_event),
            name="ZapLink-AI-ClipboardWatcher",
            daemon=True
        )
        _watcher_thread.start()
        app.logger.info("ZapLink Clipboard Watcher daemon started successfully.")

def stop_clipboard_watcher():
    """Stops the background clipboard thread."""
    global _watcher_thread, _stop_event
    with _clipboard_lock:
        _stop_event.set()
        _watcher_thread = None
