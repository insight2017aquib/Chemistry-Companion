# Phase 1 Validation Guide — Real Interactions + Job-Aware Pose Analysis + DB Persistence

This guide helps you verify that the Phase 1 work (real geometric interactions, job-aware Pose Analysis page, and DockingJob DB records) is working correctly.

## Prerequisites
- Restart the Chemistry Companion server after pulling the latest changes.
- Make sure you have the docking dependencies installed (vina + openbabel + rdkit) so `HAS_DOCKING = true`.

## Golden Validation Flow

### 1. Run a Fresh Docking Job
1. Go to `/docking-workspace`
2. Complete the full 4-step wizard with a real protein (PDB) + ligand (SMILES or file).
3. After the run succeeds, you should see:
   - A green success panel
   - A small badge: **"Real interactions computed"**
   - The "Proceed to Pose Analysis →" button should now be a real link containing `?job_id=...`

### 2. Go to Pose Analysis with the Real Job
Click the button (or manually visit `/pose-analysis?job_id=YOUR_JOB_ID`).

**What you should now clearly see (this is the main "I can see the changes" proof):**

- **Prominent emerald/green banner** near the top:
  - "Real Docking Job Loaded"
  - The actual job ID in monospace
  - Tag: "Real interactions"
  - Receptor + Ligand names (if available from DB)

- **Subtitle line**: "Real data from your docking run — interactions computed geometrically (not mocked)"

- **Interactions panel header**: Now says **"Real Interactions (Pose X)"**

- The interactions listed should be real geometrically detected ones (H-bonds, Hydrophobic, Salt Bridge, Pi-Stacking, etc.) coming from the new `interaction_analyzer.py`, **not** the two old hardcoded mock entries.

### 3. Test Pose Switching
- Click different poses in the left sidebar.
- The interaction list should update with fresh real interactions fetched for that specific pose via the API.

### 4. Verify DB Persistence (B work)
In your browser dev tools or with curl:

```bash
curl http://localhost:8000/api/docking/jobs
```

You should see your new job in the list.

```bash
curl http://localhost:8000/api/docking/job/YOUR_JOB_ID
```

You should get both `"report"` (file-based) and `"db_record"` (from the database).

### 5. AI Explanation Still Works
Click "Explain with AI" — it should still function using the real poses + real interactions data.

## Troubleshooting "I Don't See Any Changes"

- Hard restart the server (stop + start).
- Hard refresh the browser (Ctrl + Shift + R) on both pages.
- Make sure you're using a **freshly completed docking job** after the code changes (old jobs won't have the new behavior).
- Check the browser console for any JS errors.
- If `ligandSmiles` is empty, the 3D viewer may fall back to SDF (which is actually better for real poses).

## Success Criteria

- [ ] You see the green "Real Docking Job Loaded" banner with the job ID.
- [ ] Interactions say "Real Interactions".
- [ ] Switching poses updates interactions with plausible real data.
- [ ] `/api/docking/jobs` returns your job from the database.
- [ ] The experience feels clearly different from the old demo/hardcoded version.

Once this flow works end-to-end, Phase 1 (Foundation) is validated and we're ready for deeper Phase 2 work (ChimeraX integration, etc.).
