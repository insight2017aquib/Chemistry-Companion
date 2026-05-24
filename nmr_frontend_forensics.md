# NMR Frontend DOM Forensics

## Investigation
- **Target:** nalysis_results.html and spectrum_accordion.html.
- **Action:** Traced variables mapped to spectrum_data inside the Jinja loops for both NMR types.

## Findings
1. **Accordion Visibility:** The accordion parent div is successfully rendered, and the HTMX swap correctly populates the DOM. The Javascript click handlers (htmx:afterSwap) perfectly attach to .accordion-header and toggle .hidden on the content block. The accordion mechanism works.
2. **Proton Rendering Failure (
ull-safe guard issue / ield mismatch):** 
   - spectrum_accordion.html lines 13-14 iterate over spectrum_data.signals.
   - It performs sig.get('shift_ppm', 0).
   - Because shift_ppm is missing in the payload, this evaluates to None.
   - The fallback condition is not none else '—' executes. 
   - **Result:** The DOM renders — for every single Proton NMR signal.
3. **Carbon & Proton Textual Data Dropped (	emplate mismatch):**
   - The API delivers disclaimer and summary_text for both spectra.
   - spectrum_accordion.html has zero template variables to capture spectrum_data.disclaimer or spectrum_data.summary_text.
   - **Result:** The frontend entirely omits the rich heuristic warnings and text summaries, leaving a sparse, incomplete table view.
