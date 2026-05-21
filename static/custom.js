// static/custom.js
// Additional JavaScript functionality for Chemistry Companion

// Utility functions
const ChemistryUtils = {
    // Validate SMILES string (basic check)
    validateSMILES: function(smiles) {
        if (!smiles || typeof smiles !== 'string') return false;

        // Basic validation - check for common atoms and bonds
        const validChars = /^[A-Za-z0-9\[\]\(\)\=\-\+\#\@\$\%\*\.\/\\]+$/;
        return validChars.test(smiles) && smiles.length > 0 && smiles.length < 200;
    },

    // Format molecule name for display
    formatMoleculeName: function(name, smiles) {
        if (name && name.trim()) {
            return name.trim();
        }
        return `Molecule (${smiles.substring(0, 20)}${smiles.length > 20 ? '...' : ''})`;
    },

    // Copy text to clipboard
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showNotification('Copied to clipboard!', 'success');
        }
    },

    // Show notification
    showNotification: function(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-4 py-2 rounded-md text-white text-sm font-medium z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            'bg-blue-500'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    },

    // Debounce function for input handling
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// Enhanced form validation
document.addEventListener('DOMContentLoaded', function() {
    // SMILES input validation
    const smilesInputs = document.querySelectorAll('input[name="smiles"], textarea[name="molecules"]');
    smilesInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !ChemistryUtils.validateSMILES(this.value)) {
                this.classList.add('error-border');
                ChemistryUtils.showNotification('Invalid SMILES string format', 'error');
            } else {
                this.classList.remove('error-border');
            }
        });
    });

    // Auto-format molecule names
    const nameInputs = document.querySelectorAll('input[name="name"]');
    nameInputs.forEach(input => {
        const smilesInput = input.closest('form').querySelector('input[name="smiles"]');
        if (smilesInput) {
            smilesInput.addEventListener('input', ChemistryUtils.debounce(function() {
                if (!input.value && this.value) {
                    input.placeholder = ChemistryUtils.formatMoleculeName('', this.value);
                }
            }, 500));
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit forms
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeForm = document.activeElement.closest('form');
            if (activeForm) {
                e.preventDefault();
                const submitButton = activeForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.click();
                }
            }
        }

        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('search');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            }
        }
    });

    // Copy buttons for SMILES strings
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('copy-smiles') || e.target.closest('.copy-smiles')) {
            const button = e.target.classList.contains('copy-smiles') ? e.target : e.target.closest('.copy-smiles');
            const smiles = button.dataset.smiles;
            if (smiles) {
                ChemistryUtils.copyToClipboard(smiles);
            }
        }
    });

    // Enhanced loading states
    document.addEventListener('htmx:beforeRequest', function(e) {
        const target = e.target;
        if (target) {
            target.style.position = 'relative';
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div>';
            target.appendChild(overlay);
        }
    });

    document.addEventListener('htmx:afterRequest', function(e) {
        const target = e.target;
        if (target) {
            const overlay = target.querySelector('.loading-overlay');
            if (overlay) {
                overlay.remove();
            }
        }
    });

    // Auto-save form state
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const formId = form.id || form.action || 'form';
        const savedState = localStorage.getItem(`chemistry_form_${formId}`);

        if (savedState) {
            try {
                const data = JSON.parse(savedState);
                Object.keys(data).forEach(key => {
                    const input = form.querySelector(`[name="${key}"]`);
                    if (input) {
                        if (input.type === 'checkbox') {
                            input.checked = data[key];
                        } else {
                            input.value = data[key];
                        }
                    }
                });
            } catch (e) {
                console.warn('Failed to restore form state:', e);
            }
        }

        // Save state on change
        form.addEventListener('input', ChemistryUtils.debounce(function() {
            const formData = new FormData(form);
            const data = {};
            for (let [key, value] of formData.entries()) {
                const input = form.querySelector(`[name="${key}"]`);
                if (input && input.type === 'checkbox') {
                    data[key] = input.checked;
                } else {
                    data[key] = value;
                }
            }
            localStorage.setItem(`chemistry_form_${formId}`, JSON.stringify(data));
        }, 1000));
    });
});

// Export utilities for global access
window.ChemistryUtils = ChemistryUtils;