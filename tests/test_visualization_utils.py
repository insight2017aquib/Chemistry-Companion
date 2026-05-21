"""
tests/test_visualization_utils.py

Tests for chemistry_companion/core/visualization_utils.py

These tests are matched to the enhanced visualization module with:
- atom numbering support
- SMARTS-based functional-group highlighting
- aromatic ring highlighting
- PNG/SVG single-molecule rendering
- batch grid rendering
- backward-compatible aliases
"""

from __future__ import annotations

import io
import logging

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure
from PIL import Image
from rdkit import Chem

try:
    from core.visualization_utils import (
        RenderingStyle,
        default_functional_group_smarts,
        find_functional_group_matches,
        get_aromatic_ring_indices,
        mol_to_3d_html,
        mol_to_matplotlib_figure,
        mol_to_png_bytes,
        mol_to_svg_string,
        mols_to_grid_image,
        molstogridimage,
        moltopngbytes,
        molto3dhtml,
        moltomatplotlibfigure,
        moltosvgstring,
        save_2d_image,
        save2dimage,
    )
except ImportError as exc:
    raise ImportError(
        "Could not import core.visualization_utils. "
        "Run pytest from the project root, where the 'core' folder is available."
    ) from exc


def _mol(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"RDKit failed to parse SMILES: {smiles}"
    return mol


def _assert_png_bytes(data: bytes) -> None:
    assert isinstance(data, bytes)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    image = Image.open(io.BytesIO(data))
    image.load()
    assert image.width > 0
    assert image.height > 0


class TestFunctionalGroupHelpers:
    def test_default_functional_group_smarts_returns_copy(self) -> None:
        smarts_a = default_functional_group_smarts()
        smarts_b = default_functional_group_smarts()

        assert smarts_a == smarts_b
        smarts_a["fake_group"] = "[#6]"
        assert "fake_group" not in smarts_b

    def test_find_functional_group_matches_detects_aspirin_groups(self) -> None:
        aspirin = _mol("CC(=O)Oc1ccccc1C(=O)O")
        matches = find_functional_group_matches(
            aspirin,
            group_names=["ester", "carboxylic_acid"],
        )

        assert "ester" in matches
        assert "carboxylic_acid" in matches
        assert len(matches["ester"]) >= 1
        assert len(matches["carboxylic_acid"]) >= 1

    def test_find_functional_group_matches_ignores_unknown_group(self) -> None:
        ethanol = _mol("CCO")
        matches = find_functional_group_matches(
            ethanol,
            group_names=["not_a_real_group"],
        )
        assert matches == {}

    def test_get_aromatic_ring_indices_benzene(self) -> None:
        benzene = _mol("c1ccccc1")
        rings = get_aromatic_ring_indices(benzene)

        assert len(rings) == 1
        atom_ids, bond_ids = rings[0]
        assert len(atom_ids) == 6
        assert len(bond_ids) == 6

    def test_get_aromatic_ring_indices_non_aromatic_is_empty(self) -> None:
        cyclohexane = _mol("C1CCCCC1")
        rings = get_aromatic_ring_indices(cyclohexane)
        assert rings == []


class TestSingleMoleculeRendering:
    def test_mol_to_png_bytes_returns_valid_png(self) -> None:
        png = mol_to_png_bytes(_mol("CCO"))
        _assert_png_bytes(png)

    def test_mol_to_png_bytes_supports_styles_and_highlights(self) -> None:
        aspirin = _mol("CC(=O)Oc1ccccc1C(=O)O")
        style = RenderingStyle(
            size=(240, 220),
            atom_palette="bw",
            fixed_font_size=12,
            bond_line_width=2.5,
        )

        png = mol_to_png_bytes(
            aspirin,
            size=(240, 220),
            style=style,
            atom_numbering=True,
            highlight_functional_groups=["ester", "carboxylic_acid"],
            highlight_aromatic_rings=True,
        )

        _assert_png_bytes(png)
        image = Image.open(io.BytesIO(png))
        image.load()
        assert image.size == (240, 220)

    def test_mol_to_svg_string_returns_svg(self) -> None:
        svg = mol_to_svg_string(
            _mol("c1ccccc1O"),
            legend="Phenol",
            atom_numbering=True,
            highlight_aromatic_rings=True,
        )

        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "class='legend'" in svg or 'class="legend"' in svg

    def test_mol_to_svg_string_supports_functional_group_highlighting(self) -> None:
        svg = mol_to_svg_string(
            _mol("CCO"),
            highlight_functional_groups=["alcohol"],
        )
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_mol_to_matplotlib_figure_returns_figure(self) -> None:
        fig = mol_to_matplotlib_figure(
            _mol("CC(=O)O"),
            title="Acetic acid",
            highlight_functional_groups=["carboxylic_acid"],
        )

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_invalid_molecule_raises(self) -> None:
        with pytest.raises(ValueError):
            mol_to_png_bytes(None)  # type: ignore[arg-type]


class TestSaveToDisk:
    def test_save_2d_image_png_writes_file_and_logs(self, tmp_path, caplog) -> None:
        out_path = tmp_path / "aspirin.png"
        aspirin = _mol("CC(=O)Oc1ccccc1C(=O)O")

        caplog.set_level(logging.INFO)

        returned = save_2d_image(
            aspirin,
            out_path,
            title="Aspirin",
            highlight_functional_groups=["ester", "carboxylic_acid"],
            highlight_aromatic_rings=True,
            atom_numbering=True,
        )

        assert returned == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        assert any("Saved 2D molecule image to" in rec.message for rec in caplog.records)

    def test_save_2d_image_svg_writes_svg(self, tmp_path) -> None:
        out_path = tmp_path / "benzene.svg"

        returned = save_2d_image(
            _mol("c1ccccc1"),
            out_path,
            legend="Benzene",
            highlight_aromatic_rings=True,
            as_svg=True,
        )

        assert returned == out_path
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert "<svg" in text
        assert "</svg>" in text
        assert "class='legend'" in text or 'class="legend"' in text

    def test_save_2d_image_infers_svg_from_suffix(self, tmp_path) -> None:
        out_path = tmp_path / "ethanol.svg"

        returned = save_2d_image(
            _mol("CCO"),
            out_path,
            legend="Ethanol",
        )

        assert returned == out_path
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert "<svg" in text

    def test_save_2d_image_png_without_title_uses_png_bytes_path(self, tmp_path) -> None:
        out_path = tmp_path / "ethanol.png"

        returned = save_2d_image(
            _mol("CCO"),
            out_path,
            highlight_functional_groups=["alcohol"],
        )

        assert returned == out_path
        _assert_png_bytes(out_path.read_bytes())


class TestGridRendering:
    def test_mols_to_grid_image_returns_png_bytes(self) -> None:
        mols = [
            _mol("CCO"),
            _mol("c1ccccc1"),
            _mol("CC(=O)O"),
        ]

        png = mols_to_grid_image(
            mols,
            legends=["Ethanol", "Benzene", "Acetic acid"],
            mols_per_row=2,
            highlight_aromatic_rings=True,
            highlight_functional_groups=["alcohol", "carboxylic_acid"],
        )

        _assert_png_bytes(png)

    def test_mols_to_grid_image_returns_svg_text(self) -> None:
        mols = [
            _mol("CCO"),
            _mol("c1ccccc1O"),
        ]

        svg = mols_to_grid_image(
            mols,
            legends=["Ethanol", "Phenol"],
            use_svg=True,
            atom_numbering=True,
            highlight_functional_groups=["alcohol", "phenol"],
            highlight_aromatic_rings=True,
        )

        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_mols_to_grid_image_supports_custom_style(self) -> None:
        mols = [_mol("CCO"), _mol("CCN"), _mol("CCCl")]
        style = RenderingStyle(
            size=(180, 180),
            atom_palette="bw",
            fixed_font_size=11,
            add_atom_indices=True,
        )

        png = mols_to_grid_image(
            mols,
            style=style,
            sub_img_size=(180, 180),
            mols_per_row=3,
        )

        _assert_png_bytes(png)

    def test_mols_to_grid_image_requires_nonempty_input(self) -> None:
        with pytest.raises(ValueError):
            mols_to_grid_image([])


class TestBackwardCompatibility:
    def test_aliases_point_to_primary_functions(self) -> None:
        assert moltopngbytes is mol_to_png_bytes
        assert moltosvgstring is mol_to_svg_string
        assert moltomatplotlibfigure is mol_to_matplotlib_figure
        assert save2dimage is save_2d_image
        assert molto3dhtml is mol_to_3d_html
        assert molstogridimage is mols_to_grid_image

    def test_alias_call_still_works(self) -> None:
        png = moltopngbytes(_mol("CCO"))
        _assert_png_bytes(png)


class TestOptional3D:
    def test_mol_to_3d_html_is_environment_tolerant(self) -> None:
        ethanol = _mol("CCO")

        try:
            html = mol_to_3d_html(ethanol, width=250, height=200, style="stick")
        except ImportError:
            pytest.skip("py3Dmol is not installed in this environment")

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<div" in html or "3Dmol" in html

    def test_backward_compatible_3d_alias_is_environment_tolerant(self) -> None:
        ethanol = _mol("CCO")

        try:
            html = molto3dhtml(ethanol, width=220, height=180, style="line")
        except ImportError:
            pytest.skip("py3Dmol is not installed in this environment")

        assert isinstance(html, str)
        assert len(html) > 0