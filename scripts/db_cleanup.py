"""Database cleanup utility for development environments.

Provides scoped table truncation for the Dashy dev database.
Includes safety checks to prevent accidental production data loss.

Usage:
    uv run python scripts/db_cleanup.py --scope full
    uv run python scripts/db_cleanup.py --scope chores
    uv run python scripts/db_cleanup.py --scope categories
    uv run python scripts/db_cleanup.py --scope tags
    uv run python scripts/db_cleanup.py --scope status
"""

import argparse
import os
import sys

import psycopg


# Tables in dependency order (dependents before parents).
# chore_tag_links has composite PK (master_chore_id, tag_id).
CHORE_TABLES = [
    "chore_instances",
    "chore_associations",
    "chore_tag_links",
    "master_chores",
]

ALL_TABLES = [
    *CHORE_TABLES,
    "chore_categories",
    "chore_tags",
    "family_members",
]

# Database names that indicate a production environment.
# The script refuses to run against any of these.
PRODUCTION_DB_NAMES = {"dashy_prod", "dashy_production", "prod", "production"}


def _get_connection(
    host: str, port: int, user: str, password: str, dbname: str,
) -> psycopg.Connection:
    """Open a connection to the PostgreSQL database.

    Args:
        host: Database host.
        port: Database port.
        user: Database user.
        password: Database password.
        dbname: Database name.

    Returns:
        Open psycopg connection.
    """
    return psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=10,
    )


def _safety_check(conn: psycopg.Connection, dbname: str) -> None:
    """Refuse to run against a production database.

    Checks the live database name from the server to prevent
    accidental data loss even if env vars are misconfigured.

    Args:
        conn: Active database connection.
        dbname: Expected database name from configuration.

    Raises:
        SystemExit: If the database appears to be production.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        actual_db = cur.fetchone()[0]

    if actual_db.lower() in PRODUCTION_DB_NAMES:
        print(
            f"ABORT: Database '{actual_db}' looks like production. "
            "This script only runs against development databases.",
            file=sys.stderr,
        )
        sys.exit(1)

    if actual_db != dbname:
        print(
            f"WARNING: Expected database '{dbname}' but connected to '{actual_db}'. "
            "Proceeding anyway.",
            file=sys.stderr,
        )


def _truncate_tables(conn: psycopg.Connection, tables: list[str], label: str) -> None:
    """Truncate the given tables in dependency order.

    Uses TRUNCATE ... CASCADE to handle any FK constraints that
    may exist beyond the known schema.

    Args:
        conn: Active database connection.
        tables: Table names to truncate (in dependency order).
        label: Human-readable label for output.
    """
    if not tables:
        print(f"No tables to clean for '{label}'.")
        return

    table_list = ", ".join(tables)
    print(f"Truncating ({label}): {table_list}")

    with conn.cursor() as cur:
        # CASCADE handles any FK constraints we may not know about.
        cur.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")

    conn.commit()

    # Report row counts after truncation.
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows")


def _show_status(conn: psycopg.Connection) -> None:
    """Print row counts for all Dashy tables.

    Args:
        conn: Active database connection.
    """
    print("Database row counts:")
    with conn.cursor() as cur:
        for table in ALL_TABLES:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count}")


def cleanup_full(conn: psycopg.Connection) -> None:
    """Truncate all Dashy tables — complete fresh start.

    Args:
        conn: Active database connection.
    """
    _truncate_tables(conn, ALL_TABLES, "full database reset")


def cleanup_chores(conn: psycopg.Connection) -> None:
    """Truncate all chore-related tables, preserving family/categories/tags.

    Args:
        conn: Active database connection.
    """
    _truncate_tables(conn, CHORE_TABLES, "chores clean slate")


def cleanup_categories(conn: psycopg.Connection) -> None:
    """Truncate chore_categories table.

    Note: This will fail if master_chores rows reference these categories
    due to FK constraints. Clean chores first if needed.

    Args:
        conn: Active database connection.
    """
    _truncate_tables(conn, ["chore_categories"], "categories")


def cleanup_tags(conn: psycopg.Connection) -> None:
    """Truncate chore_tags table.

    Note: This will fail if chore_tag_links rows reference these tags
    due to FK constraints. Clean chores first if needed.

    Args:
        conn: Active database connection.
    """
    _truncate_tables(conn, ["chore_tags"], "tags")


def main() -> None:
    """Entry point — parse args, connect, dispatch to cleanup function."""
    parser = argparse.ArgumentParser(
        description="Dashy dev database cleanup utility",
    )
    parser.add_argument(
        "scope",
        choices=["full", "chores", "categories", "tags", "status"],
        help="Cleanup scope: full (all tables), chores, categories, tags, or status (row counts only)",
    )
    parser.add_argument(
        "--host", default=os.environ.get("POSTGRES_HOST", "localhost"),
        help="Database host (default: $POSTGRES_HOST or localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("POSTGRES_PORT", "5432")),
        help="Database port (default: $POSTGRES_PORT or 5432)",
    )
    parser.add_argument(
        "--user", default=os.environ.get("POSTGRES_USER", "dashy"),
        help="Database user (default: $POSTGRES_USER or dashy)",
    )
    parser.add_argument(
        "--password", default=os.environ.get("POSTGRES_PASSWORD", "dashy"),
        help="Database password (default: $POSTGRES_PASSWORD or dashy)",
    )
    parser.add_argument(
        "--dbname", default=os.environ.get("POSTGRES_DB", "dashy"),
        help="Database name (default: $POSTGRES_DB or dashy)",
    )

    args = parser.parse_args()

    # Safety: refuse to touch production databases.
    if args.dbname.lower() in PRODUCTION_DB_NAMES:
        print(
            f"ABORT: Database name '{args.dbname}' looks like production. "
            "This script only runs against development databases.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = _get_connection(args.host, args.port, args.user, args.password, args.dbname)

    try:
        _safety_check(conn, args.dbname)

        if args.scope == "status":
            _show_status(conn)
        elif args.scope == "full":
            cleanup_full(conn)
        elif args.scope == "chores":
            cleanup_chores(conn)
        elif args.scope == "categories":
            cleanup_categories(conn)
        elif args.scope == "tags":
            cleanup_tags(conn)

        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
