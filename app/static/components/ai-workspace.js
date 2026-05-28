/**
 * ZapLink AI Workspace UI Component — Refactored Spotlight Edition
 * Implements a calm, minimalist, search-first productivity layout.
 * Preserves all active keyword indexing and API connections.
 */

(function (window) {
    'use strict';

    const AIWorkspace = {
        /**
         * Initialize and render the AI Workspace
         * @param {string} containerId ID of target DOM node
         */
        init(containerId = 'workspaceSection') {
            const container = document.getElementById(containerId);
            if (!container) return;

            // Injects a highly polished, Raycast-inspired clean panel
            container.innerHTML = `
                <div class="card" style="padding: 24px; border: 1px solid rgba(255,255,255,0.02); background: #0c0c0f; border-radius: var(--radius-lg); box-shadow: var(--shadow-md);">
                    
                    <!-- Search Header Section (The Focal Point) -->
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="font-size: 1.15rem; font-weight: 700; color: #ffffff; letter-spacing: -0.01em; margin-bottom: 12px; justify-content: center; display: flex; align-items: center; gap: 6px;">
                            <span>🧠 Search Your Memory</span>
                        </h2>
                        
                        <div class="ai-search-box" style="margin-bottom: 10px; max-width: 440px; margin-left: auto; margin-right: auto; position: relative;">
                            <span class="ai-search-icon" style="color: #555; font-size: 0.85rem;">🔍</span>
                            <input type="text" class="ai-search-input" id="aiSearchInput" placeholder="Search screenshots, notes, files..." style="font-size: 0.88rem; padding: 12px 14px 12px 36px; border-radius: var(--radius-md); background: #131316; border-color: #202024; height: auto;">
                        </div>
                        
                        <!-- Subtle Status & Folder Path Meta Line -->
                        <div style="font-size: 0.7rem; color: var(--text-muted); display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 6px; font-weight: 500;" id="aiStatusMetaLine">
                            <span id="aiStatIndexedText">0 screenshots indexed</span>
                            <span style="opacity: 0.2;">•</span>
                            <span id="aiStatQueueText">0 in queue</span>
                            <span style="opacity: 0.2;">•</span>
                            <span id="aiFolderIndicatorText">Resolving watcher folder...</span>
                        </div>
                    </div>

                    <!-- Memories Result Section -->
                    <div style="margin-top: 14px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.02);">
                            <span style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 700;" id="aiResultsCount">Memories</span>
                            
                            <!-- Hidden Developer Panel Toggle Link -->
                            <a href="#" id="aiDevTrigger" onclick="window.AIWorkspace.toggleDevMode(event)" style="font-size: 0.65rem; color: #3a3a40; text-decoration: none; font-weight: 600; transition: color 0.2s;">Dev Options</a>
                        </div>

                        <!-- Developer Controls Drawer (Hidden from standard users) -->
                        <div id="aiDevControls" style="display: none; padding: 10px; background: rgba(255, 159, 10, 0.03); border: 1px solid rgba(255, 159, 10, 0.1); border-radius: var(--radius-md); margin-bottom: 12px;">
                            <div style="font-size: 0.68rem; font-weight: 700; color: var(--warning); margin-bottom: 6px;">🛠️ Developer Mode</div>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
                                <button class="btn btn-secondary" id="aiLoadMockBtn" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto;" onclick="window.AIWorkspace.bootstrapMock()">
                                    📥 Ingest Mock Screenshots
                                </button>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('react')">react</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('leetcode')">leetcode</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('resume')">resume</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('')">clear</span>
                            </div>
                        </div>

                        <!-- Compact Screenshot Memory List -->
                        <div id="aiSearchResultsGrid" class="ai-history-list" style="display:flex; flex-direction:column; gap:6px;">
                            <!-- Populated dynamically from API -->
                        </div>
                    </div>
                </div>
            `;

            // Wire typing triggers
            const searchInput = document.getElementById('aiSearchInput');
            if (searchInput) {
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.executeSearch(searchInput.value.trim());
                    }
                });
                
                let debounceTimer;
                searchInput.addEventListener('input', () => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        this.executeSearch(searchInput.value.trim());
                    }, 300);
                });
            }

            // Initial load of stats and screenshots list
            this.loadStats();
            this.executeSearch('');

            // Bind update events
            window.addEventListener('zaplink_history_updated', () => {
                this.loadStats();
                this.executeSearch(searchInput ? searchInput.value.trim() : '');
            });
        },

        /**
         * Dynamic dev mode visual drawer toggle
         */
        toggleDevMode(event) {
            if (event) event.preventDefault();
            const devControls = document.getElementById('aiDevControls');
            const link = event.target;
            
            if (devControls && link) {
                if (devControls.style.display === 'none') {
                    devControls.style.display = 'block';
                    link.style.color = 'var(--warning)';
                    link.textContent = 'Hide Dev Options';
                } else {
                    devControls.style.display = 'none';
                    link.style.color = '#3a3a40';
                    link.textContent = 'Dev Options';
                }
            }
        },

        /**
         * Fetch current statistics and folder targets
         */
        async loadStats() {
            try {
                const res = await fetch('/ai/stats');
                const data = await res.json();
                if (data.success) {
                    const stats = data.stats;
                    
                    const statIndexedText = document.getElementById('aiStatIndexedText');
                    const statQueueText = document.getElementById('aiStatQueueText');
                    const folderElText = document.getElementById('aiFolderIndicatorText');

                    if (statIndexedText) {
                        statIndexedText.textContent = `${stats.total_indexed} screenshots indexed`;
                    }
                    
                    if (statQueueText) {
                        if (stats.pending_queue > 0) {
                            statQueueText.innerHTML = `<span style="color:var(--info); font-weight:700;">${stats.pending_queue} processing</span>`;
                        } else {
                            statQueueText.textContent = '0 in queue';
                        }
                    }

                    if (folderElText && stats.screenshots_folder) {
                        // Extract just the folder name or keep path short
                        const pathString = stats.screenshots_folder;
                        const shortPath = pathString.length > 30 ? '...' + pathString.slice(-27) : pathString;
                        folderElText.innerHTML = `Watching <span style="font-family:monospace; color:#ccc;" title="${pathString}">${shortPath}</span>`;
                    }
                }
            } catch (err) {
                console.warn('AI Workspace: Stats fetch aborted:', err);
            }
        },

        /**
         * Triggers mock bootstrap injection to populate demo content
         */
        async bootstrapMock() {
            const btn = document.getElementById('aiLoadMockBtn');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Ingesting...';
            }

            try {
                const res = await fetch('/ai/index/mock', { method: 'POST' });
                const data = await res.json();
                
                if (data.success) {
                    window.Toast.show(data.message, 'success', 3500);
                    this.loadStats();
                    this.executeSearch('');
                } else {
                    window.Toast.show(`Bootstrap failed: ${data.error}`, 'error', 3500);
                }
            } catch (err) {
                window.Toast.show(`Bootstrap error: ${err.message}`, 'error', 3500);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '📥 Ingest Mock Screenshots';
                }
            }
        },

        /**
         * Executes keyword term queries against Flask API
         * @param {string} query
         */
        async executeSearch(query) {
            const grid = document.getElementById('aiSearchResultsGrid');
            const countEl = document.getElementById('aiResultsCount');
            
            if (!grid) return;

            // Render highly simplified skeleton loader
            grid.innerHTML = `
                <div style="padding: 10px; background: rgba(255,255,255,0.01); border: 1px solid var(--card-border); border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 4px;">
                    <div class="skeleton-box" style="width: 50%; height: 11px;"></div>
                    <div class="skeleton-box" style="width: 30%; height: 8px;"></div>
                </div>
            `;

            try {
                const res = await fetch('/ai/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, limit: 15, offset: 0 })
                });
                
                const data = await res.json();
                
                if (!data.success) {
                    throw new Error(data.error || 'Unknown search error');
                }

                const results = data.results;
                
                if (countEl) {
                    countEl.textContent = query ? `Search Results (${results.length})` : `Recent Memories (${results.length})`;
                }

                if (results.length === 0) {
                    grid.innerHTML = `
                        <div style="text-align:center; padding:20px 10px; font-size:0.75rem; color:var(--text-muted); border:1px dashed var(--card-border); border-radius:var(--radius-md);">
                            No screenshots found matching "${query}"
                        </div>
                    `;
                    return;
                }

                grid.innerHTML = results.map(item => {
                    const sizeStr = window.Transfer ? window.Transfer.formatSize(item.filesize) : `${(item.filesize / 1024).toFixed(1)} KB`;
                    
                    // Standardizes subtle, low-glow status badges
                    let badgeColor = 'var(--text-muted)';
                    let badgeBg = 'rgba(255, 255, 255, 0.03)';
                    let badgeLabel = 'Pending';
                    
                    if (item.ocr_status === 'COMPLETE') {
                        badgeColor = 'var(--success)';
                        badgeBg = 'rgba(48, 209, 88, 0.08)';
                        badgeLabel = 'OCR Complete';
                    } else if (item.ocr_status === 'METADATA_ONLY') {
                        badgeColor = 'var(--warning)';
                        badgeBg = 'rgba(255, 159, 10, 0.08)';
                        badgeLabel = 'Metadata Only';
                    } else if (item.ocr_status === 'FAILED') {
                        badgeColor = 'var(--error)';
                        badgeBg = 'rgba(255, 69, 58, 0.08)';
                        badgeLabel = 'OCR Failed';
                    } else if (item.ocr_status === 'PROCESSING') {
                        badgeColor = 'var(--info)';
                        badgeBg = 'rgba(10, 132, 255, 0.08)';
                        badgeLabel = 'Processing';
                    }

                    // Format date
                    const createdDate = new Date(item.created_at + 'Z');
                    const dateStr = createdDate.toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    const dimStr = item.width > 0 ? ` • ${item.width}x${item.height}` : '';

                    // Injects ultra-compact and clean visual row design
                    return `
                        <div class="ai-history-item" style="cursor:pointer; padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.015); background: rgba(255,255,255,0.01); display: flex; flex-direction: column; transition: var(--transition-smooth); gap: 4px;" onclick="window.AIWorkspace.viewDetails(${item.id})">
                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px;">
                                <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; width: calc(100% - 90px);">
                                    <span style="font-size: 0.9rem; opacity: 0.65; flex-shrink:0;">🖼️</span>
                                    <h4 style="margin: 0; font-size: 0.78rem; font-weight: 600; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.filename}">${item.filename}</h4>
                                </div>
                                <span style="font-size: 0.6rem; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.01);">
                                    ${badgeLabel}
                                </span>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; font-size: 0.65rem; color: var(--text-muted); padding-left: 18px;">
                                <span>${dateStr} • ${sizeStr}${dimStr}</span>
                            </div>
                            ${item.highlights ? `
                                <div style="font-size: 0.65rem; color: #a0aec0; background: rgba(0,0,0,0.18); padding: 4px 8px; border-radius: 4px; margin-top: 2px; font-family: monospace; border-left: 2px solid var(--primary-teal); word-break: break-all; margin-left: 18px; line-height: 1.35;">
                                    ${item.highlights}
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('');

            } catch (err) {
                grid.innerHTML = `
                    <div class="status-msg error" style="display:flex; font-size:0.75rem;">
                        ❌ Search failed: ${err.message}
                    </div>
                `;
            }
        },

        /**
         * Quick Search click handler from chips
         * @param {string} keyword
         */
        quickSearch(keyword) {
            const input = document.getElementById('aiSearchInput');
            if (input) {
                input.value = keyword;
                this.executeSearch(keyword);
            }
        },

        /**
         * Displays popup or toast with full indexed text details
         * @param {number} id Screenshot ID
         */
        async viewDetails(id) {
            try {
                // Fetch details
                const res = await fetch('/ai/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: '', limit: 100, offset: 0 })
                });
                const data = await res.json();
                
                if (data.success) {
                    const item = data.results.find(x => x.id === id);
                    if (item) {
                        const statusText = item.ocr_status === 'COMPLETE' ? 'Successfully Extracted OCR Text' : 'Metadata Only (OCR Unavailable)';
                        const bodyText = item.ocr_text ? `\n\nFull OCR Content:\n------------------\n${item.ocr_text}` : '\n(No OCR text extracted for this screenshot)';
                        
                        alert(
                            `Screenshot Details\n==================\n` +
                            `File: ${item.filename}\n` +
                            `Path: ${item.filepath}\n` +
                            `Status: ${statusText}\n` +
                            `Date: ${item.created_at}\n` +
                            `Dimensions: ${item.width}x${item.height} pixels\n` +
                            `${bodyText}`
                        );
                    }
                }
            } catch (err) {
                window.Toast.show(`Could not load screenshot details: ${err.message}`, 'error', 3000);
            }
        }
    };

    // Attach to global window scope
    window.AIWorkspace = AIWorkspace;

})(window);
