/**
 * ZapLink Core Transfer Logic Module
 * Decouples upload and download processes from DOM updates.
 * Tracks transfer stats (speeds, ETA, remaining sizes).
 */

(function (window) {
    'use strict';

    let activeUploadXhr = null;
    let downloadController = null;

    const Transfer = {
        /**
         * Formats bytes to human-readable size
         * @param {number} bytes
         * @returns {string}
         */
        formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(i > 1 ? 2 : 1)) + ' ' + sizes[i];
        },

        /**
         * Formats transfer speed (bytes/sec)
         * @param {number} bytesPerSec
         * @returns {string}
         */
        formatSpeed(bytesPerSec) {
            if (bytesPerSec <= 0 || !isFinite(bytesPerSec)) return '0 B/s';
            if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
            if (bytesPerSec < 1048576) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
            return `${(bytesPerSec / 1048576).toFixed(1)} MB/s`;
        },

        /**
         * Formats time remaining (seconds)
         * @param {number} seconds
         * @returns {string}
         */
        formatETA(seconds) {
            if (seconds <= 0 || !isFinite(seconds)) return 'Calculating...';
            if (seconds < 60) return `${Math.round(seconds)}s remaining`;
            const mins = Math.floor(seconds / 60);
            const secs = Math.round(seconds % 60);
            if (mins < 60) return `${mins}m ${secs}s remaining`;
            const hrs = Math.floor(mins / 60);
            const remMins = mins % 60;
            return `${hrs}h ${remMins}m remaining`;
        },

        /**
         * Cancels any active upload
         */
        cancelUpload() {
            if (activeUploadXhr) {
                activeUploadXhr.abort();
                activeUploadXhr = null;
                return true;
            }
            return false;
        },

        /**
         * Cancels any active download
         */
        cancelDownload() {
            if (downloadController) {
                downloadController.abort();
                downloadController = null;
                return true;
            }
            return false;
        },

        /**
         * Handles direct upload to storage (MinIO/S3 mode) with fallback to local Flask upload
         * @param {File} file The file to upload
         * @param {object} callbacks Progress and state hooks
         */
        async upload(file, callbacks = {}) {
            const {
                onStateChange = () => {},
                onProgress = () => {},
                onSuccess = () => {},
                onError = () => {}
            } = callbacks;

            activeUploadXhr = null;

            try {
                // Step 1: Request pairing PIN
                onStateChange('requesting_pin', 'Requesting pairing PIN...');
                const pinRes = await fetch('/request-pin');
                if (!pinRes.ok) throw new Error('Could not obtain a new transfer PIN');
                const pinData = await pinRes.json();
                const pin = pinData.pin;

                // Step 2: Request Direct-to-Storage presigned URL
                onStateChange('securing_channel', 'Securing secure direct-stream channel...');
                const contentType = file.type || 'application/octet-stream';
                
                const linkRes = await fetch(`/upload-link/${pin}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        filename: file.name,
                        content_type: contentType 
                    })
                });

                if (!linkRes.ok) {
                    // Force fallback instantly if S3 link generation fails
                    throw new Error('S3 link generation rejected by server');
                }

                const linkData = await linkRes.json();
                const s3Url = linkData.upload_url;

                // Step 3: Attempt direct stream S3 upload
                onStateChange('uploading', 'Direct Uploading...');
                
                const xhr = new XMLHttpRequest();
                activeUploadXhr = xhr;

                xhr.open('PUT', s3Url);
                xhr.setRequestHeader('Content-Type', contentType);

                const startTime = Date.now();

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable && activeUploadXhr === xhr) {
                        const pct = Math.round((e.loaded / e.total) * 100);
                        const timeElapsed = (Date.now() - startTime) / 1000;
                        const speed = e.loaded / (timeElapsed || 0.001);
                        const remaining = e.total - e.loaded;
                        const eta = speed > 0 ? remaining / speed : 0;

                        onProgress({
                            percent: pct,
                            loaded: e.loaded,
                            total: e.total,
                            speed: this.formatSpeed(speed),
                            eta: this.formatETA(eta),
                            mode: 'direct'
                        });
                    }
                };

                const triggerFallback = (reason) => {
                    console.log(`Direct stream upload failed: ${reason}. Triggering server disk relay fallback...`);
                    this.fallbackUpload(pin, file, callbacks);
                };

                xhr.onload = async () => {
                    if (activeUploadXhr !== xhr) return; // Aborted
                    
                    if (xhr.status === 200 || xhr.status === 201) {
                        try {
                            onStateChange('verifying', 'Verifying upload integrity with server...');
                            const verifyRes = await fetch(`/upload/verify/${pin}`, { method: 'POST' });
                            if (!verifyRes.ok) throw new Error('Server verification rejected direct payload');
                            
                            activeUploadXhr = null;
                            onSuccess(pin);
                        } catch (err) {
                            triggerFallback(err.message);
                        }
                    } else {
                        triggerFallback(`Server returned status code ${xhr.status}`);
                    }
                };

                xhr.onerror = () => {
                    if (activeUploadXhr !== xhr) return;
                    triggerFallback('Network connection interrupted');
                };

                xhr.send(file);

            } catch (err) {
                // If anything failed during PIN setup or presigned URL, try fallback upload direct
                onError(err.message);
            }
        },

        /**
         * Server Disk Relay fallback upload using multipart/form-data directly to Flask
         * @param {string} pin
         * @param {File} file
         * @param {object} callbacks
         */
        fallbackUpload(pin, file, callbacks = {}) {
            const {
                onStateChange = () => {},
                onProgress = () => {},
                onSuccess = () => {},
                onError = () => {}
            } = callbacks;

            onStateChange('uploading', 'Relay Uploading (Server Disk)...');

            try {
                const formData = new FormData();
                formData.append('file', file);

                const xhr = new XMLHttpRequest();
                activeUploadXhr = xhr;

                xhr.open('POST', `/upload/${pin}`);
                
                const startTime = Date.now();

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable && activeUploadXhr === xhr) {
                        const pct = Math.round((e.loaded / e.total) * 100);
                        const timeElapsed = (Date.now() - startTime) / 1000;
                        const speed = e.loaded / (timeElapsed || 0.001);
                        const remaining = e.total - e.loaded;
                        const eta = speed > 0 ? remaining / speed : 0;

                        onProgress({
                            percent: pct,
                            loaded: e.loaded,
                            total: e.total,
                            speed: this.formatSpeed(speed),
                            eta: pct === 100 ? 'Finalizing writing...' : this.formatETA(eta),
                            mode: 'relay'
                        });
                    }
                };

                xhr.onload = () => {
                    if (activeUploadXhr !== xhr) return; // Aborted
                    
                    activeUploadXhr = null;
                    if (xhr.status === 200) {
                        onSuccess(pin);
                    } else {
                        let errorMsg = `Relay upload failed: status ${xhr.status}`;
                        try {
                            const res = JSON.parse(xhr.responseText);
                            if (res.error) errorMsg = res.error;
                        } catch (e) {}
                        onError(errorMsg);
                    }
                };

                xhr.onerror = () => {
                    if (activeUploadXhr !== xhr) return;
                    activeUploadXhr = null;
                    onError('Relay connection dropped.');
                };

                xhr.send(formData);

            } catch (err) {
                activeUploadXhr = null;
                onError(err.message);
            }
        },

        /**
         * Validates a PIN structure and queries its readiness state
         * @param {string} pin
         * @returns {Promise<object>} Status data
         */
        async checkPin(pin) {
            if (!pin || pin.length !== 6 || !/^\d+$/.test(pin)) {
                throw new Error('Please enter a valid 6-digit PIN.');
            }

            const checkRes = await fetch(`/check/${pin}`);
            if (!checkRes.ok) {
                let errorMsg = `Check failed: status ${checkRes.status}`;
                try {
                    const errData = await checkRes.json();
                    if (errData.error) errorMsg = errData.error;
                } catch (e) {}
                throw new Error(errorMsg);
            }

            const checkData = await checkRes.json();
            return checkData; // returns {status: 'ready'|'waiting', filename: '...'}
        },

        /**
         * Prepares a stream download from secure endpoint
         * @param {string} pin
         * @param {string} filename
         * @param {object} callbacks Progress hooks
         */
        async download(pin, filename, callbacks = {}) {
            const {
                onProgress = () => {},
                onSuccess = () => {},
                onError = () => {}
            } = callbacks;

            downloadController = null;

            try {
                // Step 1: Fetch direct presigned download URL
                const res = await fetch(`/download-link/${pin}`);
                if (!res.ok) throw new Error('Failed to authorize secure download link');
                
                const data = await res.json();
                if (!data.download_url) throw new Error('Invalid download link provided by backend');

                // Step 2: Establish streaming read with fetch and AbortController
                downloadController = new AbortController();
                
                const response = await fetch(data.download_url, { 
                    signal: downloadController.signal 
                });
                
                if (!response.ok) throw new Error(`Server stream connection refused: status ${response.status}`);

                const contentLength = response.headers.get('content-length');
                const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
                
                const reader = response.body.getReader();
                const chunks = [];
                let receivedBytes = 0;
                
                const startTime = Date.now();
                let lastUiUpdate = Date.now();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    chunks.push(value);
                    receivedBytes += value.length;
                    
                    const now = Date.now();
                    // Throttle UI callbacks slightly to maximize throughput speed
                    if (now - lastUiUpdate > 100) { 
                        lastUiUpdate = now;
                        const pct = totalBytes > 0 ? Math.round((receivedBytes / totalBytes) * 100) : 0;
                        const timeElapsed = (Date.now() - startTime) / 1000;
                        const speed = receivedBytes / (timeElapsed || 0.001);
                        const remaining = totalBytes - receivedBytes;
                        const eta = speed > 0 ? remaining / speed : 0;

                        onProgress({
                            percent: pct,
                            loaded: receivedBytes,
                            total: totalBytes,
                            speed: this.formatSpeed(speed),
                            eta: this.formatETA(eta)
                        });
                    }
                }

                // Compile download payload blob
                const blob = new Blob(chunks);
                const objectUrl = URL.createObjectURL(blob);
                
                // Trigger client save dialogue
                const a = document.createElement('a');
                a.href = objectUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(objectUrl);

                // Notify backend of complete download to trigger immediate Wipe Protocol
                fetch(`/download-complete/${pin}`, { method: 'POST' }).catch(() => {});

                downloadController = null;
                onSuccess();

            } catch (err) {
                const wasAborted = err.name === 'AbortError';
                downloadController = null;
                onError(err.message, wasAborted);
            }
        }
    };

    // Attach to global window scope
    window.Transfer = Transfer;

})(window);
