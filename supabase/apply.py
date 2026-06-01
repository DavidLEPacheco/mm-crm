#!/usr/bin/env python3
"""Apply Supabase migrations for the Mazar Martin CRM project.

Reads the DB password from `pipeline/scripts/.mm_credentials` (gitignored)
and runs every `*.sql` file in `supabase/migrations/` in lexical order, each
in its own transaction.

Usage:
    pipeline/.venv/Scripts/python.exe supabase/apply.py

The script never prints the password — connection-string errors are sanitised.
"""
import os
import sys
from pathlib import Path

SUPABASE_PROJECT_REF = "phkmwcimpyvmxbpdmuvw"
SUPABASE_REGION      = "ap-southeast-2"  # Sydney
# We connect via the session pooler (IPv4-friendly) rather than the direct
# db.<ref>.supabase.co host (which is IPv6-only on newer projects).


CREDS_FILE = Path(__file__).resolve().parent.parent / "pipeline" / "scripts" / ".mm_credentials"


def _read_creds_line(prefix: str) -> str:
    """Return the value after `prefix=` in .mm_credentials, or ''."""
    if not CREDS_FILE.exists():
        return ""
    for line in CREDS_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def load_connection() -> tuple[str, str]:
    """Return (conn_str, secret) — conn_str to dial Supabase, secret to scrub from logs.

    Two ways to provide credentials:
      1) SUPABASE_DB_URL — a full postgresql:// URL (from the Supabase
         dashboard → Settings → Database → Connection string). Preferred.
      2) SUPABASE_DB_PASSWORD — just the password; we construct the
         session-pooler URL ourselves using SUPABASE_PROJECT_REF / SUPABASE_REGION.
    """
    url = os.environ.get("SUPABASE_DB_URL", "").strip() or _read_creds_line("SUPABASE_DB_URL=")
    if url:
        # Sanitise: the secret is whatever sits between ':' and '@' in the URL.
        try:
            secret = url.split("://", 1)[1].split("@", 1)[0].split(":", 1)[1]
        except (IndexError, ValueError):
            secret = ""
        return url, secret

    pw = os.environ.get("SUPABASE_DB_PASSWORD", "").strip() or _read_creds_line("SUPABASE_DB_PASSWORD=")
    if not pw:
        sys.exit(
            f"ERROR: no Supabase credentials found.\n"
            f"Add ONE of these lines to {CREDS_FILE}:\n"
            f"  SUPABASE_DB_URL=<copy from Supabase → Settings → Database → Connection string>\n"
            f"  SUPABASE_DB_PASSWORD=<DB password set when the project was created>"
        )
    # NOTE: The pooler subdomain prefix (aws-0 vs aws-1 vs ...) is assigned per
    # project at creation time — Supabase docs commonly show aws-0, but this
    # project uses aws-1. If the constructor ever stops working, just paste the
    # full string from the dashboard's Connect → Session pooler tab as
    # SUPABASE_DB_URL=... in .mm_credentials and that path takes over.
    url = (
        f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{pw}"
        f"@aws-1-{SUPABASE_REGION}.pooler.supabase.com:5432/postgres"
        f"?sslmode=require"
    )
    return url, pw


def ensure_psycopg2():
    """Self-install psycopg2-binary if absent (matches scrape_agency_websites's pattern)."""
    try:
        import psycopg2  # noqa: F401
        return
    except ImportError:
        pass
    import subprocess
    print("Installing psycopg2-binary into the active venv ...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "psycopg2-binary"],
        check=True,
    )


def sanitise(msg: str, secret: str) -> str:
    return msg.replace(secret, "***") if secret else msg


def main():
    ensure_psycopg2()
    import psycopg2

    conn_str, secret = load_connection()
    host = conn_str.split("@", 1)[1].split("/", 1)[0] if "@" in conn_str else "?"

    migrations_dir = Path(__file__).resolve().parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        sys.exit(f"ERROR: no .sql files in {migrations_dir}")

    print(f"Connecting to {host} ...")
    try:
        conn = psycopg2.connect(conn_str)
    except psycopg2.OperationalError as e:
        sys.exit(f"ERROR: cannot connect to Supabase: {sanitise(str(e), secret)}")

    conn.autocommit = False
    try:
        for f in sql_files:
            print(f"Applying {f.name} ...")
            with conn.cursor() as cur:
                cur.execute(f.read_text(encoding="utf-8"))
            conn.commit()

        print(f"\nApplied {len(sql_files)} migration(s) successfully.\n")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            tables = [row[0] for row in cur.fetchall()]
            print(f"Tables in public schema ({len(tables)}):")
            for t in tables:
                print(f"  - {t}")

            cur.execute("SELECT name FROM orgs ORDER BY created_at")
            orgs = [row[0] for row in cur.fetchall()]
            print(f"\nOrgs ({len(orgs)}):")
            for o in orgs:
                print(f"  - {o}")

            cur.execute("""
                SELECT m.role, u.email
                FROM org_members m
                JOIN auth.users u ON u.id = m.user_id
                ORDER BY u.email
            """)
            members = cur.fetchall()
            print(f"\nOrg members ({len(members)}):")
            for role, email in members:
                print(f"  - {email} ({role})")

    except Exception as e:
        conn.rollback()
        sys.exit(f"ERROR applying migration: {sanitise(str(e), secret)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
