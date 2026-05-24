// Alpine.js component for Docking Workspace
document.addEventListener('alpine:init', () => {
    Alpine.data('dockingWorkspace', () => ({
        proteinFile: null,
        removeWater: true,
        addCharges: true,
        proteinLog: '',
        proteinPdbqt: '',
        
        ligandSmiles: '',
        ligandLog: '',
        ligandPdbqt: '',
        
        loading: false,
        dockingReport: null,
        
        get canRun() {
            return this.proteinPdbqt && this.ligandPdbqt;
        },
        
        uploadProtein(e) {
            this.proteinFile = e.target.files[0];
            this.proteinLog = `Loaded: ${this.proteinFile.name}\nReady to prepare.`;
        },
        
        async prepareProtein() {
            if (!this.proteinFile) return;
            this.loading = true;
            this.proteinLog = "Reading file...";
            
            try {
                const text = await this.proteinFile.text();
                this.proteinLog = "Sending to server for OpenBabel preparation...";
                
                const res = await fetch('/api/docking/protein_prepare', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        pdb_text: text,
                        remove_water: this.removeWater,
                        add_charges: this.addCharges
                    })
                });
                
                if (!res.ok) throw new Error(await res.text());
                const data = await res.json();
                this.proteinPdbqt = data.pdbqt;
                this.proteinLog = `Success! Generated PDBQT (${this.proteinPdbqt.length} bytes)`;
            } catch (e) {
                this.proteinLog = `Error: ${e.message}`;
            }
            this.loading = false;
        },
        
        async prepareLigand() {
            if (!this.ligandSmiles) return;
            this.loading = true;
            this.ligandLog = "Generating 3D structure and PDBQT...";
            
            try {
                // We use the existing structure generation endpoint from core/docking_preparation
                // In the real implementation, we would call a specific endpoint, but we mock it here.
                // Assuming we have a /api/docking/generate from earlier that takes smiles
                // For this UI mockup, we will just simulate success.
                await new Promise(r => setTimeout(r, 1000));
                this.ligandPdbqt = "MOCK PDBQT DATA\nATOM 1 C...\n";
                this.ligandLog = "Success! Ligand ready for docking.";
            } catch (e) {
                this.ligandLog = `Error: ${e.message}`;
            }
            this.loading = false;
        },
        
        async runDocking() {
            if (!this.canRun) return;
            this.loading = true;
            this.dockingReport = null;
            
            try {
                const res = await fetch('/api/docking/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        protein_pdbqt: this.proteinPdbqt,
                        ligand_pdbqt: this.ligandPdbqt,
                        center_x: 0, center_y: 0, center_z: 0, // Mock auto-center
                        size_x: 20, size_y: 20, size_z: 20,
                        exhaustiveness: 8,
                        num_modes: 9
                    })
                });
                
                if (!res.ok) throw new Error(await res.text());
                const data = await res.json();
                this.dockingReport = data.report;
            } catch (e) {
                alert(`Docking failed: ${e.message}`);
            }
            this.loading = false;
        }
    }));
});
