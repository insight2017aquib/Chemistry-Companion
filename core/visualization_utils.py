"""
chemistry_companion/core/visualization_utils.py

Enhanced 2D/3D visualization utilities for Chemistry Companion.

This is a surgical, backward-compatible enhancement of the existing module.
Applied fixes:
- Ensure RDKit drawer honors requested canvas size when possible.
- Guarantee returned PNG bytes match requested pixel dimensions (fallback resize).
- Ensure legend text appears in SVG output (inject minimal legend if RDKit omits it).
- Preserve existing API and aliases.
- Add defensive logging and minimal, non-invasive behavior changes.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

Color = Tuple[float, float, float]
RGBAColor = Tuple[float, float, float, float]
Mol = Chem.Mol

# Default highlight palette and SMARTS library (conservative)
_DEFAULT_HIGHLIGHT_COLORS: Tuple[Color, ...] = (
    (0.90, 0.35, 0.25),
    (0.20, 0.55, 0.85),
    (0.20, 0.70, 0.35),
    (0.75, 0.45, 0.10),
    (0.65, 0.35, 0.80),
    (0.15, 0.65, 0.65),
)
_AROMATIC_RING_COLOR: Color = (0.95, 0.80, 0.20)

_DEFAULT_FG_SMARTS: Dict[str, str] = {
    "alcohol": "[OX2H][CX4]",
    "phenol": "[OX2H][c]",
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "ester": "[CX3](=O)[OX2][#6]",
    "amide": "[NX3][CX3](=O)[#6]",
    "amine": "[NX3;H2,H1;!$(NC=O)]",
    "ether": "[OD2]([#6])[#6]",
    "aldehyde": "[CX3H1](=O)[#6]",
    "ketone": "[#6][CX3](=O)[#6]",
    "nitrile": "[CX2]#N",
    "nitro": "[$([NX3](=O)=O),$([NX3+](=O)[O-])]",
    "alkene": "C=C",
    "alkyne": "C#C",
    "halogen": "[F,Cl,Br,I]",
}

_COMPILED_FG_SMARTS: Dict[str, Mol] = {}
for _fg_name, _smarts in _DEFAULT_FG_SMARTS.items():
    patt = Chem.MolFromSmarts(_smarts)
    if patt is not None:
        _COMPILED_FG_SMARTS[_fg_name] = patt
    else:
        logger.warning("Failed to compile SMARTS for functional group: %s", _fg_name)


@dataclass(frozen=True)
class RenderingStyle:
    """Configurable RDKit rendering style."""

    size: Tuple[int, int] = (300, 300)
    background_color: RGBAColor = (1.0, 1.0, 1.0, 1.0)
    atom_palette: str = "default"
    add_atom_indices: bool = False
    add_bond_indices: bool = False
    explicit_methyl: bool = False
    base_font_size: float = 0.60
    fixed_font_size: Optional[int] = None
    legend_font_size: int = 16
    bond_line_width: float = 2.0
    highlight_radius: float = 0.35
    highlight_bond_width_multiplier: int = 12
    fill_highlights: bool = True
    continuous_highlight: bool = True
    atom_highlights_are_circles: bool = True
    padding: float = 0.05
    use_acs_1996: bool = False


def default_functional_group_smarts() -> Dict[str, str]:
    """Return a copy of the default SMARTS library used for highlighting."""
    return dict(_DEFAULT_FG_SMARTS)


def _normalise_group_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_mol(mol: Mol) -> Mol:
    """Validate RDKit molecule input."""
    if mol is None:
        raise ValueError("Input molecule is None.")
    if not hasattr(mol, "GetNumAtoms"):
        raise TypeError("Input must be an RDKit Mol object.")
    return mol


def _prepare_mol_for_drawing(mol: Mol, kekulize: bool = True) -> Mol:
    """Return a drawing-safe copy of the molecule with 2D coordinates."""
    _validate_mol(mol)
    work = Chem.Mol(mol)
    try:
        prepared = rdMolDraw2D.PrepareMolForDrawing(work, kekulize=kekulize)
        return prepared
    except Exception as exc:
        logger.debug("PrepareMolForDrawing failed; falling back to Compute2DCoords: %s", exc)

    work = Chem.Mol(mol)
    if work.GetNumConformers() == 0:
        rdDepictor.Compute2DCoords(work)
    return work


def _apply_atom_palette(opts: rdMolDraw2D.MolDrawOptions, palette_name: str) -> None:
    """Apply a named atom palette to RDKit draw options."""
    name = palette_name.strip().lower()
    if name == "bw":
        opts.useBWAtomPalette()
    elif name == "cdk":
        opts.useCDKAtomPalette()
    elif name == "avalon":
        opts.useAvalonAtomPalette()


def _apply_style(opts: rdMolDraw2D.MolDrawOptions, style: RenderingStyle) -> None:
    """Apply RenderingStyle to an RDKit MolDrawOptions object."""
    opts.addAtomIndices = style.add_atom_indices
    opts.addBondIndices = style.add_bond_indices
    opts.explicitMethyl = style.explicit_methyl
    opts.baseFontSize = style.base_font_size
    opts.legendFontSize = style.legend_font_size
    opts.bondLineWidth = style.bond_line_width
    opts.highlightRadius = style.highlight_radius
    opts.highlightBondWidthMultiplier = style.highlight_bond_width_multiplier
    opts.fillHighlights = style.fill_highlights
    opts.continuousHighlight = style.continuous_highlight
    opts.atomHighlightsAreCircles = style.atom_highlights_are_circles
    opts.padding = style.padding
    opts.setBackgroundColour(style.background_color)
    if style.fixed_font_size is not None:
        opts.fixedFontSize = style.fixed_font_size
    _apply_atom_palette(opts, style.atom_palette)


def _substructure_bonds_for_atoms(mol: Mol, atom_indices: Sequence[int]) -> List[int]:
    """Return bond indices whose endpoints are both inside atom_indices."""
    atom_set = set(atom_indices)
    bond_ids: List[int] = []
    for bond in mol.GetBonds():
        if bond.GetBeginAtomIdx() in atom_set and bond.GetEndAtomIdx() in atom_set:
            bond_ids.append(bond.GetIdx())
    return bond_ids


def find_functional_group_matches(
    mol: Mol,
    group_names: Optional[Sequence[str]] = None,
    smarts_library: Optional[Mapping[str, str]] = None,
) -> Dict[str, List[Tuple[int, ...]]]:
    """
    Find SMARTS-based functional-group matches for highlighting.

    Returns mapping of normalized group name to list of atom-index tuples.
    """
    _validate_mol(mol)

    if smarts_library is None:
        compiled = _COMPILED_FG_SMARTS
    else:
        compiled = {}
        for name, smarts in smarts_library.items():
            patt = Chem.MolFromSmarts(smarts)
            if patt is not None:
                compiled[_normalise_group_name(name)] = patt

    if group_names is None:
        selected_names = list(compiled.keys())
    else:
        selected_names = [_normalise_group_name(name) for name in group_names]

    results: Dict[str, List[Tuple[int, ...]]] = {}
    for name in selected_names:
        patt = compiled.get(name)
        if patt is None:
            logger.debug("Requested functional group not found in SMARTS library: %s", name)
            continue
        matches = [tuple(match) for match in mol.GetSubstructMatches(patt, uniquify=True)]
        if matches:
            results[name] = matches
            logger.debug("Matched functional group %s with %d match(es)", name, len(matches))
    return results


def get_aromatic_ring_indices(mol: Mol) -> List[Tuple[List[int], List[int]]]:
    """
    Return aromatic ring atom/bond indices.

    Each item is (atom_indices, bond_indices) for one aromatic ring.
    """
    _validate_mol(mol)
    ring_info = mol.GetRingInfo()
    aromatic_rings: List[Tuple[List[int], List[int]]] = []

    atom_rings = ring_info.AtomRings()
    bond_rings = ring_info.BondRings()
    for atom_ring, bond_ring in zip(atom_rings, bond_rings):
        if atom_ring and all(mol.GetAtomWithIdx(idx).GetIsAromatic() for idx in atom_ring):
            aromatic_rings.append((list(atom_ring), list(bond_ring)))

    logger.debug("Detected %d aromatic ring(s)", len(aromatic_rings))
    return aromatic_rings


def _merge_highlight_data(
    atom_colors: Dict[int, Color],
    bond_colors: Dict[int, Color],
    atoms: Sequence[int],
    bonds: Sequence[int],
    color: Color,
) -> None:
    """Merge atom/bond highlights into color maps."""
    for atom_idx in atoms:
        atom_colors[atom_idx] = color
    for bond_idx in bonds:
        bond_colors[bond_idx] = color


def _resolve_highlights(
    mol: Mol,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
) -> Tuple[List[int], List[int], Dict[int, Color], Dict[int, Color]]:
    """Build consolidated atom/bond highlight lists and color maps."""
    atom_ids = set(highlight_atoms or [])
    bond_ids = set(highlight_bonds or [])
    atom_colors: Dict[int, Color] = {}
    bond_colors: Dict[int, Color] = {}

    if highlight_functional_groups:
        fg_matches = find_functional_group_matches(
            mol,
            group_names=highlight_functional_groups,
            smarts_library=smarts_library,
        )
        for idx, group_name in enumerate(sorted(fg_matches)):
            color = _DEFAULT_HIGHLIGHT_COLORS[idx % len(_DEFAULT_HIGHLIGHT_COLORS)]
            for match in fg_matches[group_name]:
                match_bonds = _substructure_bonds_for_atoms(mol, match)
                atom_ids.update(match)
                bond_ids.update(match_bonds)
                _merge_highlight_data(atom_colors, bond_colors, match, match_bonds, color)

    if highlight_aromatic_rings:
        for ring_atoms, ring_bonds in get_aromatic_ring_indices(mol):
            atom_ids.update(ring_atoms)
            bond_ids.update(ring_bonds)
            _merge_highlight_data(atom_colors, bond_colors, ring_atoms, ring_bonds, _AROMATIC_RING_COLOR)

    return sorted(atom_ids), sorted(bond_ids), atom_colors, bond_colors


def _final_style(style: Optional[RenderingStyle], size: Tuple[int, int], atom_numbering: bool) -> RenderingStyle:
    """Return merged rendering style."""
    base = style or RenderingStyle()
    merged = base if base.size == size else replace(base, size=size)
    if atom_numbering and not merged.add_atom_indices:
        merged = replace(merged, add_atom_indices=True)
    return merged


def _draw_single_molecule(
    mol: Mol,
    legend: str = "",
    size: Tuple[int, int] = (300, 300),
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    use_svg: bool = False,
    kekulize: bool = True,
) -> Union[bytes, str]:
    """Low-level shared single-molecule drawing routine."""
    prepared = _prepare_mol_for_drawing(mol, kekulize=kekulize)
    merged_style = _final_style(style, size=size, atom_numbering=atom_numbering)
    highlight_atom_ids, highlight_bond_ids, atom_color_map, bond_color_map = _resolve_highlights(
        prepared,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
        highlight_functional_groups=highlight_functional_groups,
        highlight_aromatic_rings=highlight_aromatic_rings,
        smarts_library=smarts_library,
    )

    width_px, height_px = merged_style.size
    if use_svg:
        drawer = rdMolDraw2D.MolDraw2DSVG(width_px, height_px)
    else:
        drawer = rdMolDraw2D.MolDraw2DCairo(width_px, height_px)

    # Try to explicitly set size on the drawer if available (some RDKit builds)
    try:
        if hasattr(drawer, "SetSize"):
            drawer.SetSize(int(width_px), int(height_px))
    except Exception:
        # non-fatal; RDKit may ignore or not support SetSize in some builds
        logger.debug("Drawer.SetSize call failed or unsupported; continuing.")

    opts = drawer.drawOptions()
    _apply_style(opts, merged_style)
    if merged_style.use_acs_1996:
        try:
            Draw.SetACS1996Mode(opts, Draw.MeanBondLength(prepared))
        except Exception as exc:
            logger.debug("ACS 1996 mode could not be applied: %s", exc)

    # Draw molecule with highlights and legend
    drawer.DrawMolecule(
        prepared,
        legend=legend,
        highlightAtoms=highlight_atom_ids,
        highlightBonds=highlight_bond_ids,
        highlightAtomColors=atom_color_map,
        highlightBondColors=bond_color_map,
    )
    drawer.FinishDrawing()
    rendered = drawer.GetDrawingText()

    # SVG: ensure legend is present; if RDKit omitted it, inject a simple legend text
    if use_svg and isinstance(rendered, str):
        svg_text = rendered.replace("svg:", "")
        if legend and legend not in svg_text:
            # inject a small legend at the bottom-right of the SVG canvas
            try:
                insert_text = (
                    f"<text x='{max(4, width_px - 10)}' y='{height_px - 6}' "
                    f"font-size='{max(10, int(merged_style.legend_font_size))}' "
                    f"text-anchor='end' fill='black'>{legend}</text>"
                )
                # place before closing </svg>
                svg_text = svg_text.rstrip()
                if svg_text.endswith("</svg>"):
                    svg_text = svg_text[:-6] + insert_text + "</svg>"
                else:
                    svg_text = svg_text + insert_text
            except Exception:
                logger.debug("Failed to inject legend into SVG; continuing without injection.")
        return svg_text

    # Raster (PNG) output: ensure bytes and correct size
    if not use_svg:
        # RDKit returns PNG bytes for Cairo drawer
        png_bytes = rendered if isinstance(rendered, (bytes, bytearray)) else bytes(rendered)
        # If PIL is available, verify size and resize if necessary to requested size
        try:
            from PIL import Image as _PILImage
            import io as _io

            img = _PILImage.open(_io.BytesIO(png_bytes))
            img.load()
            if img.size != (int(width_px), int(height_px)):
                # Resize to requested size (preserve aspect by stretching to requested dims)
                img = img.resize((int(width_px), int(height_px)), _PILImage.LANCZOS)
                buf = _io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
        except Exception:
            # If PIL not available or something failed, return original bytes
            logger.debug("PIL not available or resize failed; returning RDKit PNG bytes as-is.")
        return png_bytes

    # Fallback (should not be reached)
    return rendered


def mol_to_png_bytes(
    mol: Mol,
    size: Tuple[int, int] = (300, 300),
    legend: str = "",
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    kekulize: bool = True,
) -> bytes:
    """Render a molecule to PNG bytes using RDKit MolDraw2DCairo."""
    result = _draw_single_molecule(
        mol=mol,
        legend=legend,
        size=size,
        style=style,
        atom_numbering=atom_numbering,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
        highlight_functional_groups=highlight_functional_groups,
        highlight_aromatic_rings=highlight_aromatic_rings,
        smarts_library=smarts_library,
        use_svg=False,
        kekulize=kekulize,
    )
    if not isinstance(result, (bytes, bytearray)):
        raise TypeError("PNG rendering did not return bytes.")
    return bytes(result)


def mol_to_svg_string(
    mol: Mol,
    size: Tuple[int, int] = (300, 300),
    legend: str = "",
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    kekulize: bool = True,
) -> str:
    """Render a molecule to SVG text using RDKit MolDraw2DSVG."""
    result = _draw_single_molecule(
        mol=mol,
        legend=legend,
        size=size,
        style=style,
        atom_numbering=atom_numbering,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
        highlight_functional_groups=highlight_functional_groups,
        highlight_aromatic_rings=highlight_aromatic_rings,
        smarts_library=smarts_library,
        use_svg=True,
        kekulize=kekulize,
    )
    if not isinstance(result, str):
        raise TypeError("SVG rendering did not return text.")
    return result


def mol_to_matplotlib_figure(
    mol: Mol,
    size: Tuple[int, int] = (300, 300),
    title: Optional[str] = None,
    legend: str = "",
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    kekulize: bool = True,
) -> Figure:
    """Return a Matplotlib figure suitable for PDF/report embedding."""
    png = mol_to_png_bytes(
        mol=mol,
        size=size,
        legend=legend,
        style=style,
        atom_numbering=atom_numbering,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
        highlight_functional_groups=highlight_functional_groups,
        highlight_aromatic_rings=highlight_aromatic_rings,
        smarts_library=smarts_library,
        kekulize=kekulize,
    )
    image = Image.open(io.BytesIO(png))
    fig, ax = plt.subplots(figsize=(size[0] / 100.0, size[1] / 100.0), dpi=100)
    ax.imshow(image)
    ax.axis("off")
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def save_2d_image(
    mol: Mol,
    path: Union[str, Path],
    size: Tuple[int, int] = (300, 300),
    title: Optional[str] = None,
    legend: str = "",
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_atoms: Optional[Sequence[int]] = None,
    highlight_bonds: Optional[Sequence[int]] = None,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    as_svg: Optional[bool] = None,
    kekulize: bool = True,
) -> Path:
    """
    Save a 2D molecule image to disk.

    If title is provided for PNG output, the image is routed through Matplotlib so
    the title is included above the molecule. SVG output always uses RDKit legend.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    use_svg = as_svg if as_svg is not None else output_path.suffix.lower() == ".svg"

    if use_svg:
        svg = mol_to_svg_string(
            mol=mol,
            size=size,
            legend=legend or (title or ""),
            style=style,
            atom_numbering=atom_numbering,
            highlight_atoms=highlight_atoms,
            highlight_bonds=highlight_bonds,
            highlight_functional_groups=highlight_functional_groups,
            highlight_aromatic_rings=highlight_aromatic_rings,
            smarts_library=smarts_library,
            kekulize=kekulize,
        )
        output_path.write_text(svg, encoding="utf-8")
    else:
        if title:
            try:
                fig = mol_to_matplotlib_figure(
                    mol=mol,
                    size=size,
                    title=title,
                    legend=legend,
                    style=style,
                    atom_numbering=atom_numbering,
                    highlight_atoms=highlight_atoms,
                    highlight_bonds=highlight_bonds,
                    highlight_functional_groups=highlight_functional_groups,
                    highlight_aromatic_rings=highlight_aromatic_rings,
                    smarts_library=smarts_library,
                    kekulize=kekulize,
                )
                fig.savefig(output_path, dpi=200, bbox_inches="tight")
                plt.close(fig)
            except Exception as exc:
                logger.warning(
                    "Matplotlib title rendering failed, falling back to direct PNG rendering: %s",
                    exc,
                )
                png = mol_to_png_bytes(
                    mol=mol,
                    size=size,
                    legend=legend,
                    style=style,
                    atom_numbering=atom_numbering,
                    highlight_atoms=highlight_atoms,
                    highlight_bonds=highlight_bonds,
                    highlight_functional_groups=highlight_functional_groups,
                    highlight_aromatic_rings=highlight_aromatic_rings,
                    smarts_library=smarts_library,
                    kekulize=kekulize,
                )
                output_path.write_bytes(png)
        else:
            png = mol_to_png_bytes(
                mol=mol,
                size=size,
                legend=legend,
                style=style,
                atom_numbering=atom_numbering,
                highlight_atoms=highlight_atoms,
                highlight_bonds=highlight_bonds,
                highlight_functional_groups=highlight_functional_groups,
                highlight_aromatic_rings=highlight_aromatic_rings,
                smarts_library=smarts_library,
                kekulize=kekulize,
            )
            output_path.write_bytes(png)

    logger.info("Saved 2D molecule image to %s", output_path)
    return output_path


def mol_to_3d_html(
    mol: Mol,
    width: int = 500,
    height: int = 400,
    style: str = "stick",
) -> str:
    """
    Render a molecule as interactive HTML via py3Dmol.

    Raises ImportError if py3Dmol is not installed.
    """
    _validate_mol(mol)
    try:
        import py3Dmol  # type: ignore
    except ImportError as exc:
        raise ImportError("py3Dmol is required for 3D HTML export. Install with `pip install py3Dmol`.") from exc

    work = Chem.AddHs(Chem.Mol(mol))
    if work.GetNumConformers() == 0:
        params = AllChem.ETKDGv3()
        status = AllChem.EmbedMolecule(work, params)
        if status != 0:
            raise ValueError("3D embedding failed for the input molecule.")
        try:
            AllChem.MMFFOptimizeMolecule(work)
        except Exception as exc:
            logger.debug("MMFF optimization failed or was skipped: %s", exc)

    mol_block = Chem.MolToMolBlock(work)
    viewer = py3Dmol.view(width=width, height=height)
    viewer.addModel(mol_block, "mol")
    if style == "stick":
        viewer.setStyle({"stick": {}})
    elif style == "sphere":
        viewer.setStyle({"sphere": {"scale": 0.30}})
    elif style == "line":
        viewer.setStyle({"line": {}})
    else:
        viewer.setStyle({style: {}})
    viewer.zoomTo()
    return viewer._make_html()


def _grid_png_to_bytes(image_obj: object) -> bytes:
    """Normalize RDKit/PIL grid image output to PNG bytes."""
    if isinstance(image_obj, (bytes, bytearray)):
        return bytes(image_obj)
    if hasattr(image_obj, "save"):
        buffer = io.BytesIO()
        image_obj.save(buffer, format="PNG")
        return buffer.getvalue()
    raise TypeError("Grid rendering did not return a PNG-compatible object.")


def mols_to_grid_image(
    mols: Sequence[Mol],
    legends: Optional[Sequence[str]] = None,
    mols_per_row: int = 3,
    sub_img_size: Tuple[int, int] = (200, 200),
    style: Optional[RenderingStyle] = None,
    atom_numbering: bool = False,
    highlight_functional_groups: Optional[Sequence[str]] = None,
    highlight_aromatic_rings: bool = False,
    smarts_library: Optional[Mapping[str, str]] = None,
    use_svg: bool = False,
) -> Union[bytes, str]:
    """
    Render a batch of molecules as a grid.

    Returns PNG bytes by default, or SVG text when use_svg=True.
    """
    if not mols:
        raise ValueError("mols_to_grid_image requires at least one molecule.")

    prepared_mols: List[Mol] = []
    highlight_atom_lists: List[List[int]] = []
    highlight_bond_lists: List[List[int]] = []

    for mol in mols:
        prepared = _prepare_mol_for_drawing(mol)
        prepared_mols.append(prepared)
        atom_ids, bond_ids, _, _ = _resolve_highlights(
            prepared,
            highlight_functional_groups=highlight_functional_groups,
            highlight_aromatic_rings=highlight_aromatic_rings,
            smarts_library=smarts_library,
        )
        highlight_atom_lists.append(atom_ids)
        highlight_bond_lists.append(bond_ids)

    merged_style = _final_style(style, size=sub_img_size, atom_numbering=atom_numbering)
    draw_options = rdMolDraw2D.MolDrawOptions()
    _apply_style(draw_options, merged_style)

    result = Draw.MolsToGridImage(
        prepared_mols,
        molsPerRow=mols_per_row,
        subImgSize=sub_img_size,
        legends=list(legends) if legends is not None else None,
        highlightAtomLists=highlight_atom_lists,
        highlightBondLists=highlight_bond_lists,
        useSVG=use_svg,
        returnPNG=not use_svg,
        drawOptions=draw_options,
    )

    if use_svg:
        if not isinstance(result, str):
            raise TypeError("SVG grid rendering did not return text.")
        return result.replace("svg:", "")

    return _grid_png_to_bytes(result)


# Backward-compatible aliases (preserve original names)
moltopngbytes = mol_to_png_bytes
moltosvgstring = mol_to_svg_string
moltomatplotlibfigure = mol_to_matplotlib_figure
save2dimage = save_2d_image
molto3dhtml = mol_to_3d_html
molstogridimage = mols_to_grid_image

__all__ = [
    "RenderingStyle",
    "default_functional_group_smarts",
    "find_functional_group_matches",
    "get_aromatic_ring_indices",
    "mol_to_png_bytes",
    "mol_to_svg_string",
    "mol_to_matplotlib_figure",
    "save_2d_image",
    "mol_to_3d_html",
    "mols_to_grid_image",
    # backward aliases
    "moltopngbytes",
    "moltosvgstring",
    "moltomatplotlibfigure",
    "save2dimage",
    "molto3dhtml",
    "molstogridimage",
]
