# Publication Assistant Architecture & Logic

## 1. Evidence Linking Logic
The AI Scientific Writer (`services/ai/scientific_writer.py`) is the core engine for generating manuscript drafts. To prevent hallucination, the system prompt strictly enforces **Evidence Linking**.

**Rules:**
1. The AI is fed a JSON payload of exactly what is stored in the database.
2. The AI must cite the internal `SeriesCompound.name` or `SeriesCompound.id` whenever stating a property or activity value.
3. The AI is instructed to use an *advisory tone* (e.g., "The data suggests...") rather than a *conclusive tone* (e.g., "This proves...").
4. Output is explicitly framed as a **Draft**.

## 2. Table Generation
Located in `services/publication_service.py`, the Table Generator takes a `campaign_id` and formats the SAR/ADMET data into three supported structures:
- **CSV**: Standard comma-separated values for Excel.
- **LaTeX**: A strictly formatted `\begin{table}...\end{table}` block. The engine automatically escapes special characters (like underscores `\_`) to prevent LaTeX compilation errors.
- **DOCX**: Utilizes `python-docx` (if installed) to generate a native Microsoft Word table. The service wraps this in a `try/except ImportError` to gracefully fallback to CSV/LaTeX if the dependency is missing in lightweight environments.

## 3. Citation Formatting
Rather than relying on external APIs for citation styling (which can be slow or offline), the Citation Manager formats stored `LiteratureReference` objects locally.
Supported Styles:
- **ACS**: `Author. Title. Journal Year.`
- **APA**: `Author (Year). Title. Journal.`
- **Nature**: `1. Author. Title. Journal (Year).`

## 4. Reproducibility Package
The `ReproducibilityLog` model captures environment snapshots at the time of an experiment.
- Captures `sys.version` (Python), `platform.platform()` (OS).
- Captures installed package versions via `__version__` attributes (e.g., `rdkit.__version__`).
- Stored alongside the exact JSON parameters used for the run (e.g., Vina grid box).
