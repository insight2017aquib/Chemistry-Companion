"""
verify_fixes.py
================
Verification script to check the dependency detection for Visualization
and the rigid receptor PDBQT generation for Docking.
"""

import sys
import os

sys.path.insert(0, ".")

print("==================================================")
print("     CHEMISTRY COMPANION VERIFICATION SCRIPT     ")
print("==================================================")

# 1. Verify Visualization
print("\n--- 1. VERIFYING VISUALIZATION DEPENDENCIES ---")
try:
    import visualization
    print(f"Visualization Module Imported Successfully.")
    print(f"HAS_VISUALIZATION: {visualization.HAS_VISUALIZATION}")
    if not visualization.HAS_VISUALIZATION:
        err = getattr(visualization, "_import_error", "Unknown error")
        print(f"\n[DETERMINATION] Visualization is NOT available.")
        print(f"Detail: {err}")
        print("Please run: pip install gemmi rdkit py3Dmol pydantic")
    else:
        print("\n[SUCCESS] Visualization is FULLY available and ready!")
        print("Performing basic smoke tests...")
        
        # Test 2D rendering
        svg_res = visualization.render_ligand_2d("CCO")
        if svg_res.get("error"):
            print(f"  - 2D render failed: {svg_res.get('error')}")
        else:
            print("  - 2D SVG Rendering: SUCCESS")
            
        # Test 3D rendering
        html_res = visualization.render_ligand_3d("CCO")
        if "Error" in html_res:
            print("  - 3D HTML Rendering: FAILED")
        else:
            print("  - 3D HTML Rendering: SUCCESS")
except Exception as e:
    print(f"[ERROR] Failed to import or verify visualization: {e}")


# 2. Verify Docking Protein Preparation and Vina Execution
print("\n--- 2. VERIFYING RIGID RECEPTOR PDBQT GENERATION ---")
try:
    from docking_workflow.protein_preparation import prepare_protein
    
    mock_pdb = """ATOM      1  N   ASP A   1      18.232  17.382  22.287  1.00 20.00           N
ATOM      2  CA  ASP A   1      18.790  18.064  23.473  1.00 20.00           C
ATOM      3  C   ASP A   1      19.066  19.553  23.238  1.00 20.00           C
ATOM      4  O   ASP A   1      20.038  20.125  23.766  1.00 20.00           O
ATOM      5  CB  ASP A   1      17.828  17.873  24.646  1.00 20.00           C
ATOM      6  CG  ASP A   1      18.431  18.358  25.962  1.00 20.00           C
ATOM      7  OD1 ASP A   1      19.576  18.847  25.965  1.00 20.00           O
ATOM      8  OD2 ASP A   1      17.765  18.257  27.017  1.00 20.00           O
TER       9      ASP A   1"""

    print("Preparing rigid receptor protein...")
    pdbqt = prepare_protein(mock_pdb)
    
    # Check for rigid tags
    has_root = "ROOT" in pdbqt or "ENDROOT" in pdbqt
    has_torsdof = "TORSDOF" in pdbqt
    
    print("\nReceptor PDBQT File Checks:")
    print(f"  - Contains ATOM lines: {'ATOM' in pdbqt}")
    print(f"  - Contains ROOT/ENDROOT tags: {has_root} (Expected: False)")
    print(f"  - Contains TORSDOF tags: {has_torsdof} (Expected: False)")
    
    if not has_root and not has_torsdof:
        print("\n[SUCCESS] Rigid receptor PDBQT generated successfully and cleaned perfectly!")
    else:
        print("\n[FAILURE] Rigid receptor PDBQT incorrectly contains rigid root or torsdof tags!")

    # 3. Test active docking if vina is available
    print("\nAttempting full Vina docking smoke test...")
    from core.docking_preparation import prepare_docking_structure
    from docking_workflow.vina_runner import run_vina
    
    ligand_pdbqt = prepare_docking_structure("CCO")
    res = run_vina(
        protein_pdbqt=pdbqt,
        ligand_pdbqt=ligand_pdbqt,
        center_x=18.5, center_y=18.5, center_z=24.5,
        size_x=15.0, size_y=15.0, size_z=15.0,
        exhaustiveness=1,
        num_modes=2
    )
    print("[SUCCESS] AutoDock Vina docked successfully without rigid receptor ROOT tag errors!")
    print(f"Top Pose Binding Affinity: {res.pdbqt_output.splitlines()[1]}")
    
except Exception as e:
    print(f"\n[DOCKING LOG/ERROR]: {e}")

print("\n==================================================")
