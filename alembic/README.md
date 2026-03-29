This folder contains Alembic migration scripts for PostgreSQL schema evolution.

Run with your existing Alembic environment configuration:

1. alembic upgrade head
2. alembic history

If your project does not yet have an Alembic env.py and alembic.ini, bootstrap with:

- alembic init alembic

Then copy migration files from alembic/versions.
