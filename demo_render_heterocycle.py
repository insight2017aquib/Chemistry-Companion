# demo_render_heterocycle.py
from rdkit import Chem
from chemistry_companion.core.visualization_utils import (
    mol_to_svg_string,
    mol_to_png_bytes,
    find_functional_group_matches,
    get_aromatic_ring_indices,
    RenderingStyle,
)

smi = "c1cc2nccnc2cc1"  # quinoxaline
mol = Chem.MolFromSmiles(smi)
if mol is None:
    raise SystemExit("RDKit failed to parse SMILES")

# Functional groups found
fg = find_functional_group_matches(mol, group_names=["amine","nitro","ketone","ester"])
print("Functional group matches:", fg)

# Aromatic rings
rings = get_aromatic_ring_indices(mol)
print("Aromatic rings (atom indices):", rings)

# Render SVG with atom numbers and highlight aromatic rings
style = RenderingStyle(size=(300,300))
svg = mol_to_svg_string(mol, size=(300,300), style=style, atom_numbering=True, highlight_functional_groups=["amine"], highlight_aromatic_rings=True)
with open("quinoxaline.svg", "w", encoding="utf8") as fh:
    fh.write(svg)
print("Saved quinoxaline.svg")

# Render PNG bytes and save
png = mol_to_png_bytes(mol, size=(300,300), style=style, atom_numbering=True, highlight_aromatic_rings=True)
with open("quinoxaline.png", "wb") as fh:
    fh.write(png)
print("Saved quinoxaline.png")
