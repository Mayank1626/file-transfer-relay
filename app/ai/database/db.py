import os
import sqlite3
from flask import current_app

def get_db_path():
    """Resolves the database filepath from app configuration or defaults."""
    # Ensure folder is created under upload or app context
    db_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'ai_memory.db')

def get_db_connection():
    """Establishes and returns a thread-safe connection to the SQLite database."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    # Enable Write-Ahead Logging (WAL) mode for safe concurrent read/writes
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
    return conn

def init_db(app=None):
    """Initializes the SQLite tables and builds indexing layers on startup."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. screenshots table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screenshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        filesize INTEGER NOT NULL,
        hash TEXT UNIQUE NOT NULL, -- SHA-256 to prevent duplicate indexing
        width INTEGER DEFAULT 0,
        height INTEGER DEFAULT 0,
        folder TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. ocr_results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        screenshot_id INTEGER UNIQUE NOT NULL,
        ocr_text TEXT NOT NULL, -- Original extracted OCR raw text
        normalized_text TEXT NOT NULL, -- Preprocessed standardized keywords
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'COMPLETE', -- 'COMPLETE' or 'METADATA_ONLY'
        FOREIGN KEY (screenshot_id) REFERENCES screenshots (id) ON DELETE CASCADE
    );
    """)

    # 3. processing_jobs table (Worker-compatible FIFO state table)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processing_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
        retry_count INTEGER DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. clipboard_entries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clipboard_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        content_hash TEXT UNIQUE NOT NULL, -- SHA-256 to prevent duplicate entries
        content_type TEXT NOT NULL, -- URL, CODE, COMMAND, JSON, SQL, TEXT
        source_app TEXT, -- Name of foreground process executable
        character_count INTEGER NOT NULL,
        is_favorite INTEGER DEFAULT 0, -- 0 or 1
        session_id TEXT, -- Grouped workflow block identifier
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. excluded_hashes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS excluded_hashes (
        hash TEXT PRIMARY KEY, -- SHA-256 of text excluded permanently from index
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Indexes for retrieval speed optimizations
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_hash ON screenshots(hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ocr_results_screenshot_id ON ocr_results(screenshot_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_hash ON clipboard_entries(content_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_favorite ON clipboard_entries(is_favorite);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_type ON clipboard_entries(content_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_session ON clipboard_entries(session_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clipboard_created_at ON clipboard_entries(created_at);")

    conn.commit()
    conn.close()

    if app:
        app.logger.info("ZapLink AI Memory SQLite database schema initialized successfully (WAL mode enabled).")
