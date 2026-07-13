"""
core/resolver.py
================
Unified molecule input resolution pipeline.

Resolution order:
  1. Try SMILES  (with RDKit stderr silenced for IUPAC-like inputs)
  2. Try InChI
  3. Try IUPAC / common name:
       a. PubChem direct
       b. PubChem fuzzy  (synonyms + CID fallback)
       c. OPSIN REST     (Cambridge)
       d. NCI Cactus     (handles novel lab heterocycles)
       e. External IUPAC2Struct service  (opt-in via IUPAC2STRUCT_URL env var)

Returns a structured ResolutionResult with logging, LRU caching, and timeouts.
Every name resolver validates the returned SMILES with RDKit before accepting it.
"""
from __future__ import annotations

import contextlib
import functools
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import pubchempy as pcp
import requests
from rdkit import Chem
from rdkit.Chem.inchi import MolFromInchi, MolToInchi

from core.openbabel_utils import convert_format

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ResolutionResult:
    input_text: str
    detected_type: Optional[str] = None   # 'smiles' | 'inchi' | 'name'
    canonical_smiles: Optional[str] = None
    inchi: Optional[str] = None           # always populated on success
    inchikey: Optional[str] = None        # always populated on success
    rdkit_mol: Optional[object] = None
    source: Optional[str] = None          # which resolver succeeded
    success: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# RDKit stderr silencer  (suppresses C++-level noise for speculative parsing)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _silence_rdkit_stderr():
    """Redirect RDKit C++ stderr to /dev/null for the duration of the block."""
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    os.close(devnull_fd)
    try:
        yield
    finally:
        os.dup2(old_fd, 2)
        os.close(old_fd)


# ---------------------------------------------------------------------------
# Input-type heuristics
# ---------------------------------------------------------------------------

_IUPAC_TOKENS = re.compile(
    r"\b(azetidin|oxazol|quinoxalin|naphthalen|imidazol|pyrrol|furan|"
    r"thiazol|benzimidazol|indol|carboxamide|carboxylate|hydroxyl|chloro|"
    r"fluoro|bromo|iodo|methyl|ethyl|propyl|butyl|phenyl|benzyl|"
    r"cyclo|spiro|amine|amino|nitro|sulfonyl|phosphor|acetyl|formyl|"
    r"oxo|thio|aza|oxa|diazo|hydrazo|enyl|ylene|idene|ylidene)\b",
    re.IGNORECASE,
)
_SMILES_CHARS = frozenset("=#@[]\\%+/")


def _looks_like_name(text: str) -> bool:
    """Return True when the input is almost certainly an IUPAC/common name."""
    if " " in text:          # names always have spaces; SMILES never do
        return True
    if text.upper().startswith("INCHI="):
        return False         # InChI identifier
    has_smiles = any(c in _SMILES_CHARS for c in text)
    has_iupac  = bool(_IUPAC_TOKENS.search(text))
    return has_iupac and not has_smiles


# ---------------------------------------------------------------------------
# Low-level parsers
# ---------------------------------------------------------------------------

def _parse_smiles(text: str, *, silent: bool = False) -> Optional[Chem.Mol]:
    ctx = _silence_rdkit_stderr() if silent else contextlib.nullcontext()
    try:
        with ctx:
            mol = Chem.MolFromSmiles(text)
        if mol is None:
            return None
        Chem.SanitizeMol(mol)
        return mol
    except Exception as exc:
        logger.debug("SMILES parse failed: %s", exc)
        return None


def _parse_inchi(text: str) -> Optional[Chem.Mol]:
    try:
        mol = MolFromInchi(text)
        return mol
    except Exception as exc:
        logger.debug("InChI parse failed: %s", exc)
        return None


_OPENBABEL_FORMATS = ("mol2", "mol", "sdf", "pdb", "pdbqt", "xyz")


def _guess_openbabel_format(text: str) -> Optional[str]:
    normalized = text.strip()
    lowered = normalized.lower()
    if "@<tripos>molecule" in lowered:
        return "mol2"
    if lowered.startswith("pdbqt"):
        return "pdbqt"
    if "v2000" in lowered and "m  end" in lowered:
        return "mol"
    if normalized.endswith("$$$$") or "> <" in normalized:
        return "sdf"
    first_lines = normalized.splitlines()[:30]
    if any(line.startswith("ATOM") or line.startswith("HETATM") for line in first_lines):
        return "pdb"
    if len(first_lines) > 1:
        header_bits = first_lines[0].split()
        if len(header_bits) == 1 and header_bits[0].isdigit():
            return "xyz"
    return None


@functools.lru_cache(maxsize=512)
def _resolve_via_openbabel(
    text: str,
    timeout: int = 5,
) -> Optional[tuple[str, str]]:
    """Try to resolve a structural input string via Open Babel into canonical SMILES."""
    logger.debug("Attempting Open Babel conversion for input text")

    def _attempt_convert() -> Optional[tuple[str, str]]:
        candidates = []
        guess = _guess_openbabel_format(text)
        if guess:
            candidates.append(guess)
        candidates.extend(fmt for fmt in _OPENBABEL_FORMATS if fmt not in candidates)

        for fmt in candidates:
            try:
                smiles = convert_format(text, fmt, "smi")
            except Exception as exc:
                logger.debug("Open Babel failed for format %s: %s", fmt, exc)
                continue
            if not smiles:
                continue
            smiles = smiles.splitlines()[0].strip()
            mol = _parse_smiles(smiles, silent=True)
            if mol is not None:
                return Chem.MolToSmiles(mol, canonical=True), fmt
        return None

    if timeout is None or timeout <= 0:
        timeout = 5

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_attempt_convert)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            logger.debug("Open Babel conversion timed out after %s seconds", timeout)
            raise TimeoutError("Open Babel conversion timed out") from exc


# ---------------------------------------------------------------------------
# InChI / InChIKey helpers
# ---------------------------------------------------------------------------

def _mol_to_inchi(mol: Chem.Mol) -> Optional[str]:
    try:
        return MolToInchi(mol)
    except Exception:
        return None


def _inchi_to_inchikey(inchi: str) -> Optional[str]:
    try:
        return Chem.InchiToInchiKey(inchi)
    except Exception:
        return None


def _enrich_result(result: ResolutionResult, mol: Chem.Mol) -> None:
    """Populate inchi and inchikey on a successful result (in-place)."""
    inchi = _mol_to_inchi(mol)
    if inchi:
        result.inchi = inchi
        result.inchikey = _inchi_to_inchikey(inchi)


# ---------------------------------------------------------------------------
# Name resolvers  (each returns raw SMILES string or None)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1024)
def _resolve_name_via_pubchem(name: str, timeout: int = 5) -> Optional[str]:
    """Direct PubChem name → canonical SMILES (PubChemPy + REST fallback)."""
    logger.debug("Resolving name via PubChem: %s", name)
    try:
        try:
            compounds = pcp.get_compounds(name, "name")
            if compounds:
                comp = compounds[0]
                smiles = (
                    getattr(comp, "canonical_smiles", None)
                    or getattr(comp, "isomeric_smiles", None)
                    or getattr(comp, "smiles", None)
                )
                if smiles:
                    return smiles
        except Exception as inner:
            logger.debug("PubChemPy lookup failed, falling back to REST: %s", inner)

        url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            f"{requests.utils.quote(name)}/property/CanonicalSMILES/JSON"
        )
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        props = resp.json().get("PropertyTable", {}).get("Properties", [])
        if props:
            return props[0].get("CanonicalSMILES")
    except Exception as exc:
        logger.debug("PubChem resolution failed for %s: %s", name, exc)
    return None


def _resolve_name_via_pubchem_fuzzy(name: str, timeout: int = 5) -> Optional[str]:
    """PubChem synonym + CID fuzzy fallback."""
    logger.debug("Attempting fuzzy PubChem resolution for: %s", name)
    # --- synonym route ---
    try:
        url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            f"{quote(name)}/synonyms/JSON"
        )
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        infos = resp.json().get("InformationList", {}).get("Information", [])
        if infos:
            for synonym in infos[0].get("Synonym", [])[:10]:
                if synonym and synonym.lower() != name.lower():
                    alt = _resolve_name_via_pubchem(synonym, timeout=timeout)
                    if alt:
                        logger.debug("Fuzzy PubChem match via synonym %s", synonym)
                        return alt
    except Exception as exc:
        logger.debug("PubChem fuzzy synonym lookup failed for %s: %s", name, exc)

    # --- CID route ---
    try:
        url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            f"{quote(name)}/cids/JSON"
        )
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        cids = resp.json().get("IdentifierList", {}).get("CID", [])
        if cids:
            cid = cids[0]
            url = (
                "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
                f"{cid}/property/CanonicalSMILES/JSON"
            )
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            props = resp.json().get("PropertyTable", {}).get("Properties", [])
            if props:
                logger.debug("Fuzzy PubChem match via CID %s", cid)
                return props[0].get("CanonicalSMILES")
    except Exception as exc:
        logger.debug("PubChem fuzzy CID lookup failed for %s: %s", name, exc)

    return None


def _resolve_name_via_py2opsin(name: str, timeout: int = 6) -> Optional[str]:
    """Offline OPSIN via the bundled py2opsin jar (requires a JRE).

    Deterministic and instant for systematic IUPAC names — no network needed.
    Imported lazily so a missing package/JRE degrades gracefully to the online
    resolvers. ``timeout`` is accepted for a uniform resolver signature but is
    unused (py2opsin runs locally).
    """
    try:
        from py2opsin import py2opsin
    except Exception as exc:  # noqa: BLE001 - missing dependency is non-fatal
        logger.debug("py2opsin unavailable (%s); falling back to online resolvers", exc)
        return None
    try:
        smiles = py2opsin(name, output_format="SMILES")
        if smiles and smiles.strip():
            return smiles.strip()
    except Exception as exc:  # noqa: BLE001 - OPSIN parse failure is non-fatal
        logger.debug("py2opsin resolution failed for '%s': %s", name, exc)
    return None


def _resolve_name_via_opsin(name: str, timeout: int = 6) -> Optional[str]:
    """OPSIN REST service (University of Cambridge) — online fallback.

    Uses the base endpoint with an ``Accept: chemical/x-daylight-smiles`` header.
    The older ``…/opsin/<name>.smiles`` URL-suffix form returns HTTP 404 for many
    valid names, so it is intentionally not used here.
    """
    try:
        url = f"https://opsin.ch.cam.ac.uk/opsin/{quote(name)}"
        resp = requests.get(
            url, timeout=timeout, headers={"Accept": "chemical/x-daylight-smiles"}
        )
        if resp.status_code == 200 and resp.text.strip():
            return resp.text.strip().splitlines()[0].strip()
    except Exception as exc:
        logger.debug("OPSIN resolution failed for %s: %s", name, exc)
    return None


@functools.lru_cache(maxsize=512)
def _resolve_name_via_cactus(name: str, timeout: int = 8) -> Optional[str]:
    """NCI Cactus Chemical Identifier Resolver.

    Excels at novel heterocyclic lab compounds not yet indexed in PubChem.
    URL pattern: https://cactus.nci.nih.gov/chemical/structure/<name>/smiles
    Returns plain-text SMILES on HTTP 200; anything else → None.
    """
    try:
        url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(name)}/smiles"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.text.strip():
            # Cactus occasionally returns multi-line output; take the first line
            smiles = resp.text.strip().splitlines()[0].strip()
            logger.debug("Cactus resolved '%s' -> %s", name, smiles)
            return smiles
        logger.debug("Cactus returned HTTP %s for '%s'", resp.status_code, name)
    except requests.exceptions.Timeout:
        logger.debug("Cactus timed out for '%s'", name)
    except Exception as exc:
        logger.debug("Cactus resolution failed for '%s': %s", name, exc)
    return None


def _resolve_name_via_iupac2struct(name: str, timeout: int = 8) -> Optional[str]:
    """External IUPAC2Struct REST service (opt-in via IUPAC2STRUCT_URL env var).

    POST JSON {'name': name}  →  JSON response with a 'smiles' field.
    Skipped silently when the env var is not set.
    """
    base = os.environ.get("IUPAC2STRUCT_URL")
    if not base:
        return None
    base = base.rstrip("/")
    headers = {"Content-Type": "application/json"}
    for endpoint in (f"{base}/predict", f"{base}/convert", base):
        try:
            logger.debug("Calling IUPAC2Struct endpoint %s for '%s'", endpoint, name)
            resp = requests.post(
                endpoint, json={"name": name}, timeout=timeout, headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                smiles = (
                    data.get("smiles")
                    or data.get("canonical_smiles")
                    or data.get("smile")
                )
                if smiles:
                    return smiles
        except Exception as exc:
            logger.debug(
                "IUPAC2Struct call failed for '%s' at %s: %s", name, endpoint, exc
            )
    return None


# ---------------------------------------------------------------------------
# Reverse conversion: SMILES → IUPAC name  (display / UI helper)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=512)
def smiles_to_iupac_name(smiles: str, timeout: int = 8) -> Optional[str]:
    """Convert a canonical SMILES string to an IUPAC name via NCI Cactus.

    Best-effort: returns None on failure rather than raising.
    Suitable for UI display; not suitable for authoritative naming.
    """
    try:
        url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(smiles)}/iupac_name"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text.strip().splitlines()[0]
    except Exception as exc:
        logger.debug("Cactus SMILES→IUPAC failed for '%s': %s", smiles, exc)
    return None


# ---------------------------------------------------------------------------
# Unified name-to-SMILES dispatcher
# ---------------------------------------------------------------------------

def _resolve_name_to_smiles_with_source(
    name: str, *, timeout: int = 8
) -> tuple[str, str]:
    """Try every name resolver in order; return (canonical_smiles, source_label).

    Resolution order:
      1. py2opsin       ← offline OPSIN; instant for systematic IUPAC names
      2. PubChem direct
      3. PubChem fuzzy  (synonyms + CID)
      4. OPSIN REST     (online fallback if py2opsin is unavailable)
      5. NCI Cactus     ← handles novel lab heterocycles
      6. External IUPAC2Struct service  (requires IUPAC2STRUCT_URL env var)

    Raises ValueError with a descriptive message when all resolvers fail.
    """
    text = (name or "").strip()
    if not text:
        raise ValueError("Empty name provided")

    _steps = [
        ("py2opsin",      lambda: _resolve_name_via_py2opsin(text, timeout=min(6, timeout))),
        ("pubchem",       lambda: _resolve_name_via_pubchem(text, timeout=min(5, timeout))),
        ("pubchem-fuzzy", lambda: _resolve_name_via_pubchem_fuzzy(text, timeout=min(6, timeout))),
        ("opsin",         lambda: _resolve_name_via_opsin(text, timeout=min(6, timeout))),
        ("cactus",        lambda: _resolve_name_via_cactus(text, timeout=min(8, timeout))),
        ("iupac2struct",  lambda: _resolve_name_via_iupac2struct(text, timeout=timeout)),
    ]

    for source_label, resolver_fn in _steps:
        smiles = resolver_fn()
        if not smiles:
            continue
        mol = _parse_smiles(smiles, silent=True)
        if mol is not None:
            return Chem.MolToSmiles(mol, canonical=True), source_label
        # Resolver returned something but RDKit rejected it — log and continue
        logger.debug(
            "%s returned unparsable SMILES for '%s': %s", source_label, name, smiles
        )

    raise ValueError(
        f"Could not resolve name '{name}' via OPSIN, PubChem, Cactus or IUPAC2Struct."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_molecule_input(
    input_text: str, *, pubchem_timeout: int = 5
) -> ResolutionResult:
    """Resolve any molecule input (SMILES, InChI, or IUPAC/common name) to a
    validated RDKit Mol with canonical SMILES, InChI, and InChIKey.

    Resolution order:  SMILES → InChI → name (PubChem / OPSIN / Cactus / IUPAC2Struct)
    """
    raw_text = input_text or ""
    text = raw_text.strip()
    result = ResolutionResult(input_text=text)

    if not text:
        result.error = "Empty input"
        return result

    looks_like_name = _looks_like_name(text)

    # 1) SMILES  (suppress C++ stderr for obvious IUPAC-style strings)
    mol = _parse_smiles(text, silent=looks_like_name)
    if mol is not None:
        try:
            smiles = Chem.MolToSmiles(mol, canonical=True)
            result.detected_type  = "smiles"
            result.canonical_smiles = smiles
            result.rdkit_mol = mol
            result.source    = "smiles"
            result.success   = True
            _enrich_result(result, mol)
            logger.info("Resolved input as SMILES: %s -> %s", text, smiles)
            return result
        except Exception as exc:
            logger.debug("SMILES canonicalization failed: %s", exc)

    # 2) InChI
    if text.upper().startswith("INCHI="):
        mol = _parse_inchi(text)
        if mol is not None:
            try:
                smiles = Chem.MolToSmiles(mol, canonical=True)
                result.detected_type  = "inchi"
                result.canonical_smiles = smiles
                result.rdkit_mol = mol
                result.source    = "inchi"
                result.success   = True
                _enrich_result(result, mol)
                logger.info("Resolved input as InChI: %s -> %s", text, smiles)
                return result
            except Exception as exc:
                logger.debug("InChI canonicalization failed: %s", exc)

    # 3) Open Babel conversion for structural formats
    try:
        openbabel_result = _resolve_via_openbabel(
            raw_text, timeout=min(pubchem_timeout, 8)
        )
        if openbabel_result is not None:
            smiles, fmt = openbabel_result
            mol = _parse_smiles(smiles, silent=True)
            if mol is not None:
                canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
                result.detected_type = "openbabel"
                result.canonical_smiles = canonical_smiles
                result.rdkit_mol = mol
                result.source = f"openbabel-{fmt}"
                result.success = True
                _enrich_result(result, mol)
                logger.info(
                    "Resolved input via Open Babel %s: %s -> %s",
                    fmt,
                    text[:80].replace("\n", " "),
                    canonical_smiles,
                )
                return result
            logger.debug(
                "Open Babel conversion produced unparsable SMILES: %s", smiles
            )
    except TimeoutError as exc:
        logger.debug("Open Babel conversion timed out: %s", exc)
    except Exception as exc:
        logger.debug("Open Babel conversion failed: %s", exc)

    # 4) Name → SMILES pipeline
    try:
        smiles, source = _resolve_name_to_smiles_with_source(
            text, timeout=pubchem_timeout
        )
        mol = _parse_smiles(smiles, silent=True)
        if mol is not None:
            result.detected_type  = "name"
            result.canonical_smiles = smiles
            result.rdkit_mol = mol
            result.source    = source
            result.success   = True
            _enrich_result(result, mol)
            logger.info("Resolved name via %s: %s -> %s", source, text, smiles)
            return result
        result.error = f"Name resolver ({source}) returned unparsable SMILES: {smiles}"
    except Exception as exc:
        logger.debug("Name resolution attempt failed: %s", exc)
        result.error = str(exc)

    if result.error is None:
        result.error = "Could not resolve input as SMILES, InChI or IUPAC name"
    logger.warning("Resolution failed for '%s': %s", text, result.error)
    return result


def resolve_name_to_smiles(name: str, *, timeout: int = 8) -> str:
    """Resolve an IUPAC/common name to a canonical SMILES string.

    Order: PubChem → PubChem fuzzy → OPSIN → Cactus → IUPAC2Struct.
    Raises ValueError with a clear message if all resolvers fail.
    """
    smiles, _source = _resolve_name_to_smiles_with_source(name, timeout=timeout)
    return smiles


__all__ = [
    "ResolutionResult",
    "resolve_molecule_input",
    "resolve_name_to_smiles",
    "smiles_to_iupac_name",
]


# ---------------------------------------------------------------------------
# Quick smoke-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _test_cases = [
        "aspirin",
        "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
        "O=C(Oc1ccccc1C(=O)O)C",
        "N-(3-chloro-2-(naphthalen-1-yl)-4-oxoazetidin-1-yl)-3-hydroxyquinoxaline-2-carboxamide",
    ]
    for _t in _test_cases:
        _r = resolve_molecule_input(_t)
        if _r.success:
            print(f"[OK] {_r.source:15s}  SMILES: {_r.canonical_smiles}")
            print(f"                    InChI:  {_r.inchi}")
        else:
            print(f"[FAIL] {_t[:60]}  -> {_r.error}")
