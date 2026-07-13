from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_visualization_page_template_contains_workspace():
    content = (ROOT / "templates" / "visualization.html").read_text(encoding="utf-8")
    # Updated for Molecular Viewer tab (reuses the visualization page/template)
    assert "Molecular Viewer" in content or "Visualization Workspace" in content
    assert "Protein Viewer" in content
    assert "Overlay Complex" in content
    assert "Ligand Viewer" in content  # 2D/3D panels


def test_docking_workspace_template_contains_live_preview():
    content = (ROOT / "templates" / "docking_workspace.html").read_text(encoding="utf-8")
    assert "Docking Workspace" in content
    assert "Live Structure Preview" in content
    assert "Mol* Viewer" in content
    assert "molstar.Viewer.create" in content
    assert "loadStructureFromData" in content
    assert "Show Waters" in content
    assert "Show Active-Site Waters" in content
    assert "Show Bulk Waters" in content
    assert "Show Metals" in content
    assert "Show Cofactors" in content
    assert "Show Ligands" in content
    assert "Show Chain A" in content
    assert "Show Chain B" in content
    assert "Show Chain C" in content
    assert "Show Pockets" in content
    assert "Show Grid Box" in content
    assert "Show Missing Residues" in content
    assert "Ask the Protein Expert" in content
    assert "AI Expert Answer" in content


def test_docking_workspace_contains_phase03_wizard_steps_and_cards():
    content = (ROOT / "templates" / "docking_workspace.html").read_text(encoding="utf-8")
    for label in [
        "Upload Protein",
        "Protein Analysis",
        "Chain Selection",
        "Pocket Selection",
        "Preparation Options",
        "Generate Receptor",
        "Docking",
    ]:
        assert label in content

    for label in [
        "Recommendation Card",
        "Quality Badge",
        "Pocket Cards",
        "Water Cards",
        "Metal Cards",
        "Cofactor Cards",
    ]:
        assert label in content
