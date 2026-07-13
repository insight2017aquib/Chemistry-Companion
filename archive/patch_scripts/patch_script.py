import os

filepath = r'c:\Users\Aquib Belal\Documents\Chemistry Companion\templates\docking_workspace.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

changes_made = 0

# 1. Fix the Molstar Overlays Layout
old_layout = '''                        <div id="protein-preview-viewer" class="molstar-preview-host rounded-md border border-slate-200">
                            <div x-show="!proteinAnalysis && !molstarLoading" class="absolute inset-0 z-10 flex items-center justify-center p-6 text-center text-sm text-slate-500">
                                Mol* will render the receptor after protein analysis.
                            </div>
                            <div x-show="molstarStatus" x-cloak class="absolute inset-x-4 top-4 z-20 rounded-md bg-white/90 p-3 text-center text-xs text-slate-600 shadow" x-text="molstarStatus"></div>
                            <div x-show="molstarError" x-cloak class="absolute inset-x-4 top-4 z-20 rounded-md border border-red-200 bg-red-50 p-3 text-center text-xs text-red-700 shadow" x-text="molstarError"></div>
                            <div x-show="showGridBox && proteinAnalysis" x-cloak class="gridbox-overlay"></div>
                            <div x-show="showPockets && selectedPocket" x-cloak class="pocket-overlay"></div>
                            <div x-show="showMissingResidues && (proteinAnalysis?.missing_residues || []).length" x-cloak class="absolute bottom-4 left-4 right-4 z-20 rounded-md border border-amber-200 bg-amber-50/95 p-3 text-xs text-amber-900 shadow">
                                Missing residues:
                                <span x-text="(proteinAnalysis?.missing_residues || []).slice(0, 4).map(m => `${m.resname || ''}${m.resnum || ''} ${m.chain_id || ''}`).join(', ')"></span>
                            </div>
                        </div>'''
new_layout = '''                        <div class="relative molstar-preview-host rounded-md border border-slate-200">
                            <!-- Overlays must be siblings to the Molstar target, not inside it, because Molstar takes full control of its container and wipes children -->
                            <div x-show="!proteinAnalysis && !molstarLoading" class="absolute inset-0 z-10 flex items-center justify-center p-6 text-center text-sm text-slate-500 bg-slate-50">
                                Mol* will render the receptor after protein analysis.
                            </div>
                            <div x-show="molstarStatus" x-cloak class="absolute inset-x-4 top-4 z-20 rounded-md bg-white/90 p-3 text-center text-xs text-slate-600 shadow" x-text="molstarStatus"></div>
                            <div x-show="molstarError" x-cloak class="absolute inset-x-4 top-4 z-20 rounded-md border border-red-200 bg-red-50 p-3 text-center text-xs text-red-700 shadow" x-text="molstarError"></div>
                            
                            <!-- The actual target for Mol* -->
                            <div id="protein-preview-viewer" class="w-full h-full absolute inset-0"></div>
                        </div>
                        <div x-show="showGridBox && proteinAnalysis" x-cloak class="gridbox-overlay"></div>
                        <div x-show="showPockets && selectedPocket" x-cloak class="pocket-overlay"></div>
                        <div x-show="showMissingResidues && (proteinAnalysis?.missing_residues || []).length" x-cloak class="absolute bottom-4 left-4 right-4 z-20 rounded-md border border-amber-200 bg-amber-50/95 p-3 text-xs text-amber-900 shadow">
                            Missing residues:
                            <span x-text="(proteinAnalysis?.missing_residues || []).slice(0, 4).map(m => `${m.resname || ''}${m.resnum || ''} ${m.chain_id || ''}`).join(', ')"></span>
                        </div>'''
if old_layout in text:
    text = text.replace(old_layout, new_layout)
    changes_made += 1
    print('1. Layout fix applied')

# 2. Add Mutex to ensureMolstarViewer
old_ensure = '''        async ensureMolstarViewer(forceRecreate = false) {
            const element = document.getElementById('protein-preview-viewer');
            if (!element) {
                this.molstarError = 'Preview container not found in DOM.';
                return null;
            }

            // If we already have a viewer but are forcing recreate (e.g. bad first render), destroy it
            if (forceRecreate && this.molstarViewer) {
                try {
                    if (this.molstarViewer?.dispose) this.molstarViewer.dispose();
                } catch (e) {}
                this.molstarViewer = null;
            }

            if (this.molstarViewer && !forceRecreate) return this.molstarViewer;

            // Force explicit size on host BEFORE layout wait, so Mol* isn't created in a zero-height container
            if (element) { element.style.height = '34rem'; element.style.minHeight = '34rem'; }

            // Robust layout wait: wait for both width and height to be reasonable.
            // The sticky + CSS grid layout on this page often needs more time than 12 frames.
            let waited = 0;
            while (waited < 25) {
                const w = element.offsetWidth || element.clientWidth || 0;
                const h = element.offsetHeight || element.clientHeight || 0;
                if (w >= 120 && h >= 120) break;
                await new Promise(r => requestAnimationFrame(r));
                waited++;
            }

            await this.ensureMolstar();

            try {
                this.molstarViewer = await window.molstar.Viewer.create(element, {
                    layoutIsExpanded: false,
                    layoutShowControls: false,
                    layoutShowRemoteState: false,
                    layoutShowSequence: false,
                    layoutShowLog: false,
                    layoutShowLeftPanel: false,
                    viewportShowControls: true,
                    viewportShowExpand: true,
                    viewportShowSelectionMode: false,
                    viewportShowAnimation: false,
                    pdbProvider: 'rcsb',
                    emdbProvider: 'rcsb',
                });
            } catch (createErr) {
                this.molstarError = 'Failed to initialize Mol* viewer: ' + (createErr?.message || createErr);
                console.error('[Mol*] Viewer.create failed:', createErr);
                return null;
            }

            // Ensure the canvas actually got a size (surgical fix for sticky/grid layout timing after analyze)
            if (this.molstarViewer?.handleResize) this.molstarViewer.handleResize();
            return this.molstarViewer;
        },'''

new_ensure = '''        async ensureMolstarViewer(forceRecreate = false) {
            // Queue-based mutex to prevent concurrent viewer creation
            while (this.__molstarViewerMutex) {
                await this.__molstarViewerMutex;
            }

            let resolveMutex;
            this.__molstarViewerMutex = new Promise(r => resolveMutex = r);

            try {
                const element = document.getElementById('protein-preview-viewer');
                if (!element) {
                    this.molstarError = 'Preview container not found in DOM.';
                    return null;
                }

                // If we already have a viewer but are forcing recreate (e.g. bad first render), destroy it
                if (forceRecreate && this.molstarViewer) {
                    try {
                        if (this.molstarViewer?.dispose) this.molstarViewer.dispose();
                    } catch (e) {}
                    this.molstarViewer = null;
                }

                if (this.molstarViewer && !forceRecreate) return this.molstarViewer;

                // Force explicit size on host BEFORE layout wait, so Mol* isn't created in a zero-height container
                if (element) { element.style.height = '100%'; element.style.width = '100%'; }

                // Robust layout wait: wait for both width and height to be reasonable.
                let waited = 0;
                while (waited < 25) {
                    const w = element.offsetWidth || element.clientWidth || 0;
                    const h = element.offsetHeight || element.clientHeight || 0;
                    if (w >= 120 && h >= 120) break;
                    await new Promise(r => requestAnimationFrame(r));
                    waited++;
                }

                await this.ensureMolstar();

                // Check again in case it was created concurrently while waiting
                if (this.molstarViewer && !forceRecreate) return this.molstarViewer;

                try {
                    this.molstarViewer = await window.molstar.Viewer.create(element, {
                        layoutIsExpanded: false,
                        layoutShowControls: false,
                        layoutShowRemoteState: false,
                        layoutShowSequence: false,
                        layoutShowLog: false,
                        layoutShowLeftPanel: false,
                        viewportShowControls: true,
                        viewportShowExpand: true,
                        viewportShowSelectionMode: false,
                        viewportShowAnimation: false,
                        pdbProvider: 'rcsb',
                        emdbProvider: 'rcsb',
                    });
                } catch (createErr) {
                    this.molstarError = 'Failed to initialize Mol* viewer: ' + (createErr?.message || createErr);
                    console.error('[Mol*] Viewer.create failed:', createErr);
                    return null;
                }

                // Ensure the canvas actually got a size (surgical fix for sticky/grid layout timing after analyze)
                if (this.molstarViewer?.handleResize) this.molstarViewer.handleResize();
                return this.molstarViewer;
            } finally {
                const r = resolveMutex;
                this.__molstarViewerMutex = null;
                r();
            }
        },'''
if old_ensure in text:
    text = text.replace(old_ensure, new_ensure)
    changes_made += 1
    print('2. Mutex applied')

# 3. Add ChimeraX button to 3D Preview header
old_preview_header = '''                        <div class="flex items-center justify-between mb-4">
                            <h2 class="text-sm font-semibold text-slate-800">3D Preview</h2>
                            <div class="flex gap-2">
                                <button type="button" @click="renderProteinPreview({forceRecreate: true})" class="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">Refresh 3D</button>'''
new_preview_header = '''                        <div class="flex items-center justify-between mb-4">
                            <h2 class="text-sm font-semibold text-slate-800">3D Preview</h2>
                            <div class="flex gap-2">
                                <button type="button" @click="openInChimeraX" class="rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 flex items-center gap-1">
                                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                                    View in ChimeraX
                                </button>
                                <button type="button" @click="renderProteinPreview({forceRecreate: true})" class="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">Refresh 3D</button>'''
if old_preview_header in text:
    text = text.replace(old_preview_header, new_preview_header)
    changes_made += 1
    print('3. ChimeraX button applied')

# 4. Strip PDBQT extra columns in getFilteredPreviewPdbText
old_filter = '''                if (isMetal) return this.showMetals;
                if (isHet && isCofactor) return this.showCofactors;
                if (isHet) return this.showLigands;
                return true;
            }).join('\\n');
        },'''
new_filter = '''                if (isMetal) return this.showMetals;
                if (isHet && isCofactor) return this.showCofactors;
                if (isHet) return this.showLigands;
                return true;
            }).map(line => {
                if (line.startsWith('ATOM') || line.startsWith('HETATM')) {
                    return line.substring(0, 80);
                }
                return line;
            }).join('\\n');
        },'''
if old_filter in text:
    text = text.replace(old_filter, new_filter)
    changes_made += 1
    print('4. PDBQT parsing fix applied')

# 5. Add openInChimeraX JS method
old_clear = '''        async clearMolstarScene() {
            if (this.molstarViewer?.plugin?.clear) {
                try {
                    await this.molstarViewer.plugin.clear();
                } catch (e) {}
            }
        },'''
new_clear = '''        async clearMolstarScene() {
            if (this.molstarViewer?.plugin?.clear) {
                try {
                    await this.molstarViewer.plugin.clear();
                } catch (e) {}
            }
        },

        async openInChimeraX() {
            const pdbText = this.getFilteredPreviewPdbText();
            if (!pdbText) {
                alert('No protein loaded.');
                return;
            }
            try {
                const response = await fetch('/api/receptor/launch_chimera', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pdb_text: pdbText })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Failed to open in ChimeraX');
            } catch (err) {
                alert('Could not open ChimeraX: ' + err.message);
            }
        },'''
if old_clear in text:
    text = text.replace(old_clear, new_clear)
    changes_made += 1
    print('5. openInChimeraX function applied')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Total changes applied: {changes_made}')
