"""
services/clustering_service.py
==============================
Handles hit clustering (Scaffold analysis) for virtual screening.
Uses RDKit Murcko Scaffolds to cluster molecules.
"""

import logging

logger = logging.getLogger(__name__)

def get_murcko_scaffold(smiles: str) -> str:
    """
    Extract the Murcko Scaffold SMILES from an input SMILES.
    Gracefully falls back to original SMILES if RDKit is missing or parsing fails.
    """
    if not smiles:
        return ""
        
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
        
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return smiles
            
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        return Chem.MolToSmiles(scaffold)
    except ImportError:
        logger.warning("RDKit not installed. Clustering will degrade to raw SMILES comparison.")
        return smiles
    except Exception as e:
        logger.error(f"Failed to generate scaffold for {smiles}: {e}")
        return smiles

def cluster_screening_hits(hits: list) -> dict:
    """
    Groups a list of screening hits by their Murcko scaffold.
    Returns a dict mapping Scaffold SMILES -> List of Hits.
    """
    clusters = {}
    for hit in hits:
        scaffold = hit.scaffold_smiles or hit.smiles
        if scaffold not in clusters:
            clusters[scaffold] = []
        clusters[scaffold].append(hit)
    
    # Sort clusters by size
    return dict(sorted(clusters.items(), key=lambda item: len(item[1]), reverse=True))
