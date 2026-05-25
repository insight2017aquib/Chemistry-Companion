# NMR Root Cause Report

Based on the evidence-driven probe, the root cause for the incomplete Proton and Carbon NMR frontends falls into two distinct categories of template mismatches:

## 1. Field Drift in Proton NMR Rendering
- **Allowed Cause Match:** ield drift / 	emplate mismatch
- **Proof:** The backend (ProtonSignal) computes and serializes the chemical shift range as ppm_range and ppm_mid. However, the frontend (spectrum_accordion.html lines 14-15) expects sig.get('shift_ppm'). Because shift_ppm is entirely absent from the serialized JSON payload, the Jinja template condition sig.get('shift_ppm') is not none fails, defaulting to rendering — for every signal. The data is present, but perfectly invisible due to a field mismatch.

## 2. Missing Payload Rendering for Both NMR Types
- **Allowed Cause Match:** 	emplate mismatch
- **Proof:** Both proton_nmr_prediction and carbon_nmr_prediction serialized payloads contain a disclaimer string and a summary_text string outlining the heuristic nature of the prediction and summarizing the spectrum. nalysis_results.html routes both NMR results to the generic spectrum_accordion.html component. However, this component was coded only to render tabular peak data, entirely omitting the disclaimer and summary context fields. This leaves the frontend visually sparse and "incomplete", as it fails to surface the contextual backend data that the API provided.
