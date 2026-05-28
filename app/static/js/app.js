/**
 * ZapLink Master Application Entry & Event Broker
 * Binds DOM event listeners and maps triggers to Transfer, UI, Pairing, and AIWorkspace modules.
 * Maintains complete backwards compatibility with index.html global function triggers.
 */

(function (window) {
    'use strict';

    // State Variables
    let selectedFiles = [];
    window.selectedFiles = selectedFiles;

    /**
     * Wires DOM event listeners and registers triggers
     */
    function init() {
        const fileInput = document.getElementById('fileInput');
        const dropZone = document.getElementById('dropZone');
        const pinInput = document.getElementById('pinInput');

        // Android native app banner check
        if (/android/i.test(navigator.userAgent)) {
            const promo = document.getElementById('androidAppPromo');
            if (promo) promo.style.display = 'inline';
        }

        // File Selection listeners
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) handleFileSelection(e.target.files);
            });
        }

        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) handleFileSelection(e.dataTransfer.files);
            });
        }

        if (pinInput) {
            pinInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    window.checkPin();
                }
            });
        }

        // Initialize AI Workspace Tab Elements
        if (window.AIWorkspace) {
            window.AIWorkspace.init('workspaceSection');
        }

        // Check for active reconnection opportunities
        window.UI.checkReconnection();

        // 🟢 Deep-Link PIN auto-routing (receiver-handoff)
        const urlParams = new URLSearchParams(window.location.search);
        const autoPin = urlParams.get('pin');
        if (autoPin && autoPin.length === 6) {
            window.switchTab('receive');
            if (pinInput) {
                pinInput.value = autoPin;
                window.checkPin();
            }
            // Clear address bar query variables for clean look
            window.history.replaceState({}, document.title, '/');
        }
    }

    /**
     * Common handler for selected file pre-flight validation
     * @param {FileList} files
     */
    function handleFileSelection(files) {
        window.UI.showStatus('sendStatus', ''); // Clear active errors

        if (files.length > 1) {
            window.UI.showStatus('sendStatus', '⚠️ For maximum speed, ZapLink supports 1 file per PIN. Please ZIP them together first!', 'warning');
        }

        const targetFile = files[0];
        
        // Hard limit validation at 2GB
        if (targetFile.size > 2 * 1024 * 1024 * 1024) {
            window.UI.showStatus('sendStatus', '❌ Payload rejected: ZapLink accepts files up to 2 GB only.', 'error');
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';
            return;
        }

        selectedFiles = [targetFile];
        window.selectedFiles = selectedFiles;

        const sizeLabel = window.Transfer.formatSize(targetFile.size);
        const fileNameEl = document.getElementById('selectedFileName');
        if (fileNameEl) {
            fileNameEl.textContent = `${targetFile.name} (${sizeLabel})`;
        }

        const fileCountEl = document.getElementById('fileCount');
        if (fileCountEl) fileCountEl.textContent = '';

        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) sendBtn.disabled = false;
    }

    // ==========================================
    // EXPOSE BACKWARDS-COMPATIBLE GLOBAL METHODS
    // ==========================================

    window.switchTab = function (tab) {
        window.UI.switchTab(tab);
    };

    window.copyPin = function () {
        if (window.currentPin) {
            navigator.clipboard.writeText(window.currentPin).then(() => {
                const btn = event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                window.Toast.show('PIN copied to clipboard', 'success', 2000);
                setTimeout(() => { btn.innerHTML = originalText; }, 2000);
            });
        }
    };

    window.sharePin = function () {
        if (!window.currentPin) return;
        const text = `Download my file on ZapLink!\nPIN: ${window.currentPin}\nWebsite: ${window.location.origin}/?pin=${window.currentPin}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'ZapLink File Transfer',
                text: text,
            }).catch(() => {});
        } else {
            navigator.clipboard.writeText(text);
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Link Copied!';
            window.Toast.show('Share link copied to clipboard', 'success', 2000);
            setTimeout(() => { btn.innerHTML = originalText; }, 2000);
        }
    };

    window.cancelUpload = function () {
        if (window.Transfer.cancelUpload()) {
            window.UI.showStatus('sendStatus', '❌ Upload cancelled.', 'error');
            window.UI.hide('sendProgress');
            window.UI.hide('cancelUploadBtn');
            
            const sendBtn = document.getElementById('sendBtn');
            if (sendBtn) sendBtn.disabled = false;
            window.Toast.show('Upload cancelled', 'info', 2000);
        }
    };

    window.cancelDownload = function () {
        if (window.Transfer.cancelDownload()) {
            window.UI.showStatus('receiveStatus', '❌ Download cancelled.', 'error');
            window.UI.hide('receiveProgress');
            window.UI.hide('cancelDownloadBtn');
            
            const checkPinBtn = document.getElementById('checkPinBtn');
            if (checkPinBtn) checkPinBtn.style.display = 'block';
            
            const fileInfoCard = document.getElementById('fileInfoCard');
            if (fileInfoCard) fileInfoCard.style.display = 'block';
            window.Toast.show('Download cancelled', 'info', 2000);
        }
    };

    window.sendFile = async function () {
        if (selectedFiles.length === 0) return;

        const sendBtn = document.getElementById('sendBtn');
        const fileToUpload = selectedFiles[0];

        if (sendBtn) sendBtn.disabled = true;
        window.UI.showStatus('sendStatus', '');
        window.UI.hide('sendResult');

        window.Transfer.upload(fileToUpload, {
            onStateChange: (state, label) => {
                window.UI.show('sendProgress');
                window.UI.show('cancelUploadBtn');
                
                // Track visual verification state
                if (state === 'verifying') {
                    window.UI.hide('cancelUploadBtn'); // Too late to abort
                }
                
                window.UI.updateProgress('send', 0, '0 B/s', 'Calculating...', label);
            },
            onProgress: (p) => {
                const ratio = `${window.Transfer.formatSize(p.loaded)} / ${window.Transfer.formatSize(p.total)}`;
                const modeLabel = p.mode === 'direct' ? 'Direct S3 Stream' : 'Server Relay';
                window.UI.updateProgress('send', p.percent, p.speed, p.eta, `Uploading via ${modeLabel} (${ratio})`);
            },
            onSuccess: (pin) => {
                window.UI.hide('sendProgress');
                window.UI.hide('cancelUploadBtn');
                if (sendBtn) sendBtn.disabled = false;

                // Cache active transfer to storage
                window.currentPin = pin;
                window.Pairing.saveTransfer(pin, 'sender', fileToUpload.name, fileToUpload.size);

                // Populate UI results
                const genPinEl = document.getElementById('generatedPin');
                if (genPinEl) genPinEl.textContent = pin;

                const qrEl = document.getElementById('qrCode');
                window.Pairing.generateQR(qrEl, pin);

                window.UI.show('sendResult');
                window.Toast.show('File uploaded successfully!', 'success', 4000);
            },
            onError: (err) => {
                window.UI.hide('sendProgress');
                window.UI.hide('cancelUploadBtn');
                if (sendBtn) sendBtn.disabled = false;
                
                window.UI.showStatus('sendStatus', `❌ Upload failed: ${err}`, 'error');
                window.Toast.show(`Upload error: ${err}`, 'error', 5000);
            }
        });
    };

    window.checkPin = async function () {
        const pinInput = document.getElementById('pinInput');
        if (!pinInput) return;

        const pin = pinInput.value.trim();
        const checkPinBtn = document.getElementById('checkPinBtn');

        if (checkPinBtn) checkPinBtn.disabled = true;
        window.UI.show('receiveProgress');
        window.UI.updateProgress('receive', 0, '0 B/s', 'Calculating...', 'Checking PIN status with server...');
        window.UI.showStatus('receiveStatus', '');
        window.UI.hide('fileInfoCard');

        try {
            const checkData = await window.Transfer.checkPin(pin);
            window.UI.hide('receiveProgress');
            if (checkPinBtn) checkPinBtn.disabled = false;

            if (checkData.status === 'waiting') {
                window.UI.showStatus('receiveStatus', '⏳ The sender is still uploading. Try again in a moment.', 'warning');
                window.Toast.show('Sender is still uploading. Please wait.', 'warning', 3500);
                return;
            }

            // Successfully checked
            window.pendingPin = pin;
            const fileInfoName = document.getElementById('fileInfoName');
            if (fileInfoName) fileInfoName.textContent = checkData.filename;

            // Keep track of checked file in history
            window.Pairing.saveTransfer(pin, 'receiver', checkData.filename, 0);

            window.UI.show('fileInfoCard');
            window.Toast.show('File found and ready to download!', 'success', 3000);

        } catch (err) {
            window.UI.hide('receiveProgress');
            if (checkPinBtn) checkPinBtn.disabled = false;
            
            window.UI.showStatus('receiveStatus', `❌ ${err.message}`, 'error');
            window.Toast.show(`PIN Check error: ${err.message}`, 'error', 4500);
        }
    };

    window.confirmDownload = async function () {
        if (!window.pendingPin) return;

        const checkPinBtn = document.getElementById('checkPinBtn');
        const cancelBtn = document.getElementById('cancelDownloadBtn');
        const fileInfoCard = document.getElementById('fileInfoCard');
        const confirmBtn = document.getElementById('confirmDownloadBtn');
        const filename = document.getElementById('fileInfoName').textContent;

        if (confirmBtn) confirmBtn.disabled = true;
        window.UI.hide(fileInfoCard);
        window.UI.hide(checkPinBtn);
        window.UI.show('receiveProgress');
        window.UI.show(cancelBtn);
        window.UI.updateProgress('receive', 0, '0 B/s', 'Connecting...', 'Initiating secure chunked download stream...');

        window.UI.showStatus('receiveStatus', '');

        window.Transfer.download(window.pendingPin, filename, {
            onProgress: (p) => {
                const ratio = `${window.Transfer.formatSize(p.loaded)} / ${window.Transfer.formatSize(p.total)}`;
                window.UI.updateProgress('receive', p.percent, p.speed, p.eta, `Downloading chunked buffers (${ratio})`);
            },
            onSuccess: () => {
                window.UI.hide('receiveProgress');
                window.UI.hide(cancelBtn);
                window.UI.show(checkPinBtn);
                
                const pinInput = document.getElementById('pinInput');
                if (pinInput) pinInput.value = '';
                window.pendingPin = '';
                
                if (confirmBtn) confirmBtn.disabled = false;

                window.UI.showStatus('receiveStatus', '✅ Saved to Downloads!', 'success');
                window.Toast.show('Download completed successfully!', 'success', 4000);
            },
            onError: (err, wasAborted) => {
                window.UI.hide('receiveProgress');
                window.UI.hide(cancelBtn);
                window.UI.show(checkPinBtn);
                window.UI.show(fileInfoCard);
                
                if (confirmBtn) confirmBtn.disabled = false;

                if (wasAborted) {
                    window.UI.showStatus('receiveStatus', '❌ Download cancelled.', 'error');
                } else {
                    window.UI.showStatus('receiveStatus', `❌ Download failed: ${err}`, 'error');
                    window.Toast.show(`Download error: ${err}`, 'error', 5000);
                }
            }
        });
    };

    // DOM Ready listener
    window.addEventListener('DOMContentLoaded', init);

})(window);
