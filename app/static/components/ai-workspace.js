/**
 * ZapLink AI Workspace UI Component
 * Drives the Screenshot Intelligence System UI inside the AI Workspace tab.
 * Connects directly to Flask search, statistics, and bootstrap mock indexing APIs.
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

            // Injects responsive layout structure
            container.innerHTML = `
                <div class="card">
                    <h2>
                        <span>🧠 AI Memory Workspace</span>
                        <button class="btn btn-secondary" id="aiLoadMockBtn" style="width:auto; padding:6px 12px; font-size:0.75rem; font-weight:700;" onclick="window.AIWorkspace.bootstrapMock()">
                            📥 Load Mock Screenshots
                        </button>
                    </h2>
                    
                    <!-- Dashboard Metrics Ticker -->
                    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap:10px; margin-bottom:18px; padding:10px; background:rgba(255,255,255,0.01); border:1px solid var(--card-border); border-radius:var(--radius-md);">
                        <div style="text-align:center; padding:4px;">
                            <div style="font-size:1.2rem; font-weight:800; color:var(--primary-green);" id="aiStatIndexed">0</div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Indexed</div>
                        </div>
                        <div style="text-align:center; padding:4px;">
                            <div style="font-size:1.2rem; font-weight:800; color:var(--primary-teal);" id="aiStatOCR">0</div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">OCR Complete</div>
                        </div>
                        <div style="text-align:center; padding:4px;">
                            <div style="font-size:1.2rem; font-weight:800; color:var(--info);" id="aiStatQueue">0</div>
                            <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Queue Size</div>
                        </div>
                    </div>

                    <div class="ai-workspace-container">
                        <!-- Search & Quick Filter Section -->
                        <div>
                            <div class="ai-section-title">🔍 Semantic Memory Lookup</div>
                            <div class="ai-search-box">
                                <span class="ai-search-icon">🔍</span>
                                <input type="text" class="ai-search-input" id="aiSearchInput" placeholder="Search screenshots by keywords...">
                            </div>
                            <div class="ai-chips">
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('react')">⚡ React Error</span>
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('leetcode')">💻 Leetcode Solution</span>
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('resume')">📄 Resume CV</span>
                                <span class="ai-chip" onclick="window.AIWorkspace.quickSearch('')">🔄 Show All</span>
                            </div>
                        </div>

                        <!-- Active monitored folder path indicator -->
                        <div style="font-size:0.7rem; color:var(--text-muted); word-break:break-all; margin-top:-6px;" id="aiFolderIndicator">
                            📁 Watcher Folder: <span>Resolving...</span>
                        </div>

                        <!-- Screenshot Cards Grid (Search Results) -->
                        <div>
                            <div class="ai-section-title" id="aiResultsCount">📸 Indexed Screenshot Memory</div>
                            <div id="aiSearchResultsGrid" class="ai-history-list" style="display:flex; flex-direction:column; gap:10px;">
                                <!-- Populated dynamically from API -->
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Wire keypress event listener
            const searchInput = document.getElementById('aiSearchInput');
            if (searchInput) {
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.executeSearch(searchInput.value.trim());
                    }
                });
                
                // Active instant typing search with debounce
                let debounceTimer;
                searchInput.addEventListener('input', () => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => {
                        this.executeSearch(searchInput.value.trim());
                    }, 300);
                });
            }

            // Initial fetch of statistics and screenshot items
            this.loadStats();
            this.executeSearch('');

            // Listen for global history events to update metrics
            window.addEventListener('zaplink_history_updated', () => {
                this.loadStats();
                this.executeSearch(searchInput ? searchInput.value.trim() : '');
            });
        },

        /**
         * Fetch current indexing statistics from server
         */
        async loadStats() {
            try {
                const res = await fetch('/ai/stats');
                const data = await res.json();
                if (data.success) {
                    const stats = data.stats;
                    
                    const statIndexed = document.getElementById('aiStatIndexed');
                    const statOCR = document.getElementById('aiStatOCR');
                    const statQueue = document.getElementById('aiStatQueue');
                    const folderEl = document.getElementById('aiFolderIndicator');

                    if (statIndexed) statIndexed.textContent = stats.total_indexed;
                    if (statOCR) statOCR.textContent = stats.ocr_complete;
                    
                    // Show total active processing and pending queues
                    if (statQueue) {
                        statQueue.textContent = stats.pending_queue;
                        if (stats.pending_queue > 0) {
                            statQueue.style.color = 'var(--info)';
                            statQueue.classList.add('skeleton-box'); // Adds neat pulsing look
                        } else {
                            statQueue.style.color = 'var(--text-muted)';
                            statQueue.classList.remove('skeleton-box');
                        }
                    }

                    if (folderEl && stats.screenshots_folder) {
                        folderEl.innerHTML = `📁 Monitored: <span style="color:var(--text-main); font-family: monospace;">${stats.screenshots_folder}</span>`;
                    }
                }
            } catch (err) {
                console.warn('AI Workspace: Stats ticker fetch failed:', err);
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
                    window.Toast.show(data.message, 'success', 4000);
                    this.loadStats();
                    this.executeSearch('');
                } else {
                    window.Toast.show(`Bootstrap failed: ${data.error}`, 'error', 4000);
                }
            } catch (err) {
                window.Toast.show(`Bootstrap error: ${err.message}`, 'error', 4000);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Load Mock Screenshots';
                }
            }
        },

        /**
         * Executes search query matching matches
         * @param {string} query
         */
        async executeSearch(query) {
            const grid = document.getElementById('aiSearchResultsGrid');
            const countEl = document.getElementById('aiResultsCount');
            
            if (!grid) return;

            // Render skeleton loading state
            grid.innerHTML = `
                <div style="padding:14px; background:rgba(255,255,255,0.01); border:1px solid var(--card-border); border-radius:var(--radius-md);">
                    <div class="skeleton-box" style="width:60%; height:14px; margin-bottom:8px;"></div>
                    <div class="skeleton-box" style="width:85%; height:10px; margin-bottom:4px;"></div>
                    <div class="skeleton-box" style="width:30%; height:10px;"></div>
                </div>
            `;

            try {
                const res = await fetch('/ai/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, limit: 20, offset: 0 })
                });
                
                const data = await res.json();
                
                if (!data.success) {
                    throw new Error(data.error || 'Unknown search error');
                }

                const results = data.results;
                
                if (countEl) {
                    countEl.textContent = query ? `📸 Match Results (${results.length})` : `📸 Indexed Screenshot Memory (${results.length})`;
                }

                if (results.length === 0) {
                    grid.innerHTML = `
                        <div style="text-align:center; padding:24px 12px; font-size:0.8rem; color:var(--text-muted); border:1px dashed var(--card-border); border-radius:var(--radius-md);">
                            🔍 No screenshots found matching "${query}".<br>
                            <span style="font-size:0.7rem; display:block; margin-top:8px;">Try taking a desktop screenshot, dropping an image in the screenshots directory, or clicking "Load Mock Screenshots"!</span>
                        </div>
                    `;
                    return;
                }

                grid.innerHTML = results.map(item => {
                    const sizeStr = window.Transfer ? window.Transfer.formatSize(item.filesize) : `${(item.filesize / 1024).toFixed(1)} KB`;
                    
                    // Render status badges with HSL styled parameters
                    let badgeColor = 'var(--text-muted)';
                    let badgeBg = 'rgba(255, 255, 255, 0.05)';
                    let badgeLabel = 'Pending';
                    
                    if (item.ocr_status === 'COMPLETE') {
                        badgeColor = 'var(--success)';
                        badgeBg = 'rgba(48, 209, 88, 0.12)';
                        badgeLabel = 'OCR Complete';
                    } else if (item.ocr_status === 'METADATA_ONLY') {
                        badgeColor = 'var(--warning)';
                        badgeBg = 'rgba(255, 159, 10, 0.12)';
                        badgeLabel = 'Metadata Only';
                    } else if (item.ocr_status === 'FAILED') {
                        badgeColor = 'var(--error)';
                        badgeBg = 'rgba(255, 69, 58, 0.12)';
                        badgeLabel = 'OCR Failed';
                    } else if (item.ocr_status === 'PROCESSING') {
                        badgeColor = 'var(--info)';
                        badgeBg = 'rgba(10, 132, 255, 0.12)';
                        badgeLabel = 'Processing';
                    }

                    // Format date
                    const createdDate = new Date(item.created_at + 'Z'); // Treat as UTC
                    const dateStr = createdDate.toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    // Dimensions
                    const dimStr = item.width > 0 ? ` • ${item.width}x${item.height}` : '';

                    return `
                        <div class="ai-history-item" style="cursor:pointer;" onclick="window.AIWorkspace.viewDetails(${item.id})">
                            <div class="ai-history-info">
                                <span style="font-size:1.3rem;">🖼️</span>
                                <div class="ai-history-meta" style="width:100%; max-width:calc(100% - 30px);">
                                    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
                                        <h4 style="margin:0; font-size:0.82rem; color:#ffffff;" title="${item.filename}">${item.filename}</h4>
                                        <span style="font-size:0.65rem; font-weight:700; padding:2px 6px; border-radius:4px; background:${badgeBg}; color:${badgeColor}; border:1px solid rgba(255,255,255,0.02);">
                                            ${badgeLabel}
                                        </span>
                                    </div>
                                    <p style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">
                                        ${dateStr} • ${sizeStr}${dimStr}
                                    </p>
                                    ${item.highlights ? `
                                        <p style="font-size:0.72rem; color:#d1d1d6; background:rgba(0,0,0,0.15); padding:6px 10px; border-radius:6px; margin-top:6px; font-family:monospace; line-height:1.4; border-left:2px solid var(--primary-teal); word-break:break-all;">
                                            ${item.highlights}
                                        </p>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                grid.innerHTML = `
                    <div class="status-msg error" style="display:flex;">
                        ❌ Search query failed: ${err.message}
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
                // Fetch stats or search to find item
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
