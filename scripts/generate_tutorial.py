import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("# Chemistry Companion — Quick Start & API Tutorial\n\nThis notebook demonstrates how to use the core APIs of **Chemistry Companion** for structural analysis, spectral prediction, and descriptor generation."),
    
    nbf.v4.new_markdown_cell("## 1. Loading Molecules\n\nThe `core.molecule_utils` package provides robust parsing for SMILES and other formats."),
    
    nbf.v4.new_code_cell("from core.molecule_utils import load_molecule\n\n# Load aspirin\nmol_rec = load_molecule('CC(=O)OC1=CC=CC=C1C(=O)O')\nprint(f'Name: {mol_rec.name}')\nprint(f'Formula: {mol_rec.formula}')\nprint(f'Exact Mass: {mol_rec.exact_mass:.2f}')"),
    
    nbf.v4.new_markdown_cell("## 2. Functional Group Detection\n\nDetect complex semantic functional groups out-of-the-box (27 standard categories)."),
    
    nbf.v4.new_code_cell("from spectra.functional_group_detector import detect_functional_groups\n\nfg_report = detect_functional_groups(mol_rec.rdkit_mol)\nprint('Detected Groups:')\nfor match in fg_report.matches:\n    print(f'- {match.name} (Count: {match.count})')"),
    
    nbf.v4.new_markdown_cell("## 3. Spectral Prediction (IR & NMR)\n\nPredict IR bands, ¹H NMR, and ¹³C NMR spectra using heuristic rules."),
    
    nbf.v4.new_code_cell("from spectra.ir_predictor import predict_ir\nfrom spectra.proton_nmr import predict_proton_nmr\nfrom spectra.carbon_nmr import predict_carbon_nmr\n\nir_pred = predict_ir(mol_rec.rdkit_mol)\nprint('IR Bands:\\n' + '-'*30)\nfor band in ir_pred.bands:\n    print(f'{band.label}: {band.lower_cm1}-{band.upper_cm1} cm⁻¹ ({band.intensity})')\n\nprint('\\n\\n¹H NMR Signals:\\n' + '-'*30)\nh_pred = predict_proton_nmr(mol_rec.rdkit_mol)\nfor signal in h_pred.signals:\n    print(f'{signal.shift_ppm} ppm | {signal.multiplicity} | {signal.label}')\n\nprint('\\n\\n¹³C NMR Environments:\\n' + '-'*30)\nc_pred = predict_carbon_nmr(mol_rec.rdkit_mol)\nfor env in c_pred.environments:\n    print(f'{env.shift_ppm} ppm | {env.label}')"),
    
    nbf.v4.new_markdown_cell("## 4. Using the Full Pipeline\n\nThe `ChemistryPipeline` orchestrates parsing, descriptors, functional groups, and spectral predictions into a single structured `AnalysisResult`."),
    
    nbf.v4.new_code_cell("from core.pipeline import ChemistryPipeline\nfrom core.config import get_settings\n\npipeline = ChemistryPipeline(settings=get_settings())\nresult = pipeline.process_smiles('c1ccccc1') # Benzene\n\nprint(f'Descriptors computed: {len(result.descriptors.to_dict())}')\nprint(f'IR Prediction summary:\\n{result.ir_prediction.summary_text}')"),
    
    nbf.v4.new_markdown_cell("## 5. Docking Preparation\n\nPrepare 3D structures and assign Gasteiger charges natively for AutoDock Vina."),
    
    nbf.v4.new_code_cell("from core.docking_preparation import prepare_docking_structure\n\n# Generates 3D coordinates, adds hydrogens at pH 7.4, and saves PDBQT\nresult = prepare_docking_structure('CC(=O)O', output_dir='data/', filename_prefix='acetic_acid')\nprint(f'Generated PDBQT: {result}')")
]

with open('tutorial.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)
print("tutorial.ipynb created!")
