// Utility Functions for Chemistry Companion

/**
 * Show a toast notification
 * @param {string} message - Notification message
 * @param {string} type - 'success', 'error', 'info' (default: 'info')
 * @param {number} duration - How long to show (ms, default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast border rounded-lg p-4 shadow-lg flex items-start gap-3 max-w-sm ${type}`;
    
    const icons = {
        success: '✓',
        error: '✕',
        info: 'ℹ'
    };

    toast.innerHTML = `
        <span class="text-xl flex-shrink-0">${icons[type] || icons.info}</span>
        <span class="text-sm">${escapeHtml(message)}</span>
        <button onclick="this.closest('.toast').remove()" class="ml-auto text-lg cursor-pointer hover:opacity-70">×</button>
    `;

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Format numbers nicely
 */
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'number') {
        return value.toFixed(decimals);
    }
    return value;
}

/**
 * Fetch with error handling
 */
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Create a table from data
 */
function createTable(columns, rows) {
    const table = document.createElement('table');
    table.className = 'w-full border-collapse';

    // Header
    const thead = document.createElement('thead');
    thead.className = 'bg-slate-50 border-b border-slate-200';
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        th.className = 'px-4 py-2 text-left text-sm font-semibold text-slate-900 text-xs uppercase';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-slate-200 hover:bg-slate-50 transition-colors';
        Object.values(row).forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            td.className = 'px-4 py-2 text-sm text-slate-700';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    return table;
}

/**
 * Create a property card
 */
function createPropertyCard(label, value, unit = '', icon = '') {
    const card = document.createElement('div');
    card.className = 'bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg p-4 border border-slate-200';
    
    card.innerHTML = `
        ${icon ? `<div class="text-2xl mb-2">${icon}</div>` : ''}
        <div class="text-xs font-semibold text-slate-600 uppercase tracking-wider">${escapeHtml(label)}</div>
        <div class="text-xl font-bold text-slate-900 mt-1">${formatNumber(value)}${unit ? ' ' + unit : ''}</div>
    `;
    
    return card;
}

/**
 * Create a functional group badge
 */
function createFunctionalGroupBadge(name, count) {
    const badge = document.createElement('span');
    badge.className = 'inline-block bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium border border-blue-300 mr-2 mb-2';
    badge.textContent = `${escapeHtml(name)} (${count})`;
    return badge;
}

/**
 * Download file
 */
function downloadFile(content, filename, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Debounce function for search/input
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Copy to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success', 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        showToast('Failed to copy', 'error');
    }
}

/**
 * Format SMILES for display
 */
function formatSMILES(smiles) {
    if (!smiles) return 'N/A';
    return `<code class="bg-slate-100 px-2 py-1 rounded font-mono text-xs">${escapeHtml(smiles)}</code>`;
}

/**
 * Get color for intensity
 */
function getIntensityColor(intensity) {
    const colors = {
        'strong': '#dc2626',
        'medium': '#f59e0b',
        'weak': '#6b7280',
        'broad': '#3b82f6'
    };
    return colors[intensity] || '#6b7280';
}

/**
 * Render spectral table
 */
function renderSpectralTable(data, columns) {
    const table = document.createElement('table');
    table.className = 'w-full text-sm border-collapse';

    const thead = document.createElement('thead');
    thead.className = 'bg-slate-100 border-b-2 border-slate-300';
    const headerRow = document.createElement('tr');

    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.label;
        th.className = 'px-4 py-2 text-left font-semibold text-slate-900';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    if (Array.isArray(data)) {
        data.forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = idx % 2 ? 'bg-slate-50' : 'bg-white';
            tr.addEventListener('mouseenter', () => tr.classList.add('bg-blue-50'));
            tr.addEventListener('mouseleave', () => tr.classList.toggle('bg-slate-50', idx % 2));

            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row[col.key];
                
                if (col.format) {
                    td.innerHTML = col.format(value);
                } else if (typeof value === 'number') {
                    td.textContent = formatNumber(value, col.decimals || 2);
                } else {
                    td.textContent = value || '—';
                }
                
                td.className = 'px-4 py-2 text-slate-700';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }
    table.appendChild(tbody);

    return table;
}

/**
 * Show loading skeleton
 */
function showSkeleton(element, count = 5) {
    element.innerHTML = '';
    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'bg-slate-200 h-12 rounded mb-2 animate-pulse';
        element.appendChild(skeleton);
    }
}

/** Spectrum tab switcher (analysis results partial) */
function showSpectrumTab(name) {
    ['ir', 'hnmr', 'cnmr'].forEach((tab) => {
        const panel = document.getElementById('panel-' + tab);
        const btn = document.getElementById('tab-' + tab);
        if (panel) panel.classList.toggle('hidden', tab !== name);
        if (btn) {
            btn.classList.toggle('border-sci-blue', tab === name);
            btn.classList.toggle('text-sci-blue', tab === name);
            btn.classList.toggle('border-transparent', tab !== name);
            btn.classList.toggle('text-slate-500', tab !== name);
        }
    });
}

// HTMX Event Handlers
if (document.body) {
    document.body.addEventListener('htmx:responseError', (evt) => {
        console.error('HTMX Error:', evt.detail);
        showToast('Request failed. Please try again.', 'error');
    });

    document.body.addEventListener('htmx:error', (evt) => {
        console.error('HTMX Error:', evt.detail);
        showToast('An error occurred. Please try again.', 'error');
    });
}
