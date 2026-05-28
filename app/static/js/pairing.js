/**
 * ZapLink Pairing & Reconnection Module
 * Handles deep-link QR generation and client-side transfer history preservation.
 */

(function (window) {
    'use strict';

    const HISTORY_KEY = 'zaplink_transfer_history';
    const EXPIRY_MS = 60 * 60 * 1000; // 1 hour session lifetime

    const Pairing = {
        /**
         * Renders QR code targeting an element with deep-link URL parsing
         * @param {HTMLElement} element The target container element
         * @param {string} pin The 6-digit session PIN
         * @param {number} [width=160] QR width
         * @param {number} [height=160] QR height
         */
        generateQR(element, pin, width = 160, height = 160) {
            if (!element) return;
            element.innerHTML = '';
            
            // Generate full deep-link handoff URL
            const url = `${window.location.origin}/?pin=${pin}`;

            try {
                if (typeof window.QRCode !== 'undefined') {
                    new window.QRCode(element, {
                        text: url,
                        width: width,
                        height: height,
                        colorDark: '#0a0a0c',
                        colorLight: '#ffffff',
                        correctLevel: window.QRCode.CorrectLevel.H
                    });
                } else {
                    console.error('QRCode JS library is not loaded.');
                }
            } catch (err) {
                console.error('Failed to generate QR Code:', err);
            }
        },

        /**
         * Persist transfer history record locally
         * @param {string} pin 6-digit PIN
         * @param {'sender'|'receiver'} role User transfer role
         * @param {string} filename Name of the file
         * @param {number} size File size in bytes
         */
        saveTransfer(pin, role, filename, size) {
            try {
                const history = this.getHistory();
                
                // Avoid duplicating active transfers
                const filtered = history.filter(item => item.pin !== pin);
                
                const newItem = {
                    pin,
                    role,
                    filename,
                    size,
                    timestamp: Date.now(),
                };

                filtered.unshift(newItem);
                
                // Keep only top 5 transfers
                if (filtered.length > 5) {
                    filtered.pop();
                }

                localStorage.setItem(HISTORY_KEY, JSON.stringify(filtered));
                
                // Dispatch event to update components dynamically
                window.dispatchEvent(new CustomEvent('zaplink_history_updated'));
            } catch (err) {
                console.warn('LocalStorage save failed:', err);
            }
        },

        /**
         * Retrieve transfer records from localStorage, filtering out expired sessions (> 1hr)
         * @returns {Array<object>}
         */
        getHistory() {
            try {
                const data = localStorage.getItem(HISTORY_KEY);
                if (!data) return [];
                
                const parsed = JSON.parse(data);
                const now = Date.now();
                
                // Filter expired entries
                const active = parsed.filter(item => (now - item.timestamp) < EXPIRY_MS);
                
                if (active.length !== parsed.length) {
                    localStorage.setItem(HISTORY_KEY, JSON.stringify(active));
                }
                
                return active;
            } catch (err) {
                console.warn('LocalStorage read failed:', err);
                return [];
            }
        },

        /**
         * Clear cached transfers
         */
        clearHistory() {
            try {
                localStorage.removeItem(HISTORY_KEY);
                window.dispatchEvent(new CustomEvent('zaplink_history_updated'));
            } catch (err) {
                console.warn('LocalStorage clear failed:', err);
            }
        },

        /**
         * Checks for an active reconnection opportunity (active transfer < 1hr)
         * @returns {object|null}
         */
        getReconnectOption() {
            const history = this.getHistory();
            if (history.length > 0) {
                // Return the latest transfer
                return history[0];
            }
            return null;
        }
    };

    // Attach to global window scope
    window.Pairing = Pairing;

})(window);
