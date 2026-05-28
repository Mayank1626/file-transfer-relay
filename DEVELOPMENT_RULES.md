# ZapLink Engineering & Development Rules

This document defines strict engineering rules, design boundaries, file limits, and coding guidelines for the ZapLink codebase. Adhering to these constraints ensures maintainability, prevents modular degradation, and guarantees seamless team collaboration.

---

## 1. Modular Architecture Principles

- **Unidirectional Layer Boundaries**: Imports must flow strictly downwards (Presentation -> Domain Abstractions -> Infrastructure Concrete -> Utilities). Sub-packages must never import layers above them.
- **Interface-Driven Design**: Presentation logic (Blueprints/Routes) must depend solely on abstract base interfaces (`StorageEngine`, `SessionProvider`). Concrete engine implementations must never be directly instantiated inside endpoints.
- **Config-Driven Dependency Injection**: Active providers must be resolved and instantiated during startup in the Application Factory (`app/__init__.py`) using unified registry systems.

---

## 2. Code Duplication Rules

- **Zero Duplication Policy**: Core domain logic, validation formulas, or database routines must be written exactly once. Any helper routine used in more than one module must be exported to `app/utils/helpers.py`.
- **Inheritance vs. Polymorphism**: Abstract Base Classes (ABCs) must enforce shared behaviors across concrete implementations, rather than duplicating boilerplate routines across files.

---

## 3. Strict File Size Recommendations

To prevent the accumulation of massive monolithic files that complicate code reviews and AI reasoning, developers must respect the following limits:

- **Views & Route Blueprints (`app/api/*`, `app/views/*`)**: Maximum **300 lines** per file. Large routing logic must be broken down by feature domain (e.g. `pins.py`, `transfer.py`, `stats.py`).
- **Engines & Abstractions (`app/storage/*`, `app/sessions/*`)**: Maximum **250 lines** per file. If an engine grows too large, extract helper subroutines to helper files or utils.
- **Configuration & Initializers (`app/config.py`, `app/__init__.py`)**: Maximum **150 lines** per file.
- **Frontend Template (`templates/index.html`)**: Maximum **800 lines**.

---

## 4. Isolated Services & State Consistency

- **State Independence**: Blueprints must never store local state in-memory inside the Flask worker. All transaction states must be managed explicitly via the injected `SessionProvider`.
- **Stateless File Management**: The server must remain fully stateless. No local file operations may assume the presence of a persistent drive, unless the local directory is mounted and selected via `LocalStorageEngine`.
- **Pre-Ready Verification**: A session must *never* transition to `READY` until file integrity and length validation are run and verified by the server.

---

## 5. Security & Robust Handling

- **Explicit Filename Sanitization**: All uploaded files must be forced through `sanitize_filename` (via `werkzeug.utils.secure_filename` or custom regex replacements) to block path-traversal attacks (`../../etc/passwd`).
- **Strict Size Guardrails**: Backend routes must strictly validate file sizes against incoming request headers prior to reading stream buffers. High payload sizes (max 2GB) must trigger immediate `413 Payload Too Large` responses.
- **Explicit Request Context Tracing**: All API and app logs must record a unique `RequestID` fetched from request environment variables to allow seamless log tracking across distributed requests.

---

## 6. Future-Ready AI Memory Constraints

As ZapLink evolves to ingest workspace state, screenshots, and clipboards, the following constraints apply:
- **Non-blocking Ingestion**: AI operations (OCR processing, vector calculations, text extractions) must be designed as *asynchronous* jobs (using separate worker threads or task queues), keeping the main HTTP transfer loop fully non-blocking.
- **Clean Interface Extension**: Semantic search and indexing connectors must reside strictly under `app/ai/` interfaces, leaving core pairing services untouched.

---

## 7. AI-Assisted Development Constraints

When utilizing LLMs or agentic systems for code generation, the following constraints must be strictly enforced:
- **No Monolithic Sweeps**: Agents must never replace entire files to make a minor edit. Always use localized replacements (`replace_file_content` or `multi_replace_file_content`).
- **Preserve Documentation**: Code changes must strictly preserve all pre-existing inline comments, type annotations, and docstrings unless explicitly asked to rewrite them.
- **Dry-Run Validation**: Before declaring a feature complete, test both the lightweight standard stack (`STORAGE_ENGINE=local`, `SESSION_PROVIDER=local`) and the distributed production stack (`STORAGE_ENGINE=s3`, `SESSION_PROVIDER=redis`) natively inside a multi-container local stack.
