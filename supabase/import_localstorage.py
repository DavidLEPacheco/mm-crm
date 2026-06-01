#!/usr/bin/env python3
"""Import a localStorage dump (DevTools snippet output) into Supabase.

Reads a JSON file produced by this one-liner in the browser console:
    copy(Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])))

For each known mm* key, writes to the appropriate Supabase tables via the
SAME patterns as the JS adapters in mm-supabase.js. Unknown keys and
sensitive/cache keys are skipped (logged).

Run-time prerequisites:
  - Org '{ORG_NAME}' must exist (run supabase/apply.py first).
  - User '{USER_EMAIL}' must exist in auth.users (the shared login).
  - Credentials in pipeline/scripts/.mm_credentials (same as apply.py).

Usage:
    pipeline/.venv/Scripts/python.exe supabase/import_localstorage.py path/to/dump.json
    pipeline/.venv/Scripts/python.exe supabase/import_localstorage.py path/to/dump.json --wipe
        (--wipe clears the org's existing localStorage-derived tables first;
         use it at cutover so Gerard's dump becomes canonical)
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS = REPO_ROOT / "pipeline" / "scripts" / ".mm_credentials"

SUPABASE_PROJECT_REF = "phkmwcimpyvmxbpdmuvw"
SUPABASE_REGION = "ap-southeast-2"
ORG_NAME = "Mazar Martin"
USER_EMAIL = "mazarmartinapp@gmail.com"

# Simple per-user blobs → user_kv table.
USER_KV_KEYS = {
    'mmCommissionUnlocked', 'mmStatOverrides', 'mmWeek', 'mm_news_dismissed',
    'mmAutoMatches', 'mmAutoMatchLastRun', 'mmAutoMatchTs',
    'mmBuyerTemp', 'mmBuyerTemps', 'mmTemps', 'mmNewSale', 'mmNewOff',
}

# Keys we deliberately do NOT import (sensitive or regenerable cache).
SKIP_KEYS = {
    'mmClaudeKey',    # API key — stays browser-local
    'mmGeoCache', 'mmZoningCache2', 'mmPropImgCache', 'mmDomainEnrich',
    'mmMatchSummary', 'mmSwipeDeckMount',
}


# ─── Credentials & connection (mirrors apply.py / migrate_data.py) ───────

def read_creds_line(prefix: str) -> str:
    if not CREDS.exists():
        return ""
    for line in CREDS.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def load_conn_str() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_DB_URL", "").strip() or read_creds_line("SUPABASE_DB_URL=")
    if url:
        try:
            secret = url.split("://", 1)[1].split("@", 1)[0].split(":", 1)[1]
        except (IndexError, ValueError):
            secret = ""
        return url, secret
    pw = os.environ.get("SUPABASE_DB_PASSWORD", "").strip() or read_creds_line("SUPABASE_DB_PASSWORD=")
    if not pw:
        sys.exit(f"ERROR: no Supabase credentials in {CREDS}")
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


def sanitise(msg: str, secret: str) -> str:
    return msg.replace(secret, "***") if secret else msg


# ─── Parsing helpers ─────────────────────────────────────────────────────

def parse_json(value, fallback=None):
    """localStorage values are strings; usually JSON. Parse leniently."""
    if value is None:
        return fallback
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def resolve_client_id(cur, name: str, org_id, user_id) -> str:
    """Find a client by (org_id, name) or create it on the fly."""
    cur.execute("SELECT id FROM clients WHERE org_id = %s AND name = %s", (org_id, name))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO clients (org_id, name, created_by) VALUES (%s, %s, %s) RETURNING id",
        (org_id, name, user_id),
    )
    return cur.fetchone()[0]


# ─── Importers (one per mm* key, mirroring the JS adapters) ──────────────

def import_user_kv_blob(cur, key, raw, user_id):
    from psycopg2.extras import Json
    cur.execute(
        """INSERT INTO user_kv (user_id, key, value) VALUES (%s, %s, %s)
           ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value""",
        (user_id, key, Json(raw)),
    )
    return 1


def import_client_edits(cur, raw, org_id, user_id):
    from psycopg2.extras import Json
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    for name, edits in obj.items():
        if not name:
            continue
        cur.execute(
            """INSERT INTO clients (org_id, name, edits, created_by) VALUES (%s, %s, %s, %s)
               ON CONFLICT (org_id, name) DO UPDATE SET edits = EXCLUDED.edits""",
            (org_id, name, Json(edits or {}), user_id),
        )
    return len(obj)


def import_deleted_clients(cur, raw, org_id):
    arr = parse_json(raw, [])
    if not isinstance(arr, list):
        return 0
    for name in arr:
        if isinstance(name, str) and name:
            cur.execute(
                """UPDATE clients SET deleted_at = COALESCE(deleted_at, now())
                   WHERE org_id = %s AND name = %s""",
                (org_id, name),
            )
    return len(arr)


def import_call_status(cur, raw, org_id):
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    for agent_key, status in obj.items():
        if not isinstance(status, dict):
            continue
        cur.execute(
            """INSERT INTO agent_calls (org_id, agent_key, called, voicemail) VALUES (%s, %s, %s, %s)
               ON CONFLICT (org_id, agent_key) DO UPDATE SET called = EXCLUDED.called, voicemail = EXCLUDED.voicemail""",
            (org_id, agent_key, bool(status.get('called')), bool(status.get('voicemail'))),
        )
    return len(obj)


def import_call_comments(cur, raw, org_id):
    from psycopg2.extras import Json
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    for agent_key, comments in obj.items():
        comments = comments if isinstance(comments, list) else []
        cur.execute(
            """INSERT INTO agent_calls (org_id, agent_key, comments) VALUES (%s, %s, %s)
               ON CONFLICT (org_id, agent_key) DO UPDATE SET comments = EXCLUDED.comments""",
            (org_id, agent_key, Json(comments)),
        )
    return len(obj)


def import_saved_matches(cur, raw, org_id, user_id):
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    n = 0
    for client_name, items in obj.items():
        if not isinstance(items, list):
            continue
        cid = resolve_client_id(cur, client_name, org_id, user_id)
        cur.execute("DELETE FROM saved_matches WHERE client_id = %s", (cid,))
        for it in items:
            if not isinstance(it, dict):
                continue
            cur.execute(
                """INSERT INTO saved_matches
                   (client_id, property_address, suburb, price, property_type, note, saved_by, saved_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (cid, it.get('address') or '', it.get('suburb'), it.get('price'),
                 it.get('type'), it.get('note'), user_id, it.get('savedAt')),
            )
            n += 1
    return n


def import_per_client_addresses(cur, raw, table, addr_col, by_col, org_id, user_id):
    """Shared logic for mmDismissedProps / mmPresented: {name: [address, …]}."""
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    n = 0
    for client_name, items in obj.items():
        if not isinstance(items, list):
            continue
        cid = resolve_client_id(cur, client_name, org_id, user_id)
        cur.execute(f"DELETE FROM {table} WHERE client_id = %s", (cid,))
        for it in items:
            address = it if isinstance(it, str) else (it.get('address') if isinstance(it, dict) else None)
            if not address:
                continue
            cur.execute(
                f"INSERT INTO {table} (client_id, property_address, {by_col}) VALUES (%s, %s, %s)",
                (cid, address, user_id),
            )
            n += 1
    return n


def import_client_comments(cur, raw, org_id, user_id):
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    n = 0
    for client_name, items in obj.items():
        if not isinstance(items, list):
            continue
        cid = resolve_client_id(cur, client_name, org_id, user_id)
        cur.execute("DELETE FROM client_comments WHERE client_id = %s", (cid,))
        for it in items:
            body = it if isinstance(it, str) else (it.get('body') if isinstance(it, dict) else None)
            if not body:
                continue
            cur.execute(
                "INSERT INTO client_comments (client_id, body, created_by) VALUES (%s, %s, %s)",
                (cid, body, user_id),
            )
            n += 1
    return n


def import_client_activity(cur, raw, org_id, user_id):
    from psycopg2.extras import Json
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    n = 0
    for client_name, items in obj.items():
        if not isinstance(items, list):
            continue
        cid = resolve_client_id(cur, client_name, org_id, user_id)
        cur.execute("DELETE FROM client_activity WHERE client_id = %s", (cid,))
        for it in items:
            kind = (it.get('kind') if isinstance(it, dict) else None) or 'note'
            body = it if isinstance(it, dict) else {'value': it}
            cur.execute(
                "INSERT INTO client_activity (client_id, kind, body, created_by) VALUES (%s, %s, %s, %s)",
                (cid, kind, Json(body), user_id),
            )
            n += 1
    return n


def import_prop_comments(cur, raw, org_id, user_id):
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    n = 0
    for address, items in obj.items():
        if not address or not isinstance(items, list):
            continue
        cur.execute(
            "DELETE FROM property_comments WHERE org_id = %s AND property_address = %s",
            (org_id, address),
        )
        for it in items:
            body = it if isinstance(it, str) else (it.get('body') if isinstance(it, dict) else None)
            if not body:
                continue
            cur.execute(
                """INSERT INTO property_comments (org_id, property_address, body, created_by)
                   VALUES (%s, %s, %s, %s)""",
                (org_id, address, body, user_id),
            )
            n += 1
    return n


def import_listing_edits(cur, raw, listing_type, org_id):
    from psycopg2.extras import Json
    obj = parse_json(raw, {})
    if not isinstance(obj, dict):
        return 0
    for address, edits in obj.items():
        if not address:
            continue
        cur.execute(
            """INSERT INTO listing_edits (org_id, property_address, listing_type, edits)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (org_id, property_address, listing_type) DO UPDATE SET edits = EXCLUDED.edits""",
            (org_id, address, listing_type, Json(edits or {})),
        )
    return len(obj)


def import_listing_flag(cur, raw, flag_col, listing_type, org_id):
    arr = parse_json(raw, [])
    if not isinstance(arr, list):
        return 0
    for address in arr:
        if isinstance(address, str) and address:
            # Sanity: flag_col is whitelisted, so f-string interpolation is safe.
            assert flag_col in ('is_blacklisted', 'is_deleted')
            cur.execute(
                f"""INSERT INTO listing_edits (org_id, property_address, listing_type, {flag_col})
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (org_id, property_address, listing_type) DO UPDATE SET {flag_col} = true""",
                (org_id, address, listing_type),
            )
    return len(arr)


# ─── Wipe (optional, for clean cutover re-import) ────────────────────────

def wipe_org_data(cur, org_id):
    print(f"  Wiping existing localStorage-derived data for org {org_id} …")
    cur.execute(
        "DELETE FROM saved_matches WHERE client_id IN (SELECT id FROM clients WHERE org_id = %s)",
        (org_id,))
    cur.execute(
        "DELETE FROM dismissed_props WHERE client_id IN (SELECT id FROM clients WHERE org_id = %s)",
        (org_id,))
    cur.execute(
        "DELETE FROM presented_props WHERE client_id IN (SELECT id FROM clients WHERE org_id = %s)",
        (org_id,))
    cur.execute(
        "DELETE FROM client_comments WHERE client_id IN (SELECT id FROM clients WHERE org_id = %s)",
        (org_id,))
    cur.execute(
        "DELETE FROM client_activity WHERE client_id IN (SELECT id FROM clients WHERE org_id = %s)",
        (org_id,))
    cur.execute("DELETE FROM property_comments WHERE org_id = %s", (org_id,))
    cur.execute("DELETE FROM agent_calls WHERE org_id = %s", (org_id,))
    cur.execute("DELETE FROM listing_edits WHERE org_id = %s", (org_id,))
    cur.execute("DELETE FROM manual_listings WHERE org_id = %s", (org_id,))
    cur.execute(
        "UPDATE clients SET edits = '{}'::jsonb, deleted_at = NULL WHERE org_id = %s",
        (org_id,))


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", help="path to localStorage dump JSON file")
    ap.add_argument("--wipe", action="store_true",
                    help="clear the org's localStorage-derived tables before importing")
    args = ap.parse_args()

    dump_path = Path(args.dump)
    if not dump_path.exists():
        sys.exit(f"ERROR: dump file not found: {dump_path}")

    ensure_psycopg2()
    import psycopg2

    conn_str, secret = load_conn_str()

    print(f"Loading {dump_path} ...")
    dump = json.loads(dump_path.read_text(encoding="utf-8"))
    if not isinstance(dump, dict):
        sys.exit("ERROR: dump must be a JSON object {key: value, ...}")
    print(f"  Found {len(dump)} keys in dump")

    print("Connecting ...")
    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM orgs WHERE name = %s", (ORG_NAME,))
            row = cur.fetchone()
            if not row:
                sys.exit(f"ERROR: org '{ORG_NAME}' not found — run supabase/apply.py first")
            org_id = row[0]

            cur.execute("SELECT id FROM auth.users WHERE email = %s", (USER_EMAIL,))
            row = cur.fetchone()
            if not row:
                sys.exit(f"ERROR: user '{USER_EMAIL}' not found in auth.users")
            user_id = row[0]
            print(f"  org_id = {org_id}")
            print(f"  user_id = {user_id}")

            if args.wipe:
                wipe_org_data(cur, org_id)

            counts = {}
            skipped = {}

            for key, raw in dump.items():
                if key in SKIP_KEYS or key.startswith('mmSwipeQueue_'):
                    skipped[key] = '(skipped — sensitive or ephemeral)'
                    continue
                if key in USER_KV_KEYS:
                    counts[key] = import_user_kv_blob(cur, key, raw, user_id)
                elif key == 'mmClientEdits':
                    counts[key] = import_client_edits(cur, raw, org_id, user_id)
                elif key == 'mmDeletedClients':
                    counts[key] = import_deleted_clients(cur, raw, org_id)
                elif key == 'mmCallStatus':
                    counts[key] = import_call_status(cur, raw, org_id)
                elif key == 'mmCallComments':
                    counts[key] = import_call_comments(cur, raw, org_id)
                elif key == 'mmSavedMatches':
                    counts[key] = import_saved_matches(cur, raw, org_id, user_id)
                elif key == 'mmDismissedProps':
                    counts[key] = import_per_client_addresses(
                        cur, raw, 'dismissed_props', 'property_address', 'dismissed_by',
                        org_id, user_id)
                elif key == 'mmPresented':
                    counts[key] = import_per_client_addresses(
                        cur, raw, 'presented_props', 'property_address', 'presented_by',
                        org_id, user_id)
                elif key == 'mmClientComments':
                    counts[key] = import_client_comments(cur, raw, org_id, user_id)
                elif key == 'mmClientActivity':
                    counts[key] = import_client_activity(cur, raw, org_id, user_id)
                elif key == 'mmPropComments':
                    counts[key] = import_prop_comments(cur, raw, org_id, user_id)
                elif key == 'mmForSaleEdits':
                    counts[key] = import_listing_edits(cur, raw, 'forsale', org_id)
                elif key == 'mmSoldEdits':
                    counts[key] = import_listing_edits(cur, raw, 'sold', org_id)
                elif key == 'mmBlacklist':
                    counts[key] = import_listing_flag(cur, raw, 'is_blacklisted', 'forsale', org_id)
                elif key == 'mmDeletedFS':
                    counts[key] = import_listing_flag(cur, raw, 'is_deleted', 'forsale', org_id)
                else:
                    skipped[key] = '(unknown key — not imported)'

            conn.commit()

            print(f"\n✅ Imported {len(counts)} key(s):")
            for k, n in sorted(counts.items()):
                print(f"  {k}: {n} item(s)")
            if skipped:
                print(f"\nSkipped {len(skipped)} key(s):")
                for k, reason in sorted(skipped.items()):
                    print(f"  {k} {reason}")

    except Exception as e:
        conn.rollback()
        sys.exit(f"ERROR: {sanitise(str(e), secret)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
