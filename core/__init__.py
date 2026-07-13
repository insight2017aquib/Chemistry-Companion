"""
core/__init__.py
================
Core package for Chemistry Companion.

Exposes stable, low-risk public interfaces for:
  - molecule loading & resolution
  - descriptor calculation
  - visualization
  - configuration and logging

IMPORTANT
---------
Pipeline objects are loaded lazily to avoid circular imports with spectra.
Use either:
    from core import ChemistryPipeline, AnalysisResult
or:
    from core import get_pipeline_classes

Resolver helpers are available directly:
    from core import resolve_molecule_input, resolve_name_to_smiles, smiles_to_iupac_name
"""

from .config import (
    ChemistryCompanionSettings,
    LLMProvider,
    LLMSettings,
    get_settings,
    reset_settings_cache,
)
from .descriptor_utils import (
    DescriptorRecord,
    compute_descriptors,
    summarise_descriptors,
)
from .descriptor_benchmark import (
    DescriptorBenchmarkSummary,
    DescriptorComparison,
    benchmark_from_csv,
    benchmark_molecule,
    benchmark_summary,
    compute_rdkit_reference_descriptors,
    export_benchmark_report,
)
from .logging_utils import get_logger, set_verbosity
from .molecule_utils import MoleculeInput, MoleculeRecord, load_molecule
from .resolver import (
    ResolutionResult,
    resolve_molecule_input,
    resolve_name_to_smiles,
    smiles_to_iupac_name,
)
from .docking_preparation import prepare_docking_structure
from .docking_validation import (
    DockingValidationReport,
    DockingValidationRecord,
    export_validation_report,
    validate_docking_workflow,
)
from .spectra_validation import (
    SpectraDomainMetrics,
    SpectraValidationRecord,
    SpectraValidationReport,
    build_markdown_report,
    export_validation_report as export_spectra_validation_report,
    plot_spectra_validation_report,
    validate_spectra_workflow,
)
from .visualization_utils import save_2d_image
from .llm_utils import (
    LLMExplanation,
    LLMErrorKind,
    generate_explanation,
    explain_descriptors,
    explain_docking,
    explain_spectra,
    get_available_providers,
    get_active_provider,
    set_primary_provider,
    reset_primary_provider,
    clear_explanation_cache,
    get_cache_size,
)


def get_pipeline_classes():
    from .pipeline import AnalysisResult, ChemistryPipeline
    return AnalysisResult, ChemistryPipeline


def __getattr__(name: str):
    if name in {"AnalysisResult", "ChemistryPipeline"}:
        AnalysisResult, ChemistryPipeline = get_pipeline_classes()
        return {
            "AnalysisResult": AnalysisResult,
            "ChemistryPipeline": ChemistryPipeline,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnalysisResult",
    "ChemistryCompanionSettings",
    "ChemistryPipeline",
    "DescriptorBenchmarkSummary",
    "DescriptorComparison",
    "DescriptorRecord",
    "LLMErrorKind",
    "LLMExplanation",
    "LLMProvider",
    "LLMSettings",
    "MoleculeInput",
    "MoleculeRecord",
    "DockingValidationRecord",
    "DockingValidationReport",
    "ResolutionResult",
    "SpectraDomainMetrics",
    "SpectraValidationRecord",
    "SpectraValidationReport",
    "benchmark_from_csv",
    "benchmark_molecule",
    "benchmark_summary",
    "clear_explanation_cache",
    "compute_rdkit_reference_descriptors",
    "build_markdown_report",
    "compute_descriptors",
    "explain_descriptors",
    "explain_docking",
    "explain_spectra",
    "export_benchmark_report",
    "export_spectra_validation_report",
    "generate_explanation",
    "get_active_provider",
    "get_available_providers",
    "get_cache_size",
    "get_logger",
    "get_pipeline_classes",
    "get_settings",
    "load_molecule",
    "plot_spectra_validation_report",
    "prepare_docking_structure",
    "reset_primary_provider",
    "reset_settings_cache",
    "resolve_molecule_input",
    "resolve_name_to_smiles",
    "save_2d_image",
    "set_primary_provider",
    "set_verbosity",
    "smiles_to_iupac_name",
    "summarise_descriptors",
]
