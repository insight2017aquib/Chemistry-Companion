"""
database/migrations.py
======================
Idempotent, dependency-free schema reconciliation + data backfill for the
Research Workflow Integration.

Why not Alembic: Chemistry Companion ships as a packaged Windows desktop app
against a local SQLite file. A versionless, idempotent reconcile that runs at
startup avoids shipping a migrations directory and a build-time dependency.
Alembic is still the right tool for the staged follow-up that introduces real
ForeignKey constraints (which require full SQLite table rebuilds).

Everything here is safe to run on every startup.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import text

logger = logging.getLogger(__name__)


# Columns introduced by the Research Workflow Integration.
# (table, column, DDL type)
_ADD_COLUMNS = [
    ("portfolios", "project_id", "VARCHAR(50)"),
    ("knowledge_rules", "project_id", "VARCHAR(50)"),
]

# Indexes on the "logical FK" columns. The schema declares no real
# ForeignKeys, so these indexes are what keep scoped queries cheap.
_INDEXES = [
    ("ix_portfolios_project_id", "portfolios", "project_id", False),
    ("ix_knowledge_rules_project_id", "knowledge_rules", "project_id", False),
    ("ix_campaigns_portfolio_id", "optimization_campaigns", "portfolio_id", False),
    ("ix_series_compounds_series_id", "series_compounds", "series_id", False),
    ("ix_decisions_campaign_id", "optimization_decisions", "campaign_id", False),
    ("ix_notebook_project_id", "notebook_entries", "project_id", False),
    ("ix_literature_project_id", "literature_references", "project_id", False),
    ("ix_pub_workspaces_project_id", "publication_workspaces", "project_id", False),
    ("ix_pub_drafts_workspace_id", "publication_drafts", "workspace_id", False),
    ("ix_screening_hits_screening_id", "screening_hits", "screening_id", False),
    # Prevents a series being linked to the same campaign twice.
    ("ux_campaign_series_link", "campaign_series_links", "campaign_id, series_id", True),
]

LEGACY_PROJECT_NAME = "Imported Research Project"
LEGACY_PORTFOLIO_NAME = "Default Portfolio"


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone()
    return row is not None


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    return any(r[1] == column for r in rows)


def _add_missing_columns(conn) -> int:
    added = 0
    for table, column, ddl in _ADD_COLUMNS:
        if not _table_exists(conn, table):
            continue
        if _column_exists(conn, table, column):
            continue
        conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}'))
        logger.info("Migration: added %s.%s", table, column)
        added += 1
    return added


def _create_indexes(conn) -> int:
    created = 0
    for name, table, cols, unique in _INDEXES:
        if not _table_exists(conn, table):
            continue
        # Skip if any referenced column is missing (older/partial schemas).
        if not all(_column_exists(conn, table, c.strip()) for c in cols.split(",")):
            continue
        kind = "UNIQUE INDEX" if unique else "INDEX"
        conn.execute(text(f'CREATE {kind} IF NOT EXISTS "{name}" ON "{table}" ({cols})'))
        created += 1
    return created


def _backfill_portfolio_project_id(conn) -> int:
    """
    Carry any legacy ProjectPortfolioLink rows over to the new
    Portfolio.project_id ownership column. No-op on fresh databases.
    """
    if not _table_exists(conn, "project_portfolio_links"):
        return 0
    result = conn.execute(
        text(
            """
            UPDATE portfolios
               SET project_id = (
                   SELECT l.project_id FROM project_portfolio_links l
                    WHERE l.portfolio_id = portfolios.id
                    LIMIT 1
               )
             WHERE project_id IS NULL
               AND EXISTS (
                   SELECT 1 FROM project_portfolio_links l
                    WHERE l.portfolio_id = portfolios.id
               )
            """
        )
    )
    return result.rowcount or 0


def _orphan_series(conn):
    """
    Chemical series that are NOT reachable from any project via
    Project -> Portfolio -> Campaign -> CampaignSeriesLink.

    This — not "are there zero projects" — is the correct adoption trigger:
    a user may already have projects while older series remain unattached.
    """
    return conn.execute(
        text(
            """
            SELECT s.id, s.name
              FROM chemical_series s
             WHERE s.id NOT IN (
                   SELECT l.series_id
                     FROM campaign_series_links l
                     JOIN optimization_campaigns c ON c.id = l.campaign_id
                     JOIN portfolios p            ON p.id = c.portfolio_id
                    WHERE p.project_id IS NOT NULL
             )
             ORDER BY s.created_at
            """
        )
    ).fetchall()


def _get_or_create_import_project(conn) -> str:
    project_id = conn.execute(
        text("SELECT id FROM research_projects WHERE name = :n LIMIT 1"),
        {"n": LEGACY_PROJECT_NAME},
    ).scalar()
    if project_id:
        return project_id

    project_id = f"proj_{uuid.uuid4().hex[:10]}"
    conn.execute(
        text(
            "INSERT INTO research_projects (id, name, objectives, target, status) "
            "VALUES (:id, :name, :obj, '', 'Active')"
        ),
        {
            "id": project_id,
            "name": LEGACY_PROJECT_NAME,
            "obj": "Automatically created to adopt data that predates project-scoped workflows.",
        },
    )
    return project_id


def _backfill_legacy_project(conn) -> bool:
    """
    Adopt pre-integration data into the canonical hierarchy, in two steps:

      1. Orphan PORTFOLIOS (project_id IS NULL) are attached to the import
         project. This preserves the user's real structure and its campaigns
         rather than synthesizing a parallel one.
      2. Any series still unreachable afterwards get a "<Series> Campaign"
         under a Default Portfolio.

    Idempotent: once adopted, nothing is orphaned, so re-runs are no-ops.
    Existing user projects are never modified.
    """
    required = ("research_projects", "chemical_series", "portfolios",
                "optimization_campaigns", "campaign_series_links")
    if not all(_table_exists(conn, t) for t in required):
        return False

    orphan_portfolios = conn.execute(
        text("SELECT id FROM portfolios WHERE project_id IS NULL")
    ).fetchall()
    if not orphan_portfolios and not _orphan_series(conn):
        return False

    project_id = _get_or_create_import_project(conn)

    # Step 1 — adopt orphan portfolios (brings their campaigns + series along).
    if orphan_portfolios:
        conn.execute(
            text("UPDATE portfolios SET project_id = :p WHERE project_id IS NULL"),
            {"p": project_id},
        )
        logger.info(
            "Migration: adopted %d orphan portfolio(s) into '%s'",
            len(orphan_portfolios), LEGACY_PROJECT_NAME,
        )

    # Step 2 — any series still unattached gets its own campaign.
    series = _orphan_series(conn)
    if series:
        portfolio_id = conn.execute(
            text("SELECT id FROM portfolios WHERE project_id = :p AND name = :n LIMIT 1"),
            {"p": project_id, "n": LEGACY_PORTFOLIO_NAME},
        ).scalar()

        if not portfolio_id:
            portfolio_id = f"port_{uuid.uuid4().hex[:10]}"
            conn.execute(
                text(
                    "INSERT INTO portfolios (id, project_id, name, description) "
                    "VALUES (:id, :pid, :name, :desc)"
                ),
                {
                    "id": portfolio_id,
                    "pid": project_id,
                    "name": LEGACY_PORTFOLIO_NAME,
                    "desc": "Holds campaigns adopted from pre-integration chemical series.",
                },
            )

        for series_id, series_name in series:
            campaign_id = f"camp_{uuid.uuid4().hex[:10]}"
            conn.execute(
                text(
                    "INSERT INTO optimization_campaigns (id, portfolio_id, name, goal_type, mpo_weights) "
                    "VALUES (:id, :pid, :name, 'generic', '{}')"
                ),
                {"id": campaign_id, "pid": portfolio_id, "name": f"{series_name} Campaign"},
            )
            conn.execute(
                text("INSERT INTO campaign_series_links (campaign_id, series_id) VALUES (:c, :s)"),
                {"c": campaign_id, "s": series_id},
            )
        logger.info(
            "Migration: adopted %d orphan series into '%s'", len(series), LEGACY_PROJECT_NAME
        )

    return True


def run_migrations(engine) -> None:
    """Reconcile schema and backfill legacy data. Safe to call on every startup."""
    with engine.begin() as conn:
        added = _add_missing_columns(conn)
        _create_indexes(conn)
        carried = _backfill_portfolio_project_id(conn)
        adopted = _backfill_legacy_project(conn)

    if added or carried or adopted:
        logger.info(
            "Migration complete (columns_added=%s, portfolios_relinked=%s, legacy_adopted=%s)",
            added,
            carried,
            adopted,
        )
