# ZapLink Cloud Relay System Architecture

This document provides a comprehensive overview of the ZapLink Cloud Relay system architecture, detailing design abstractions, lifecycle management, scalability considerations, and future compatibility for expansion into an **AI Memory OS / AI Workspace OS**.

---

## 1. Complete System Architecture

ZapLink is structured as a highly decoupling, config-driven Flask application designed to run seamlessly either in a lightweight, single-developer local sandbox or in a fully distributed, high-throughput cloud environment.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 ZapLink Client Devices                 │
                  │        (Android App / Web DOM / PC Client GUI)         │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                     HTTPS / WebSocket
                                             │
                                             ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                    Nginx Reverse Proxy                 │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
         Paths: `/` & `/api/*`                         Path: `/filedrop/*`
                       │                                           │
                       ▼                                           ▼
      ┌─────────────────────────────────┐         ┌─────────────────────────────────┐
      │          Gunicorn WSGI          │         │          MinIO Object           │
      │    [Flask Application Factory]   │         │          Storage Vault          │
      └────────────────┬────────────────┘         └────────────────▲────────────────┘
                       │                                           │
          Imports / Instantiates (Config-driven)                   │
                       │                                           │
                       ▼                                           │ Presigned Upload
  ┌───────────────────────────────────────────────┐                │ & Direct Download
  │                 Domain Abstractions           ├────────────────┘
  │                                               │
  │  1. SessionProvider (Local/Redis/InMemory)    │
  │  2. StorageEngine (Local/S3/MinIO)            ├────────────────┐
  │  3. TransferStateMachine                      │                │
  └───────────────────────────────────────────────┘                │
                                                                   ▼
                                                  ┌─────────────────────────────────┐
                                                  │         Local Filesystem        │
                                                  │       (`uploads/` Directory)    │
                                                  └─────────────────────────────────┘
```

---

## 2. Abstraction Layers & Core Design

To completely eliminate code duplication between `app.py` and `app_minio.py` while ensuring scalability, the refactored architecture relies on strictly bounded abstraction layers.

### 2.1 Storage Abstraction (`StorageEngine` ABC)
All file payload movements (generating pairing credentials, writing, reading, deleting) are governed by the `StorageEngine` interface.
- **`LocalStorageEngine`**: Handles payload management using the container’s local disk (`uploads/` directory). Uploads fall back to a streaming endpoint through the Flask process.
- **`S3StorageEngine`**: Integrates with Amazon S3 or self-hosted MinIO clusters. It generates presigned URLs (signatures containing custom bucket permissions and headers) so that files bypass the Flask application process entirely, streaming directly from the client web browser/native OkHttp engine to storage. This guarantees near-zero RAM usage on Flask workers even when handling massive 2GB+ payloads.

### 2.2 Session Abstraction (`SessionProvider` ABC)
Session pairings require pairing states, file metadata, pairing timestamps, and status flags. The storage layer is decoupled:
- **`InMemorySessionProvider`**: An in-memory dict provider suited for super-fast local testing without spinning up any database or creating local temporary files.
- **`LocalSessionProvider`**: Write-to-disk JSON file provider. Maintains persistence across server crashes using simple local files.
- **`RedisSessionProvider`**: High-performance key-value distributed cache provider. Essential for multi-instance, clustered production deploys where multiple Flask API workers behind Nginx must query shared pairing pins.

### 2.3 Transfer State Machine (`TransferStateMachine`)
A strict, deterministic state machine handles safety and transfer verification, preventing file race-conditions and out-of-order execution. The states are:
- `CREATED`: Pairing code generated; waiting for file metadata initialization.
- `UPLOADING`: Upload URL generated and stream started by the client.
- `UPLOADED`: Data payload written successfully to the storage backend.
- `VERIFIED`: Integrity verification passed (hash checks and content-length validation completed successfully).
- `READY`: File is verified and available for secure download.
- `DOWNLOADED`: The file has been successfully downloaded by the receiver. This state triggers the **Immediate Wipe Protocol**.
- `EXPIRED`: File/Session lifetime exceeded the configured threshold (typically 1 hour).

---

## 3. Request and Data Lifecycles

### 3.1 Pairing & Upload Lifecycle
```
Client (Sender)           Flask API Blueprint            Session Backend            Storage Backend
      │                            │                            │                          │
      │── 1. GET /request-pin ────>│                            │                          │
      │                            │── 2. Create Session ──────>│                          │
      │                            │      (Status: CREATED)     │                          │
      │<─ 3. Return 6-Digit PIN ───│                            │                          │
      │                            │                            │                          │
      │── 4. POST /upload-link ───>│                            │                          │
      │      (Pin, filename)       │── 5. Fetch Session ───────>│                          │
      │                            │── 6. Update to UPLOADING ─>│                          │
      │                            │── 7. Generate Upload URL ────────────────────────────>│
      │<─ 8. Return Upload URL ────│                                                       │
      │                                                                                    │
      │── 9. Direct Stream Binary PUT Payload to Upload URL ──────────────────────────────>│
      │                                                                                    │
      │── 10. POST /upload/verify ─>│                                                      │
      │                       (Pin)│── 11. Run Verification ──────────────────────────────>│
      │                            │       (Check size/hash)    │                          │
      │                            │── 12. State -> READY ─────>│                          │
      │<─ 13. Return verified ok ──│                            │                          │
```

### 3.2 Download & Ephemeral Expiration Lifecycle
- **Step 1 (Verification)**: The receiver enters the 6-digit PIN. The client makes a `GET /check/<pin>` request.
- **Step 2 (Response)**: Flask checks the session provider. If the state is `READY`, the file name is returned to the client DOM.
- **Step 3 (Download Authorization)**: The receiver triggers the download. The client makes a `GET /download-link/<pin>` request. The Storage Engine returns a download link (either presigned S3 GET URL or local Flask download endpoint).
- **Step 4 (Download & Wipe)**: The receiver’s browser streams the file payload. Once the stream completes, the client signals successful receipt to `POST /download/complete/<pin>`. Flask updates the session state to `DOWNLOADED` and immediately triggers `delete_file` on the storage engine and wipes the session from the database.

---

## 4. Background Garbage Collection & Cleanup Services

To avoid storage leaks in cases where users generate PINs but never download files, ZapLink employs a highly optimized, dual-strategy garbage collection routine:

1. **Active Local Garbage Collector**: A background daemon thread manages pruning for local filesystem structures. Once every 10 minutes, the thread scans the `uploads/` directory, reading JSON session files and local binaries. Any files or sessions whose age (`current_time - session_timestamp`) exceeds 1 hour are permanently unlinked (`os.remove()`).
2. **Native Cloud Garbage Collector**: In production S3/MinIO mode, active polling is inefficient. S3 is instead configured with **Bucket Lifecycle Rules** that natively expire objects after exactly 1 day. Redis keys are similarly configured with a 1-hour Time-to-Live (TTL), allowing Redis's internal engine to prune expired records automatically.

---

## 5. Scalability Considerations

- **Stateless Flask API**: By utilizing Redis for sessions and S3/MinIO for storage, the core Flask container remains entirely stateless. This allows developers to scale horizontal workers (e.g., across Kubernetes or AWS ECS) behind Nginx/HAProxy without session-stickiness or local directory mounting synchronization issues.
- **Worker CPU/RAM Preservation**: By streaming directly to S3 via presigned PUT requests, Flask does not handle the raw binary upload stream. A single Flask container running under Gunicorn (2 workers, 4 threads) can easily coordinate thousands of concurrent multi-gigabyte transfers because its work is restricted to signing URLs and verifying states.

---

## 6. Future AI Memory OS Expansion Strategy

ZapLink's refactored architecture is specifically designed to eventually act as the core ingestion pipeline for a high-performance **AI Memory OS / AI Workspace OS** (a system that continuously indexes a user's digital workspace, screenshots, clipboard, and interactions to provide a searchable semantic memory bank).

To support this evolution, the modular app includes the following hooks:
- **Unified Event Pipeline (`app/events`)**: Can easily hook into real-time websockets. During a file transfer, instead of just transferring bytes, the event system will allow background AI workers to stream state updates (e.g., OCR processing progress).
- **Extensible AI Namespace (`app/ai`)**: Prepares structural placeholders for pipeline tasks:
  - **OCR & Document Parsing Services**: When documents (PDFs, screenshots) are uploaded, a background task pipeline will route the files through OCR engines (e.g., Tesseract or Gemini APIs) to extract textual context.
  - **Embedding & Semantic Extraction**: Parsed documents and files will have metadata transformed into high-dimensional vector embeddings (e.g., via Sentence-Transformers or OpenAI Embeddings).
  - **Vector DB Connectors**: Hooks for writing these embeddings to high-speed indexing databases (e.g., pgvector, Qdrant, or Chroma) to allow users to ask semantic search queries like *"Find the PDF invoice I transferred from my phone yesterday about hosting fees."*
  - **Clipboard & Action Controllers**: AI workspace commands can programmatically trigger silent, pairwise local relays to fetch clipboards or execute quick automation workflows across linked desktops and mobile nodes.
