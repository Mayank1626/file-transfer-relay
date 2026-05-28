# ZapLink System Lifecycles & Flows

This document details the exact structural and programmatic flows within ZapLink. It charts how sessions, uploads, downloads, and storage engines behave across both local filesystem and cloud infrastructure.

---

## 1. Session Lifecycle State Machine

Each file pairing session is governed by a strict, non-reversible state machine designed to maintain consistency, enforce security, and prevent race conditions.

```
       [ Client GET /request-pin ]
                     │
                     ▼
                ┌─────────┐
                │ CREATED │  ◄── Session initialized; 6-digit pairing PIN issued.
                └────┬────┘
                     │
        [ Client POST /upload-link ]
                     │
                     ▼
              ┌───────────┐
              │ UPLOADING │  ◄── Presigned or fallback upload URL generated; client streaming.
              └────┬──────┘
                   │
       [ File streaming completed ]
                   │
                   ▼
               ┌──────────┐
               │ UPLOADED │  ◄── Bytes written to storage; pending integrity verification.
               └────┬─────┘
                    │
      [ Background Verification Check ]
                    │
                    ▼
               ┌──────────┐
               │ VERIFIED │  ◄── File size & hash checked; matches expected metadata.
               └────┬─────┘
                    │
       [ Mark available for download ]
                    │
                    ▼
                ┌─────────┐
                │  READY  │  ◄── Receiver client allowed to access download link.
                └────┬────┘
                     │
         [ Receiver downloads file ]
                     │
                     ▼
              ┌────────────┐
              │ DOWNLOADED │ ◄── Immediately unlinks file payload and wipes session.
              └────┬───────┘
                   │
                   ▼
               ( Wiped )
```

*Note: Any state in the diagram above can transition directly to `EXPIRED` if the elapsed session duration exceeds 1 hour. An expired session immediately triggers safe resource cleanup and deletes the matching payload from storage.*

---

## 2. Dynamic Upload Flow (Direct S3 vs. Local Fallback)

ZapLink supports dual-strategy uploading. The client will attempt a fast direct-to-S3 presigned stream first. If that fails due to CORS, network policies, or local-only mode, the system seamlessly falls back to standard HTTP multi-part streaming through Flask.

### 2.1 Direct-to-Storage (MinIO / S3) Flow
This is the high-scale production flow. The Flask API only signs headers and manages state, leaving the heavy network payload handling entirely to MinIO's optimized storage engines.

```
Browser (DOM UI)               Nginx Proxy                Flask API              S3 / MinIO
       │                            │                         │                       │
       │── 1. request PIN ─────────>│                         │                       │
       │                            │── 2. request-pin ──────>│                       │
       │<─ 3. return PIN (123456) ──│<────────────────────────│                       │
       │                            │                         │                       │
       │── 4. POST /upload-link ───>│                         │                       │
       │      (with filename)       │── 5. upload-link ──────>│                       │
       │                            │                         │── 6. Generate         │
       │                            │                         │      Presigned PUT ──>│
       │                            │                         │<───── URL Signature ──│
       │<─ 7. return upload_url ────│<────────────────────────│                       │
       │                            │                         │                       │
       │── 8. PUT Raw File Binary Buffer ────────────────────────────────────────────>│
       │      (Direct stream using presigned upload_url)                              │
       │<─ 9. HTTP 200 OK (S3 write finished) ────────────────────────────────────────│
       │                            │                         │                       │
       │── 10. POST /upload/verify ─>│                         │                       │
       │       (PIN = 123456)       │── 11. upload/verify ───>│                       │
       │                            │                         │── 12. Run check ─────>│
       │                            │                         │       (Check headers) │
       │                            │                         │── 13. State -> READY  │
       │<─ 14. upload success! ─────│<────────────────────────│                       │
```

### 2.2 Fallback Stream (Local Filesystem) Flow
When running locally or when direct S3 channels are blocked, the file streams in chunks through Flask, saving directly to local disk.

```
Browser (DOM UI)               Nginx Proxy                Flask API              Local Storage
       │                            │                         │                       │
       │── 1. request PIN ─────────>│                         │                       │
       │<─ 2. return PIN (123456) ──│─────────────────────────│                       │
       │                            │                         │                       │
       │── 3. PUT upload_url fails (CORS / S3 unreachable) ───┐                        │
       │                                                      │                        │
       │◄─ 4. Enter Fallback Mode ────────────────────────────┘                        │
       │                                                                               │
       │── 5. POST multipart /upload/123456 ─────────────────>│                        │
       │      (Streaming chunked payload)                     │── 6. Stream chunks ──>│
       │                                                      │      to disk          │
       │                                                      │      (uploads/)       │
       │                                                      │── 7. Verify size      │
       │                                                      │── 8. State -> READY   │
       │<─ 9. Return HTTP 200 OK (success) ───────────────────│                        │
```

---

## 3. Secure Download & Immediate Wipe Flow

To maintain the system's ephemeral nature, files are deleted immediately after download. This sequence is strictly enforced:

```
Browser (Receiver)             Nginx Proxy                Flask API            Storage Engine
       │                            │                         │                       │
       │── 1. Input PIN (123456) ──>│                         │                       │
       │── 2. GET /check/123456 ───>│                         │                       │
       │                            │── 3. GET /check/123456 >│                       │
       │                            │      (Check Session)    │                       │
       │<─ 4. Status: READY, ───────│<────────────────────────│                       │
       │      Filename: report.pdf  │                         │                       │
       │                            │                         │                       │
       │── 5. Click "Download" ────>│                         │                       │
       │── 6. GET /download-link ──>│                         │                       │
       │                            │── 7. download-link ────>│                       │
       │                            │                         │── 8. Generate         │
       │                            │                         │      Presigned GET ──>│
       │<─ 9. Return download_url ──│<────────────────────────│                       │
       │                            │                         │                       │
       │── 10. Fetch stream from download_url ───────────────────────────────────────>│
       │<─ 11. Stream binary payload (Save to Disk) ──────────────────────────────────│
       │                            │                         │                       │
       │── 12. POST /download/done >│                         │                       │
       │       (Confirm success)    │── 13. download/done ───>│                       │
       │                            │                         │── 14. State ->        │
       │                            │                         │       DOWNLOADED      │
       │                            │                         │── 15. Delete Payload >│
       │                            │                         │       (Wipe from S3 / │
       │                            │                         │        local disk)    │
       │                            │                         │── 16. Wipe Session ──>│
       │<─ 17. Return clean success │<────────────────────────│                       │
```

---

## 4. Ephemeral Expiration Flow (Garbage Collection)

```
                     ┌────────────────────────────────────────┐
                     │          Background Timer Fired        │
                     │          (Scheduled Every 10m)         │
                     └───────────────────┬────────────────────┘
                                         │
                                         ▼
                     ┌────────────────────────────────────────┐
                     │    Scan Active Sessions Registry       │
                     │      (Redis Keys / Disk JSONs)         │
                     └───────────────────┬────────────────────┘
                                         │
                                         ▼
                     ┌────────────────────────────────────────┐
                     │    Check If Elapsed Time > 1 Hour      │
                     └───────────────────┬────────────────────┘
                                         │
                       ┌─────────────────┴─────────────────┐
                       │                                   │
                      YES                                  NO
                       │                                   │
                       ▼                                   ▼
        ┌─────────────────────────────┐           ┌─────────────────┐
        │   Trigger Expiration Flow   │           │   Keep Active   │
        └──────────────┬──────────────┘           └─────────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │   Set State -> EXPIRED      │
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │    Call storage.delete()    │
        │   (Removes files cleanly)   │
        └──────────────┬──────────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │    Delete Session Object    │
        └─────────────────────────────┘
```
