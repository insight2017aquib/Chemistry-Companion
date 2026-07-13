# Developer Guide

> Chemistry Companion — Developer Reference

## Project Structure

```
chemistry_companion/
├── api/                          # FastAPI application & routes
│   ├── app.py                    # Application factory, lifespan, route mounting
│   ├── routes/                   # Route handlers (one file per feature)
│   ├── schemas/                  # Pydantic request/response models
│   ├── serializers.py            # Data serialization helpers
│   └── templating.py             # Jinja2 template configuration
├── core/                         # Core business logic & utilities
│   ├── config.py                 # Centralized Pydantic settings
│   ├── llm_utils.py              # Multi-provider LLM engine
│   ├── molecule_utils.py         # RDKit molecule handling
│   ├── descriptor_utils.py       # Molecular descriptors
│   ├── pipeline.py               # Analysis pipeline orchestrator
│   ├── resolver.py               # Chemical name/ID resolution
│   └── ...
├── docking_workflow/             # Molecular docking modules
│   ├── protein_preparation.py    # PDB → PDBQT receptor prep
│   ├── protein_analysis.py       # Pre-docking structural analysis
│   ├── vina_runner.py            # AutoDock Vina subprocess wrapper
│   ├── pocket_detection.py       # fpocket-based pocket detection
│   ├── water_analysis.py         # Water classification
│   └── ...
├── services/                     # Service layer (business orchestration)
│   ├── ai/                       # AI Provider Manager (Phase 01)
│   │   ├── provider_manager.py   # Unified provider facade
│   │   ├── models.py             # AIResponse, HealthCheckResult
│   │   └── recommendations.py    # recommend_chain/pocket/waters/...
│   ├── docking_workspace_service.py
│   ├── llm_service.py            # Legacy LLM client
│   └── ...
├── llm/                          # Legacy LLM integration
├── spectra/                      # IR & NMR prediction
├── database/                     # SQLAlchemy models
├── templates/                    # Jinja2 HTML templates
├── static/                       # CSS, JS, images
├── tests/                        # pytest test suite
├── docs/                         # Documentation
│   ├── architecture/             # System diagrams
│   ├── developer/                # (future) detailed guides
│   └── changelog/                # Release notes
└── outputs/                      # Runtime artifacts
    └── docking_workspace/        # Per-job docking files
```

---

## Adding a New LLM Provider

### Step 1: Register the Provider

In `core/llm_utils.py`, add an entry to `_PROVIDER_REGISTRY`:

```python
_PROVIDER_REGISTRY["my_provider"] = {
    "env_key": "MY_PROVIDER_API_KEY",
    "default_model": "my-model-name",
    "display_name": "My Provider (Model Name)",
    "api_url": "https://api.myprovider.com/v1/chat/completions",
    "note": "Rate limit info, pricing tier, etc.",
}
```

### Step 2: Handle Non-Standard API Formats

If the provider uses the standard OpenAI chat completions format, no additional code is needed — `_call_provider` handles it automatically.

If the provider has a different request/response format (like Gemini), add a conditional branch in `_call_provider`:

```python
if provider == "my_provider":
    # Build provider-specific payload
    payload = {...}
    # Parse provider-specific response
    content = response_data["my_content_field"]
```

### Step 3: Add Environment Variable

In `.env.example`:
```
MY_PROVIDER_API_KEY=...
```

### Step 4: Update Config (Optional)

In `core/config.py`, add the provider to the `LLMProvider` literal type:
```python
LLMProvider = Literal["deepseek", "openrouter", "groq", "gemini", "my_provider"]
```

### Step 5: Test

```python
# tests/test_my_provider.py
from unittest.mock import patch
from core.llm_utils import _call_provider

def test_my_provider_call():
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        mock_post.return_value.raise_for_status = lambda: None
        result = _call_provider("my_provider", "test-key", "model", "prompt")
        assert result == "test response"
```

---

## Adding a New Recommendation Function

### Step 1: Define the Function

In `services/ai/recommendations.py`:

```python
def recommend_something(
    input_data: Dict[str, Any],
    manager: Optional[AIProviderManager] = None,
) -> Recommendation:
    """
    AI-powered recommendation for [description].
    
    Returns a Recommendation with:
    - recommendation: the structured result
    - confidence: "high" / "medium" / "low"
    - reasoning: human-readable explanation
    """
    mgr = manager or AIProviderManager()
    
    prompt = _build_something_prompt(input_data)
    response = mgr.query_structured(prompt, expected_keys=["result", "confidence", "reasoning"])
    
    return Recommendation(
        recommendation=response.get("result"),
        confidence=response.get("confidence", "low"),
        reasoning=response.get("reasoning", "No reasoning provided."),
        provider_used=mgr.last_provider_used,
    )
```

### Step 2: Write Tests

```python
def test_recommend_something_returns_valid_recommendation():
    rec = recommend_something({"key": "value"})
    assert isinstance(rec, Recommendation)
    assert rec.confidence in ("high", "medium", "low")
```

### Step 3: Wire to API (Future Phase)

```python
@router.post("/recommend_something")
async def recommend_something_endpoint(request: SomethingRequest):
    rec = recommend_something(request.data)
    return rec.__dict__
```

---

## Testing Patterns

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_ai_provider_manager.py -v

# With coverage
pytest tests/ --cov=services/ai --cov-report=term-missing
```

### Mocking LLM Calls

All LLM tests should mock network calls. Use the existing patterns:

```python
from unittest.mock import patch, MagicMock

# Mock the modern LLM system
with patch("core.llm_utils._call_provider") as mock_call:
    mock_call.return_value = '{"key": "value"}'
    # ... test code ...

# Mock the legacy client
with patch("services.llm_service.get_llm_client") as mock_get:
    mock_client = MagicMock()
    mock_client.explain.return_value = "response text"
    mock_get.return_value = mock_client
    # ... test code ...
```

### Test File Naming

Follow existing convention: `tests/test_<module_name>.py`

---

## Configuration

All settings use Pydantic with environment variable support:

```
CHEM_COMPANION_LLM__PRIMARY_PROVIDER=groq
CHEM_COMPANION_LLM__FALLBACK_PROVIDERS=deepseek,openrouter,gemini
CHEM_COMPANION_LLM__ENABLE_LLM=true
CHEM_COMPANION_LLM__MAX_RETRIES=2
```

See `core/config.py` for the full `ChemistryCompanionSettings` model.

---

## Key Conventions

1. **Optional dependency guards**: Use `HAS_DOCKING` / `HAS_LLM` flags to guard imports
2. **Service layer**: All business logic goes through service classes, not directly in routes
3. **Graceful degradation**: Every LLM call returns a usable result, even on failure
4. **File-based artifacts**: Docking jobs persist to `outputs/docking_workspace/<job_id>/`
5. **DB for metadata**: SQLAlchemy models store searchable metadata; files store bulk data
6. **GUI Live Previews & Visualization**: There are exactly two supported stacks (do not create more):
   - Lightweight/always-on: `/api/structure.png` + `/api/structure.svg` (and optional 3D HTML) via `core/visualization_utils.py` (RDKit) + `api/routes/structure.py`. Used for instant molecule input previews.
   - Heavy (optional): `visualization/` package (gemmi + rdkit + py3Dmol) guarded by `HAS_VISUALIZATION` / `VisualizationService`, exposed at `/api/visualization/*`. Used for interactive ligand 2D/3D and protein-ligand overlays (and by the visualization.html workspace).
   - Protein live preview in docking is pure-frontend Mol* (CDN) + client-side PDB filtering in `docking_workspace.html` (see `docs/developer/molstar_integration.md` for the 2026 wiring audit and activation of the simple PNG path via `workbench.js` + global include).
   - Health surface: `/health` now includes `visualization.available`. Always extend existing health/audit surfaces instead of new endpoints.
