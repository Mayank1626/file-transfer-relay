/**
 * ZapLink AI Workspace UI Component
 * Renders interactive mock elements preparing the application for future AI capabilities:
 * Screenshot Memory, Semantic Search, Action Commands, and Dynamic Workspace History.
 */

(function (window) {
    'use strict';

    const AIWorkspace = {
        /**
         * Initialize and render the AI Workspace inside the target container
         * @param {string} containerId ID of target DOM node
         */
        init(containerId = 'workspaceSection') {
            const container = document.getElementById(containerId);
            if (!container) return;

            // Base Layout injection
            container.innerHTML = `
                <div class="card">
                    <h2>🧠 AI Workspace <span style="font-size:0.75rem; background:rgba(0, 191, 165, 0.15); color:var(--primary-teal); padding:2px 8px; border-radius:10px; font-weight:700;">PREVIEW</span></h2>
                    
                    <div class="ai-workspace-container">
                        
                        <!-- Section 1: Semantic Search -->
                        <div>
                            <div class="ai-section-title">🔍 Semantic Memory Search</div>
                            <div class="ai-search-box">
                                <span class="ai-search-icon">🔍</span>
                                <input type="text" class="ai-search-input" id="aiSearchInput" placeholder="Search across all synced screenshots, files and links...">
                            </div>
                            <div class="ai-chips">
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('invoice')">📄 Invoice</span>
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('design')">🎨 Design assets</span>
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('meeting')">✍️ Meeting notes</span>
                            </div>
                            <div id="aiSearchResults" style="margin-top:8px;"></div>
                        </div>

                        <!-- Section 2: AI Action Pills -->
                        <div>
                            <div class="ai-section-title">⚡ AI Instant Commands</div>
                            <div class="ai-chips">
                                <span class="ai-chip" style="border-color:rgba(0,230,118,0.15); color:var(--primary-green);" onclick="window.AIWorkspace.triggerCommand('/ocr')">🤖 /ocr extract</span>
                                <span class="ai-chip" style="border-color:rgba(10,132,255,0.15); color:var(--info);" onclick="window.AIWorkspace.triggerCommand('/summarize')">📝 /summarize doc</span>
                                <span class="ai-chip" style="border-color:rgba(255,159,10,0.15); color:var(--warning);" onclick="window.AIWorkspace.triggerCommand('/transcribe')">🎙️ /transcribe audio</span>
                                <span class="ai-chip" style="border-color:rgba(0,191,165,0.15); color:var(--primary-teal);" onclick="window.AIWorkspace.triggerCommand('/insights')">📊 /generate insights</span>
                            </div>
                        </div>

                        <!-- Section 3: Screenshot Memory Grid -->
                        <div>
                            <div class="ai-section-title">🖼️ Screenshot OS Memory</div>
                            <div class="screenshot-grid">
                                <div class="screenshot-card" onclick="window.AIWorkspace.viewScreenshot('active_vscode')">
                                    <div class="screenshot-thumb"></div>
                                    <div class="screenshot-card-title">
                                        VS Code Workspace
                                        <span class="screenshot-card-time">Synced 5m ago</span>
                                    </div>
                                </div>
                                <div class="screenshot-card" onclick="window.AIWorkspace.viewScreenshot('browser_dashboard')">
                                    <div class="screenshot-thumb"></div>
                                    <div class="screenshot-card-title">
                                        Analytics Dashboard
                                        <span class="screenshot-card-time">Synced 14m ago</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Section 4: Dynamic History -->
                        <div>
                            <div class="ai-section-title">📁 Workspace Sync History</div>
                            <div id="aiWorkspaceHistory" class="ai-history-list">
                                <!-- Populated dynamically from local storage pairing history -->
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Wire Search Enter handler
            const searchInput = document.getElementById('aiSearchInput');
            if (searchInput) {
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.executeSearch(searchInput.value.trim());
                    }
                });
            }

            // Render current transfer history
            this.renderHistory();

            // Setup real-time updates listener
            window.addEventListener('zaplink_history_updated', () => {
                this.renderHistory();
            });
        },

        /**
         * Renders the dynamic sync history from local cache
         */
        renderHistory() {
            const listContainer = document.getElementById('aiWorkspaceHistory');
            if (!listContainer) return;

            const history = window.Pairing.getHistory();
            if (history.length === 0) {
                listContainer.innerHTML = `
                    <div style="text-align:center; padding:12px; font-size:0.75rem; color:var(--text-muted); border:1px dashed var(--card-border); border-radius:8px;">
                        No workspace assets synced yet. Synced files appear here automatically.
                    </div>
                `;
                return;
            }

            listContainer.innerHTML = history.map(item => {
                const date = new Date(item.timestamp);
                const timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const sizeStr = window.Transfer ? window.Transfer.formatSize(item.size) : `${(item.size / (1024 * 1024)).toFixed(1)} MB`;
                const icon = item.role === 'sender' ? '📤' : '📥';
                const roleLabel = item.role === 'sender' ? 'Sent' : 'Received';
                
                return `
                    <div class="ai-history-item">
                        <div class="ai-history-info">
                            <span style="font-size:1.1rem;">${icon}</span>
                            <div class="ai-history-meta">
                                <h4 title="${item.filename}">${item.filename}</h4>
                                <p>${roleLabel} • ${sizeStr} • PIN ${item.pin}</p>
                            </div>
                        </div>
                        <div class="ai-history-status done">${timeString}</div>
                    </div>
                `;
            }).join('');
        },

        /**
         * Executes semantic search mock simulation
         * @param {string} query
         */
        executeSearch(query) {
            const resultsBox = document.getElementById('aiSearchResults');
            if (!resultsBox || !query) return;

            // Show skeleton loader
            resultsBox.innerHTML = `
                <div style="padding:14px; background:rgba(255,255,255,0.01); border:1px solid var(--card-border); border-radius:8px;">
                    <div class="skeleton-box" style="width:70%; margin-bottom:8px;"></div>
                    <div class="skeleton-box" style="width:40%;"></div>
                </div>
            `;

            // Timeout simulation for semantic index retrieval
            setTimeout(() => {
                const lowerQuery = query.toLowerCase();
                let matches = [];

                if (lowerQuery.includes('invoice') || lowerQuery.includes('bill') || lowerQuery.includes('pay')) {
                    matches = [
                        { icon: '📄', title: 'Invoice_Q1_Mayank.pdf', context: 'Found total amount match of <strong>$1,250.00 USD</strong> inside billing section.', time: 'Synced 2 hours ago' }
                    ];
                } else if (lowerQuery.includes('design') || lowerQuery.includes('ui') || lowerQuery.includes('asset')) {
                    matches = [
                        { icon: '🎨', title: 'ZapLink_V2_FigmaMockups.png', context: 'Image match: Contains layers matching "Dark Mode Layout", "Tabs Navigation" and "Progress Speed Ring".', time: 'Synced yesterday' }
                    ];
                } else if (lowerQuery.includes('meeting') || lowerQuery.includes('notes') || lowerQuery.includes('agenda')) {
                    matches = [
                        { icon: '✍️', title: 'ZapLink_Weekly_MeetingNotes.txt', context: 'Text match: "AI Memory Workspace handoff protocol planned for Q3 release including OCR endpoints."', time: 'Synced 3 hours ago' }
                    ];
                } else {
                    matches = [
                        { icon: '🧠', title: `Context lookup: "${query}"`, context: `AI model resolved search constraints for "${query}" across workspace nodes. No active matches found in this local preview database.`, time: 'Search complete' }
                    ];
                }

                resultsBox.innerHTML = matches.map(match => `
                    <div class="ai-history-item" style="border-color:rgba(0, 191, 165, 0.25); background:rgba(0, 191, 165, 0.02); animation: fadeIn 0.3s ease;">
                        <div class="ai-history-info">
                            <span style="font-size:1.2rem;">${match.icon}</span>
                            <div class="ai-history-meta">
                                <h4 style="color:var(--primary-teal);">${match.title}</h4>
                                <p style="color:#a5a5a5; font-size:0.75rem; margin-top:2px;">${match.context}</p>
                                <p style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">${match.time}</p>
                            </div>
                        </div>
                    </div>
                `).join('');

            }, 750);
        },

        /**
         * Triggers click from Chip selection
         * @param {string} val
         */
        quickSearch(val) {
            const input = document.getElementById('aiSearchInput');
            if (input) {
                input.value = val;
                this.executeSearch(val);
            }
        },

        /**
         * Simulates triggering AI Instant Command
         * @param {string} cmd
         */
        triggerCommand(cmd) {
            const labelMap = {
                '/ocr': 'OCR extraction requested. Scanning last shared document...',
                '/summarize': 'Document summarization pipeline initialized...',
                '/transcribe': 'Audio transcriber loaded. Decoding local voice files...',
                '/insights': 'Insight processor initialized. Analyzing workspace network trends...'
            };
            const label = labelMap[cmd] || `Executing ${cmd}...`;
            window.Toast.show(`🧠 AI: ${label}`, 'info', 3500);
        },

        /**
         * Simulates viewing screenshot memory details
         * @param {string} id
         */
        viewScreenshot(id) {
            const names = {
                active_vscode: 'VS Code Active Session Workspace capture',
                browser_dashboard: 'Chrome Cloud Relay Monitor capture'
            };
            window.Toast.show(`🖼️ Memory: Viewing high-resolution capture details for ${names[id] || id}`, 'success', 3000);
        }
    };

    // Attach to global window scope
    window.AIWorkspace = AIWorkspace;

})(window);
