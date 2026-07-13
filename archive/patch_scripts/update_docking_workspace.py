import os

file_path = r"c:\Users\Aquib Belal\Documents\Chemistry Companion\templates\docking_workspace.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# We will inject the Job Manager UI just above the main wizard section
target_ui = """    <div x-show="errorMessage" x-cloak class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700" x-text="errorMessage"></div>
    <div x-show="statusMessage" x-cloak class="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700" x-text="statusMessage"></div>"""

new_ui = """
    <!-- DOCKING JOB MANAGER (Phase 6) -->
    <div class="mb-4 rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden" x-show="jobs.length > 0">
        <div class="flex items-center justify-between bg-slate-50 px-4 py-3 border-b border-slate-200 cursor-pointer" @click="showJobManager = !showJobManager">
            <h2 class="text-sm font-bold text-slate-800 flex items-center gap-2">
                <span>📋</span> Docking Job Manager 
                <span class="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.5 rounded-full" x-text="jobs.length + ' jobs'"></span>
            </h2>
            <button class="text-slate-500 text-xs hover:text-slate-700" x-text="showJobManager ? 'Hide' : 'Show'"></button>
        </div>
        <div x-show="showJobManager" x-cloak class="p-0">
            <div class="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100">
                <!-- Running/Queued Jobs -->
                <div class="p-4">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Active Jobs</h3>
                    <div class="space-y-2">
                        <template x-for="job in jobs.filter(j => j.status === 'running' || j.status === 'queued')" :key="job.id">
                            <div class="text-sm p-2 border border-blue-100 bg-blue-50/50 rounded flex justify-between items-center">
                                <div class="truncate pr-2">
                                    <span class="font-medium text-slate-700" x-text="job.receptor_name || 'Receptor'"></span>
                                    <div class="text-[10px] text-slate-500" x-text="job.ligand_name || 'Ligand'"></div>
                                </div>
                                <span class="flex h-2 w-2 relative">
                                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                  <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                                </span>
                            </div>
                        </template>
                        <div x-show="!jobs.some(j => j.status === 'running' || j.status === 'queued')" class="text-xs text-slate-400 italic">No active jobs.</div>
                    </div>
                </div>
                <!-- Completed Jobs -->
                <div class="p-4">
                    <h3 class="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-3">Completed</h3>
                    <div class="space-y-2 max-h-40 overflow-y-auto">
                        <template x-for="job in jobs.filter(j => j.status === 'completed')" :key="job.id">
                            <a :href="'/pose-analysis?job_id=' + job.id" class="block text-sm p-2 border border-emerald-100 bg-emerald-50/30 rounded hover:bg-emerald-50 transition-colors">
                                <div class="flex justify-between items-start">
                                    <div class="truncate pr-2">
                                        <span class="font-medium text-slate-700" x-text="job.receptor_name || 'Receptor'"></span>
                                        <div class="text-[10px] text-slate-500 truncate" x-text="job.ligand_name || 'Ligand'"></div>
                                    </div>
                                    <span class="font-mono text-emerald-600 text-xs font-bold" x-text="job.best_affinity"></span>
                                </div>
                            </a>
                        </template>
                        <div x-show="!jobs.some(j => j.status === 'completed')" class="text-xs text-slate-400 italic">No completed jobs.</div>
                    </div>
                </div>
                <!-- Failed Jobs -->
                <div class="p-4">
                    <h3 class="text-xs font-bold text-red-500 uppercase tracking-wider mb-3">Failed</h3>
                    <div class="space-y-2 max-h-40 overflow-y-auto">
                        <template x-for="job in jobs.filter(j => j.status === 'failed')" :key="job.id">
                            <div class="text-sm p-2 border border-red-100 bg-red-50/50 rounded flex justify-between items-center">
                                <div class="truncate pr-2">
                                    <span class="font-medium text-slate-700" x-text="job.receptor_name || 'Receptor'"></span>
                                    <div class="text-[10px] text-red-600 truncate" title="Job failed">Failed</div>
                                </div>
                                <span class="text-lg">❌</span>
                            </div>
                        </template>
                        <div x-show="!jobs.some(j => j.status === 'failed')" class="text-xs text-slate-400 italic">No failed jobs.</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
""" + target_ui

content = content.replace(target_ui, new_ui)

# Now let's inject Alpine state variables and fetching logic
state_vars = """        // Advanced Phase 6 Docking State
        jobs: [],
        showJobManager: true,
        pollingInterval: null,"""

if "jobs: []," not in content:
    content = content.replace("step: 1,", "step: 1,\n" + state_vars)

init_logic_old = """            if (urlWorkspaceId) {
                this.workspaceId = urlWorkspaceId;
                await this.loadWorkspace(urlWorkspaceId);
            }"""

init_logic_new = """            if (urlWorkspaceId) {
                this.workspaceId = urlWorkspaceId;
                await this.loadWorkspace(urlWorkspaceId);
            }
            
            // Start Job Manager polling
            this.fetchJobs();
            this.pollingInterval = setInterval(() => this.fetchJobs(), 5000);"""

content = content.replace(init_logic_old, init_logic_new)

fetch_method = """        async fetchJobs() {
            try {
                const res = await fetch('/api/docking/jobs?limit=20');
                if (res.ok) {
                    const data = await res.json();
                    this.jobs = data.items || [];
                }
            } catch(e) {}
        },"""

if "fetchJobs()" not in content.replace("this.fetchJobs()", ""):
    content = content.replace("goToStep(newStep) {", fetch_method + "\n\n        goToStep(newStep) {")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
