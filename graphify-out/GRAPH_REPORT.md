# Graph Report - chemistry Companion  (2026-05-20)

## Corpus Check
- 106 files · ~76,703 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2294 nodes · 5059 edges · 36 communities detected
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 1874 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]

## God Nodes (most connected - your core abstractions)
1. `ChemistryPipeline` - 141 edges
2. `AnalysisResult` - 115 edges
3. `FunctionalGroupReport` - 111 edges
4. `DescriptorRecord` - 109 edges
5. `MoleculeRecord` - 106 edges
6. `CarbonNMRPrediction` - 105 edges
7. `IRPrediction` - 104 edges
8. `ProtonNMRPrediction` - 104 edges
9. `FunctionalGroupDetector` - 76 edges
10. `ProtonNMRPredictor` - 69 edges

## Surprising Connections (you probably didn't know these)
- `_load_mol()` --calls--> `load_molecule()`  [INFERRED]
  chemistry_companion.py → core\molecule_utils.py
- `chemistry_companion.py ====================== CLI entry point for Chemistry Comp` --uses--> `IRPredictor`  [INFERRED]
  chemistry_companion.py → spectra\ir_predictor.py
- `Full Phase 1 pipeline: parse → descriptors → image → export.` --uses--> `IRPredictor`  [INFERRED]
  chemistry_companion.py → spectra\ir_predictor.py
- `Parse input flags into a MoleculeRecord.` --uses--> `IRPredictor`  [INFERRED]
  chemistry_companion.py → spectra\ir_predictor.py
- `IR band prediction subcommand.` --uses--> `IRPredictor`  [INFERRED]
  chemistry_companion.py → spectra\ir_predictor.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (145): Protocol for settings objects consumable by configure_logging().      Expected, SupportsLoggingSettings, AnalysisResult, CarbonEnvironment, CarbonNMRPrediction, _convert_value(), DescriptorRecord, FunctionalGroupReport (+137 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (40): run_ir(), FunctionalGroupMatch, Mapping, detect_functional_groups(), FunctionalGroupDetector, get_registry(), spectra/functional_group_detector.py ==================================== Struct, spectra package ===============  Heuristic spectral prediction modules for Chemi (+32 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (62): BatchResult, _build_result(), _count_heterocyclic_rings(), _detect_columns(), MoleculeRow, _normalise_header(), process_file(), _process_one() (+54 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (34): debug_heterocycles.py ===================== Advanced debug script for testing, _average(), _cap_range(), _legacy_hnmr_label(), LegacyMappingMixin, MLShiftModel, NMRPrediction, _norm_key() (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (98): apply_workbook_properties(), build_workbook(), build_workbook_bytes(), _payload_from_any(), Build scientific Excel workbooks from normalized export payloads., Create an openpyxl Workbook from normalized export data., Render a workbook into an in-memory XLSX byte stream., CsvExporter (+90 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (45): services/spectra_service.py ========================== Service layer for spect, Service for handling spectral prediction operations., Predict IR spectrum for a molecule.          Args:             mol: RDKit mol, Predict ¹H NMR spectrum for a molecule.          Args:             mol: RDKit, Predict ¹³C NMR spectrum for a molecule.          Args:             mol: RDKi, Predict all spectra for a molecule.          Args:             mol: RDKit mol, SpectraService, _cap_range() (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (99): BaseModel, BaseSettings, test_default_export_extension(), test_directory_creation(), test_env_override(), test_invalid_image_width(), test_save_and_load(), BatchSettings (+91 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (48): build_record(), count_atoms(), is_aromatic(), load_molecule(), mol_from_file(), mol_from_inchi(), mol_from_smiles(), MoleculeInput (+40 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (26): FGDefinition, register_custom_group(), detector(), mol(), chemistry_companion/tests/test_functional_group_detector.py ====================, Every SMARTS in the registry must compile without error., Custom registry must not mutate FUNCTIONAL_GROUP_REGISTRY., A bad SMARTS must not crash __init__ — it should be skipped. (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (63): Reporting and export helpers for Chemistry Companion., BatchSpectraReport, build_batch_spectra_reports(), build_spectra_report(), _empty_report(), export_csv_report(), export_json_report(), export_markdown_report() (+55 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (56): _add_input_group(), analyse(), _banner(), build_parser(), _cmd_analyse(), _cmd_batch(), _cmd_cnmr(), _cmd_demo() (+48 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (57): _apply_atom_palette(), _apply_style(), default_functional_group_smarts(), _draw_single_molecule(), _final_style(), find_functional_group_matches(), get_aromatic_ring_indices(), _grid_png_to_bytes() (+49 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (51): _cmd_benchmark(), run_cnmr(), run_hnmr(), _autosize_columns(), benchmark_from_csv(), benchmark_molecule(), benchmark_summary(), build_plots() (+43 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (61): convert_file_format(), Convert a file from one molecular format to another using Open Babel., batch_smiles_to_inchi(), embed_3d(), inchi_to_molblock(), inchi_to_smiles(), mol_to_inchi(), mol_to_inchikey() (+53 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (46): analyse_page(), analysis_page(), batch_page(), dashboard(), docs_page(), exports_page(), history_page(), _page_ctx() (+38 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (20): ChemistryApp, exportAnalysis(), getExportData(), previewExport(), readExportHistory(), renderIRPlot(), saveExportHistory(), showSpectrumTab() (+12 more)

### Community 16 - "Community 16"
Cohesion: 0.1
Nodes (6): bands_for(), has_band_key(), has_label_containing(), TestAliphaticCH, TestPredictKnownBands, TestPredictNegativeCases

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (33): mol_from_iupac(), _enrich_result(), _inchi_to_inchikey(), _looks_like_name(), _mol_to_inchi(), _parse_inchi(), _parse_smiles(), core/resolver.py ================ Unified molecule input resolution pipeline.  R (+25 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (11): pipeline(), pipeline_no_spectra(), tests/test_pipeline.py ======================= Pytest suite for core/pipeline., TestAnalysisResult, TestBasicAnalysis, TestDescriptors, TestEdgeCases, TestFunctionalGroups (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.18
Nodes (12): build_markdown_report(), DockingValidationRecord, DockingValidationReport, _ensure_output_format(), export_validation_report(), core/docking_validation.py ========================== Validation workflow for, validate_docking_workflow(), _write_rows_to_sheet() (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (23): _coerce_level(), _ColorFormatter, configure_logging(), get_logger(), _is_managed_handler(), LoggingConfig, _make_formatter(), _mark_handler() (+15 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (21): _canonical_smiles_from_mol(), DatasetLoadError, generate_descriptor_table(), load_molecular_dataset(), _load_sdf(), process_molecular_dataset(), chemistry_companion/core/dataset_utils.py =====================================, Load a molecular dataset from CSV, Excel, or SDF.      Returns a DataFrame wit (+13 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (17): lifespan(), Base, Database package for Chemistry Companion., BatchJob, configure_database(), create_database_engine(), create_session_factory(), get_db() (+9 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (14): display_header(), number_format_for(), Cell-safe formatting helpers for workbook rendering., Return a scalar value suitable for an Excel cell., safe_cell_value(), _metadata_rows(), Worksheet renderers for normalized scientific export payloads., render_sheet() (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (1): FastAPI endpoint and template integration tests.

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (15): tests/test_logging_utils.py  Unit tests for core/logging_utils.py  Covers:, set_verbosity should update logger and managed handler levels., Enabling colored console output should still create a managed stream handler., File handler creation failure should not raise if console logging is enabled., Remove handlers managed by logging_utils from the application logger., configure_logging should attach a managed console handler and emit records., configure_logging should attach a managed rotating file handler with the     ex, Repeated configuration should not duplicate managed handlers. (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.32
Nodes (7): Resolve IUPAC/common names to SMILES and validate with RDKit.  Tries PubChem (, High-level helper: name -> SMILES -> RDKit Mol. Returns (success, mol, smiles, e, Resolve a chemical name to a SMILES string.      Returns (success, smiles_or_N, Parse SMILES with RDKit and sanitize.      Returns (success, mol_or_None, erro, resolve_name_to_mol(), resolve_name_to_smiles(), smiles_to_rdkit_mol()

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): conftest.py  (project root) Adds the project root and the spectra package to sys

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Chemistry Companion – chemistry_companion package.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): api/__init__.py =============== API package initialization.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Excel workbook rendering for normalized Chemistry Companion exports.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Full path to the configured log file.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Return the default file extension for exports.          Raises         ------

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Load settings from a JSON file.          Environment variables still override

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Number of successful reports.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Number of failed items.

## Knowledge Gaps
- **234 isolated node(s):** `conftest.py  (project root) Adds the project root and the spectra package to sys`, `Chemistry Companion – chemistry_companion package.`, `api/__init__.py =============== API package initialization.`, `api/routes/batch.py =================== Batch molecule processing (file upload`, `Process batch from JSON molecule list.` (+229 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 24`** (17 nodes): `client()`, `test_api.py`, `FastAPI endpoint and template integration tests.`, `test_analyse_alias()`, `test_analyze_benzene()`, `test_batch_csv_upload()`, `test_batch_page()`, `test_dashboard_page()`, `test_export_json()`, `test_export_xlsx_profile()`, `test_funcgroups()`, `test_health()`, `test_history_crud()`, `test_history_page()`, `test_htmx_analyse()`, `test_new_pages()`, `test_structure_png()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `conftest.py  (project root) Adds the project root and the spectra package to sys`, `conftest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `Chemistry Companion – chemistry_companion package.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `__init__.py`, `api/__init__.py =============== API package initialization.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `Excel workbook rendering for normalized Chemistry Companion exports.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Full path to the configured log file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Return the default file extension for exports.          Raises         ------`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Load settings from a JSON file.          Environment variables still override`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Number of successful reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Number of failed items.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ChemistryPipeline` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 12`, `Community 13`, `Community 18`?**
  _High betweenness centrality (0.258) - this node is a cross-community bridge._
- **Why does `FunctionalGroupDetector` connect `Community 1` to `Community 0`, `Community 3`, `Community 7`, `Community 8`, `Community 16`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Why does `core/__init__.py ================ Core package for Chemistry Companion.  Exposes` connect `Community 12` to `Community 0`, `Community 6`, `Community 7`, `Community 17`, `Community 19`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 133 inferred relationships involving `ChemistryPipeline` (e.g. with `AnalysisResult` and `CarbonNMRPrediction`) actually correct?**
  _`ChemistryPipeline` has 133 INFERRED edges - model-reasoned connections that need verification._
- **Are the 111 inferred relationships involving `AnalysisResult` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`AnalysisResult` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Are the 105 inferred relationships involving `FunctionalGroupReport` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`FunctionalGroupReport` has 105 INFERRED edges - model-reasoned connections that need verification._
- **Are the 104 inferred relationships involving `DescriptorRecord` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`DescriptorRecord` has 104 INFERRED edges - model-reasoned connections that need verification._