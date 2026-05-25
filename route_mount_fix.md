# Route Mount Fix

## Verified Root Cause
The `404 Not Found` responses logged during the API Live Audit for `/api/analysis/analyse` and `/api/batch/batch` were **false positives**. The test probe made the assumption that the Python module name was automatically appended to the router prefix.

## Mount Integrity Verification
- `api/app.py` correctly registers the routers with `prefix="/api"`.
- The actual endpoints exposed are `/api/analyse` and `/api/batch`.
- HTMX requests in the frontend templates (`analysis.html` and `batch.html`) perfectly align with these exact paths.

Therefore, no modifications to `api/app.py` or the `api/routes/*.py` files were necessary. The integration layer routing is perfectly sound.

## Resolution
- Live tests in `tests/test_route_mounting.py` have been implemented to guarantee the exposed endpoints never drift and are strictly reachable by the UI.
