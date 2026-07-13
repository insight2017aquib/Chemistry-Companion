from rdkit import Chem
from core.docking_preparation import prepare_docking_structure
smiles = 'O=C(NN1C(=O)C(Cl)C1c1ccc(Cl)cc1Cl)c1nc2ccccc2nc1O'
pdbqt = prepare_docking_structure(smiles, output_format='pdbqt')
print('SUCCESS! Length:', len(pdbqt))
