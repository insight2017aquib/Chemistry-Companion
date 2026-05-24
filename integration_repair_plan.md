# Integration Repair Plan — Chemistry Companion

## 1. 13C NMR GUI Repair
- **Problem:** `carbon_nmr_prediction` is returned by the API but dropped by the `analysis_results.html` template.
- **Fix:** Create a reusable `templates/components/spectrum_accordion.html` for rendering spectra without duplicating HTML. Use it to render 1H NMR and 13C NMR side-by-side, matching existing styles.

## 2. Docking GUI Repair
- **Problem:** Missing API endpoint for `/api/docking/generate`.
- **Fix:** Create `api/routes/docking.py` that utilizes `core.docking_preparation.prepare_docking_structure`. Ensure it returns a JSON status object (`success`, `job_id`, `download_url`, `status`) to support future async capability. Modify frontend to handle the JSON response and provide a download link.

## 3. Validation GUI Repair
- **Problem:** `validation.html` presents static plots without a way to execute the pipeline.
- **Fix:** Add a minimal `Run Validation` button to `validation.html`. Create `POST /api/validation/run` in `api/routes/validation.py` to trigger `core.spectra_validation.validate_spectra_workflow()` and return updated metrics/plots through a serializer.

## 4. Benchmark GUI Repair
- **Problem:** `benchmarks.html` presents static plots.
- **Fix:** Add a `Run Benchmarks` button. Create `POST /api/benchmarks/run` in `api/routes/benchmarks.py` using `core.descriptor_benchmark.benchmark_from_csv()`. Implement a 24-hour cache so unchanged data isn't recomputed unnecessarily.

## 5. End-to-End API Contracts
- **Problem:** Need automated guarantees that these contracts remain intact.
- **Fix:** Implement `tests/test_gui_integration.py`, `tests/test_api_contracts.py`, and `tests/test_frontend_backend_contract.py` to exercise the complete pipeline from GUI payload through to the serializer output.

## 6. Frontend Cleanup
- **Problem:** Leftover, orphaned, or unused code.
- **Fix:** Review `templates/` for any dead buttons, unused JS handlers, or duplicated rendering logic. Strict enforcement of "presentation only" rules for the frontend.
