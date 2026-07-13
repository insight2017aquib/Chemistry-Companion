"""
docking_workflow/protein_analysis.py
====================================
Pre-docking protein structure inspection and chain analysis.

Provides Chimera-like insights before any preparation or docking occurs:
- Accurate per-chain breakdown (residue counts, ranges, composition)
- Detection of hetero groups, waters, and co-crystallized ligands
- Intelligent recommendation of the biologically most relevant chain(s)
- Designed for direct use from the Docking Workspace UI

This is the core of Advanced Docking Phase 1 (pre-docking chain selection).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set

from docking_workflow.quality_scorer import attach_quality_to_report

logger = logging.getLogger(__name__)

# Standard amino acids (used for "protein-like" scoring)
STANDARD_AA: Set[str] = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"
}

# Common non-protein / solvent residues
WATER_RESIDUES: Set[str] = {"HOH", "WAT", "H2O", "WTR"}
ION_RESIDUES: Set[str] = {"NA", "CL", "K", "MG", "CA", "ZN", "FE", "CU", "MN", "NI"}


@dataclass
class ChainInfo:
    """Detailed information about a single chain in the structure."""
    chain_id: str
    num_residues: int = 0
    num_standard_aa: int = 0
    first_resnum: Optional[int] = None
    last_resnum: Optional[int] = None
    num_hetero: int = 0
    hetero_names: List[str] = field(default_factory=list)
    num_waters: int = 0
    is_likely_protein: bool = False
    # Optional: could hold a short sequence snippet in future
    sample_residues: List[str] = field(default_factory=list)


@dataclass
class ProteinAnalysis:
    """Complete pre-docking analysis result for a protein structure."""
    chains: List[ChainInfo]
    total_chains: int
    total_residues: int
    total_waters: int
    total_hetero_groups: int
    hetero_ligand_names: List[str]
    num_models: int = 1
    format_detected: str = "pdb"  # or "pdbqt"
    recommendation: Dict[str, Any] = field(default_factory=dict)  # {recommended_chain_ids, rationale, confidence}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict (for API responses and report.json)."""
        return {
            "chains": [asdict(c) for c in self.chains],
            "total_chains": self.total_chains,
            "total_residues": self.total_residues,
            "total_waters": self.total_waters,
            "total_hetero_groups": self.total_hetero_groups,
            "hetero_ligand_names": self.hetero_ligand_names,
            "num_models": self.num_models,
            "format_detected": self.format_detected,
            "recommendation": self.recommendation,
        }


def _guess_format(pdb_text: str) -> str:
    """Detect whether input looks like raw PDBQT (contains torsion tags)."""
    for line in pdb_text.splitlines()[:50]:
        if line.startswith(("ROOT", "BRANCH", "ENDBRANCH", "TORSDOF")):
            return "pdbqt"
    return "pdb"


def _parse_with_gemmi(pdb_text: str) -> Optional[ProteinAnalysis]:
    """Preferred parser using gemmi (already a project dependency)."""
    try:
        import gemmi
    except Exception as e:
        logger.debug("gemmi not available for protein analysis: %s", e)
        return None

    try:
        st = gemmi.read_structure_string(pdb_text)
        chains_map: Dict[str, ChainInfo] = {}
        waters = 0
        hetero_names: Set[str] = set()
        num_models = len(st)

        for model in st:
            for chain in model:
                cid = chain.name or "_"
                if cid not in chains_map:
                    chains_map[cid] = ChainInfo(chain_id=cid)

                ch = chains_map[cid]
                for res in chain:
                    resname = res.name.upper().strip()
                    try:
                        resnum = int(res.seqid.num)
                    except Exception:
                        resnum = 0

                    ch.num_residues += 1

                    if resname in STANDARD_AA:
                        ch.num_standard_aa += 1
                        ch.is_likely_protein = True
                    elif resname in WATER_RESIDUES:
                        ch.num_waters += 1
                        waters += 1
                    else:
                        ch.num_hetero += 1
                        if resname not in WATER_RESIDUES and resname not in ION_RESIDUES:
                            if resname not in ch.hetero_names:
                                ch.hetero_names.append(resname)
                            hetero_names.add(resname)

                    # Track residue number range
                    if ch.first_resnum is None or resnum < ch.first_resnum:
                        ch.first_resnum = resnum
                    if ch.last_resnum is None or resnum > ch.last_resnum:
                        ch.last_resnum = resnum

                    if len(ch.sample_residues) < 6:
                        ch.sample_residues.append(f"{resname}{resnum}")

        # Build final list sorted by chain id (common convention: A, B, C...)
        chain_list = sorted(chains_map.values(), key=lambda c: c.chain_id or "_")

        total_res = sum(c.num_residues for c in chain_list)
        total_het = sum(c.num_hetero for c in chain_list)

        analysis = ProteinAnalysis(
            chains=chain_list,
            total_chains=len(chain_list),
            total_residues=total_res,
            total_waters=waters,
            total_hetero_groups=total_het,
            hetero_ligand_names=sorted(hetero_names),
            num_models=num_models,
            format_detected=_guess_format(pdb_text),
        )

        analysis.recommendation = _compute_recommendation(analysis)
        return analysis

    except Exception as e:
        logger.warning("gemmi parsing failed, will use fallback: %s", e)
        return None


def _fallback_line_parser(pdb_text: str) -> ProteinAnalysis:
    """
    Robust pure-Python fallback (reuses patterns from protein_loader.py
    and interaction_analyzer.py).
    """
    chains_map: Dict[str, ChainInfo] = {}
    waters = 0
    hetero_names: Set[str] = set()
    num_models = 1  # crude

    for line in pdb_text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            if line.startswith("MODEL"):
                num_models += 1
            continue

        try:
            chain_id = line[21:22].strip() or "_"
            resname = line[17:20].strip().upper()
            resnum_str = line[22:26].strip()
            resnum = int(resnum_str) if resnum_str.lstrip("-").isdigit() else 0
        except Exception:
            continue

        if chain_id not in chains_map:
            chains_map[chain_id] = ChainInfo(chain_id=chain_id)

        ch = chains_map[chain_id]
        ch.num_residues += 1

        if resname in STANDARD_AA:
            ch.num_standard_aa += 1
            ch.is_likely_protein = True
        elif resname in WATER_RESIDUES:
            ch.num_waters += 1
            waters += 1
        else:
            ch.num_hetero += 1
            if resname not in WATER_RESIDUES and resname not in ION_RESIDUES:
                if resname not in ch.hetero_names:
                    ch.hetero_names.append(resname)
                hetero_names.add(resname)

        if ch.first_resnum is None or resnum < ch.first_resnum:
            ch.first_resnum = resnum
        if ch.last_resnum is None or resnum > ch.last_resnum:
            ch.last_resnum = resnum

        if len(ch.sample_residues) < 6:
            ch.sample_residues.append(f"{resname}{resnum}")

    chain_list = sorted(chains_map.values(), key=lambda c: c.chain_id or "_")
    total_res = sum(c.num_residues for c in chain_list)
    total_het = sum(c.num_hetero for c in chain_list)

    analysis = ProteinAnalysis(
        chains=chain_list,
        total_chains=len(chain_list),
        total_residues=total_res,
        total_waters=waters,
        total_hetero_groups=total_het,
        hetero_ligand_names=sorted(hetero_names),
        num_models=max(1, num_models),
        format_detected=_guess_format(pdb_text),
    )

    analysis.recommendation = _compute_recommendation(analysis)
    return analysis


def _compute_recommendation(analysis: ProteinAnalysis) -> Dict[str, Any]:
    """
    Simple but effective heuristic for recommending which chain(s) to dock against.

    Scoring rules (v1):
    - Strong bonus for chains that are mostly standard amino acids (protein-like).
    - Extra points if the chain has hetero groups that are NOT waters/ions
      (classic signal for the chain that had a co-crystallized ligand).
    - Prefer larger chains when scores are close.
    """
    if not analysis.chains:
        return {
            "recommended_chain_ids": [],
            "rationale": "No chains detected in the uploaded structure.",
            "confidence": "low",
        }

    scored = []
    for ch in analysis.chains:
        score = 0.0
        # Protein-likeness (0-100)
        if ch.num_residues > 0:
            aa_ratio = ch.num_standard_aa / ch.num_residues
            score += aa_ratio * 70

        # Size bonus (encourages the main functional chain)
        score += min(ch.num_standard_aa / 50.0, 1.5) * 15

        # Ligand proximity signal (very important)
        real_hets = ch.num_hetero - ch.num_waters
        if real_hets > 0:
            score += min(real_hets * 4, 25)

        # Penalize tiny chains (often artifacts or small peptides)
        if ch.num_standard_aa < 20:
            score *= 0.6

        scored.append((score, ch))

    scored.sort(key=lambda x: x[0], reverse=True)

    top = scored[0]
    recommended_ids = [top[1].chain_id]

    # If there is a very close second that also looks good, suggest both
    if len(scored) > 1:
        second = scored[1]
        if second[0] > (top[0] * 0.75) and second[1].is_likely_protein:
            recommended_ids.append(second[1].chain_id)

    rationale_parts = []
    best = top[1]
    if best.is_likely_protein:
        rationale_parts.append(f"Chain {best.chain_id} is the largest protein-like chain")
    if (best.num_hetero - best.num_waters) > 0:
        rationale_parts.append(f"contains non-solvent hetero groups ({', '.join(best.hetero_names[:3])})")

    if not rationale_parts:
        rationale = f"Chain {best.chain_id} selected by size."
    else:
        rationale = " and ".join(rationale_parts) + "."

    confidence = "high" if top[0] > 60 else ("medium" if top[0] > 30 else "low")

    return {
        "recommended_chain_ids": recommended_ids,
        "rationale": rationale,
        "confidence": confidence,
        "scores": {ch.chain_id: round(s, 1) for s, ch in scored[:4]},  # top few for debugging/transparency
    }


def analyze_protein(pdb_text: str) -> ProteinAnalysis:
    """
    Main public entry point.

    Analyzes a raw PDB (or PDBQT) file and returns rich per-chain information
    plus a docking recommendation — exactly the kind of insight Chimera shows
    immediately after loading a structure.

    This function is intentionally lightweight and has no dependency on vina/meeko.
    It can be called at any time after the user selects a PDB file in the UI.
    """
    if not pdb_text or not pdb_text.strip():
        raise ValueError("PDB text is empty.")

    # Try gemmi first (best quality)
    result = _parse_with_gemmi(pdb_text)
    if result is not None:
        logger.info(
            "Protein analysis (gemmi): %d chains, %d residues, recommendation=%s",
            result.total_chains, result.total_residues,
            result.recommendation.get("recommended_chain_ids"),
        )
        return result

    # Fallback (always works)
    result = _fallback_line_parser(pdb_text)
    logger.info(
        "Protein analysis (fallback): %d chains, %d residues, recommendation=%s",
        result.total_chains, result.total_residues,
        result.recommendation.get("recommended_chain_ids"),
    )
    return result


# =============================================================================
# PHASE 1 EXTENSION: Rich Receptor Analysis (Publication-Quality)
# =============================================================================
#
# This section adds a significantly richer analysis while preserving 100%
# backward compatibility with the existing analyze_protein() API.
#
# New public entry point: analyze_receptor(pdb_text) -> ReceptorReport
# =============================================================================

from dataclasses import dataclass
from typing import Optional


@dataclass
class LigandInfo:
    """Information about a co-crystallized ligand (not a cofactor or metal)."""
    resname: str
    chain_id: str
    resnum: int
    num_atoms: int
    centroid: Optional[Dict[str, float]] = None   # x, y, z if computable


@dataclass
class MetalInfo:
    """Information about metal ions in the structure."""
    resname: str
    chain_id: str
    resnum: int
    element: str
    coordinating_residues: List[str] = field(default_factory=list)
    catalytic_relevance: str = "unknown"


@dataclass
class CofactorInfo:
    """Information about common enzymatic cofactors."""
    resname: str
    chain_id: str
    resnum: int
    classification: str   # e.g. "nucleotide", "flavin", "heme", etc.
    status: str = "optional"   # required / optional / artifact


@dataclass
class ReceptorReport:
    """
    Rich, publication-grade receptor analysis report.

    This is the new recommended object for serious docking work.
    It supersedes the simpler ProteinAnalysis for new features while
    the old API remains fully supported for backward compatibility.
    """
    # === Basic structure ===
    chains: List[ChainInfo]
    total_chains: int
    total_residues: int
    total_waters: int
    total_hetero_groups: int
    num_models: int = 1
    format_detected: str = "pdb"

    # === New rich data (Phase 1) ===
    ligands: List[LigandInfo] = field(default_factory=list)
    cofactors: List[CofactorInfo] = field(default_factory=list)
    metals: List[MetalInfo] = field(default_factory=list)

    # Experimental metadata
    resolution: Optional[float] = None
    experimental_method: Optional[str] = None
    has_biological_assembly: bool = False

    # Quality assessment
    missing_residues: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0          # 0-100
    quality_label: str = "Unknown"      # Excellent / Good / Acceptable / Poor

    # Chain recommendation (re-uses existing logic for now)
    recommendation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable representation for API and reports."""
        base = {
            "chains": [asdict(c) for c in self.chains],
            "total_chains": self.total_chains,
            "total_residues": self.total_residues,
            "total_waters": self.total_waters,
            "total_hetero_groups": self.total_hetero_groups,
            "num_models": self.num_models,
            "format_detected": self.format_detected,
            "recommendation": self.recommendation,
        }

        # Rich fields
        base.update({
            "ligands": [asdict(l) for l in self.ligands],
            "cofactors": [asdict(c) for c in self.cofactors],
            "metals": [asdict(m) for m in self.metals],
            "resolution": self.resolution,
            "experimental_method": self.experimental_method,
            "has_biological_assembly": self.has_biological_assembly,
            "missing_residues": self.missing_residues,
            "quality_score": round(self.quality_score, 1),
            "quality_label": self.quality_label,
        })
        return base


# =============================================================================
# Cofactor & Metal Classification (used by both analysis and preparation)
# =============================================================================

# Common cofactor residue names with categories
COFACTOR_RESNAMES = {
    # Nucleotides
    "ATP": "nucleotide", "ADP": "nucleotide", "AMP": "nucleotide",
    "GTP": "nucleotide", "GDP": "nucleotide", "GMP": "nucleotide",
    "CTP": "nucleotide", "CDP": "nucleotide",
    "UTP": "nucleotide", "UDP": "nucleotide",
    # Redox cofactors
    "NAD": "nucleotide", "NADH": "nucleotide", "NDP": "nucleotide",
    "NAP": "nucleotide", "NDP": "nucleotide",
    "FAD": "flavin", "FMN": "flavin",
    # Heme
    "HEM": "heme", "HME": "heme", "HEC": "heme", "HEB": "heme",
    # Others
    "SAM": "methyl", "SAH": "methyl",
    "COA": "coa", "ACC": "coa",
    "PLP": "other", "B12": "other",
}

# Cofactor statuses used for richer reporting
REQUIRED_COFACORS = {"ATP", "ADP", "NAD", "NADH", "FAD", "FMN", "HEM", "HEC", "HEB", "SAM", "COA"}
COFACTOR_ARTIFACTS = {"EDO", "GOL", "PEG", "SO4", "PO4", "ACT", "FMT", "DMS", "MES"}

# Metal elements relevant for docking (expanded)
METAL_ELEMENTS = {
    "ZN", "MG", "FE", "MN", "CU", "CA", "NI", "CO", "NA", "K",
    "CD", "HG", "PB", "MO", "W", "SE"
}

# Common ions that are usually safe to remove
COMMON_IONS = {"NA", "K", "CL", "SO4", "PO4", "ACT", "FMT", "EDO", "PEG"}

# Residues that often collaborate with catalytic metals
CATALYTIC_RESIDUES = {"ASP", "GLU", "HIS", "CYS", "SER", "TYR", "LYS", "ARG", "GLN", "ASN"}


def _classify_hetatm(resname: str) -> tuple[str, Optional[str], str]:
    """Classify a HETATM residue into ligand, cofactor, or metal."""
    res = resname.upper().strip()

    # Check METAL_ELEMENTS before the generic solvent/ion check: several catalytically
    # important metals (Zn, Mg, Ca, Fe, Mn, Cu, Ni) also appear in the simpler
    # ION_RESIDUES set (used elsewhere for lightweight chain summaries), and would
    # otherwise be misclassified as disposable "solvent" and never reach docking
    # preparation's metal-retention logic.
    if res in METAL_ELEMENTS:
        return "metal", None, "artifact"

    if res in WATER_RESIDUES or res in ION_RESIDUES:
        return "solvent", None, "artifact"

    if res in COFACTOR_RESNAMES or res in COFACTOR_ARTIFACTS:
        classification = COFACTOR_RESNAMES.get(res, "artifact")
        status = "required" if res in REQUIRED_COFACORS else "artifact"
        if res in COFACTOR_ARTIFACTS:
            status = "artifact"
        return "cofactor", classification, status

    # Default: treat as ligand (small molecule / substrate)
    return "ligand", None, "optional"


def _compute_basic_quality_score(report: ReceptorReport) -> tuple[float, str]:
    """Very simple but useful initial quality score (0-100)."""
    score = 70.0  # baseline

    # Resolution penalty
    if report.resolution:
        if report.resolution <= 2.0:
            score += 15
        elif report.resolution <= 2.5:
            score += 8
        elif report.resolution > 3.5:
            score -= 15

    # Missing residues penalty
    missing_penalty = min(len(report.missing_residues) * 3, 25)
    score -= missing_penalty

    # Ligand / active site signal bonus
    if report.ligands:
        score += 8

    # Metal / cofactor presence (context dependent)
    if report.metals:
        score -= 3   # slight penalty because metals complicate scoring

    score = max(0, min(100, score))

    if score >= 85:
        label = "Excellent"
    elif score >= 70:
        label = "Good"
    elif score >= 50:
        label = "Acceptable"
    else:
        label = "Poor"

    return round(score, 1), label


def _parse_missing_residues(pdb_text: str) -> List[Dict[str, Any]]:
    """Parse REMARK 465 lines to detect missing residues in a PDB."""
    missing = []
    for line in pdb_text.splitlines():
        if not line.startswith("REMARK 465"):
            continue
        match = re.match(r"REMARK\s+465\s+M\s+RES\s+(\w+)\s+([A-Za-z0-9_])\s+(-?\d+)", line)
        if not match:
            continue
        resname, chain_id, resnum = match.groups()
        missing.append({
            "chain_id": chain_id,
            "resname": resname,
            "resnum": int(resnum),
            "comment": line.strip()
        })
    return missing


def _metal_context(metal_res, st) -> tuple[List[str], str]:
    """Return coordinating residues and catalytic relevance for a metal site."""
    try:
        metal_atoms = [atom.pos for atom in metal_res]
        coord_residues = []
        catalytic_present = False
        for model in st:
            for chain in model:
                chain_id = chain.name or "_"
                for residue in chain:
                    if residue is metal_res:
                        continue
                    resname = residue.name.upper().strip()
                    if resname in WATER_RESIDUES or resname in ION_RESIDUES:
                        continue

                    closest = float("inf")
                    for atom in residue:
                        for metal_atom in metal_atoms:
                            try:
                                dx = atom.pos.x - metal_atom.x
                                dy = atom.pos.y - metal_atom.y
                                dz = atom.pos.z - metal_atom.z
                                dist = (dx * dx + dy * dy + dz * dz) ** 0.5
                            except Exception:
                                continue
                            if dist < closest:
                                closest = dist
                    if closest <= 3.2:
                        resnum = int(residue.seqid.num) if hasattr(residue.seqid, "num") else 0
                        coord_residues.append(f"{chain_id}:{resnum}")
                        if resname in CATALYTIC_RESIDUES:
                            catalytic_present = True
        relevance = "likely" if catalytic_present else ("possible" if coord_residues else "unknown")
        return coord_residues, relevance
    except Exception:
        return [], "unknown"


def _extract_metadata(st) -> Dict[str, Any]:
    """Extract resolution and experimental method from gemmi structure if available."""
    meta = {"resolution": None, "method": None}

    try:
        if hasattr(st, "resolution") and st.resolution:
            meta["resolution"] = float(st.resolution)
    except Exception:
        pass

    try:
        # gemmi often puts this in info or raw headers
        if hasattr(st, "info"):
            info = st.info
            if isinstance(info, dict):
                meta["method"] = info.get("method") or info.get("experimental_method")
    except Exception:
        pass

    return meta


def analyze_receptor(pdb_text: str) -> ReceptorReport:
    """
    NEW recommended entry point for rich receptor analysis (Phase 1+).

    This function returns a much richer report than the legacy analyze_protein().
    It is designed for publication-quality work and future virtual screening use.

    The legacy analyze_protein() remains fully supported and unchanged.
    """
    if not pdb_text or not pdb_text.strip():
        raise ValueError("PDB text is empty.")

    # Try gemmi first
    try:
        import gemmi
        st = gemmi.read_structure_string(pdb_text)
    except Exception as e:
        logger.warning("gemmi failed in analyze_receptor, falling back: %s", e)
        # For now fall back to old analysis and wrap it
        old = analyze_protein(pdb_text)
        report = ReceptorReport(
            chains=old.chains,
            total_chains=old.total_chains,
            total_residues=old.total_residues,
            total_waters=old.total_waters,
            total_hetero_groups=old.total_hetero_groups,
            num_models=old.num_models,
            format_detected=old.format_detected,
            recommendation=old.recommendation,
            missing_residues=_parse_missing_residues(pdb_text),
        )
        report = attach_quality_to_report(report)
        return report

    # === Rich analysis using gemmi ===
    chains_map: Dict[str, ChainInfo] = {}
    waters = 0
    hetero_names: Set[str] = set()
    ligands: List[LigandInfo] = []
    cofactors: List[CofactorInfo] = []
    metals: List[MetalInfo] = []

    for model in st:
        for chain in model:
            cid = chain.name or "_"
            if cid not in chains_map:
                chains_map[cid] = ChainInfo(chain_id=cid)

            ch = chains_map[cid]
            for res in chain:
                resname = res.name.upper().strip()
                try:
                    resnum = int(res.seqid.num)
                except Exception:
                    resnum = 0

                ch.num_residues += 1

                if resname in STANDARD_AA:
                    ch.num_standard_aa += 1
                    ch.is_likely_protein = True
                elif resname in WATER_RESIDUES:
                    ch.num_waters += 1
                    waters += 1
                else:
                    ch.num_hetero += 1
                    if resname not in WATER_RESIDUES and resname not in ION_RESIDUES:
                        if resname not in ch.hetero_names:
                            ch.hetero_names.append(resname)
                        hetero_names.add(resname)

                    # Classify the hetero group
                    kind, classification, status = _classify_hetatm(resname)

                    if kind == "ligand":
                        centroid = None
                        coords = _parse_coordinates_from_residue(res)
                        if coords:
                            centroid = {
                                "x": sum(c[0] for c in coords) / len(coords),
                                "y": sum(c[1] for c in coords) / len(coords),
                                "z": sum(c[2] for c in coords) / len(coords),
                            }
                        ligands.append(LigandInfo(
                            resname=resname,
                            chain_id=cid,
                            resnum=resnum,
                            num_atoms=len(list(res)),
                            centroid=centroid
                        ))
                    elif kind == "cofactor" and classification:
                        cofactors.append(CofactorInfo(
                            resname=resname,
                            chain_id=cid,
                            resnum=resnum,
                            classification=classification,
                            status=status
                        ))
                    elif kind == "metal":
                        coord_residues, relevance = _metal_context(res, st)
                        metals.append(MetalInfo(
                            resname=resname,
                            chain_id=cid,
                            resnum=resnum,
                            element=resname,
                            coordinating_residues=coord_residues,
                            catalytic_relevance=relevance
                        ))

                # residue range
                if ch.first_resnum is None or resnum < ch.first_resnum:
                    ch.first_resnum = resnum
                if ch.last_resnum is None or resnum > ch.last_resnum:
                    ch.last_resnum = resnum

    chain_list = sorted(chains_map.values(), key=lambda c: c.chain_id or "_")
    total_res = sum(c.num_residues for c in chain_list)
    total_het = sum(c.num_hetero for c in chain_list)

    # Metadata
    meta = _extract_metadata(st)

    report = ReceptorReport(
        chains=chain_list,
        total_chains=len(chain_list),
        total_residues=total_res,
        total_waters=waters,
        total_hetero_groups=total_het,
        num_models=len(st),
        format_detected=_guess_format(pdb_text),
        ligands=ligands,
        cofactors=cofactors,
        metals=metals,
        resolution=meta.get("resolution"),
        experimental_method=meta.get("method"),
        missing_residues=_parse_missing_residues(pdb_text),
        recommendation={},  # will be filled below
    )

    # Reuse the existing (very reasonable) recommendation logic
    # We temporarily wrap it in the old object for reuse
    temp_old = ProteinAnalysis(
        chains=chain_list,
        total_chains=len(chain_list),
        total_residues=total_res,
        total_waters=waters,
        total_hetero_groups=total_het,
        hetero_ligand_names=sorted(hetero_names),
    )
    report.recommendation = _compute_recommendation(temp_old)

    # Quality scoring (Phase 8)
    report = attach_quality_to_report(report)

    logger.info(
        "Receptor analysis complete: chains=%d, ligands=%d, cofactors=%d, metals=%d, quality=%s",
        report.total_chains, len(report.ligands), len(report.cofactors), len(report.metals), report.quality_label
    )

    return report


# =============================================================================
# PHASE 3A — Ligand-Based Binding Site Detection
# =============================================================================

@dataclass
class BindingSiteSuggestion:
    """Suggested binding site derived from a co-crystallized ligand."""
    ligand_resname: str
    ligand_chain: str
    ligand_resnum: int
    centroid: Dict[str, float]          # x, y, z
    radius: float                       # approximate radius of the site
    nearby_residues: List[str]          # e.g. ["A:45", "A:46", "B:12"]
    suggested_grid: GridBoxConfig       # ready-to-use gridbox
    confidence: str = "high"            # high if ligand is clear and complete


def _parse_coordinates_from_residue(res) -> List[tuple]:
    """Extract (x, y, z) from all atoms in a gemmi residue."""
    coords = []
    for atom in res:
        try:
            pos = atom.pos
            coords.append((pos.x, pos.y, pos.z))
        except Exception:
            continue
    return coords


def suggest_binding_site_from_ligand(
    pdb_text: str,
    ligand: LigandInfo,
    margin: float = 6.0,
    contact_cutoff: float = 5.5
) -> Optional[BindingSiteSuggestion]:
    """
    Given a detected ligand from ReceptorReport, compute a high-quality
    binding site definition + recommended gridbox.

    This is the core of Phase 3A (ligand-based active site detection).
    """
    try:
        import gemmi
        from docking_workflow.gridbox_builder import GridBoxConfig
    except ImportError:
        return None

    try:
        st = gemmi.read_structure_string(pdb_text)
    except Exception:
        return None

    ligand_coords = []
    nearby_residues = set()

    for model in st:
        for chain in model:
            if chain.name != ligand.chain_id:
                continue
            for res in chain:
                if res.name.upper().strip() == ligand.resname and int(res.seqid.num) == ligand.resnum:
                    ligand_coords.extend(_parse_coordinates_from_residue(res))

                # Check for nearby protein residues
                if res.name.upper().strip() in STANDARD_AA:
                    res_coords = _parse_coordinates_from_residue(res)
                    for lx, ly, lz in ligand_coords:
                        for rx, ry, rz in res_coords:
                            dist = ((lx-rx)**2 + (ly-ry)**2 + (lz-rz)**2) ** 0.5
                            if dist <= contact_cutoff:
                                nearby_residues.add(f"{chain.name}:{res.seqid.num}")
                                break

    if not ligand_coords:
        return None

    # Compute centroid
    cx = sum(x for x, y, z in ligand_coords) / len(ligand_coords)
    cy = sum(y for x, y, z in ligand_coords) / len(ligand_coords)
    cz = sum(z for x, y, z in ligand_coords) / len(ligand_coords)

    # Estimate radius (max distance from centroid + padding)
    max_dist = 0.0
    for x, y, z in ligand_coords:
        dist = ((x-cx)**2 + (y-cy)**2 + (z-cz)**2) ** 0.5
        if dist > max_dist:
            max_dist = dist

    radius = max_dist + 2.0

    # Suggested gridbox (reasonable default size for a ligand site)
    size = max(20.0, radius * 2 + margin * 2)

    suggested_grid = GridBoxConfig(
        center_x=round(cx, 3),
        center_y=round(cy, 3),
        center_z=round(cz, 3),
        size_x=size,
        size_y=size,
        size_z=size
    )

    return BindingSiteSuggestion(
        ligand_resname=ligand.resname,
        ligand_chain=ligand.chain_id,
        ligand_resnum=ligand.resnum,
        centroid={"x": round(cx, 3), "y": round(cy, 3), "z": round(cz, 3)},
        radius=round(radius, 2),
        nearby_residues=sorted(list(nearby_residues)),
        suggested_grid=suggested_grid,
        confidence="high" if len(ligand_coords) > 5 else "medium"
    )


def detect_ligand_binding_sites(pdb_text: str, report: ReceptorReport) -> List[BindingSiteSuggestion]:
    """
    High-level helper: given a full ReceptorReport, return binding site
    suggestions for all detected ligands.
    """
    suggestions = []
    for ligand in report.ligands:
        site = suggest_binding_site_from_ligand(pdb_text, ligand)
        if site:
            suggestions.append(site)
    return suggestions
