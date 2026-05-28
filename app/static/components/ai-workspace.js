/**
 * ZapLink AI Workspace UI Component — Refactored Spotlight Edition
 * Implements a calm, minimalist, search-first productivity layout.
 * Preserves all active keyword indexing and API connections.
 */

(function (window) {
    'use strict';

    const AIWorkspace = {
        sourceFilter: 'all',
        expandedEntries: [],

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
                        
                        <div class="ai-search-box" style="margin-bottom: 12px; max-width: 440px; margin-left: auto; margin-right: auto; position: relative;">
                            <span class="ai-search-icon" style="color: #555; font-size: 0.85rem;">🔍</span>
                            <input type="text" class="ai-search-input" id="aiSearchInput" placeholder="Search screenshots, notes, clips..." style="font-size: 0.88rem; padding: 12px 14px 12px 36px; border-radius: var(--radius-md); background: #131316; border-color: #202024; height: auto;">
                        </div>

                        <!-- Source Filter Pills (All | Screenshots | Clipboard) -->
                        <div style="display: flex; justify-content: center; gap: 6px; margin-bottom: 14px;" id="aiSourceFiltersContainer">
                            <button id="pill-all" onclick="window.AIWorkspace.setSourceFilter('all')" style="background: rgba(0, 168, 150, 0.15); color: #00a896; border: 1px solid rgba(0, 168, 150, 0.3); font-weight: 600; padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; cursor: pointer; transition: all 0.2s;">All</button>
                            <button id="pill-screenshots" onclick="window.AIWorkspace.setSourceFilter('screenshots')" style="background: #131316; color: var(--text-muted); border: 1px solid #202024; font-weight: 500; padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; cursor: pointer; transition: all 0.2s;">Screenshots</button>
                            <button id="pill-clipboard" onclick="window.AIWorkspace.setSourceFilter('clipboard')" style="background: #131316; color: var(--text-muted); border: 1px solid #202024; font-weight: 500; padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; cursor: pointer; transition: all 0.2s;">Clipboard</button>
                        </div>
                        
                        <!-- Subtle Status & Folder Path Meta Line -->
                        <div style="font-size: 0.7rem; color: var(--text-muted); display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 6px; font-weight: 500;" id="aiStatusMetaLine">
                            <span id="aiStatIndexedText">0 screenshots indexed</span>
                            <span style="opacity: 0.2;">•</span>
                            <span id="aiStatClipboardText">0 clips</span>
                            <span style="opacity: 0.2;">•</span>
                            <span id="aiStatQueueText">0 in queue</span>
                            <span style="opacity: 0.2;">•</span>
                            <span id="aiFolderIndicatorText">Resolving watcher folder...</span>
                            <span style="opacity: 0.2;" id="aiPauseSep" style="display:none;">•</span>
                            <span id="aiPauseIndicatorText" style="color: var(--warning); display:none; font-weight:700;">⏸️ Tracking Paused</span>
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
                        <div id="aiDevControls" style="display: none; padding: 12px; background: rgba(255, 159, 10, 0.02); border: 1px solid rgba(255, 159, 10, 0.08); border-radius: var(--radius-md); margin-bottom: 12px; font-family: system-ui, -apple-system, sans-serif;">
                            <div style="font-size: 0.68rem; font-weight: 700; color: var(--warning); margin-bottom: 6px;">🛠️ Developer Mode</div>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 10px;">
                                <button class="btn btn-secondary" id="aiLoadMockBtn" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto;" onclick="window.AIWorkspace.bootstrapMock()">
                                    📥 Ingest Mock Memories
                                </button>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('react')">react</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('npm')">npm</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('github')">github</span>
                                <span class="ai-chip" style="font-size:0.65rem; padding: 4px 8px; margin: 0;" onclick="window.AIWorkspace.quickSearch('')">clear</span>
                            </div>

                            <div style="font-size: 0.68rem; font-weight: 700; color: var(--info); margin-bottom: 6px; margin-top: 6px;">🛡️ Tracking Controls (Privacy Drawer)</div>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
                                <button class="btn btn-secondary" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto; background:#1b1c22; border-color:#2e303d;" onclick="window.AIWorkspace.setTrackingPause(900)">
                                    ⏸️ Pause 15m
                                </button>
                                <button class="btn btn-secondary" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto; background:#1b1c22; border-color:#2e303d;" onclick="window.AIWorkspace.setTrackingPause(3600)">
                                    ⏸️ Pause 1h
                                </button>
                                <button class="btn btn-secondary" id="aiPausePermanentBtn" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto; background:#1b1c22; border-color:#2e303d;" onclick="window.AIWorkspace.toggleTrackingPermanent()">
                                    ⏸️ Pause Tracking
                                </button>
                                <button class="btn btn-danger" style="width:auto; padding:4px 8px; font-size:0.65rem; height: auto; background: rgba(255, 69, 58, 0.08); color: var(--error); border-color: rgba(255, 69, 58, 0.15);" onclick="window.AIWorkspace.clearClipboardHistory()">
                                    🧹 Clear Clipboard (Non-Favs)
                                </button>
                            </div>
                        </div>

                        <!-- Compact memories List -->
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

            // Initial load
            this.loadStats();
            this.executeSearch('');

            // Bind update events
            window.addEventListener('zaplink_history_updated', () => {
                this.loadStats();
                this.executeSearch(searchInput ? searchInput.value.trim() : '');
            });
        },

        /**
         * Set the active source filter pill and refresh search
         */
        setSourceFilter(source) {
            this.sourceFilter = source;

            // Visual toggle pill styles
            const pills = {
                'all': document.getElementById('pill-all'),
                'screenshots': document.getElementById('pill-screenshots'),
                'clipboard': document.getElementById('pill-clipboard')
            };

            for (const [key, element] of Object.entries(pills)) {
                if (!element) continue;
                if (key === source) {
                    element.style.background = 'rgba(0, 168, 150, 0.15)';
                    element.style.color = '#00a896';
                    element.style.borderColor = 'rgba(0, 168, 150, 0.3)';
                    element.style.fontWeight = '600';
                } else {
                    element.style.background = '#131316';
                    element.style.color = 'var(--text-muted)';
                    element.style.borderColor = '#202024';
                    element.style.fontWeight = '500';
                }
            }

            const searchInput = document.getElementById('aiSearchInput');
            this.executeSearch(searchInput ? searchInput.value.trim() : '');
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
                    const statClipboardText = document.getElementById('aiStatClipboardText');
                    const statQueueText = document.getElementById('aiStatQueueText');
                    const folderElText = document.getElementById('aiFolderIndicatorText');
                    const pauseText = document.getElementById('aiPauseIndicatorText');
                    const pauseSep = document.getElementById('aiPauseSep');
                    const pausePermanentBtn = document.getElementById('aiPausePermanentBtn');

                    if (statIndexedText) {
                        statIndexedText.textContent = `${stats.total_indexed} screenshots`;
                    }
                    
                    if (statClipboardText) {
                        statClipboardText.textContent = `${stats.total_clipboard} clips`;
                    }
                    
                    if (statQueueText) {
                        if (stats.pending_queue > 0) {
                            statQueueText.innerHTML = `<span style="color:var(--info); font-weight:700;">${stats.pending_queue} processing</span>`;
                        } else {
                            statQueueText.textContent = '0 in queue';
                        }
                    }

                    if (folderElText && stats.screenshots_folder) {
                        const pathString = stats.screenshots_folder;
                        const shortPath = pathString.length > 25 ? '...' + pathString.slice(-22) : pathString;
                        folderElText.innerHTML = `Watching <span style="font-family:monospace; color:#ccc;" title="${pathString}">${shortPath}</span>`;
                    }

                    // Display Pause state
                    if (pauseText) {
                        if (stats.is_tracking_paused) {
                            pauseText.style.display = 'inline';
                            if (pauseSep) pauseSep.style.display = 'inline';
                            
                            if (stats.pause_remaining_seconds === -1) {
                                pauseText.textContent = '⏸️ Tracking Paused';
                                if (pausePermanentBtn) pausePermanentBtn.textContent = '▶️ Resume Tracking';
                            } else {
                                const mins = Math.ceil(stats.pause_remaining_seconds / 60);
                                pauseText.textContent = `⏸️ Paused (${mins}m)`;
                                if (pausePermanentBtn) pausePermanentBtn.textContent = '▶️ Resume Tracking';
                            }
                        } else {
                            pauseText.style.display = 'none';
                            if (pauseSep) pauseSep.style.display = 'none';
                            if (pausePermanentBtn) pausePermanentBtn.textContent = '⏸️ Pause Tracking';
                        }
                    }
                }
            } catch (err) {
                console.warn('AI Workspace: Stats fetch aborted:', err);
            }
        },

        /**
         * Sets tracking pause duration
         */
        async setTrackingPause(seconds) {
            try {
                const res = await fetch('/ai/clipboard/toggle-tracking', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration: seconds })
                });
                const data = await res.json();
                if (data.success) {
                    window.Toast.show(seconds === 0 ? 'Tracking Resumed' : `Tracking paused for ${Math.ceil(seconds / 60)} minutes`, 'success', 2000);
                    this.loadStats();
                }
            } catch (err) {
                window.Toast.show(`Could not update tracking status: ${err.message}`, 'error', 3000);
            }
        },

        /**
         * Toggle permanent pause tracking
         */
        async toggleTrackingPermanent() {
            const pauseText = document.getElementById('aiPauseIndicatorText');
            const isCurrentlyPaused = pauseText && pauseText.style.display !== 'none';
            // Set 0 to resume, -1 to pause permanently
            await this.setTrackingPause(isCurrentlyPaused ? 0 : -1);
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
                    btn.textContent = '📥 Ingest Mock Memories';
                }
            }
        },

        /**
         * Executes unified term queries against flask server
         */
        async executeSearch(query) {
            const grid = document.getElementById('aiSearchResultsGrid');
            const countEl = document.getElementById('aiResultsCount');
            
            if (!grid) return;

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
                    body: JSON.stringify({ 
                        query: query, 
                        limit: 15, 
                        offset: 0,
                        source: this.sourceFilter
                    })
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
                            No memories found matching "${query}" under "${this.sourceFilter}" filter
                        </div>
                    `;
                    return;
                }

                grid.innerHTML = results.map(item => {
                    const createdDate = new Date(item.created_at + 'Z');
                    const dateStr = createdDate.toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    // 1. RENDER SCREENSHOT RESULTS
                    if (item.type === 'screenshot') {
                        const sizeStr = window.Transfer ? window.Transfer.formatSize(item.filesize) : `${(item.filesize / 1024).toFixed(1)} KB`;
                        
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

                        const dimStr = item.width > 0 ? ` • ${item.width}x${item.height}` : '';

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
                    }

                    // 2. RENDER CLIPBOARD RESULTS (Option B Card Design)
                    if (item.type === 'clipboard') {
                        const isExpanded = this.expandedEntries.includes(item.id);
                        
                        // Limit preview display
                        let displayContent = item.content;
                        const needsTruncation = item.content.length > 250;
                        if (needsTruncation && !isExpanded) {
                            displayContent = item.content.slice(0, 240) + ' ...';
                        }

                        // Colors for content type tags
                        let typeColor = '#00a896';
                        let typeBg = 'rgba(0, 168, 150, 0.08)';
                        if (item.content_type === 'COMMAND') {
                            typeColor = '#ffb703';
                            typeBg = 'rgba(255, 183, 3, 0.08)';
                        } else if (item.content_type === 'SQL') {
                            typeColor = '#9d4edd';
                            typeBg = 'rgba(157, 78, 221, 0.08)';
                        } else if (item.content_type === 'JSON') {
                            typeColor = '#ffb5a7';
                            typeBg = 'rgba(255, 181, 167, 0.08)';
                        } else if (item.content_type === 'URL') {
                            typeColor = '#028090';
                            typeBg = 'rgba(2, 128, 144, 0.08)';
                        }

                        const favIcon = item.is_favorite === 1 ? '★' : '☆';
                        const favColor = item.is_favorite === 1 ? 'var(--warning)' : '#555';

                        return `
                            <div class="ai-history-item" style="padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.015); background: rgba(255,255,255,0.01); display: flex; flex-direction: column; transition: var(--transition-smooth); gap: 4px;">
                                <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px;">
                                    <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; width: calc(100% - 100px);">
                                        <span style="font-size: 0.9rem; opacity: 0.65; flex-shrink:0;">📋</span>
                                        <h4 style="margin: 0; font-size: 0.76rem; font-weight: 600; color: #a0aec0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Copied from ${item.source_app}">
                                            via <span style="color:#ffffff; font-family:monospace;">${item.source_app}</span>
                                        </h4>
                                    </div>
                                    
                                    <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                                        <span style="font-size: 0.58rem; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: ${typeBg}; color: ${typeColor}; border: 1px solid rgba(255,255,255,0.01);">
                                            ${item.content_type}
                                        </span>
                                        
                                        <!-- Minimal visual star favorite badge -->
                                        <button onclick="window.AIWorkspace.toggleClipboardFav(${item.id}, event)" style="background:none; border:none; color:${favColor}; font-size:0.85rem; cursor:pointer; padding:0 2px; outline:none; transition: color 0.2s;" title="Toggle Favorite">
                                            ${favIcon}
                                        </button>
                                        
                                        <!-- Permanent exclude and delete icon -->
                                        <button onclick="window.AIWorkspace.deleteClipboardEntry(${item.id}, event)" style="background:none; border:none; color:#444; font-size:0.8rem; cursor:pointer; padding:0 2px; outline:none; transition: color 0.2s;" onmouseover="this.style.color='var(--error)'" onmouseout="this.style.color='#444'" title="Delete and optionally exclude">
                                            ✕
                                        </button>
                                    </div>
                                </div>

                                <!-- Text Display Area -->
                                <div style="font-size: 0.72rem; color: #cbd5e0; background: rgba(0,0,0,0.18); padding: 6px 10px; border-radius: 4px; margin-top: 2px; font-family: monospace; border-left: 2px solid #00a896; word-break: break-all; margin-left: 18px; line-height: 1.45; white-space: pre-wrap;">${displayContent}</div>
                                
                                <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; font-size: 0.65rem; color: var(--text-muted); padding-left: 18px; margin-top: 2px;">
                                    <span>${dateStr} • ${item.character_count} chars</span>
                                    
                                    <div style="display: flex; gap: 8px;">
                                        ${needsTruncation ? `
                                            <a href="#" onclick="window.AIWorkspace.toggleEntryExpand(${item.id}, event)" style="color:#00a896; text-decoration:none; font-weight:600;">
                                                ${isExpanded ? 'Show Less' : 'Show More'}
                                            </a>
                                        ` : ''}
                                        <a href="#" onclick="window.AIWorkspace.copyEntryBack(\`${encodeURIComponent(item.content)}\`, event)" style="color:#00a896; text-decoration:none; font-weight:600; display:flex; align-items:center; gap:2px;">
                                            📋 Copy back
                                        </a>
                                    </div>
                                </div>
                            </div>
                        `;
                    }
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
         * Expands/collapses clipboard preview
         */
        toggleEntryExpand(id, event) {
            if (event) event.preventDefault();
            if (this.expandedEntries.includes(id)) {
                this.expandedEntries = this.expandedEntries.filter(x => x !== id);
            } else {
                this.expandedEntries.push(id);
            }
            const searchInput = document.getElementById('aiSearchInput');
            this.executeSearch(searchInput ? searchInput.value.trim() : '');
        },

        /**
         * Toggles favorites toggle visual star
         */
        async toggleClipboardFav(id, event) {
            if (event) event.stopPropagation();
            try {
                const res = await fetch('/ai/clipboard/favorite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });
                const data = await res.json();
                if (data.success) {
                    this.loadStats();
                    const searchInput = document.getElementById('aiSearchInput');
                    this.executeSearch(searchInput ? searchInput.value.trim() : '');
                }
            } catch (err) {
                window.Toast.show(`Could not toggle favorite: ${err.message}`, 'error', 2000);
            }
        },

        /**
         * Deletes permanent entries and prompts for exclusion
         */
        async deleteClipboardEntry(id, event) {
            if (event) event.stopPropagation();
            const yes = confirm("Delete this clipboard memory permanently?");
            if (!yes) return;

            // Prompt permanent exclusion
            const exclude = confirm(
                "Would you also like to permanently EXCLUDE this text from being tracked in the future?\n\n" +
                "Click OK to permanently exclude, or Cancel to only delete this copy record."
            );

            try {
                const res = await fetch('/ai/clipboard/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id, exclude: exclude })
                });
                const data = await res.json();
                if (data.success) {
                    window.Toast.show(exclude ? 'Memory deleted and text hash excluded!' : 'Memory deleted!', 'success', 2000);
                    this.loadStats();
                    const searchInput = document.getElementById('aiSearchInput');
                    this.executeSearch(searchInput ? searchInput.value.trim() : '');
                }
            } catch (err) {
                window.Toast.show(`Deletion failed: ${err.message}`, 'error', 3000);
            }
        },

        /**
         * Clears clipboard history
         */
        async clearClipboardHistory() {
            const yes = confirm("Clear all non-favorited clipboard memory entries?");
            if (!yes) return;

            try {
                const res = await fetch('/ai/clipboard/clear', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    window.Toast.show('Clipboard history cleared!', 'success', 2000);
                    this.loadStats();
                    const searchInput = document.getElementById('aiSearchInput');
                    this.executeSearch(searchInput ? searchInput.value.trim() : '');
                }
            } catch (err) {
                window.Toast.show(`Clear failed: ${err.message}`, 'error', 3000);
            }
        },

        /**
         * Copies clipboard memory content back to the operating system clipboard
         */
        async copyEntryBack(encodedText, event) {
            if (event) event.preventDefault();
            const text = decodeURIComponent(encodedText);
            try {
                await navigator.clipboard.writeText(text);
                window.Toast.show('Copied back to clipboard!', 'success', 2000);
            } catch (err) {
                window.Toast.show('Failed to copy to clipboard', 'error', 2000);
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
         * Displays popup or toast with full indexed text details for screenshots
         * @param {number} id Screenshot ID
         */
        async viewDetails(id) {
            try {
                const res = await fetch('/ai/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: '', limit: 100, offset: 0, source: 'screenshots' })
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
