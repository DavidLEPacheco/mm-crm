#!/usr/bin/env python3
"""Migrate whiteboard data into Supabase clients table.

Reads `whiteboard_data.json` (Gerard's manual export from his app's Safari)
and upserts each client record into the Mazar Martin org's `clients` table.

IDEMPOTENT — re-running with a fresher whiteboard updates existing rows by
(org_id, name), inserts any new ones, and resets soft-deletes. The `edits`
JSONB column on existing rows is preserved (the upsert only touches the
schema columns it writes).

NOTE: This script does NOT migrate localStorage state (mmCallStatus,
mmSavedMatches, mmClientComments, etc.) — those live in Gerard's browser
and need a separate DevTools-snippet capture at cutover time.

Usage:
    pipeline/.venv/Scripts/python.exe supabase/migrate_data.py
    pipeline/.venv/Scripts/python.exe supabase/migrate_data.py --whiteboard <path>
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS = REPO_ROOT / "pipeline" / "scripts" / ".mm_credentials"
DEFAULT_WHITEBOARD = REPO_ROOT / "pythonfiles" / "loose_files" / "whiteboard_data.json"

SUPABASE_PROJECT_REF = "phkmwcimpyvmxbpdmuvw"
SUPABASE_REGION = "ap-southeast-2"
ORG_NAME = "Mazar Martin"

# Whiteboard top-level keys → app section labels. Used as a fallback when a
# record doesn't have an explicit `section` field of its own.
SECTION_MAP = {
    "activeBuyers": "Active Buyer",
    "pipeline":     "Pipeline",
    "settlements":  "Settlements",
    "offMarkets":   "Off Markets",
    "sellers":      "Sellers",
}


def read_creds_line(prefix: str) -> str:
    if not CREDS.exists():
        return ""
    for line in CREDS.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def load_conn_str() -> tuple[str, str]:
    """Return (conn_str, secret-to-scrub) from .mm_credentials or env."""
    url = os.environ.get("SUPABASE_DB_URL", "").strip() or read_creds_line("SUPABASE_DB_URL=")
    if url:
        try:
            secret = url.split("://", 1)[1].split("@", 1)[0].split(":", 1)[1]
        except (IndexError, ValueError):
            secret = ""
        return url, secret
    pw = os.environ.get("SUPABASE_DB_PASSWORD", "").strip() or read_creds_line("SUPABASE_DB_PASSWORD=")
    if not pw:
        sys.exit(
            f"ERROR: no Supabase credentials found. Add SUPABASE_DB_URL=… or "
            f"SUPABASE_DB_PASSWORD=… to {CREDS}"
        )
    url = (
        f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{pw}"
        f"@aws-1-{SUPABASE_REGION}.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    return url, pw


def ensure_psycopg2():
    try:
        import psycopg2  # noqa: F401
        return
    except ImportError:
        import subprocess
        print("Installing psycopg2-binary ...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "psycopg2-binary"],
            check=True,
        )


def parse_commission(v):
    """Parse a commission value into float-or-None.

    Handles raw numbers, '143000', '$143,000', '', and None.
    """
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_row(c: dict, org_id: str) -> dict:
    """Convert a whiteboard client dict to a clients-table row."""
    return {
        "org_id":     org_id,
        "name":       (c.get("name") or "").strip(),
        "section":    c.get("section") or None,
        "ba":         c.get("ba") or None,
        "referrer":   c.get("referrer") or None,
        "budget":     c.get("budget") or None,
        "spec":       c.get("spec") or None,
        "locations":  c.get("locations") or None,
        "target":     c.get("target") or None,
        "commission": parse_commission(c.get("commission")),
        "exp":        c.get("exp") or None,
        "status":     c.get("status") or None,
        "notes":      c.get("notes") or None,
        "date":       c.get("date") or None,
        # Always reset soft-delete on re-import — treat the whiteboard as
        # canonical for "who exists right now". (Refine later if needed.)
        "deleted_at": None,
    }


def sanitise(msg: str, secret: str) -> str:
    return msg.replace(secret, "***") if secret else msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--whiteboard", default=str(DEFAULT_WHITEBOARD),
                    help="path to whiteboard_data.json (default: pythonfiles/loose_files/whiteboard_data.json)")
    args = ap.parse_args()

    wb_path = Path(args.whiteboard)
    if not wb_path.exists():
        sys.exit(f"ERROR: whiteboard file not found: {wb_path}")

    ensure_psycopg2()
    import psycopg2
    from psycopg2.extras import execute_values

    conn_str, secret = load_conn_str()

    print(f"Loading {wb_path} ...")
    data = json.loads(wb_path.read_text(encoding="utf-8"))

    # Flatten all clients across sections, but use the parent key as a
    # fallback `section` for records that don't have one of their own.
    raw_clients = []
    for key, items in data.items():
        if not isinstance(items, list):
            continue
        default_section = SECTION_MAP.get(key, key)
        for c in items:
            if not c.get("section"):
                c = {**c, "section": default_section}
            raw_clients.append(c)
    print(f"  Found {len(raw_clients)} client records across {len(data)} sections")

    # Filter out unnamed records — we can't upsert without a natural key.
    usable = [c for c in raw_clients if (c.get("name") or "").strip()]
    skipped = len(raw_clients) - len(usable)
    if skipped:
        print(f"  Skipping {skipped} records without a name")

    if not usable:
        sys.exit("ERROR: nothing to import")

    host = conn_str.split("@", 1)[1].split("/", 1)[0] if "@" in conn_str else "?"
    print(f"Connecting to {host} ...")
    conn = psycopg2.connect(conn_str)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM orgs WHERE name = %s LIMIT 1", (ORG_NAME,))
            row = cur.fetchone()
            if not row:
                sys.exit(f"ERROR: org '{ORG_NAME}' not found — apply migration 0001 first")
            org_id = row[0]
            print(f"  Mazar Martin org_id: {org_id}")

            # Dedupe by name (case-insensitive) — last occurrence wins.
            # Source whiteboard sometimes lists the same client in two sections.
            by_name = {}
            for r in [to_row(c, org_id) for c in usable]:
                by_name[r["name"].lower()] = r
            rows = list(by_name.values())
            collapsed = len(usable) - len(rows)
            if collapsed:
                print(f"  Collapsed {collapsed} duplicate name(s) — keeping last occurrence")

            columns = list(rows[0].keys())
            update_cols = [c for c in columns if c not in ("org_id", "name")]
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
            sql = (
                f"INSERT INTO clients ({', '.join(columns)}) VALUES %s "
                f"ON CONFLICT (org_id, name) DO UPDATE SET {set_clause}"
            )
            values = [[r[k] for k in columns] for r in rows]
            execute_values(cur, sql, values, page_size=100)
            conn.commit()
            print(f"  Upserted {len(rows)} client rows")

            # Summary
            cur.execute(
                "SELECT count(*) FROM clients WHERE org_id = %s AND deleted_at IS NULL",
                (org_id,),
            )
            total = cur.fetchone()[0]
            print(f"\nLive clients in org: {total}")

            cur.execute(
                "SELECT section, count(*) FROM clients WHERE org_id = %s "
                "AND deleted_at IS NULL GROUP BY section ORDER BY count(*) DESC",
                (org_id,),
            )
            print("By section:")
            for sec, n in cur.fetchall():
                print(f"  {sec or '(no section)'}: {n}")

    except Exception as e:
        conn.rollback()
        sys.exit(f"ERROR: {sanitise(str(e), secret)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
