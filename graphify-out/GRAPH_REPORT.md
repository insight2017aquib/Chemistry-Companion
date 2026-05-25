# Graph Report - Chemistry Companion  (2026-05-24)

## Corpus Check
- 242 files · ~442,043 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3234 nodes · 6700 edges · 59 communities detected
- Extraction: 65% EXTRACTED · 35% INFERRED · 0% AMBIGUOUS · INFERRED: 2318 edges (avg confidence: 0.61)
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
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `ChemistryPipeline` - 154 edges
2. `AnalysisResult` - 117 edges
3. `FunctionalGroupReport` - 111 edges
4. `DescriptorRecord` - 109 edges
5. `MoleculeRecord` - 106 edges
6. `CarbonNMRPrediction` - 105 edges
7. `IRPrediction` - 104 edges
8. `ProtonNMRPrediction` - 104 edges
9. `FunctionalGroupDetector` - 76 edges
10. `ProtonNMRPredictor` - 69 edges

## Surprising Connections (you probably didn't know these)
- `serialize_analysis_result()` --calls--> `_run_analysis()`  [INFERRED]
  api\serializers.py → api\routes\analysis.py
- `postprocess_residue()` --calls--> `main_branch()`  [INFERRED]
  AutoDock-Vina\src\lib\parse_pdbqt.cpp → AutoDock-Vina\src\lib\model.h
- `inchi_to_molblock()` --calls--> `_read_molecules()`  [INFERRED]
  core\conversion_utils.py → core\openbabel_utils.py
- `core/descriptor_utils.py ======================== Descriptor calculation utiliti` --uses--> `DescriptorRecord`  [INFERRED]
  core\descriptor_utils.py → core\models.py
- `MoleculeRecord` --uses--> `core/molecule_utils.py ====================== Utilities for parsing molecule inp`  [INFERRED]
  core\models.py → core\molecule_utils.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (157): Protocol for settings objects consumable by configure_logging().      Expected, SupportsLoggingSettings, AnalysisResult, CarbonEnvironment, CarbonNMRPrediction, _convert_value(), DescriptorRecord, FunctionalGroupReport (+149 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (39): run_ir(), Mapping, _BandSpec, _intensity_for(), IRBand, IRPeak, IRPrediction, _LegacyMappingMixin (+31 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (144): BaseModel, BaseSettings, test_default_export_extension(), test_directory_creation(), test_env_override(), test_invalid_image_width(), test_save_and_load(), BatchSettings (+136 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (62): BatchResult, _build_result(), _count_heterocyclic_rings(), _detect_columns(), MoleculeRow, _normalise_header(), process_file(), _process_one() (+54 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (123): convert_file_format(), Convert a file from one molecular format to another using Open Babel., display_header(), number_format_for(), Cell-safe formatting helpers for workbook rendering., Return a scalar value suitable for an Excel cell., safe_cell_value(), _metadata_rows() (+115 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (33): _average(), _cap_range(), _legacy_hnmr_label(), LegacyMappingMixin, MLShiftModel, NMRPrediction, _norm_key(), predict_from_groups() (+25 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (97): cross_product(), elementwise_product(), normalize_angle(), normalized_angle(), sqr(), vec(), apply(), external_too_close() (+89 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (37): _validate_sheet_name(), FunctionalGroupMatch, set(), get_python_files(), main(), parse_file(), main(), detect_functional_groups() (+29 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (93): batch_smiles_to_inchi(), embed_3d(), inchi_to_molblock(), inchi_to_smiles(), mol_to_inchi(), mol_to_inchikey(), mol_to_xyz(), chemistry_companion/core/conversion_utils.py =================================== (+85 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (80): api/serializers.py ================== Convert pipeline/service results into JS, Full analysis payload for API and templates., _safe_dict(), serialize_analysis_result(), serialize_carbon_nmr(), serialize_descriptors(), serialize_functional_groups(), serialize_ir() (+72 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (39): debug_heterocycles.py ===================== Advanced debug script for testing, _cap_range(), CarbonEnvironment, CarbonNMRPrediction, CarbonNMRPredictor, _legacy_cnmr_label(), LegacyMappingMixin, _mean() (+31 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (50): _load_mol(), build_record(), count_atoms(), is_aromatic(), load_molecule(), mol_from_file(), mol_from_inchi(), mol_from_iupac() (+42 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (93): atom_type(), average(), cluster_waters(), confirm_predictions(), coord(), dist(), experimental_match(), get_waters() (+85 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (90): run_cnmr(), run_hnmr(), load_benchmark(), main(), parse_args(), _parse_peaks(), print_results_table(), run_spectra_validation.py ========================= Spectra Validation Workflow (+82 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (64): run_funcgroups(), _canonical_smiles_from_mol(), DatasetLoadError, generate_descriptor_table(), load_molecular_dataset(), _load_sdf(), process_molecular_dataset(), chemistry_companion/core/dataset_utils.py ===================================== (+56 more)

### Community 15 - "Community 15"
Cohesion: 0.03
Nodes (69): are_atom_types_grid_initialized(), eval(), eval_deriv(), eval_intra(), read(), read_ad4_map(), split(), ad_is_heteroatom() (+61 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (76): analyse_page(), analysis_page(), batch_page(), benchmarks_page(), dashboard(), docking_page(), docking_workspace_page(), docs_page() (+68 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (57): _apply_atom_palette(), _apply_style(), default_functional_group_smarts(), _draw_single_molecule(), _final_style(), find_functional_group_matches(), get_aromatic_ring_indices(), _grid_png_to_bytes() (+49 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (59): prepare_docking_structure(), core/docking_preparation.py =========================== Open Babel docking pre, Prepare a docking-ready ligand from SMILES and export it as a formatted string., _validate_smiles(), build_markdown_report(), DockingValidationRecord, DockingValidationReport, _ensure_output_format() (+51 more)

### Community 19 - "Community 19"
Cohesion: 0.04
Nodes (48): vec_distance_sqr(), ConfIndependent(), rmsd_upper_bound(), about(), append(), appender, assign_bonds(), assign_types() (+40 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (27): about(), angle(), angled(), bruteNearbyAtoms(), crossProd(), dihedral(), dotProd(), load_pdbqt() (+19 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (18): ChemistryApp, exportAnalysis(), getExportData(), previewExport(), readExportHistory(), renderIRPlot(), saveExportHistory(), showSpectrumTab() (+10 more)

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (36): is_non_ad_metal_name(), string_to_ad_type(), starts_with(), substring_is_blank(), pdbqt_parse_error(), add_bonds(), add_context(), checked_convert_substring() (+28 more)

### Community 23 - "Community 23"
Cohesion: 0.06
Nodes (11): pipeline(), pipeline_no_spectra(), tests/test_pipeline.py ======================= Pytest suite for core/pipeline., TestAnalysisResult, TestBasicAnalysis, TestDescriptors, TestEdgeCases, TestFunctionalGroups (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (23): _coerce_level(), _ColorFormatter, configure_logging(), get_logger(), _is_managed_handler(), LoggingConfig, _make_formatter(), _mark_handler() (+15 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (20): _cmd_benchmark(), _autosize_columns(), benchmark_from_csv(), benchmark_molecule(), benchmark_summary(), build_plots(), compare_descriptors(), comparisons_to_rows() (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (17): lifespan(), Base, Database package for Chemistry Companion., BatchJob, configure_database(), create_database_engine(), create_session_factory(), get_db() (+9 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (1): FastAPI endpoint and template integration tests.

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (15): tests/test_logging_utils.py  Unit tests for core/logging_utils.py  Covers:, set_verbosity should update logger and managed handler levels., Enabling colored console output should still create a managed stream handler., File handler creation failure should not raise if console logging is enabled., Remove handlers managed by logging_utils from the application logger., configure_logging should attach a managed console handler and emit records., configure_logging should attach a managed rotating file handler with the     ex, Repeated configuration should not duplicate managed handlers. (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.32
Nodes (4): checked_multiply(), dim(), resize(), append()

### Community 32 - "Community 32"
Cohesion: 0.32
Nodes (7): Resolve IUPAC/common names to SMILES and validate with RDKit.  Tries PubChem (, High-level helper: name -> SMILES -> RDKit Mol. Returns (success, mol, smiles, e, Resolve a chemical name to a SMILES string.      Returns (success, smiles_or_N, Parse SMILES with RDKit and sanitize.      Returns (success, mol_or_None, erro, resolve_name_to_mol(), resolve_name_to_smiles(), smiles_to_rdkit_mol()

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (4): Dynamically imports every backend file to ensure dependency wiring is intact., Skeleton for frontend-backend integration checks.     Proves that the test file, test_backend_connectivity_import(), test_frontend_backend_contract()

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (4): Simulates real batch upload from the batch.html page., Simulates the form submission from the analysis page., test_live_batch_upload_works(), test_live_single_analysis_works()

### Community 37 - "Community 37"
Cohesion: 0.6
Nodes (5): get_html_files(), get_js_files(), main(), parse_html_files(), parse_js_files()

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (1): tests/test_api_contracts.py =========================== Verifies that all API en

### Community 41 - "Community 41"
Cohesion: 0.4
Nodes (4): Ensure matplotlib is installed., Ensure seaborn is installed to prevent the ModuleNotFoundError boundary cascade, test_matplotlib_installed(), test_seaborn_installed_for_benchmarks()

### Community 42 - "Community 42"
Cohesion: 0.67
Nodes (2): Print helpful, accurate usage statement to stdout., usage()

### Community 46 - "Community 46"
Cohesion: 0.67
Nodes (1): tests/test_gui_integration.py ============================= Tests the routing of

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): conftest.py  (project root) Adds the project root and the spectra package to sys

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): verify_fixes.py ================ Verification script to check the dependency det

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Chemistry Companion – chemistry_companion package.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): api/__init__.py =============== API package initialization.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Excel workbook rendering for normalized Chemistry Companion exports.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Full path to the configured log file.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Return the default file extension for exports.          Raises         ------

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Load settings from a JSON file.          Environment variables still override

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Number of successful reports.

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Number of failed items.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (1): Check whether the docking backend is ready.

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (1): Runs Vina, maps interactions, builds report, saves outputs.

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (1): Run the full Vina pipeline.  Returns report dict or error dict.

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (1): Generate an LLM explanation; returns fallback string on failure.

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (1): Generate a 3D overlay; returns error dict on failure.

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (1): Check whether the visualization backend is ready.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Process batch from JSON molecule list.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Process batch from uploaded CSV, Excel, or TXT.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (1): HTMX partial for batch results.

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (1): Convert a molecule representation from one format to another.

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (1): Normalize analysis or batch results into the shared export payload.

## Knowledge Gaps
- **314 isolated node(s):** `conftest.py  (project root) Adds the project root and the spectra package to sys`, `run_spectra_validation.py ========================= Spectra Validation Workflow`, `Parse a JSON list column into a Python list of floats.`, `Load spectra_benchmark.csv into validation input records.`, `verify_fixes.py ================ Verification script to check the dependency det` (+309 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (17 nodes): `client()`, `test_api.py`, `FastAPI endpoint and template integration tests.`, `test_analyse_alias()`, `test_analyze_benzene()`, `test_batch_csv_upload()`, `test_batch_page()`, `test_dashboard_page()`, `test_export_json()`, `test_export_xlsx_profile()`, `test_funcgroups()`, `test_health()`, `test_history_crud()`, `test_history_page()`, `test_htmx_analyse()`, `test_new_pages()`, `test_structure_png()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (6 nodes): `test_api_contracts.py`, `tests/test_api_contracts.py =========================== Verifies that all API en`, `test_analysis_contract()`, `test_benchmarks_contract()`, `test_docking_contract()`, `test_validation_contract()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (3 nodes): `Print helpful, accurate usage statement to stdout.`, `usage()`, `prepare_flexreceptor.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (3 nodes): `test_gui_integration.py`, `tests/test_gui_integration.py ============================= Tests the routing of`, `test_gui_pages_exist()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `conftest.py  (project root) Adds the project root and the spectra package to sys`, `conftest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `verify_fixes.py ================ Verification script to check the dependency det`, `verify_fixes.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `Chemistry Companion – chemistry_companion package.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (2 nodes): `__init__.py`, `api/__init__.py =============== API package initialization.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (2 nodes): `Excel workbook rendering for normalized Chemistry Companion exports.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Full path to the configured log file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Return the default file extension for exports.          Raises         ------`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Load settings from a JSON file.          Environment variables still override`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Number of successful reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Number of failed items.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `Check whether the docking backend is ready.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `Runs Vina, maps interactions, builds report, saves outputs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `Run the full Vina pipeline.  Returns report dict or error dict.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `Generate an LLM explanation; returns fallback string on failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `Generate a 3D overlay; returns error dict on failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `Check whether the visualization backend is ready.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Process batch from JSON molecule list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `Process batch from uploaded CSV, Excel, or TXT.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `HTMX partial for batch results.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (1 nodes): `Convert a molecule representation from one format to another.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (1 nodes): `Normalize analysis or batch results into the shared export payload.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ChemistryPipeline` connect `Community 0` to `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 23`?**
  _High betweenness centrality (0.235) - this node is a cross-community bridge._
- **Why does `print()` connect `Community 12` to `Community 2`, `Community 6`, `Community 7`, `Community 13`, `Community 20`, `Community 25`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Why does `FunctionalGroupDetector` connect `Community 7` to `Community 0`, `Community 1`, `Community 5`, `Community 9`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 146 inferred relationships involving `ChemistryPipeline` (e.g. with `AnalysisResult` and `CarbonNMRPrediction`) actually correct?**
  _`ChemistryPipeline` has 146 INFERRED edges - model-reasoned connections that need verification._
- **Are the 113 inferred relationships involving `AnalysisResult` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`AnalysisResult` has 113 INFERRED edges - model-reasoned connections that need verification._
- **Are the 105 inferred relationships involving `FunctionalGroupReport` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`FunctionalGroupReport` has 105 INFERRED edges - model-reasoned connections that need verification._
- **Are the 104 inferred relationships involving `DescriptorRecord` (e.g. with `api/serializers.py ================== Convert pipeline/service results into JS` and `Full analysis payload for API and templates.`) actually correct?**
  _`DescriptorRecord` has 104 INFERRED edges - model-reasoned connections that need verification._