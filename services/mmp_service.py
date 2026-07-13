"""
services/mmp_service.py
=======================
Abstracts the Matched Molecular Pair (MMP) analysis engine.
Uses RDKit's rdFMCS to find the Maximum Common Substructure (MCS),
and computes the difference in fragments (e.g. H -> Cl) as well as the 
observed delta in properties and activity.
"""

import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from database.models import SeriesCompound

logger = logging.getLogger(__name__)

class MMPEngine:
    def __init__(self, db: Session):
        self.db = db

    def _extract_diff(self, mol1, mol2, mcs) -> Tuple[str, str]:
        """
        Extracts the real R-group difference between mol1 and mol2 given their
        Maximum Common Substructure (the rdFMCS result ``mcs``).

        Strategy: match the MCS core onto each molecule; the atoms NOT covered by
        that match are the differing substituent(s). Those atoms are serialized to
        SMILES, giving a concrete transformation such as ``H -> Cl`` or ``C -> OC``.
        Falls back to generic labels only if RDKit or the match is unavailable.
        """
        try:
            from rdkit import Chem

            core = Chem.MolFromSmarts(mcs.smartsString) if getattr(mcs, "smartsString", None) else None
            if core is None:
                return ("R1", "R2")

            frag1 = self._diff_smiles(mol1, core)
            frag2 = self._diff_smiles(mol2, core)

            if frag1 is None or frag2 is None:
                return ("R1", "R2")

            return (frag1 or "H", frag2 or "H")
        except Exception as e:
            logger.error(f"Error extracting diff: {e}")
            return ("R1", "R2")

    def _diff_smiles(self, mol, core):
        """
        Returns the SMILES of the atoms in ``mol`` that fall outside the common
        ``core`` match (i.e. the substituent that differs). Returns "H" when the
        molecule is exactly the core (no extra atoms), or None if the core does
        not match.
        """
        from rdkit import Chem
        match = mol.GetSubstructMatch(core)
        if not match:
            return None
        match_set = set(match)
        diff_atoms = [a.GetIdx() for a in mol.GetAtoms() if a.GetIdx() not in match_set]
        if not diff_atoms:
            return "H"
        try:
            return Chem.MolFragmentToSmiles(mol, atomsToUse=diff_atoms, canonical=True)
        except Exception:
            return None

    def find_mmps(self, series_id: str) -> List[Dict[str, Any]]:
        """
        Cross-compares all compounds in a series to find MMPs.
        """
        compounds = self.db.query(SeriesCompound).filter_by(series_id=series_id).all()
        if len(compounds) < 2:
            return []
            
        mmps = []
        
        try:
            from rdkit import Chem
            from rdkit.Chem import rdFMCS
            
            # Create mol objects
            mols = []
            for c in compounds:
                mol = Chem.MolFromSmiles(c.smiles)
                if mol:
                    mols.append((c, mol))
                    
            # O(N^2) comparison - fine for small MedChem series (<1000 cmpds)
            for i in range(len(mols)):
                for j in range(i + 1, len(mols)):
                    c1, m1 = mols[i]
                    c2, m2 = mols[j]
                    
                    res = rdFMCS.FindMCS([m1, m2], timeout=1)
                    if res.numAtoms == 0:
                        continue
                        
                    ratio1 = res.numAtoms / m1.GetNumAtoms()
                    ratio2 = res.numAtoms / m2.GetNumAtoms()
                    
                    # If they share 75%+ core, consider it an MMP
                    if ratio1 >= 0.75 and ratio2 >= 0.75:
                        frag1, frag2 = self._extract_diff(m1, m2, res)
                        
                        # Calculate deltas
                        delta_pic50 = None
                        if c1.normalized_value is not None and c2.normalized_value is not None:
                            delta_pic50 = round(c2.normalized_value - c1.normalized_value, 2)
                            
                        p1_logp = c1.properties.get('logp', 0) if c1.properties else 0
                        p2_logp = c2.properties.get('logp', 0) if c2.properties else 0
                        delta_logp = round(p2_logp - p1_logp, 2)
                        
                        mmps.append({
                            "cmpd1_id": c1.id,
                            "cmpd1_name": c1.name,
                            "cmpd2_id": c2.id,
                            "cmpd2_name": c2.name,
                            "transformation": f"{frag1} -> {frag2}",
                            "delta_pic50": delta_pic50,
                            "delta_logp": delta_logp
                        })
                        
        except ImportError:
            logger.warning("RDKit not installed. MMP detection skipped.")
            
        return mmps
