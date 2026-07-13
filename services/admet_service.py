"""
services/admet_service.py
=========================
Heuristic engine for predicting ADMET risks, developability scores, and identifying Structural Alerts (PAINS/Brenk).
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Very basic SMARTS for demonstration of Toxicophores / PAINS / Brenk
# In a production environment, you would use RDKit's built-in PAINS filters (rdkit.Chem.FilterCatalog)
STRUCTURAL_ALERTS = [
    {"name": "Quinone", "smarts": "O=C1C=CC(=O)C=C1", "type": "PAINS", "description": "Highly reactive Michael acceptor / Redox cycler"},
    {"name": "Nitroaromatic", "smarts": "c1([N+](=O)[O-])ccccc1", "type": "Brenk", "description": "Associated with mutagenicity (Ames positive)"},
    {"name": "Aliphatic Halide", "smarts": "[CX4][F,Cl,Br,I]", "type": "Brenk", "description": "Potential alkylating agent (hepatotoxicity risk)"},
    {"name": "Thiol", "smarts": "[SH]", "type": "Brenk", "description": "Reactive nucleophile, high risk of off-target binding"}
]

def calculate_admet_heuristics(smiles: str, physchem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates heuristic ADMET risks based on computed physicochemical properties.
    Returns the metric and an explanation string.
    """
    results = {}
    
    mw = physchem.get('mw', 0)
    logp = physchem.get('logp', 0)
    tpsa = physchem.get('tpsa', 0)
    rot = physchem.get('rotatable_bonds', 0)
    hbd = physchem.get('hbd', 0)
    
    # Solubility (LogS proxy)
    # Heuristic: High MW + High LogP = Poor Solubility
    if logp > 4.5 and mw > 400:
        results['solubility'] = {"risk": "High", "explanation": f"High lipophilicity (LogP {logp}) and MW ({mw}) typically result in poor aqueous solubility."}
    elif logp < 2 and mw < 350:
        results['solubility'] = {"risk": "Low", "explanation": "Low MW and hydrophilic nature predict good aqueous solubility."}
    else:
        results['solubility'] = {"risk": "Moderate", "explanation": "Moderate properties suggest acceptable solubility."}

    # Permeability (Caco-2 / PAMPA proxy)
    # Heuristic: High TPSA and HBD = Poor Permeability
    if tpsa > 120 or hbd > 4:
        results['permeability'] = {"risk": "High", "explanation": f"High TPSA ({tpsa}) and/or H-bond donors ({hbd}) restrict passive membrane permeability."}
    else:
        results['permeability'] = {"risk": "Low", "explanation": "Low polar surface area facilitates passive diffusion."}

    # Blood Brain Barrier (BBB)
    # Heuristic: Egan Rule (LogP < 5.88, TPSA < 131.6) but BBB specifically requires tighter bounds (LogP 2-5, TPSA < 90)
    if 2.0 <= logp <= 5.0 and tpsa < 90:
        results['bbb'] = {"risk": "High Penetration", "explanation": "Optimal lipophilicity and low TPSA predict high CNS penetration."}
    else:
        results['bbb'] = {"risk": "Low Penetration", "explanation": "Properties fall outside optimal CNS space; peripheral restriction likely."}

    # hERG Risk (Cardiotoxicity)
    # Heuristic: High LogP + basic amine (approximated here simply by high LogP and MW, assuming typical kinase/GPCR ligands)
    if logp > 3.5 and mw > 350:
        results['herg'] = {"risk": "Moderate to High", "explanation": "Lipophilic, heavy compounds carry an increased risk of hERG channel blockade."}
    else:
        results['herg'] = {"risk": "Low", "explanation": "Low lipophilicity mitigates promiscuous hERG binding."}

    # Toxicophores (PAINS / Brenk)
    alerts = []
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            for alert in STRUCTURAL_ALERTS:
                patt = Chem.MolFromSmarts(alert['smarts'])
                if patt and mol.HasSubstructMatch(patt):
                    alerts.append(alert)
    except ImportError:
        pass
        
    results['alerts'] = alerts
    
    # Developability Ranking (0-10)
    # Start at 10, subtract points for liabilities
    score = 10.0
    if results['solubility']['risk'] == 'High': score -= 1.5
    if results['permeability']['risk'] == 'High': score -= 1.5
    if results['herg']['risk'] == 'Moderate to High': score -= 2.0
    score -= len(alerts) * 1.5
    
    # Bound score between 0 and 10
    score = max(0.0, min(10.0, score))
    
    results['developability_score'] = round(score, 1)
    
    if score >= 8.0:
        results['developability_rank'] = "Excellent"
    elif score >= 5.0:
        results['developability_rank'] = "Fair"
    else:
        results['developability_rank'] = "Poor"

    return results
