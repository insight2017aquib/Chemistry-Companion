"""Workbook profile and sheet models for scientific exports."""

from __future__ import annotations

from dataclasses import dataclass


SUMMARY = "Summary"
MOLECULES = "Molecules"
DESCRIPTORS = "Descriptors"
FUNCTIONAL_GROUPS = "Functional_Groups"
IR_PREDICTIONS = "IR_Predictions"
PROTON_NMR = "Proton_NMR"
CARBON_NMR = "Carbon_NMR"
FAILED_ENTRIES = "Failed_Entries"
METADATA = "Metadata"

ALL_WORKBOOK_SHEETS = [
    SUMMARY,
    MOLECULES,
    DESCRIPTORS,
    FUNCTIONAL_GROUPS,
    IR_PREDICTIONS,
    PROTON_NMR,
    CARBON_NMR,
    FAILED_ENTRIES,
    METADATA,
]


@dataclass(frozen=True, slots=True)
class ExportProfile:
    key: str
    name: str
    description: str
    sheets: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "sheets": list(self.sheets),
        }


PROFILE_DEFINITIONS: dict[str, ExportProfile] = {
    "full": ExportProfile(
        key="full",
        name="Full Report",
        description="Complete workbook with molecule, descriptor, functional group, spectra, failure, and metadata sheets.",
        sheets=tuple(ALL_WORKBOOK_SHEETS),
    ),
    "medchem": ExportProfile(
        key="medchem",
        name="Medicinal Chemistry",
        description="Drug-discovery focused workbook with physicochemical and functional group tables.",
        sheets=(SUMMARY, MOLECULES, DESCRIPTORS, FUNCTIONAL_GROUPS, FAILED_ENTRIES, METADATA),
    ),
    "spectroscopy": ExportProfile(
        key="spectroscopy",
        name="Spectroscopy",
        description="IR and NMR focused workbook for spectral interpretation.",
        sheets=(SUMMARY, MOLECULES, IR_PREDICTIONS, PROTON_NMR, CARBON_NMR, FAILED_ENTRIES, METADATA),
    ),
    "teaching": ExportProfile(
        key="teaching",
        name="Teaching",
        description="Readable instructional workbook with core descriptors and first-pass spectra.",
        sheets=(SUMMARY, MOLECULES, DESCRIPTORS, FUNCTIONAL_GROUPS, IR_PREDICTIONS, PROTON_NMR, FAILED_ENTRIES, METADATA),
    ),
    "minimal": ExportProfile(
        key="minimal",
        name="Minimal",
        description="Compact workbook with summary, molecule identity, descriptors, failures, and metadata.",
        sheets=(SUMMARY, MOLECULES, DESCRIPTORS, FAILED_ENTRIES, METADATA),
    ),
}

PROFILE_ALIASES = {
    "full report": "full",
    "medicinal chemistry": "medchem",
    "medicinal_chemistry": "medchem",
    "medicinal-chemistry": "medchem",
    "medchem": "medchem",
    "spectra": "spectroscopy",
    "spectroscopy": "spectroscopy",
    "teaching": "teaching",
    "minimal": "minimal",
}


def resolve_profile(profile: str | None) -> ExportProfile:
    """Return a workbook profile, accepting display names and legacy aliases."""
    if not profile:
        return PROFILE_DEFINITIONS["full"]
    key = str(profile).strip().lower().replace("-", "_")
    key = PROFILE_ALIASES.get(key, key)
    return PROFILE_DEFINITIONS.get(key, PROFILE_DEFINITIONS["full"])


def list_profiles() -> list[dict[str, object]]:
    """Return API-friendly profile metadata."""
    return [profile.to_dict() for profile in PROFILE_DEFINITIONS.values()]
