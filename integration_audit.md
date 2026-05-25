# Integration Audit — Chemistry Companion

This document provides a comprehensive audit of the GUI-to-backend integration in Chemistry Companion.

## Overview
The goal of this audit is to identify any backend chemistry engines that are not exposed to the GUI, and any GUI elements that lack backend connectivity. 

## Phase 1 & 2: Feature Connectivity and Event Tracing

| Feature | GUI Page | Frontend Event | API Endpoint | Status |
|---|---|---|---|---|
| Descriptors | Analysis / Dashboard | `hx-post` to `/api/analyse` | `/api/analyse` | CONNECTED |
| Functional Groups | Analysis / Dashboard | `hx-post` to `/api/analyse` | `/api/analyse` | CONNECTED |
| IR Prediction | Analysis / Dashboard | `hx-post` to `/api/analyse` | `/api/analyse` | CONNECTED |
| 1H NMR Prediction | Analysis / Dashboard | `hx-post` to `/api/analyse` | `/api/analyse` | CONNECTED |
| **13C NMR Prediction** | Analysis / Dashboard | `hx-post` to `/api/analyse` | `/api/analyse` | **DISCONNECTED** (Data computed, not rendered in GUI) |
| **Docking Prep** | Docking | `submit` on form | `/api/docking/generate` | **DISCONNECTED** (Missing API route) |
| **Validation** | Validation | Static HTML | N/A | **DISCONNECTED** (No GUI trigger to run pipeline) |
| **Benchmarks** | Benchmarks | Static HTML | N/A | **DISCONNECTED** (No GUI trigger to run pipeline) |
| Exports | Exports | `submit` on form | `/api/export/profile` | CONNECTED |
| History | History | Server Render | `/api/history` | CONNECTED |
| Batch | Batch Analysis | `hx-post` on form | `/api/batch/process` | CONNECTED |

## Phase 3 & 4: API Routes and Serializers
- **API Mapping:** All core functionalities are well-mapped to `services` and `core` pipelines except Docking, Validation, and Benchmarks which have no routes.
- **Serializers:** `serialize_carbon_nmr` successfully serializes the 13C NMR backend results, but the frontend template `analysis_results.html` drops this output.

## Phase 5: Service Coverage Audit
The following backend engines were found to lack adequate GUI exposure:
- `core/docking_preparation.py`
- `core/descriptor_benchmark.py`
- `core/spectra_validation.py`

## Conclusion
The architecture wiring is mostly sound, but critical pathways (Docking, Validation, Benchmarks, 13C NMR) need explicit wiring to meet the requirement that no visual feature exists without backend connection and no backend engine exists without GUI exposure.
