# Runtime API Probe Report

## Endpoint: /api/analysis/analyse
- **Status**: 404
- **Exception**: None
```json
{
  "detail": "Not Found"
}
```

## Endpoint: /api/batch/batch
- **Status**: 404
- **Exception**: None
```json
{
  "detail": "Not Found"
}
```

## Endpoint: /api/validation/run
- **Status**: 200
- **Exception**: None
```json
{
  "success": false,
  "error": "No module named 'seaborn'",
  "status": "failed"
}
```

## Endpoint: /api/benchmarks/run
- **Status**: 200
- **Exception**: None
```json
{
  "success": false,
  "error": "No module named 'seaborn'",
  "status": "failed"
}
```

## Endpoint: /api/docking/generate
- **Status**: 422
- **Exception**: None
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "input_text"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

