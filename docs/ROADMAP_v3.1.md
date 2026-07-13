# Roadmap — Chemistry Companion 3.1

**Branch:** `develop/v3.1`  
**Base:** `v3.0.0` (`main` is maintenance for the public 3.0 line)

Version 3.0 is the stable public release. New development proceeds here so `main` can receive only fixes and documentation for 3.0.x patches.

---

## Goals (candidates)

| Theme | Description |
|-------|-------------|
| **Alembic migrations** | Formal DB migration chain for schema evolution |
| **FK enforcement** | Service-layer → database foreign key integrity |
| **AI provider plugins** | Plugin architecture for LLM providers |
| **Reporting & dashboards** | Enhanced reports and operational dashboards |
| **Workflow automation** | Advanced multi-step research automation |
| **Collaboration groundwork** | Multi-user / multi-project foundations |

---

## Process

1. Keep **`main`** at `v3.0.0` (or 3.0.x hotfix tags only).  
2. Land 3.1 features on **`develop/v3.1`** (or feature branches merged into it).  
3. When 3.1 is ready: merge → tag `v3.1.0` → new GitHub Release.  
4. Do not regress installer acceptance criteria without a new validation cycle.

---

## Non-goals for early 3.1

- Rewriting science pipelines without clear need  
- Breaking portable/installer layout without migration notes  
- Shipping unsigned binaries without documenting SmartScreen impact (same as 3.0)
