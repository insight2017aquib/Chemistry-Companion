"""
services/bioisostere_service.py
===============================
Provides curated, rule-based bioisostere replacements.
Used by the Analog Designer to suggest classic MedChem optimizations.
"""

from typing import List, Dict

# Curated dictionary of classic bioisosteres.
# In a full system, this would be SMARTS-based transformations.
# For simplicity, we match literal SMILES fragments or names.
BIOISOSTERES = [
    {
        "target_group": "Carboxylic Acid",
        "smarts": "C(=O)O",
        "replacements": [
            {"smiles": "c1nnnHc1", "name": "Tetrazole", "rationale": "Similar pKa, better membrane permeability, improved metabolic stability."},
            {"smiles": "C(=O)NS(=O)(=O)C", "name": "Acylsulfonamide", "rationale": "Tunable pKa, increased lipophilicity."},
            {"smiles": "C1=C(O)C(=O)C=C1", "name": "Hydroxyisoxazole", "rationale": "Reduced polarity while maintaining hydrogen bond donor/acceptor geometry."}
        ]
    },
    {
        "target_group": "Amide",
        "smarts": "C(=O)N",
        "replacements": [
            {"smiles": "c1cnoc1", "name": "1,2,4-Oxadiazole", "rationale": "Metabolically stable, restricts conformation, maintains H-bond acceptor."},
            {"smiles": "N(C)C(=O)", "name": "Reverse Amide", "rationale": "Can evade specific proteolytic cleavage while maintaining overall geometry."},
            {"smiles": "C(F)(F)", "name": "Difluoromethylene", "rationale": "Removes H-bond donor, increases lipophilicity, stereoelectronically similar."}
        ]
    },
    {
        "target_group": "Phenyl",
        "smarts": "c1ccccc1",
        "replacements": [
            {"smiles": "c1ccncc1", "name": "Pyridine", "rationale": "Lowers LogP, introduces H-bond acceptor, can improve aqueous solubility."},
            {"smiles": "c1sccc1", "name": "Thiophene", "rationale": "Similar volume, more electron-rich, often avoids planar-stacking toxicities."},
            {"smiles": "C1CCCC1", "name": "Cyclopentyl", "rationale": "Reduces aromaticity (increases Fsp3), improves solubility and flexibility."}
        ]
    }
]

def suggest_replacements(smiles: str) -> List[Dict]:
    """
    Given a SMILES, identify functional groups and suggest bioisosteres.
    """
    suggestions = []
    
    if not smiles:
        return suggestions
        
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return suggestions
            
        for rule in BIOISOSTERES:
            target_smarts = rule["smarts"]
            patt = Chem.MolFromSmarts(target_smarts)
            if patt and mol.HasSubstructMatch(patt):
                suggestions.append({
                    "target_group": rule["target_group"],
                    "replacements": rule["replacements"]
                })
    except ImportError:
        # Fallback to simple string matching if RDKit is missing
        if "C(=O)O" in smiles or "c(=o)o" in smiles.lower():
            suggestions.append(BIOISOSTERES[0])
        if "c1ccccc1" in smiles:
            suggestions.append(BIOISOSTERES[2])
            
    return suggestions
