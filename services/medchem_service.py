"""
services/medchem_service.py
===========================
Calculates MedChem properties using RDKit.
Computes MW, LogP, TPSA, HBD, HBA, Rotatable Bonds, Fsp3, and Synthetic Accessibility (SAScore).
Evaluates Lipinski and Veber rules.
Includes basic Matched Molecular Pair (MMP) detection.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from database.models import ChemicalSeries, SeriesCompound

logger = logging.getLogger(__name__)

def calculate_properties(smiles: str) -> Dict[str, Any]:
    """Calculates all RDKit-based properties for a SMILES string."""
    if not smiles:
        return {}
        
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
        from rdkit.Chem import rdMolDescriptors
        from rdkit.Chem import Lipinski
        
        # We also need SAScore. RDkit provides it in Contrib usually, or we can use a stub if unavailable.
        try:
            from rdkit.Chem.RDConfig import RDDataDir
            import sys
            import os
            sys.path.append(os.path.join(RDDataDir, 'Contrib', 'SA_Score'))
            import sascorer
            has_sascorer = True
        except ImportError:
            has_sascorer = False

        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return {}

        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        tpsa = Descriptors.TPSA(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rot_bonds = Lipinski.NumRotatableBonds(mol)
        fsp3 = rdMolDescriptors.CalcFractionCSP3(mol)
        
        # Synthetic Accessibility (1-10, lower is easier)
        sa_score = None
        sa_category = "Unknown"
        if has_sascorer:
            try:
                sa_score = sascorer.calculateScore(mol)
                if sa_score <= 3:
                    sa_category = "High"
                elif sa_score <= 6:
                    sa_category = "Moderate"
                else:
                    sa_category = "Low"
            except Exception as e:
                logger.warning(f"Failed to calculate SAScore: {e}")

        # Lipinski Rule of 5 violations
        lipinski_violations = sum([
            1 if mw > 500 else 0,
            1 if logp > 5 else 0,
            1 if hbd > 5 else 0,
            1 if hba > 10 else 0
        ])
        
        # Veber Rules (TPSA <= 140, Rotatable Bonds <= 10)
        veber_violations = sum([
            1 if tpsa > 140 else 0,
            1 if rot_bonds > 10 else 0
        ])
        
        # Ring Count
        ring_count = mol.GetRingInfo().NumRings()
        
        # Ghose Filter
        molar_refractivity = Descriptors.MolMR(mol)
        num_atoms = mol.GetNumAtoms()
        ghose_pass = (160 <= mw <= 480) and (-0.4 <= logp <= 5.6) and (40 <= molar_refractivity <= 130) and (20 <= num_atoms <= 70)
        
        # Egan Filter
        egan_pass = (logp <= 5.88) and (tpsa <= 131.6)
        
        # Muegge Filter
        num_carbons = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6)
        num_hetero = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in (1, 6))
        muegge_pass = (200 <= mw <= 600) and (-2 <= logp <= 5) and (tpsa <= 150) and (ring_count <= 7) and (num_carbons > 4) and (num_hetero > 1) and (rot_bonds <= 15) and (hba <= 10) and (hbd <= 5)

        return {
            "mw": round(mw, 2),
            "logp": round(logp, 2),
            "tpsa": round(tpsa, 2),
            "hbd": hbd,
            "hba": hba,
            "rotatable_bonds": rot_bonds,
            "fsp3": round(fsp3, 2),
            "ring_count": ring_count,
            "sa_score": round(sa_score, 2) if sa_score else None,
            "sa_category": sa_category,
            "lipinski_violations": lipinski_violations,
            "lipinski_pass": lipinski_violations <= 1,
            "veber_violations": veber_violations,
            "veber_pass": veber_violations == 0,
            "ghose_pass": ghose_pass,
            "egan_pass": egan_pass,
            "muegge_pass": muegge_pass
        }
    except ImportError:
        logger.warning("RDKit not installed. Property calculation skipped.")
        return {}
    except Exception as e:
        logger.error(f"Error calculating properties for {smiles}: {e}")
        return {}


def detect_mmp(smiles1: str, smiles2: str) -> bool:
    """
    Coarse boolean pre-filter for Matched Molecular Pair candidates.
    Returns True if the maximum common substructure (MCS) covers >= 75% of both
    molecules. For the full transformation analysis (actual R-group diffs and
    property deltas) use services/mmp_service.py MMPEngine.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS
        
        mol1 = Chem.MolFromSmiles(smiles1)
        mol2 = Chem.MolFromSmiles(smiles2)
        if not mol1 or not mol2: return False
        
        res = rdFMCS.FindMCS([mol1, mol2], timeout=1)
        if res.numAtoms == 0: return False
        
        # Check if MCS is large enough
        ratio1 = res.numAtoms / mol1.GetNumAtoms()
        ratio2 = res.numAtoms / mol2.GetNumAtoms()
        
        return ratio1 >= 0.75 and ratio2 >= 0.75
    except ImportError:
        return False


class MedchemService:
    def __init__(self, db: Session):
        self.db = db

    def get_series(self, series_id: str) -> Optional[ChemicalSeries]:
        return self.db.query(ChemicalSeries).filter_by(id=series_id).first()

    def list_series(self) -> List[Dict[str, Any]]:
        series = self.db.query(ChemicalSeries).order_by(ChemicalSeries.updated_at.desc()).all()
        return [s.to_dict() for s in series]

    def create_series(self, name: str, target_name: str, notes: str = "") -> ChemicalSeries:
        series_id = f"ser_{uuid.uuid4().hex[:12]}"
        series = ChemicalSeries(id=series_id, name=name, target_name=target_name, notes=notes)
        self.db.add(series)
        self.db.commit()
        self.db.refresh(series)
        return series

    def add_compound(self, series_id: str, smiles: str, name: str, ic50: Optional[float] = None, pic50: Optional[float] = None, docking_affinity: Optional[str] = None, screening_hit_id: Optional[str] = None) -> SeriesCompound:
        # Legacy method to maintain compatibility with Phase 9 tests/UI
        # Map it to the advanced method
        act_val = pic50 if pic50 is not None else ic50
        act_type = "pIC50" if pic50 is not None else "IC50" if ic50 is not None else None
        act_unit = "" if pic50 is not None else "nM" if ic50 is not None else None
        
        normalized = None
        if pic50 is not None:
            normalized = pic50
        elif ic50 is not None and ic50 > 0:
            import math
            normalized = 9 - math.log10(ic50)
            
        return self.add_compound_advanced(
            series_id=series_id,
            smiles=smiles,
            name=name,
            activity_type=act_type,
            activity_value=act_val,
            activity_unit=act_unit,
            normalized_value=normalized,
            docking_affinity=docking_affinity,
            screening_hit_id=screening_hit_id
        )

    def add_compound_advanced(
        self, 
        series_id: str, 
        smiles: str, 
        name: str, 
        activity_type: Optional[str] = None,
        activity_value: Optional[float] = None,
        activity_unit: Optional[str] = None,
        normalized_value: Optional[float] = None,
        docking_affinity: Optional[str] = None,
        screening_hit_id: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> SeriesCompound:
        compound_id = f"cmp_{uuid.uuid4().hex[:12]}"
        
        properties = calculate_properties(smiles)
        
        # Phase 10: ADMET Integration
        from services.admet_service import calculate_admet_heuristics
        admet = calculate_admet_heuristics(smiles, properties)
        properties['admet'] = admet

        compound = SeriesCompound(
            id=compound_id,
            series_id=series_id,
            smiles=smiles,
            name=name,
            activity_type=activity_type,
            activity_value=activity_value,
            activity_unit=activity_unit,
            normalized_value=normalized_value,
            docking_affinity=docking_affinity,
            screening_hit_id=screening_hit_id,
            properties=properties,
            notes=notes,
            tags=tags or []
        )
        self.db.add(compound)
        
        # Update series updated_at
        series = self.get_series(series_id)
        if series:
            series.updated_at = datetime.utcnow()
            
        self.db.commit()
        self.db.refresh(compound)
        return compound
        
    def get_compounds(self, series_id: str) -> List[Dict[str, Any]]:
        compounds = self.db.query(SeriesCompound).filter_by(series_id=series_id).all()
        return [c.to_dict() for c in compounds]
