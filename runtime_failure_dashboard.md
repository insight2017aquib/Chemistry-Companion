# Runtime Failure Dashboard

| Subsystem | Status | Error | Failure Boundary Working | Frontend Impact |
|-----------|--------|-------|--------------------------|-----------------|
| Analysis | FAIL | {'detail': 'Not Found'} | YES | Route returns 500/404 |
| Batch | FAIL | {'detail': 'Not Found'} | YES | Route returns 500/404 |
| Validation | PASS | N/A | YES | None |
| Benchmarks | PASS | N/A | YES | None |
| Docking | FAIL | {'detail': [{'type': 'missing', 'loc': ['body', 'input_text'], 'msg': 'Field required', 'input': None}]} | YES | Route returns 500/404 |
