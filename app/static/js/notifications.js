/**
 * ZapLink Toast Notification System
 * Dependency-free, highly performant visual feedback module.
 */

(function (window) {
    'use strict';

    const Toast = {
        /**
         * Initialize the Toast container in DOM
         * @private
         */
        _getContainer() {
            let container = document.getElementById('zaplink-toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'zaplink-toast-container';
                container.className = 'toast-container';
                document.body.appendChild(container);
            }
            return container;
        },

        /**
         * Shows a toast message
         * @param {string} message The text content to display
         * @param {'success'|'error'|'warning'|'info'} type The status type
         * @param {number} [duration=4000] Time in ms before auto-dismissal
         */
        show(message, type = 'info', duration = 4000) {
            const container = this._getContainer();
            
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            
            const iconMap = {
                success: '✅',
                error: '❌',
                warning: '⚠️',
                info: 'ℹ️'
            };
            const icon = iconMap[type] || 'ℹ️';

            toast.innerHTML = `
                <div class="toast-content">
                    <span class="toast-icon">${icon}</span>
                    <span>${message}</span>
                </div>
                <button class="toast-close" aria-label="Dismiss toast">×</button>
            `;

            // Close button click handler
            const closeBtn = toast.querySelector('.toast-close');
            const dismiss = () => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(12px) scale(0.95)';
                setTimeout(() => {
                    if (toast.parentNode === container) {
                        container.removeChild(toast);
                    }
                }, 300);
            };

            closeBtn.addEventListener('click', dismiss);
            container.appendChild(toast);

            // Auto-dismiss timeout
            if (duration > 0) {
                setTimeout(() => {
                    dismiss();
                }, duration);
            }
            
            return { dismiss };
        }
    };

    // Listen for network offline/online states and trigger automated feedback
    window.addEventListener('offline', () => {
        Toast.show('Network connection lost. Please check your internet connection.', 'warning', 6000);
    });

    window.addEventListener('online', () => {
        Toast.show('Network connection restored. Back online!', 'success', 3000);
    });

    // Attach to global window scope
    window.Toast = Toast;

})(window);
