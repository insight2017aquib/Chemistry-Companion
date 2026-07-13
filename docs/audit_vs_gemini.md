# Virtual Screening Dropdown Audit (8AAJ)

## Part 1 — Verify Workspace Existence

**Querying the `workspaces` table for 8AAJ:**
```sql
SELECT * FROM workspaces WHERE name LIKE '%8aaj%' COLLATE NOCASE;
```
**Result:** `0 rows returned.`

**Querying the `docking_jobs` table for 8AAJ:**
```sql
SELECT * FROM docking_jobs WHERE receptor_name LIKE '%8aaj%' COLLATE NOCASE;
```
**Result:** `3 rows returned.` (IDs: `8d2a1f74...`, `94ada481...`, `6fb1b9bf...`)

**Conclusion:** 
An 8AAJ *docking job* exists, but an 8AAJ *workspace* does **NOT** exist in the `workspaces` table.

---

## Part 2 — Compare with 4DUH

The newest **4DUH** entry is a full workspace in the `workspaces` table (ID: `wksp_b8d5ffc1a4f8`).
The **8AAJ** entry is a docking job in the `docking_jobs` table (ID: `8d2a1f74-943d-4d3a-92d9-0269ac864128`).

Here is the field-by-field comparison demonstrating the schema and logical differences:

| Field / Attribute | 4DUH (from `workspaces`) | 8AAJ (from `docking_jobs`) | Difference |
| :--- | :--- | :--- | :--- |
| **Table** | `workspaces` | `docking_jobs` | Saved to entirely different database tables. |
| **ID** | `wksp_b8d5ffc1a4f8` | `8d2a1f74-943d-4d3a-92d9-0269ac864128` | Workspace IDs use `wksp_` prefix, Job IDs use pure UUIDs. |
| **module** | `docking` | N/A | `docking_jobs` table does not have a module column. |
| **state JSON** | Yes (`{"step": 3, "exhaustiveness": 8, ...}`) | No (`state` column does not exist) | 8AAJ lacks the Alpine frontend state tracking JSON. |
| **grid JSON** | Inside `state` JSON | Native column (`{"center": {"x": 65.9...}, "size": ...}`) | Structure of grid definition differs completely. |
| **heavy_data.json** | Exists (`...outputs\workspaces\wksp_b8d...\heavy_data.json`) | Does not exist | 8AAJ instead has a `report.json` in the `outputs\docking_workspace` folder. |
| **file_path** | `outputs\workspaces\wksp_b8d5ffc1a4f8\heavy_data.json` | `outputs\docking_workspace\8d2a1f74...` (`workspace_path`) | Paths point to different output directories. |

**First field that differs:** The target **database table** (`workspaces` vs `docking_jobs`). This cascades into missing `state` JSON, missing `heavy_data.json`, and different primary keys.

---

## Part 3 — Workspace Creation Flow

**Did 8AAJ follow exactly the same code path?** 
**No.**

**Trace of the divergent paths:**
*   **Legacy Path (4DUH):** Frontend Wizard -> `WorkspaceManager.create_workspace()` (via POST `/api/workspaces`) -> `workspaces` DB insert -> Workspace updated with `heavy_data.json`.
*   **Current Path (8AAJ):** Frontend Wizard (Job Manager Update) -> `POST /api/docking/run` -> `DockingWorkspaceService.save_docking_job()` -> `docking_jobs` DB insert -> Background task writes `report.json`.

The `update_docking_workspace.py` script migrated the frontend UI to a new "Job Manager" which queues background tasks via `/api/docking/run`. The step that called `WorkspaceManager.create_workspace()` to insert a row into the `workspaces` table is no longer executed. 

---

## Part 4 — Virtual Screening Filter

**Determine exactly why 8AAJ is excluded:**
The Virtual Screening dropdown logic is hardcoded to expect the legacy `workspaces` table schema.

1.  **Network Request:** The UI executes `fetch('/api/workspaces?module=docking')`.
2.  **Received JSON:** The backend serves rows exclusively from the `workspaces` table. Because 8AAJ was saved to `docking_jobs`, it is completely missing from the API payload.
3.  **Filtered JSON:** The frontend filters `this.recentWorkspaces = workspaces.filter(w => w.module === 'docking' && w.file_path);`. (Even if 8AAJ was included, it lacks a `module` property and `file_path` property).
4.  **Final Rendered Options:** Only legacy `4DUH` and `test_probe` rows from the `workspaces` table are appended to the DOM. 8AAJ never reaches the client.
