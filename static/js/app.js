// Chemistry Companion - Main Application Logic

class ChemistryApp {
    constructor() {
        this.currentAnalysis = null;
        this.currentBatchJob = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkHealth();
    }

    setupEventListeners() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    async checkHealth() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            console.log('Health check:', data);
        } catch (error) {
            console.error('Health check failed:', error);
            showToast('Connection to server failed', 'error');
        }
    }

    /**
     * Analyze a single molecule
     */
    async analyzeMolecule(input, method = 'smiles') {
        try {
            const payload = {
                molecule: {
                    [method]: input
                },
                include_spectra: true,
                save_image: false
            };

            const response = await fetchAPI('/api/analyze', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            this.currentAnalysis = response;
            return response;

        } catch (error) {
            console.error('Analysis error:', error);
            throw error;
        }
    }

    /**
     * Get IR prediction for molecule
     */
    async predictIR(smiles) {
        try {
            const response = await fetchAPI('/api/ir', {
                method: 'POST',
                body: JSON.stringify({ smiles })
            });
            return response;
        } catch (error) {
            console.error('IR prediction error:', error);
            throw error;
        }
    }

    /**
     * Get 1H NMR prediction
     */
    async predictProtonNMR(smiles) {
        try {
            const response = await fetchAPI('/api/hnmr', {
                method: 'POST',
                body: JSON.stringify({ smiles })
            });
            return response;
        } catch (error) {
            console.error('Proton NMR error:', error);
            throw error;
        }
    }

    /**
     * Get 13C NMR prediction
     */
    async predictCarbonNMR(smiles) {
        try {
            const response = await fetchAPI('/api/cnmr', {
                method: 'POST',
                body: JSON.stringify({ smiles })
            });
            return response;
        } catch (error) {
            console.error('Carbon NMR error:', error);
            throw error;
        }
    }

    /**
     * Process batch of molecules
     */
    async processBatch(file, options = {}) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            if (options.include_spectra !== undefined) {
                formData.append('include_spectra', options.include_spectra ? 'true' : 'false');
            }

            const response = await fetch('/api/batch/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Batch processing failed: ${response.statusText}`);
            }

            this.currentBatchJob = await response.json();
            return this.currentBatchJob;

        } catch (error) {
            console.error('Batch processing error:', error);
            throw error;
        }
    }

    /**
     * Export analysis results
     */
    async exportResults(format) {
        if (!this.currentAnalysis) {
            showToast('No analysis to export', 'error');
            return;
        }

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    data: this.currentAnalysis,
                    format: format
                })
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const timestamp = new Date().toISOString().split('T')[0];
            const filename = `chemistry-companion-${timestamp}.${format}`;
            downloadFile(blob, filename);
            showToast(`Exported as ${format.toUpperCase()}`, 'success');

        } catch (error) {
            console.error('Export error:', error);
            showToast('Export failed', 'error');
        }
    }

    /**
     * Load analysis history
     */
    async loadHistory() {
        try {
            const response = await fetchAPI('/api/history');
            return response;
        } catch (error) {
            console.error('History error:', error);
            throw error;
        }
    }

    /**
     * Save analysis to history
     */
    async saveToHistory(analysis) {
        console.warn('saveToHistory is not available via API; history is saved automatically during analysis.');
        return null;
    }

    closeModals() {
        // Close any open modals
        document.querySelectorAll('[role="dialog"]').forEach(modal => {
            modal.style.display = 'none';
        });
    }
}

// Initialize app when DOM is ready
const app = new ChemistryApp();

// Utility function for rendering analysis results
function renderAnalysisResults(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    // Molecular Properties Grid
    const propsSection = document.createElement('section');
    propsSection.className = 'mb-8';
    propsSection.innerHTML = '<h2 class="text-xl font-bold mb-4">Molecular Properties</h2>';

    const propsGrid = document.createElement('div');
    propsGrid.className = 'grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3';

    const props = [
        { label: 'Formula', key: 'formula', icon: '⚛️' },
        { label: 'MW', key: 'molecular_weight', icon: '⚖️', decimals: 2 },
        { label: 'LogP', key: 'logp', icon: '🧪', decimals: 2 },
        { label: 'TPSA', key: 'tpsa', icon: '📐', decimals: 1 },
        { label: 'HBD', key: 'hbd', icon: '🔗' },
        { label: 'HBA', key: 'hba', icon: '🔗' },
    ];

    props.forEach(prop => {
        const value = data.descriptors?.[prop.key];
        if (value !== undefined && value !== null) {
            propsGrid.appendChild(createPropertyCard(prop.label, value, '', prop.icon));
        }
    });

    propsSection.appendChild(propsGrid);
    container.appendChild(propsSection);

    // Functional Groups Section
    if (data.functional_groups && data.functional_groups.names && data.functional_groups.names.length > 0) {
        const fgSection = document.createElement('section');
        fgSection.className = 'mb-8';
        fgSection.innerHTML = '<h2 class="text-xl font-bold mb-4">Functional Groups</h2>';

        const fgContainer = document.createElement('div');
        fgContainer.className = 'flex flex-wrap gap-2';

        data.functional_groups.names.forEach((name, idx) => {
            const count = data.functional_groups.counts?.[name] || 1;
            const badge = document.createElement('span');
            badge.className = 'inline-block bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium';
            badge.textContent = `${name} (${count})`;
            fgContainer.appendChild(badge);
        });

        fgSection.appendChild(fgContainer);
        container.appendChild(fgSection);
    }
}

// Export for use in other scripts
window.ChemistryApp = ChemistryApp;
window.renderAnalysisResults = renderAnalysisResults;

// Live resolution helper for the analysis form
function debounce(fn, wait) {
    let t = null;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

async function resolveInputLive(text) {
    try {
        const resp = await fetch('/api/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input_text: text })
        });
        return await resp.json();
    } catch (err) {
        return { success: false, error: String(err) };
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const ta = document.getElementById('input_text');
    const preview = document.getElementById('structure-preview');
    if (!ta || !preview) return;

    const update = debounce(async () => {
        const text = ta.value.trim();
        if (!text) {
            preview.textContent = 'Enter SMILES for instant preview';
            return;
        }
        preview.textContent = 'Resolving...';
        const info = await resolveInputLive(text);
        if (!info.success) {
            preview.textContent = `Error: ${info.error || 'Could not resolve input'}`;
            return;
        }
        preview.innerHTML = `Detected: <strong>${info.detected_type || 'unknown'}</strong><br>SMILES: <code>${info.canonical_smiles || ''}</code><br>Source: ${info.source || ''}`;
    }, 350);

    ta.addEventListener('input', update);
});

