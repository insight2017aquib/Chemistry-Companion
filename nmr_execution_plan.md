# NMR GUI Execution Plan

## Root Cause Verification
The forensic probes conclusively prove that the incompleteness of the NMR frontend is due strictly to **template mismatch** and **field drift** in 	emplates/components/spectrum_accordion.html, and completely unrelated to the backend engine, prediction logic, serialization, or API transport.

## Files to Modify
1. 	emplates/components/spectrum_accordion.html (ONLY)

## Risk Level
**LOW.** The modification is strictly bounded to the GUI template that renders the HTMX response.

## Rollback Plan
A simple git checkout -- templates/components/spectrum_accordion.html will revert all changes if any collateral breakage occurs.

## Frontend Changes
1. Add <p class="text-xs text-amber-700 mb-4">{{ spectrum_data.disclaimer }}</p> immediately before the data tables to render the context string.
2. Add <p class="mt-4 text-sm text-slate-600">{{ spectrum_data.summary_text }}</p> immediately after the data tables to render the summary string.
3. For Proton NMR (spectrum_type == '1h'), replace the sig.get('shift_ppm') access with conditional logic for sig.get('ppm_range') or sig.get('ppm_mid').

## Backend Changes
**NONE.**

## Justification
Backend payload generation and frontend payload ingestion are operating perfectly. The frontend merely fails to render the data it is handed due to hardcoded field names and missing layout elements. Making precise adjustments to the generic spectrum_accordion.html directly aligns the frontend with the established API schema without touching unrelated infrastructure.
