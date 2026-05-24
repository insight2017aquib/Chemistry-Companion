# Frontend API Endpoint Alignment Report

## Overview
Scraped all frontend components for API interactions and cross-referenced them with the exact mounted FastAPI routes.

## Matrix

| Component | UI Event | URL Declared | Mounted Route | Status |
|-----------|----------|--------------|---------------|--------|
| `analysis.html` | `<form hx-post>` | `/api/analyse` | `/api/analyse` | **PASS** |
| `batch.html` | `<form hx-post>` | `/api/batch/process` | `/api/batch/process` | **PASS** |
| `dashboard.html` | `<form hx-post>` | `/analyse` | `/analyse` (in `app.py`) | **PASS** |

## Conclusion
All frontend endpoints are perfectly aligned with the backend routes. There are no frontend links pointing to unmounted or orphaned APIs.
