import logging

from core.visualization_utils import mol_to_3d_html
from rdkit import Chem
from rdkit.Chem import AllChem

logger = logging.getLogger(__name__)


def build_ligand_3d_mol(smiles: str) -> Chem.Mol:
    """
    Build an RDKit molecule with a 3D conformer from a SMILES string.
    """
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError("Invalid SMILES")

    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42

    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        raise ValueError("3D embedding failed for the input ligand.")

    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception as exc:
        logger.debug("MMFF optimization failed or was skipped: %s", exc)

    return mol


def ligand_mol_to_mol_block(mol: Chem.Mol) -> str:
    """
    Convert a 3D RDKit molecule to a MolBlock that 3Dmol.js can render directly.
    """
    return Chem.MolToMolBlock(mol)


def generate_ligand_mol_block(smiles: str) -> str:
    """
    Generate a 3D MolBlock for client-side 3Dmol.js rendering.
    """
    try:
        return ligand_mol_to_mol_block(build_ligand_3d_mol(smiles))
    except Exception:
        logger.exception("Error generating 3D ligand MolBlock")
        return ""


def render_ligand_3d_from_mol(mol: Chem.Mol) -> str:
    """
    Render an already embedded ligand as a py3Dmol HTML document/snippet.
    """
    return mol_to_3d_html(mol, width=500, height=400)


def render_ligand_3d(smiles: str) -> str:
    """
    Renders a 3D py3Dmol HTML snippet of a ligand SMILES.
    Uses existing core.visualization_utils.
    """
    try:
        return render_ligand_3d_from_mol(build_ligand_3d_mol(smiles))
    except Exception as e:
        logger.exception("Error rendering 3D ligand")
        return f"<div class='text-red-500'>Error: {str(e)}</div>"
