#!/usr/bin/env python3
"""Ensure the 'svix' database exists, creating it if necessary.

Runs before migrations so that svix-server can connect on first deploy.
Uses autocommit because CREATE DATABASE cannot run inside a transaction.
"""

import psycopg
import psycopg.errors
from psycopg.conninfo import make_conninfo

from app.config import settings


def create_svix_db() -> None:
    dsn = make_conninfo("", **settings.db_connection_kwargs)
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'svix'").fetchone()
        if exists:
            print("Svix database already exists, skipping.")
            return

        try:
            conn.execute("CREATE DATABASE svix")
            print("✓ Created 'svix' database.")
        except psycopg.errors.DuplicateDatabase:
            print("Svix database already exists, skipping.")


if __name__ == "__main__":
    create_svix_db()
