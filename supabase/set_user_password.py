#!/usr/bin/env python3
"""Set a Supabase user's password directly via the Auth Admin API.

Uses SUPABASE_SECRET_KEY from pipeline/scripts/.mm_credentials. Prompts for the
new password interactively (input is hidden); never logs the value.

Usage:
    pipeline/.venv/Scripts/python.exe supabase/set_user_password.py <email>

Example:
    pipeline/.venv/Scripts/python.exe supabase/set_user_password.py mazarmartinapp@gmail.com
"""
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SUPABASE_PROJECT_REF = "phkmwcimpyvmxbpdmuvw"
CREDS = Path(__file__).resolve().parent.parent / "pipeline" / "scripts" / ".mm_credentials"


def read_creds_line(prefix: str) -> str:
    if not CREDS.exists():
        return ""
    for line in CREDS.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def get_secret() -> str:
    secret = (os.environ.get("SUPABASE_SECRET_KEY", "").strip()
              or read_creds_line("SUPABASE_SECRET_KEY="))
    if not secret:
        sys.exit(
            f"ERROR: SUPABASE_SECRET_KEY not set / not found in {CREDS}.\n"
            f"Add a line `SUPABASE_SECRET_KEY=sb_secret_...` to that file."
        )
    return secret


def api_get(url: str, secret: str):
    req = urllib.request.Request(url, headers={
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_put(url: str, body: dict, secret: str):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
        headers={
            "apikey": secret,
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_user_id(email: str, secret: str, base_url: str) -> str:
    # GoTrue admin /users supports pagination; for this project a single page is plenty.
    data = api_get(f"{base_url}/auth/v1/admin/users?per_page=1000", secret)
    users = data.get("users") if isinstance(data, dict) else data
    if not users:
        sys.exit(f"ERROR: no users found in the project")
    for u in users:
        if (u.get("email") or "").lower() == email.lower():
            return u["id"]
    sys.exit(f"ERROR: user '{email}' not found")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: set_user_password.py <email>")
    email = sys.argv[1].strip()

    secret = get_secret()
    base_url = f"https://{SUPABASE_PROJECT_REF}.supabase.co"

    print(f"Looking up user '{email}' ...")
    try:
        user_id = find_user_id(email, secret, base_url)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        sys.exit(f"ERROR: HTTP {e.code} during lookup: {body}")
    print(f"  Found user id: {user_id}")

    new_pw = getpass.getpass("New password (hidden): ")
    if not new_pw:
        sys.exit("ERROR: empty password")
    confirm = getpass.getpass("Confirm new password: ")
    if new_pw != confirm:
        sys.exit("ERROR: passwords do not match")

    print("Updating password ...")
    try:
        api_put(f"{base_url}/auth/v1/admin/users/{user_id}", {"password": new_pw}, secret)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        # Sanitise — never include the password in errors
        sys.exit(f"ERROR: HTTP {e.code} during update: {body}")

    print(f"\n✅ Password updated for {email}")
    print("Sign in to the app with the new password to verify.")


if __name__ == "__main__":
    main()
