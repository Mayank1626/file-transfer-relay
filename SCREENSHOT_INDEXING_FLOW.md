# ZapLink Screenshot Watcher & Indexing Flow

This document details the background filesystem monitoring, atomic queue state changes, write-lock guards, and Singleton lifecycle controls implemented in the ZapLink AI Memory subsystem.

---

## 🗺️ Indexing Ingestion Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as User Capture
    participant Watch as watchdog Observer
    participant Queue as SQLite jobs Queue
    participant Worker as Daemon Indexing Worker
    participant DB as SQLite Memory DB

    User->>Watch: Writes screenshot (.png) on hard drive
    Note over Watch: Sleep 0.5s write lock buffer
    Watch->>Queue: Registers PENDING job (filepath)
    loop Background Poller (Every 3s)
        Worker->>Queue: SELECT oldest PENDING job
        Queue->>Worker: Returns filepath & locks status to 'PROCESSING'
    end
    Worker->>Worker: Computes SHA-256 file content hash
    Worker->>DB: Check if hash already exists
    alt Hash exists (Duplicate image)
        Worker->>Queue: UPDATE status to 'COMPLETED' & delete job row
        Note over Worker: Ingestion skipped (Fast exit)
    else Hash is unique (New screenshot)
        Worker->>Worker: Reads image width/height (Pillow)
        Worker->>Worker: Executes extract_text() OCR engine
        Worker->>Worker: Normalizes text (scrubs tokens, lowercase)
        Worker->>DB: INSERT screenshots metadata & ocr_results
        Worker->>DB: Run Retention Manager quota checks (limit 500)
        Worker->>Queue: UPDATE status to 'COMPLETED' & delete job row
    end
```

---

## 🔒 Write-Lock & File Stability Guard

During active desktop screenshot capture events, operating system disk write buffers can trigger watchdog creation callbacks before the image file is fully written on hard disk. 
To prevent hashing corrupt or partial binaries:
1. **Time Delay**: Watchdog catches `on_created` and sleeps for `0.5 seconds` to let the OS complete the file write block.
2. **Hash Validation**: The background poller opens the stabilized file, computes its SHA-256 hash, and compares it against the database. If a duplicate exists (e.g., repeating the same image file name or copy operations), the task is immediately marked as completed and removed, eliminating duplicate entries.

---

## 🦄 Singleton Daemon & Safe Reloader Boots

Flask's local reloader (`werkzeug`) boots the application stack double-times during standard debug executions (one parent reloader process monitoring file edits, one active child worker executing Flask endpoints). 
To prevent launching double duplicate observer threads and resource lock conflicts:
* **Reloader Check**: The subsystem watcher (`watcher.py`) checks if `WERKZEUG_RUN_MAIN` is set. It suppresses thread start operations if the reloader thread is not fully booted.
* **Lock Guard**: A thread safety lock (`_watcher_lock`) validates state indicators and active observers, ensuring only one instance of the background thread starts:

```python
with _watcher_lock:
    if _active_observer is not None or _queue_thread is not None:
        # Already active, skip startup
        return
```
* **Graceful Exit**: On shutdown, the thread-safe `stop_screenshot_watcher()` stops the watchdog observer, joins running threads, and clears memory pointer allocations.
