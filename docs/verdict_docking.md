# Docking Logic — Scientific Audit & Verdict

**Scope:** Full docking pipeline: `docking_workflow/*`, `core/docking_preparation.py`, `core/openbabel_utils.py`, `services/docking_workspace_service.py`, `api/routes/docking.py`, `api/routes/docking_workspace.py`.
**Method:** Direct code read of every module in the pipeline (not a wiring/UI audit — this is a chemistry/physics correctness review).
**Status:** All 9 proposed fixes below have been implemented and verified live (fixes #1-#8; #9 was deferred to a future phase per your decision). See the "Implementation notes" addendum after the fix list for what actually changed and how it was verified.

---

## Pipeline as implemented (end to end)

1. **Protein analysis** (`protein_analysis.py`) — gemmi-based parse → chains, ligands, cofactors, metals, waters, missing residues (from `REMARK 465`), resolution, a 0–100 heuristic quality score, and a chain recommendation (with an optional LLM "25-year expert" second opinion).
2. **Binding site definition** — either from a co-crystallized ligand centroid (`suggest_binding_site_from_ligand`), from `fpocket` blind-pocket detection (`pocket_detection.py`), or a raw bounding-box of the whole receptor (`auto_gridbox`).
3. **Water classification** (`water_analysis.py`) — active-site vs. bulk vs. "conserved" (buried), with keep/remove recommendation.
4. **Optional protonation** (`protonation.py`) — PDB2PQR + PropKa, pKa-aware, per-residue.
5. **Receptor → PDBQT** (`protein_preparation.py`) — `obabel -ipdb ... -opdbqt -xr -p 7.4`, then strips any `ROOT/ENDROOT/BRANCH/ENDBRANCH/TORSDOF` tags so Vina treats it as a rigid receptor.
6. **Ligand → PDBQT** (`core/docking_preparation.py`) — RDKit SMILES parse → `embed_3d` (ETKDGv3 + MMFF94, fixed seed) → SDF → OpenBabel SDF→PDBQT.
7. **Docking** (`vina_runner.py`) — AutoDock Vina CLI (or the `vina` Python package as fallback) with configurable `exhaustiveness` (default 8) and `num_modes` (default 9).
8. **Pose parsing** (`pose_manager.py`) — splits `MODEL/ENDMDL` blocks, reads Vina's own reported affinity/RMSD-lb/RMSD-ub.
9. **Interaction detection** (`interaction_analyzer.py`) — distance + atom-name heuristics for H-bonds, hydrophobic contacts, salt bridges, pi-stacking, metal coordination, water bridges.
10. **Quality scoring & reporting** (`quality_scorer.py`, `report_builder.py`) and **ChimeraX export** (`chimera_exporter.py`).

---

## What's actually solid (credit where due)

- **Ligand 3D generation is good practice**: `core/conversion_utils.py:embed_3d` uses ETKDGv3 (a real, modern distance-geometry embedder) with a fixed `randomSeed=42`, followed by MMFF94 minimization with tiered fallback logging. This is legitimate, reproducible conformer generation — better than naively trusting OpenBabel's builder.
- **Rigid-receptor tag stripping is correct and defensively validated**: `clean_rigid_receptor_pdbqt` + `validate_rigid_receptor_pdbqt` correctly enforce that a rigid receptor PDBQT must not contain ligand-style torsion-tree records (`ROOT`/`BRANCH`/`TORSDOF`) — this is a real Vina requirement and it's handled correctly with a hard validation failure if violated.
- **Ligand-based and pocket-based grid box construction are reasonable**: centroid + padding for co-crystallized ligands, `max(22.0, radius*2.2)` for fpocket-derived sites — sane, focused box sizes for real docking.
- **Vina internally re-samples ligand torsions during docking**, so a single reasonable starting ligand conformer (rather than a full conformer ensemble) is an acceptable input — this is not a flaw, just worth knowing why it's fine.
- **Honest framing in the UI/footer** ("heuristic-based, for educational purposes") — the quality score and chain recommendation are correctly presented as heuristics, not as validated metrics.

---

## Findings — scientific correctness issues

### 1. Ligand pH/protonation control is a complete no-op (real bug)
- `api/routes/docking.py:19-33` (`/docking/generate`) accepts `ph: float = Form(7.4)` from the UI, but **never passes it** to `prepare_docking_structure()`.
- `core/docking_preparation.py:47-95` (`prepare_docking_structure`) doesn't even have a `ph` parameter — it's RDKit's raw SMILES parse with zero ionization-state correction.
- **Consequence**: the "pH" field the user sees in Docking Workspace step "Prepare Ligand" does nothing. Docking runs on whatever protonation state is literally encoded in the input SMILES — for most drug-like SMILES (typed as neutral by convention), that means **no automatic protonation of amines or deprotonation of carboxylic/phosphoric acids at physiological pH**, which changes the ligand's formal charge, partial charges, and H-bond donor/acceptor pattern — all of which directly affect Vina's scoring.
- Ironically, the correct tool for this already exists and works: `core/openbabel_utils.py:protonate_structure()`/`adjust_ph()` call `OBMol.CorrectForPH(ph)` properly — it's just never wired into the actual ligand-docking-prep path.

### 2. Receptor protonation: the optional, scientifically superior step is silently overwritten by a cruder one
- `docking_workflow/protein_preparation.py:177-219` (`prepare_receptor`): if `run_protonation=True`, it runs PDB2PQR+PropKa first (per-residue pKa prediction — the *right* way to do this), then **unconditionally pipes the result through `prepare_protein()`**, which runs `obabel ... -p 7.4` again.
- OpenBabel's `-p` flag does its own (much cruder, non-per-residue) pH correction/hydrogen placement. Running it *after* PDB2PQR risks altering or duplicating the very protonation states (e.g. correct His tautomer: HID/HIE/HIP) that PropKa just computed carefully.
- **Net effect**: enabling the "Run Protonation" toggle buys you PDB2PQR's better science, then the pipeline immediately risks undoing part of it. This isn't a UI bug — it's a pipeline ordering/logic bug with real chemical consequences for His-rich active sites, metal-adjacent residues, and other pH-sensitive titratable groups.

### 3. The "Keep Cofactors / Keep Metals / Keep Active-Site Waters" toggles are non-functional
- `docking_workflow/protein_preparation.py:196-213` explicitly logs: *"Advanced retention flags are accepted but the underlying preparation engine does not yet implement selective cofactor/metal/active-site water retention... proceeding with standard path."* Then it calls the same plain `prepare_protein()` regardless.
- `prepare_protein()`'s water removal (`_remove_water_records`) is a **blanket strip of every water residue** whenever `remove_water=True` (the default) — it has no concept of "active site" vs "bulk," so even if a user explicitly toggles "Keep Active-Site Waters" in step 5 of the wizard, that water is still deleted in the actual PDBQT sent to Vina.
- This matters scientifically: for many real targets (kinase hinge-bridging waters, metalloenzyme catalytic waters), keeping or removing the right water changes docking accuracy substantially. Right now the UI presents a control that has **zero effect on the real output** — this is worse than not having the control at all, because it actively misleads the user about what was done.
- Related: plain `obabel`-based PDB→PDBQT conversion (no MGLTools/AutoDockTools-style receptor preparation script) is not a robust way to carry metal ions and cofactors into a rigid receptor PDBQT in the first place — OpenBabel's PDBQT writer isn't purpose-built for correctly atom-typing non-standard HETATMs like Zn²⁺/Mg²⁺/heme/NAD for AutoDock. Even if the retention flags were wired up, this receptor-prep approach for metalloenzymes/cofactor-dependent targets needs verification, not just a flag.

### 4. Water classification (Phase 6) is advisory-only — disconnected from what's actually built
- `water_analysis.py:classify_waters()` produces a genuinely useful active-site/bulk/conserved classification with keep/remove reasoning. But as in #3, nothing downstream in `prepare_protein()`/`prepare_receptor()` consults this classification. It's surfaced to the UI as information but has no path into the receptor that's actually docked.

### 5. `auto_gridbox()` (blind-docking mode) produces an oversized, low-quality box by default
- `docking_workflow/gridbox_builder.py:28-60`: takes the bounding box of **every atom in the entire receptor PDBQT** + a flat 5 Å margin. Called on a whole-protein receptor (not a ligand/pocket subset), this typically yields a box spanning the entire protein (tens of Å per side).
- Vina's default `exhaustiveness=8` (also this app's default) is tuned for a focused ~20–25 Å pocket-sized box. Running it against a box covering the whole protein without scaling exhaustiveness up dramatically undersamples the search space — poses and affinities from this path are not reliable for real decision-making, even though the UI presents "Auto-detect Grid" as a normal, safe default action.
- This is mitigated only when the user instead picks a ligand-derived or fpocket-derived site (both of which *are* reasonably sized) — but nothing in the flow warns the user when they're about to run a blind, oversized box at default exhaustiveness.

### 6. Interaction detection is a name-based heuristic, not real chemistry — and is fed to the AI as "absolute truth"
This is the most consequential science finding.
- `interaction_analyzer.py:_find_interactions_rdkit()` — despite the module docstring claiming "RDKit-powered detection with proper chemistry perception" — builds the protein side as a mol of **dummy carbon atoms** (`Chem.Atom(6)` for every single protein atom, line ~192) purely for coordinate bookkeeping. Real element identity for the protein side is discarded entirely.
- H-bond, hydrophobic, salt-bridge, and metal-coordinator classification all rely on **atom-name substring matching** (`_looks_like_hbond_pair`, `_looks_hydrophobic`, `_looks_like_salt_bridge`, `_looks_like_metal_coordinator`) rather than actual element, hybridization, formal charge, or hydrogen-bond donor/acceptor perception.
- **Pi-stacking has a declared but unused angle cutoff**: `PI_STACKING_ANGLE_CUTOFF = 30.0` is defined and never referenced anywhere in the detection logic. "Pi-stacking" is really just "any PHE/TYR/TRP residue within 5.5 Å of an atom whose name contains C/RING/AR" — there is no ring-plane angle check at all, despite the constant implying one exists.
- **H-bond angle is a hardcoded placeholder**: `angle=180.0` (line 263) is reported as if measured — it is not computed from any actual donor-H...acceptor geometry.
- **Salt-bridge detection only checks the protein residue name** (`ASP/GLU/LYS/ARG/HIS`) — it does not verify the ligand atom is actually charged/ionizable. Any ligand atom near an Asp counts as a "salt bridge," which is not chemically accurate (a salt bridge requires two oppositely charged groups, not one).
- The codebase already has better information available and ignores it: every PDBQT atom carries a real AutoDock atom type in its last column (`OA`, `HD`, `NA`, `A`, `C`, etc. — these directly encode H-bond donor/acceptor/aromatic character) but the interaction analyzer never reads that column; it re-derives (weaker) guesses from atom *names* instead.
- **Why this matters beyond cosmetics**: `services/ai/docking_expert.py`'s system prompt explicitly instructs the LLM: *"The docking results (affinities, RMSD, interactions) are absolute truth... NEVER invent interactions that are not present in the provided JSON data."* The AI is told to treat this heuristic's output as ground truth and reason authoritatively about it (H-bond networks, "conserved interactions across poses," medicinal chemistry suggestions). If the underlying detection reports a fabricated 180° H-bond angle or a spurious salt bridge, the AI will confidently build scientific-sounding narrative on top of it. The trust boundary is set one layer too early.

### 7. `docking_validation.py` doesn't validate what its name implies
- It benchmarks **ligand file-preparation success rate** (SMILES → 3D → PDBQT, did OpenBabel/RDKit not crash) across a batch of SMILES. It does **not** perform the standard docking sanity check of redocking a co-crystallized ligand into its own site and checking RMSD to the native pose — the actual "does this docking setup reproduce known binding modes" validation that the name suggests and that real docking studies rely on before trusting results on novel ligands. Not wrong, just a scope/naming mismatch worth being explicit about — there is currently no pose-accuracy validation workflow anywhere in this codebase.

### 8. No salt-stripping in the actual ligand-docking path
- `core/openbabel_utils.py:remove_salts()` exists and works (keeps the largest fragment by heavy-atom count) but is **never called** from `prepare_docking_structure()`. If a user submits a multi-component SMILES (e.g., a salt form straight out of a database, `"CC(=O)O.[Na+]"`-style), RDKit will parse it as a multi-fragment `Mol`, and the resulting PDBQT can contain a disconnected counter-ion alongside the real ligand — which Vina will treat as part of the same rigid/flexible ligand entity, corrupting the docking input silently.

### 9. No scoring-function choice, seed control, or exhaustiveness guidance
- `vina_runner.py:run_vina()` doesn't expose Vina's `--scoring` option (`vina` vs `vinardo`), `--seed` (for exact run-to-run reproducibility), `--cpu`, or `--local_only` (useful for the redocking-validation workflow noted in #7). `exhaustiveness` and `num_modes` are configurable but have no guidance or auto-scaling tied to box volume or ligand rotatable-bond count — a user can unknowingly run a large blind-docking box (see #5) at the same default exhaustiveness intended for a focused pocket. Not a bug, but a real gap versus what a careful docking practitioner would want exposed.

---

## Severity summary

| # | Finding | Severity | Type |
|---|---|---|---|
| 1 | Ligand pH control is a no-op | **High** | Real bug — silently wrong ligand ionization state |
| 2 | PDB2PQR protonation overwritten by OpenBabel `-p` | **High** | Real bug — pipeline ordering undermines its own more-accurate step |
| 3 | Cofactor/metal/active-site-water retention toggles do nothing | **High** | Real bug — UI actively misrepresents what happens to the receptor |
| 4 | Water classification is advisory-only, not enforced | Medium | Design gap — sophisticated analysis has no effect on output |
| 5 | `auto_gridbox()` blind-docking box is oversized for default exhaustiveness | Medium | Design gap — silent quality trap on a "default" action |
| 6 | Interaction detection is name-heuristic, not chemistry; feeds AI as "absolute truth" | Medium-High | Scientific validity gap — most consequential for user-facing trust |
| 7 | `docking_validation.py` validates file prep, not pose accuracy | Low | Naming/scope mismatch, not incorrect |
| 8 | No salt-stripping before ligand docking prep | Medium | Real bug for real-world (database) SMILES input |
| 9 | No scoring function/seed/exhaustiveness-scaling controls | Low | Missing feature, not a defect |

---

## Proposed fixes (for your review — nothing implemented yet)

**Do not implement any of these until you say go.** Ordered by priority; each is independent and can be accepted/rejected individually.

1. **Wire up ligand pH correction** — pass `ph` from `/docking/generate` into `prepare_docking_structure()`, and inside it call the existing, working `core/openbabel_utils.adjust_ph()`/`protonate_structure()` on the RDKit/OpenBabel molecule before PDBQT export. Low risk, closes finding #1.
2. **Fix protonation ordering** — when `run_protonation=True`, skip OpenBabel's `-p` pH correction in the subsequent `prepare_protein()` call (the receptor is already protonated by PDB2PQR); only apply `-p` when PDB2PQR protonation was *not* requested. Low risk, closes finding #2.
3. **Either implement or remove the non-functional retention toggles** — this is a product decision: (a) implement real selective retention (parse HETATM records for cofactors/metals/active-site waters identified by the existing classification and preserve them explicitly through the PDBQT conversion instead of blanket-stripping), or (b) if that's too large a lift right now, disable/hide the toggles and label the feature "coming soon" rather than presenting controls that silently do nothing. I'd recommend (a) if you plan to dock metalloenzyme/cofactor-dependent targets, otherwise (b) as an honest interim fix.
4. **Connect water classification to receptor prep** — once retention is implemented (#3), have `prepare_receptor()` actually consult `classify_waters()` output rather than a blanket strip, so "keep active-site waters" reflects reality.
5. **Warn on oversized blind-docking boxes** — when the ligand/pocket-based site isn't used and `auto_gridbox()` falls back to whole-receptor bounding box, surface a clear warning in the UI and suggest a higher exhaustiveness (or block the run without confirmation).
6. **Upgrade interaction detection to use real AutoDock atom types** — replace atom-name heuristics with the atom type already present in column 79 of every PDBQT line (`OA`/`HD`/`NA`/`A` etc. directly encode donor/acceptor/aromatic character); compute a real pi-stacking ring-plane angle instead of a distance-only proxy; remove the fabricated `angle=180.0` placeholder (either compute a real angle or omit the field); require the ligand atom to be charged/ionizable for salt-bridge classification, not just proximity to a charged residue name. This is the highest-value fix for scientific credibility, especially given the AI Expert treats this output as ground truth.
7. **Add salt-stripping to the ligand docking-prep path** — call the existing `remove_salts()` before 3D embedding in `prepare_docking_structure()`.
8. **Expose Vina scoring function and seed** — add `scoring_function` (`vina`/`vinardo`) and optional `seed` parameters to `run_vina()` and the `/docking/run` request schema, defaulting to current behavior so nothing breaks for existing callers.
9. **(Optional, larger effort)** Add a genuine redocking/self-validation workflow — given a structure with a co-crystallized ligand, re-dock it into its own site and report RMSD to the native pose, as a trust check before docking novel ligands against the same receptor. This would be a new feature, not a bug fix — flagging it as a "nice to have" for a future phase rather than part of this fix pass.

---

## Implementation notes (post-fix addendum)

All fixes below were implemented on top of the analysis above and verified against the live dev server, not just unit-tested in isolation.

**#1 — Ligand pH correction (`core/docking_preparation.py`, `api/routes/docking.py`)**
`prepare_docking_structure()` now accepts `ph`, corrects ionization via `OpenBabel.adjust_ph()` on the canonical SMILES before RDKit 3D embedding, and `/docking/generate` actually passes its `ph` form field through. **Verified**: aspirin at pH 7.4 produces 13 heavy/polar atoms vs. 14 without correction — the carboxylic acid is correctly deprotonated at physiological pH.

**#2 — Protonation ordering (`docking_workflow/protein_preparation.py`)**
`prepare_receptor()` now tracks whether PDB2PQR/PropKa protonation ran and skips OpenBabel's `-p` pH flag in the subsequent `prepare_protein()` call when it did, so the more accurate per-residue protonation isn't immediately overwritten.

**#3 + #4 — Real selective retention, water classification enforced (`docking_workflow/protein_preparation.py`, `docking_workflow/protein_analysis.py`)**
Added `_classify_and_filter_pdb()`, which uses `analyze_receptor()`/`classify_waters()`/`_classify_hetatm()` as the source of truth to actually filter cofactors, metals, and active-site vs. bulk waters before PDBQT conversion — the `keep_cofactors`/`keep_metals`/`keep_active_site_waters` toggles now do something real.
**Bonus bug found and fixed while wiring this up**: `_classify_hetatm()` checked the generic `ION_RESIDUES` set *before* `METAL_ELEMENTS`, and `ION_RESIDUES` already contained Zn/Mg/Ca/Fe/Cu/Mn/Ni — meaning these catalytically important metals were being classified as disposable "solvent" and never reached the "metal" branch at all. This silently broke the pre-existing `/protein/metals` detection endpoint too, not just the new retention feature. Fixed by checking `METAL_ELEMENTS` first.
**Also found and fixed**: the `/protein_prepare` API route only used the rich preparation path when `keep_cofactors`/`keep_metals`/`remove_bulk_waters` were touched — `run_protonation` and `keep_active_site_waters` alone wouldn't route there, silently skipping protonation. Fixed the routing condition.
**Verified**: a real Zn-metalloprotein PDB (AutoDock-Vina's zinc example) — `keep_metals=False` strips the catalytic Zn (0 remaining), `keep_metals=True` retains it (1 remaining). A synthetic active-site-water/bulk-water test confirms the near-ligand water is kept and the far-away water is stripped exactly as classified.

**#5 — Blind-docking box warning (`templates/docking_workspace.html`)**
`autoGrid()` now checks the returned box's largest dimension; if it exceeds 35 Å (a clear signal of a whole-receptor bounding box rather than a focused pocket), it shows an amber warning naming the actual box size, the current exhaustiveness, and a suggested higher value — cleared automatically if the user then selects a pocket/ligand site instead.

**#6 — Interaction detection rewrite (`docking_workflow/interaction_analyzer.py`, `docking_workflow/interaction_mapper.py`, `docking_workflow/report_builder.py`)**
Replaced the atom-name-heuristic implementation with one based on real AutoDock atom types (`OA`/`HD`/`NA`/`SA`/`A`/`C` — the last field of every PDBQT line). H-bond angles are now computed from an actual bonded donor hydrogen when present, or reported as `None` (not a fabricated `180.0`) when no explicit polar hydrogen exists. Pi-stacking now fits a real ring plane on both the protein aromatic residue and nearby ligand aromatic atoms and classifies parallel vs. T-shaped geometry from the angle between plane normals, instead of a bare distance + name-substring check. Salt bridges now require the ligand atom to itself be charged/ionizable (protonated amine or a close oxygen pair reading as carboxylate/sulfonate-like), matched against specific charged protein side-chain atoms (not just "any atom near Asp/Glu/Lys/Arg"). `Interaction.angle` is now `Optional[float]`, and the report JSON exposes it (previously omitted entirely).
**Verified live**: a real docking run (see below) returned a mix of computed angles (e.g. 163.4°, 139.5° for genuine H-bonds with a resolved donor hydrogen) and honest `None` values, plus one correctly-gated salt bridge (ligand N confirmed protonated, near Glu 58).

**#7 — Salt-stripping (`core/docking_preparation.py`)**
`prepare_docking_structure()` now calls the existing `remove_salts()` whenever the input SMILES contains a `.` (multi-component), keeping only the largest fragment before 3D embedding. **Verified**: `CC(=O)[O-].[Na+]` (sodium acetate) produces a clean 4-heavy-atom acetate PDBQT with no separate sodium fragment.

**#8 — Vina scoring function + seed (`docking_workflow/vina_runner.py`, `services/docking_workspace_service.py`, `api/routes/docking_workspace.py`, `templates/docking_workspace.html`)**
`run_vina()` now accepts `scoring_function` (`vina`/`vinardo`/`ad4`) and `seed`, passed through the CLI (`--scoring`, `--seed`) and the Python `vina` package fallback (`Vina(sf_name=..., seed=...)`), threaded through the service layer, the `/docking/run` request schema, and two new UI fields (Scoring Function dropdown, optional Random Seed input) in Docking Workspace.
**Verified live end-to-end**: ran a real docking job via the HTTP API with `scoring_function="vinardo"`, `seed=42` — Vina's own log confirms `Scoring function : vinardo`, the saved `grid_config` records both values, and the job completed with real poses/affinities and correctly-typed interactions.

**#9 — Redocking/self-validation**: deferred, not built, per your decision.

**Regression check**: all existing pages (`/`, `/docking-workspace`, `/pose-analysis`, `/docking`, dashboard) still return 200 with no new console errors after all changes.
