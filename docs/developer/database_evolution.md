# Database Evolution & Migration Strategy

## Current State
The Chemistry Companion currently relies on SQLite via SQLAlchemy. Database schema generation is handled by `Base.metadata.create_all(bind=engine)`, which creates tables if they do not exist.

## Problem
`create_all()` does not modify existing tables (e.g., adding a new column to an existing table, changing column types, or adding foreign key constraints). As the application scales (Phase 11 introduces Campaign tracking and Portfolio layers), we need a robust way to alter existing tables without dropping the database and losing user data.

## Future Strategy: Alembic Migrations
To support production-level schema evolution, the project should transition to using **Alembic**.

### Migration Path
1. **Initialize Alembic**: Run `alembic init alembic` to create the migration environment.
2. **Configure `env.py`**: Bind Alembic to the existing SQLAlchemy `engine` and `Base.metadata`.
3. **Generate Baseline**: Create a baseline migration that reflects the *current* state of the database using `alembic revision --autogenerate -m "baseline"`.
4. **Stamp Existing DB**: Stamp the existing SQLite database with the baseline revision hash so it doesn't try to recreate existing tables: `alembic stamp head`.
5. **Future Changes**: For any subsequent changes (like adding the `candidate_status` column to `SeriesCompound` in Phase 11), generate a new migration script and run `alembic upgrade head`.

## Interim Phase 11 Strategy (No Alembic)
Until Alembic is fully configured, Phase 11 avoids altering existing schema columns. 
- New concepts (Portfolios, Campaigns, Decisions) are implemented as completely **new tables** which `create_all()` will seamlessly generate.
- Additional metadata for existing entities (like the `candidate_status` for `SeriesCompound`) will be stored within the existing flexible `properties` JSON column or `tags` array to prevent SQL structural errors.
