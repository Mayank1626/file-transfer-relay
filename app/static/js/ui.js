/**
 * ZapLink View/UI Management Module
 * Manages active tabs, progress rendering, and visual state handshakes.
 */

(function (window) {
    'use strict';

    const UI = {
        /**
         * Switches the active UI tab panel
         * @param {'send'|'receive'|'workspace'} tab
         */
        switchTab(tab) {
            const tabs = document.querySelectorAll('.tab');
            const sections = document.querySelectorAll('.section');
            
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            const tabIndexMap = {
                send: 0,
                receive: 1,
                workspace: 2
            };

            const index = tabIndexMap[tab];
            if (index !== undefined && tabs[index]) {
                tabs[index].classList.add('active');
            }

            const targetSection = document.getElementById(`${tab}Section`);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        },

        /**
         * Shows a specific DOM element
         * @param {HTMLElement|string} el
         * @param {string} [display='block']
         */
        show(el, display = 'block') {
            const element = typeof el === 'string' ? document.getElementById(el) : el;
            if (element) {
                element.style.display = display;
            }
        },

        /**
         * Hides a specific DOM element
         * @param {HTMLElement|string} el
         */
        hide(el) {
            const element = typeof el === 'string' ? document.getElementById(el) : el;
            if (element) {
                element.style.display = 'none';
            }
        },

        /**
         * Displays a centralized alert status within a container card
         * @param {string} elId The target element ID
         * @param {string} message The text content to display
         * @param {'success'|'error'|'warning'|''} type The alert class type
         */
        showStatus(elId, message, type = '') {
            const el = document.getElementById(elId);
            if (!el) return;

            el.innerHTML = '';
            if (!message) {
                el.className = 'status-msg';
                this.hide(el);
                return;
            }

            el.className = `status-msg ${type}`;
            
            const iconMap = {
                success: '✅',
                error: '❌',
                warning: '⚠️'
            };
            const icon = iconMap[type] ? `<span style="font-size:1rem">${iconMap[type]}</span> ` : '';
            
            el.innerHTML = `${icon}<span>${message}</span>`;
            this.show(el, 'flex');
        },

        /**
         * Updates the real-time progress layout
         * @param {'send'|'receive'} prefix Target prefix
         * @param {number} percent Current completed percent
         * @param {string} speed Speed label
         * @param {string} eta ETA label
         * @param {string} detail Detailed text transfer ratio
         */
        updateProgress(prefix, percent, speed, eta, detail = '') {
            const fill = document.getElementById(`${prefix}ProgressFill`);
            const text = document.getElementById(`${prefix}ProgressText`);
            
            if (fill) {
                fill.style.width = `${percent}%`;
            }

            if (text) {
                text.innerHTML = `
                    <div style="font-weight: 700; margin-bottom: 2px;">${percent}% Completed</div>
                    <div style="font-size: 0.72rem; opacity: 0.85;">${detail}</div>
                    <div class="progress-stats">
                        <span class="stat-item">⚡ ${speed}</span>
                        <span class="stat-item">⏳ ${eta}</span>
                    </div>
                `;
            }
        },

        /**
         * Triggers reconnection options if an active session is found in cache
         */
        checkReconnection() {
            const reconnect = window.Pairing.getReconnectOption();
            const banner = document.getElementById('reconnectBanner');
            
            if (reconnect && banner) {
                const now = Date.now();
                const diffMins = Math.floor((now - reconnect.timestamp) / 60000);
                
                // Show only if within active limits
                if (diffMins < 60) {
                    const activePin = reconnect.pin;
                    const roleLabel = reconnect.role === 'sender' ? 'Uploaded' : 'Checked';
                    
                    banner.querySelector('.text').innerHTML = `
                        <span>🔄</span>
                        <span>Active transfer found! Resume PIN <strong>${activePin}</strong> (${roleLabel} ${diffMins}m ago)</span>
                    `;
                    
                    // Setup buttons
                    const resumeBtn = banner.querySelector('.resume-btn');
                    const dismissBtn = banner.querySelector('.dismiss-btn');
                    
                    resumeBtn.onclick = () => {
                        this.hide(banner);
                        if (reconnect.role === 'sender') {
                            this.switchTab('send');
                            
                            // Re-render sender result screen
                            const result = document.getElementById('sendResult');
                            const pinDisplay = document.getElementById('generatedPin');
                            
                            if (result && pinDisplay) {
                                window.currentPin = activePin;
                                pinDisplay.textContent = activePin;
                                result.style.display = 'block';
                                
                                const qrEl = document.getElementById('qrCode');
                                window.Pairing.generateQR(qrEl, activePin);
                                
                                window.Toast.show(`Resumed sender session for PIN ${activePin}`, 'success', 3000);
                            }
                        } else {
                            this.switchTab('receive');
                            const pinInput = document.getElementById('pinInput');
                            if (pinInput) {
                                pinInput.value = activePin;
                                // Auto check PIN
                                if (window.checkPin) window.checkPin();
                            }
                        }
                    };
                    
                    dismissBtn.onclick = () => {
                        this.hide(banner);
                        // Clean history so banner doesn't pop up again
                        window.Pairing.clearHistory();
                    };
                    
                    this.show(banner, 'flex');
                } else {
                    this.hide(banner);
                }
            } else if (banner) {
                this.hide(banner);
            }
        }
    };

    // Attach to global window scope
    window.UI = UI;

})(window);
