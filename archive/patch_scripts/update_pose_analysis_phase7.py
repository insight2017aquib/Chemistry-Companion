import os

file_path = r"c:\Users\Aquib Belal\Documents\Chemistry Companion\templates\pose_analysis.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Old panel block
old_panel_start = content.find("<!-- LLM Explanation Panel (HTMX-powered) -->")
old_panel_end = content.find("</div>\n\n        </div>\n    </div>\n</div>")

if old_panel_start != -1 and old_panel_end != -1:
    old_panel = content[old_panel_start:old_panel_end]

    new_panel = """<!-- AI Docking Expert Panel (Phase 7) -->
            <div class="card p-0 border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-900 shadow-sm" x-data="{ expertTab: 'pose' }">
                <!-- Header & Tabs -->
                <div class="bg-indigo-50/50 dark:bg-indigo-900/10 p-4 border-b border-indigo-100 dark:border-indigo-800">
                    <h2 class="text-lg font-bold text-indigo-900 dark:text-indigo-300 flex items-center gap-2 mb-4">
                        <span>🤖</span> AI Docking Expert
                    </h2>
                    
                    <div class="flex flex-wrap gap-2 text-sm font-medium">
                        <button @click="expertTab = 'pose'" :class="expertTab === 'pose' ? 'bg-indigo-600 text-white shadow' : 'bg-white text-indigo-600 hover:bg-indigo-50 border border-indigo-200'" class="px-3 py-1.5 rounded transition-colors">
                            Explain Pose
                        </button>
                        <button @click="expertTab = 'compare'" :class="expertTab === 'compare' ? 'bg-blue-600 text-white shadow' : 'bg-white text-blue-600 hover:bg-blue-50 border border-blue-200'" class="px-3 py-1.5 rounded transition-colors" :disabled="selectedPoses.length < 2">
                            Compare Poses
                        </button>
                        <button @click="expertTab = 'improve'" :class="expertTab === 'improve' ? 'bg-emerald-600 text-white shadow' : 'bg-white text-emerald-600 hover:bg-emerald-50 border border-emerald-200'" class="px-3 py-1.5 rounded transition-colors">
                            Suggest Improvements
                        </button>
                        <button @click="expertTab = 'report'" :class="expertTab === 'report' ? 'bg-purple-600 text-white shadow' : 'bg-white text-purple-600 hover:bg-purple-50 border border-purple-200'" class="px-3 py-1.5 rounded transition-colors">
                            Generate Report
                        </button>
                    </div>
                </div>

                <!-- Action Area -->
                <div class="p-5">
                    <!-- Tab Forms -->
                    <div class="mb-4 flex items-center justify-between">
                        <div class="text-sm text-slate-500">
                            <span x-show="expertTab === 'pose'">Analyze the interactions and binding mode of the selected pose.</span>
                            <span x-show="expertTab === 'compare'">Highlight structural and energetic differences between selected poses.</span>
                            <span x-show="expertTab === 'improve'">Get text-based SAR and medicinal chemistry optimization advice.</span>
                            <span x-show="expertTab === 'report'">Synthesize a comprehensive Markdown report for this docking run.</span>
                        </div>
                        
                        <!-- Dynamic HTMX Forms based on Tab -->
                        <div>
                            <!-- Explain Pose Form -->
                            <form x-show="expertTab === 'pose'" hx-post="/api/llm/expert/pose" hx-target="#expert-result" hx-swap="innerHTML" hx-indicator="#expert-spinner">
                                <input type="hidden" name="smiles" :value="ligandSmiles">
                                <input type="hidden" name="poses_json" :value="JSON.stringify(selectedPoses)">
                                <input type="hidden" name="interactions_json" :value="JSON.stringify(poseInteractions)">
                                <button type="submit" class="btn-primary bg-indigo-600 hover:bg-indigo-700" :disabled="selectedPoses.length === 0">Analyze</button>
                            </form>
                            
                            <!-- Compare Poses Form -->
                            <form x-show="expertTab === 'compare'" hx-post="/api/llm/expert/compare" hx-target="#expert-result" hx-swap="innerHTML" hx-indicator="#expert-spinner">
                                <input type="hidden" name="smiles" :value="ligandSmiles">
                                <input type="hidden" name="poses_json" :value="JSON.stringify(selectedPoses)">
                                <input type="hidden" name="interactions_json" :value="JSON.stringify(poseInteractions)">
                                <button type="submit" class="btn-primary bg-blue-600 hover:bg-blue-700" :disabled="selectedPoses.length < 2">Compare</button>
                            </form>

                            <!-- Suggest Improvements Form -->
                            <form x-show="expertTab === 'improve'" hx-post="/api/llm/expert/improve" hx-target="#expert-result" hx-swap="innerHTML" hx-indicator="#expert-spinner">
                                <input type="hidden" name="smiles" :value="ligandSmiles">
                                <input type="hidden" name="poses_json" :value="JSON.stringify(selectedPoses)">
                                <input type="hidden" name="interactions_json" :value="JSON.stringify(poseInteractions)">
                                <button type="submit" class="btn-primary bg-emerald-600 hover:bg-emerald-700" :disabled="selectedPoses.length === 0">Improve</button>
                            </form>

                            <!-- Generate Report Form -->
                            <form x-show="expertTab === 'report'" hx-post="/api/llm/expert/report" hx-target="#expert-result" hx-swap="innerHTML" hx-indicator="#expert-spinner">
                                <input type="hidden" name="poses_json" :value="JSON.stringify(poses)">
                                <input type="hidden" name="interactions_json" :value="JSON.stringify(poseInteractions)">
                                <input type="hidden" name="metadata_json" :value="JSON.stringify(jobMetadata || {})">
                                <button type="submit" class="btn-primary bg-purple-600 hover:bg-purple-700">Generate</button>
                            </form>
                        </div>
                    </div>

                    <!-- Spinner -->
                    <div id="expert-spinner" class="htmx-indicator flex flex-col items-center justify-center py-8 text-indigo-400 space-y-4">
                        <svg class="animate-spin h-8 w-8" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span class="text-sm font-medium">Expert is analyzing the structural data...</span>
                    </div>

                    <!-- Results Area -->
                    <div id="expert-result" class="bg-slate-50 dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800 p-6 min-h-[200px]">
                        <div class="text-center text-slate-400 py-8">
                            <div class="text-3xl mb-3 opacity-50">🔬</div>
                            <p class="text-sm">Select a tab and click the action button to generate an expert analysis.</p>
                            <p class="text-xs mt-2 text-slate-300">Analysis strictly bound to calculated geometric constraints.</p>
                        </div>
                    </div>
                </div>
            </div>"""

    content = content.replace(old_panel, new_panel)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
