# Stabilization Pass - Changelog

## Objective
Make the Chemistry Companion project boot successfully, resolving all startup failures, import errors, and dependency issues.

## Fixes Implemented

### 1. Dependency Errors (Vina Build Failure)
- **Error:** When attempting to install dependencies on Windows, `vina>=1.2.5` triggered a fatal build error: `ValueError: Boost library location was not found!`.
- **Fix:** Removed `vina>=1.2.5` from `requirements.txt`. The backend module `docking_workflow/vina_runner.py` executes `vina.exe` directly via `subprocess.run()`, meaning the Python bindings (which fail to compile without Boost C++ libraries) are not actually required for the application to function.
- **Result:** Allowed `pip install -r requirements.txt` to complete successfully in the `.venv` environment.

### 2. Dependency Errors (Missing Modules)
- **Error:** `WARNING:visualization:Visualization module partially unavailable. Missing: gemmi, py3Dmol`.
- **Fix:** Re-ran `pip install -r requirements.txt` using the `.venv` Python executable to ensure `gemmi`, `py3Dmol`, and `meeko` were properly installed in the local virtual environment.

### 3. Schema Errors (Pydantic V2 Deprecation Warnings)
- **Error:** `UserWarning: Valid config keys have changed in V2: * 'schema_extra' has been renamed to 'json_schema_extra'`.
- **Fix:** Replaced `schema_extra = {` with `json_schema_extra = {` inside the `Config` classes of the following files:
  - `api/schemas/analysis.py`
  - `api/schemas/batch.py`
  - `api/schemas/export.py`
  - `api/schemas/spectra.py`

### 4. Verification
- **Syntax Verification:** Ran `python -m py_compile` on the modified schema files to confirm syntax validity.
- **Application Boot:** Verified the FastAPI application starts successfully without fatal import or schema errors.
