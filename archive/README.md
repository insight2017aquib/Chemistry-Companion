# Archive

Prototype, experimental, and one-shot developer artifacts moved out of the
project root during **Cleanup Phase 2** (2026-07-10). Nothing here is imported
by the running application (`api.app`), packaging, or the `tests/` suite. Kept
for historical reference — **not deleted**.

| Folder | Contents | Notes |
|---|---|---|
| `molstar_prototypes/` | `test_molstar_local*.py` (7), `test_molstar_local*.html` (7), `test_molstar.js`, `molstar_source.js`, `test_protein.pdb` | Playwright/headless-Chromium experiments for Mol\* rendering. Superseded by `visualization/` + 3Dmol.js. `test_protein.pdb` was their fixture. |
| `patch_scripts/` | `update_pose_analysis_phase7.py`, `update_llm_routes.py`, `update_docking_workspace.py`, `patch_script.py` | One-shot source-patching scripts with hardcoded absolute paths. Already applied; superseded. |
| `experimental_tests/` | `test_e2e_docking.py`, `test_ligand.py`, `test_interaction_analyzer.py` | Root-level ad-hoc test scripts (never part of the `tests/` suite; not imported by it). |
| `screenshots/` | 17 `*.png` | Developer/QA validation screenshots from earlier phases. |

All files were **untracked** in git prior to the move, so no rename history was lost.
