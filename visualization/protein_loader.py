import gemmi
from typing import Optional
from .viewer_models import ProteinViewerData


def _guess_structure_format(pdb_text: str, filename: Optional[str] = None) -> str:
    if filename and filename.lower().endswith(".pdbqt"):
        return "pdbqt"

    for line in pdb_text.splitlines():
        if line.startswith(("ROOT", "BRANCH", "ENDBRANCH", "TORSDOF")):
            return "pdbqt"

    return "pdb"


def _fallback_metadata_from_pdb_lines(pdb_text: str):
    chains = set()
    residues = set()
    ligands = set()

    for line in pdb_text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue

        chain_id = line[21:22].strip() or "_"
        residue_number = line[22:26].strip()
        insertion_code = line[26:27].strip()
        residue_name = line[17:20].strip()

        chains.add(chain_id)
        residues.add((chain_id, residue_number, insertion_code, residue_name))
        if line.startswith("HETATM") and residue_name not in {"HOH", "WAT"}:
            ligands.add(residue_name)

    return len(chains), len(residues), ligands


def load_protein_pdb(pdb_text: str, filename: Optional[str] = None) -> ProteinViewerData:
    """
    Parses PDB text using gemmi to extract basic metadata for visualization.
    """
    # gemmi can read from a string using read_structure_string
    # But since PDBQT might fail parsing completely as standard PDB, we fallback gracefully
    structure_format = _guess_structure_format(pdb_text, filename)

    num_chains = 0
    num_residues = 0
    ligands = set()

    try:
        st = gemmi.read_structure_string(pdb_text)

        for model in st:
            num_chains += len(model)
            for chain in model:
                for res in chain:
                    num_residues += 1
                    if res.is_ligand():
                        ligands.add(res.name)
    except Exception:
        num_chains, num_residues, ligands = _fallback_metadata_from_pdb_lines(pdb_text)
                    
    return ProteinViewerData(
        pdb_id=filename or "protein",
        num_chains=num_chains,
        num_residues=num_residues,
        has_ligands=len(ligands) > 0,
        ligand_names=list(ligands),
        structure_format=structure_format,
        pdb_content=pdb_text
    )
