/**
 * Chemistry Companion — App shell (theme, sidebar, command palette)
 */

function appShell() {
  return {
    sidebarCollapsed: localStorage.getItem('cc-sidebar-collapsed') === 'true',
    mobileSidebarOpen: false,
    commandOpen: false,
    commandQuery: '',

    init() {
      this.applyTheme();
      document.addEventListener('keydown', (e) => this.onKeydown(e));
    },

    applyTheme() {
      const root = document.documentElement;
      const theme = localStorage.getItem('cc-theme') || 'dark';
      root.classList.toggle('dark', theme === 'dark');
      root.classList.toggle('light', theme === 'light');
    },

    toggleTheme() {
      const root = document.documentElement;
      const next = root.classList.contains('dark') ? 'light' : 'dark';
      root.classList.toggle('dark', next === 'dark');
      root.classList.toggle('light', next === 'light');
      localStorage.setItem('cc-theme', next);
    },

    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      localStorage.setItem('cc-sidebar-collapsed', this.sidebarCollapsed);
    },

    toggleMobileSidebar() {
      this.mobileSidebarOpen = !this.mobileSidebarOpen;
    },

    openCommand() {
      this.commandOpen = true;
      this.commandQuery = '';
      this.$nextTick(() => this.$refs.commandInput?.focus());
    },

    closeCommand() {
      this.commandOpen = false;
    },

    onKeydown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.commandOpen ? this.closeCommand() : this.openCommand();
      }
      if (e.key === 'Escape') {
        this.closeCommand();
        this.mobileSidebarOpen = false;
      }
    },

    navCommands() {
      return [
        { label: 'Dashboard', href: '/', icon: '⌂' },
        { label: 'Single Analysis', href: '/analysis', icon: '⚗' },
        { label: 'Batch Analysis', href: '/batch', icon: '▤' },
        { label: 'Spectral Analysis', href: '/spectra', icon: '〰' },
        { label: 'History', href: '/history', icon: '◷' },
        { label: 'Exports', href: '/exports', icon: '↓' },
        { label: 'Validation', href: '/validation', icon: '✓' },
        { label: 'Settings', href: '/settings', icon: '⚙' },
        { label: 'Documentation', href: '/docs', icon: '?' },
      ].filter((c) =>
        !this.commandQuery ||
        c.label.toLowerCase().includes(this.commandQuery.toLowerCase())
      );
    },
  };
}

/** Spectrum tab switcher */
function showSpectrumTab(name) {
  ['ir', 'hnmr', 'cnmr'].forEach((tab) => {
    const panel = document.getElementById('panel-' + tab);
    const btn = document.getElementById('tab-' + tab);
    if (panel) panel.classList.toggle('hidden', tab !== name);
    if (btn) {
      btn.classList.toggle('cc-tab-active', tab === name);
      btn.classList.toggle('cc-tab-inactive', tab !== name);
    }
  });
  if (name === 'ir' && typeof renderIRPlot === 'function') renderIRPlot();
  if (name === 'hnmr' && typeof renderHNMRPlot === 'function') renderHNMRPlot();
}

const CC_EXPORT_HISTORY_KEY = 'cc-export-history';

function getExportData() {
  const el = document.getElementById('analysis-export-data');
  if (!el || !el.textContent.trim()) return null;
  return JSON.parse(el.textContent);
}

function readExportHistory() {
  try {
    return JSON.parse(localStorage.getItem(CC_EXPORT_HISTORY_KEY) || '[]');
  } catch (_) {
    return [];
  }
}

function saveExportHistory(item) {
  const history = readExportHistory();
  const next = [{ id: Date.now(), ...item }, ...history].slice(0, 12);
  localStorage.setItem(CC_EXPORT_HISTORY_KEY, JSON.stringify(next));
  return next;
}

async function previewExport(profile) {
  const data = getExportData();
  if (!data) return null;
  const response = await fetch('/api/export/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data, format: 'xlsx', profile: profile || 'full' }),
  });
  if (!response.ok) throw new Error('Preview failed');
  return response.json();
}

function exportModal() {
  return {
    open: false,
    profile: localStorage.getItem('cc-export-profile') || 'full',
    preview: null,
    previewReady: false,
    history: [],
    busy: false,
    progress: 0,
    statusText: 'Preparing',

    openModal() {
      this.open = true;
      this.history = readExportHistory();
      this.refreshPreview();
    },

    async refreshPreview() {
      localStorage.setItem('cc-export-profile', this.profile);
      try {
        this.preview = await previewExport(this.profile);
        this.previewReady = !!this.preview;
      } catch (_) {
        this.preview = null;
        this.previewReady = false;
      }
    },

    startExport(format) {
      exportAnalysis(format, this.profile);
    },

    onExportStart(event) {
      this.busy = true;
      this.progress = 8;
      this.statusText = `Preparing ${event.detail.format.toUpperCase()}`;
    },

    onExportProgress(event) {
      this.progress = event.detail.progress;
      this.statusText = 'Downloading';
    },

    onExportComplete(event) {
      this.busy = false;
      this.progress = 100;
      this.statusText = 'Complete';
      this.history = readExportHistory();
      this.refreshPreview();
      setTimeout(() => { this.progress = 0; }, 1400);
    },

    onExportError() {
      this.busy = false;
      this.statusText = 'Export failed';
    },
  };
}

/** Export via API */
async function exportAnalysis(format, profile) {
  let data;
  try {
    data = getExportData();
  } catch (err) {
    console.error(err);
  }
  if (!data) {
    if (typeof showToast === 'function') showToast('No analysis data to export', 'error');
    return;
  }

  const selectedProfile = profile || localStorage.getItem('cc-export-profile') || 'full';
  window.dispatchEvent(new CustomEvent('cc-export-start', { detail: { format, profile: selectedProfile } }));

  try {
    const body = { data, format, profile: selectedProfile };
    const response = await fetch('/api/export/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());

    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `export.${format}`;
    const total = Number(response.headers.get('Content-Length') || 0);
    let received = 0;
    let blob;

    if (response.body && response.body.getReader) {
      const reader = response.body.getReader();
      const chunks = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.length;
        const progress = total ? Math.min(98, Math.round((received / total) * 100)) : 85;
        window.dispatchEvent(new CustomEvent('cc-export-progress', { detail: { progress } }));
      }
      blob = new Blob(chunks, { type: response.headers.get('Content-Type') || 'application/octet-stream' });
    } else {
      blob = await response.blob();
      window.dispatchEvent(new CustomEvent('cc-export-progress', { detail: { progress: 90 } }));
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
    const history = saveExportHistory({
      filename,
      format,
      profile: selectedProfile,
      createdAt: new Date().toISOString(),
    });
    window.dispatchEvent(new CustomEvent('cc-export-complete', { detail: { filename, history } }));
    if (typeof showToast === 'function') showToast(`Exported ${format.toUpperCase()}`, 'success');
  } catch (err) {
    console.error(err);
    window.dispatchEvent(new CustomEvent('cc-export-error', { detail: { error: String(err) } }));
    if (typeof showToast === 'function') showToast('Export failed', 'error');
  }
}

function openExportModal() {
  window.dispatchEvent(new CustomEvent('cc-open-export-modal'));
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('.export-btn');
  if (btn?.dataset.format) exportAnalysis(btn.dataset.format, btn.dataset.profile);
});

/** Plotly IR stick spectrum from embedded JSON */
function renderIRPlot() {
  const el = document.getElementById('ir-plot-data');
  const target = document.getElementById('ir-plot');
  if (!el || !target || typeof Plotly === 'undefined') return;
  const bands = JSON.parse(el.textContent || '[]');
  if (!bands.length) return;
  const xs = [], ys = [], labels = [];
  bands.forEach((b) => {
    const low = b.lower_cm1 || b.low_cm || 0;
    const high = b.upper_cm1 || b.high_cm || low;
    const mid = (low + high) / 2;
    const h = b.intensity === 'strong' ? 1 : b.intensity === 'medium' ? 0.6 : 0.35;
    xs.push(mid, mid, null);
    ys.push(0, h, null);
    labels.push(b.label || '');
  });
  Plotly.newPlot(target, [{
    x: xs, y: ys, mode: 'lines',
    line: { color: '#6366f1', width: 2 },
    hoverinfo: 'skip',
  }], {
    margin: { t: 24, r: 16, b: 40, l: 48 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#94a3b8', size: 11 },
    xaxis: { title: 'Wavenumber (cm⁻¹)', autorange: 'reversed', gridcolor: 'rgba(148,163,184,0.1)' },
    yaxis: { title: 'Rel. intensity', showticklabels: false, gridcolor: 'rgba(148,163,184,0.1)' },
  }, { responsive: true, displayModeBar: false });
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    if (typeof showToast === 'function') showToast('Copied', 'success', 1500);
  });
}
