# ZapLink Implementation Roadmap

This document outlines the systematic, phased timeline to modularize the ZapLink Cloud Relay application and lays the groundwork for the upcoming **AI Memory / AI Workspace OS** features.

---

## Part 1: Phase 1 to 10 Refactoring Path

The refactoring is split into logically independent milestones. Each milestone requires passing a validation checkpoint before moving to the next.

```
       [ Phase 1: Planning & Docs ] ──► (Completed)
                     │
                     ▼
       [ Phase 2: Folder Layout & Factory ]
                     │
                     ▼
       [ Phase 3: Storage Engine Abstractions ]
                     │
                     ▼
       [ Phase 4: Session Provider Systems ]
                     │
                     ▼
       [ Phase 5: Transfer State Machine ]
                     │
                     ▼
       [ Phase 6: Security Middleware & Cleanups ]
                     │
                     ▼
       [ Phase 7: Frontend Progress & UX Checks ]
                     │
                     ▼
       [ Phase 8: Event System Preparation ]
                     │
                     ▼
       [ Phase 9: AI Memory OS Scaffold ]
                     │
                     ▼
       [ Phase 10: Integrated End-to-End Validation ]
```

---

## 2. Milestone Details & Checkpoints

### Milestone 1: App Factory & Configuration
- **Objective**: Establish the structural skeleton and load configs cleanly.
- **Tasks**:
  - Implement `app/config.py`.
  - Implement the app factory in `app/__init__.py`.
  - Register `app/views/main.py` and move HTML/assets to their respective directories.
- **Verification Checkpoint**:
  - Run `python run.py` (Local memory/disk defaults).
  - Verify that `http://localhost:5000/` loads the UI successfully.

### Milestone 2: Abstraction Layers (Storage & Sessions)
- **Objective**: Implement engines and session backends to remove `app.py`/`app_minio.py` code duplication.
- **Tasks**:
  - Write base classes and concrete subclasses (`LocalStorageEngine`, `S3StorageEngine`).
  - Write session subclasses (`LocalSessionProvider`, `RedisSessionProvider`, `InMemorySessionProvider`).
  - Inject active services dynamically into route blueprints.
- **Verification Checkpoint**:
  - Verify API endpoints `/request-pin` and `/upload` work in local disk/local session mode.
  - Verify S3 and Redis backends function when environment variables are supplied.

### Milestone 3: State Machine & Verification Security
- **Objective**: Enforce safe file lifecycle transactions.
- **Tasks**:
  - Define state transition validation logic.
  - Implement UUID context logging filters and error response pages.
  - Setup background garbage cleanup routines.
- **Verification Checkpoint**:
  - Simulate out-of-order calls (e.g. hitting `/download` on a PIN in `CREATED` state) and verify that the request is safely rejected.
  - Ensure the local clean-up daemon unlinks expired records.

### Milestone 4: Event-Ready Web UX & Scaffold
- **Objective**: Complete UI improvements and structural placeholders.
- **Tasks**:
  - Update `templates/index.html` to handle the transfer states, display progress bars properly, and render pairing QR codes cleanly.
  - Setup `app/events/` placeholders.
  - Setup `app/ai/` modular service interfaces.
- **Verification Checkpoint**:
  - Verify pairing QR codes render and decode successfully.
  - Validate mobile phone upload flow works smoothly using a local Wi-Fi pairing environment.

---

## 3. Future AI Memory OS Roadmap

Following the successful execution of our core transfer refactoring, ZapLink will expand into an **AI Workspace Memory System** which records, OCRs, embeds, and indexes active file pairings to create a searchable second-brain.

### AI Milestone 1: Ingestion Pipelines (Local OCR & Metadata Extraction)
- **Objective**: Parse files programmatically on upload completion.
- **Sub-tasks**:
  - Integrate a non-blocking worker pipeline (e.g. `Celery` or standard `ThreadPoolExecutor`).
  - Run Tesseract OCR / PDF-plumber routines on documents (`.pdf`, `.png`, `.jpg`).
  - Generate automatic AI textual summaries for massive data files.

### AI Milestone 2: High-Dimensional Embeddings & Indexing
- **Objective**: Map extracted context to high-dimensional space.
- **Sub-tasks**:
  - Pull down a localized sentence-embedding model (e.g. `all-MiniLM-L6-v2` via HuggingFace).
  - Hook in a lightweight vector database (e.g., standard `Chroma` or `SQLite-vec` extension).
  - Map text metadata chunks to embeddings and write to the vector database.

### AI Milestone 3: Natural Language Semantic Search UI
- **Objective**: Provide search interfaces inside the ZapLink UI.
- **Sub-tasks**:
  - Create `/api/search` blueprint endpoints accepting semantic search queries.
  - Run vector search querying active and historical pairing indexes.
  - Create a premium Search dashboard in the frontend allowing instant downloads of matched files.
