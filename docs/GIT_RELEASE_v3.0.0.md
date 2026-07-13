# Git Release & Distribution — v3.0.0

| Field | Value |
|-------|-------|
| **Version** | 3.0.0 |
| **Build** | 20260713.2254 |
| **Tag** | `v3.0.0` |
| **Commit** | `5d92d12` (`release: Chemistry Companion 3.0.0`) |
| **Branch (stable)** | `main` |
| **Branch (next)** | `develop/v3.1` |
| **Remote** | `origin` → `https://github.com/insight2017aquib/Chemistry-Companion.git` |

---

## Completed locally

- [x] Hardened `.gitignore` (secrets, `dist/`, `node_modules/`, installer tools, archives)
- [x] Clean release commit (278 files, product + docs + installer **sources**)
- [x] Fast-forward `main` to release commit
- [x] Annotated tag `v3.0.0`
- [x] Local archive under `release_archives/v3.0.0/` (gitignored):
  - `ChemistryCompanion-3.0.0-Setup.exe` (SHA-256 `43891280…1EDB`)
  - `ChemistryCompanion-3.0.0-portable-onedir.zip` (SHA-256 `6E7ADEDA…E0D6`)
  - `ARCHIVE_MANIFEST.txt`
- [x] Branch `develop/v3.1` from `main` for post-3.0 work

---

## Push & GitHub Release (operator)

```powershell
# From repository root, on main:
git push -u origin main
git push origin v3.0.0
git push -u origin develop/v3.1
```

Create the GitHub Release (requires `gh` authenticated, or the website):

```powershell
# Install GitHub CLI if needed, then:
gh auth login
gh release create v3.0.0 `
  "release_archives/v3.0.0/ChemistryCompanion-3.0.0-Setup.exe" `
  --title "Chemistry Companion 3.0.0" `
  --notes-file release_notes_v3.md `
  --latest
```

Or: GitHub → Releases → Draft from tag `v3.0.0` → paste `release_notes_v3.md` → upload Setup.exe only.

### Verify download

1. Open the Release page; download Setup.exe.  
2. Confirm size ~131.6 MB and SHA-256 matches:

```text
438912808E2ECF5FB734E0DE4E05DD8C3EECE4453F293411B0B982FD13DE1EDB
```

3. Optional silent smoke:

```powershell
.\ChemistryCompanion-3.0.0-Setup.exe /VERYSILENT /CURRENTUSER `
  /DIR="%LOCALAPPDATA%\Programs\ChemistryCompanion"
```

---

## Do not publish

- `ChemistryCompanion-1.0.0-Setup.exe`
- Full `dist/ChemistryCompanion/` tree with local `.env` / DB pollution
- `release_archives/` portable zip (optional secondary asset; keep offline unless intentional)
- `installer/tools/` (Inno Setup binaries)

---

## Post-3.0 policy

| Line | Branch | Purpose |
|------|--------|---------|
| 3.0.x maintenance | `main` | Hotfixes, docs, security only |
| 3.1 features | `develop/v3.1` | See `docs/ROADMAP_v3.1.md` |

---

## Remote publication status (executed 2026-07-13)

| Item | Status |
|------|--------|
| Tag `v3.0.0` pushed | Yes |
| Branch `release/v3.0.0` pushed | Yes |
| Branch `develop/v3.1` pushed | Yes |
| GitHub Release created | Yes |
| Setup.exe attached | Yes (138,005,950 bytes) |
| Download verified | Yes (HTTP 200, SHA-256 match) |
| `origin/main` updated | **No** — histories diverged; do **not** force-push without explicit decision |

**Release URL:** https://github.com/insight2017aquib/Chemistry-Companion/releases/tag/v3.0.0  

**Installer download:** https://github.com/insight2017aquib/Chemistry-Companion/releases/download/v3.0.0/ChemistryCompanion-3.0.0-Setup.exe  

**SHA-256:** `438912808E2ECF5FB734E0DE4E05DD8C3EECE4453F293411B0B982FD13DE1EDB`

### Decision pending: `main`

Local `main` (v3.0.0 line) and `origin/main` have **unrelated divergent histories** (15 vs 18 commits from different bases after earlier recovery/security rewrites).

Options (choose deliberately):

1. **Force-push local main** (`git push --force-with-lease origin main`) — makes GitHub default branch the v3.0.0 product line.  
2. **Leave default branch** as remote history; treat `release/v3.0.0` + tag as the public product source.  
3. **Merge/reconcile** histories with a merge commit (may be noisy).

Recommendation: option 1 only if no collaborators depend on the current remote `main` tip; otherwise option 2 + set default branch to `release/v3.0.0` in GitHub settings.
