#!/usr/bin/env python3
"""
run_email_update.py
Master runner: parses Proping + off-market emails, then injects into dashboard.
Run this each morning after Proping emails arrive (or schedule it at 8am weekdays).

Usage:
    python3 run_email_update.py
    python3 run_email_update.py --proping-only
    python3 run_email_update.py --offmarket-only
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS = Path(__file__).parent


def run(script_name, label):
    print(f"\n{'='*60}")
    print(f"▶ {label}")
    print('='*60)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name)],
        capture_output=False  # stream output directly
    )
    if result.returncode != 0:
        print(f"⚠ {script_name} exited with code {result.returncode}")
    return result.returncode == 0


def main():
    args = sys.argv[1:]
    proping_only  = '--proping-only'  in args
    offmarket_only = '--offmarket-only' in args

    print(f"\n{'#'*60}")
    print(f"  Email Update Pipeline")
    print(f"  {datetime.now().strftime('%A %d %B %Y  %H:%M')}")
    print(f"{'#'*60}")

    ok = True

    if not offmarket_only:
        ok &= run('parse_proping.py', 'Step 1/3 — Parse Proping emails')

    if not proping_only:
        ok &= run('parse_offmarket_emails.py', 'Step 2/3 — Parse off-market agent emails')

    run('inject_email_data.py', 'Step 3/3 — Inject data into dashboard')

    print(f"\n{'='*60}")
    print(f"✅ Done  —  {datetime.now().strftime('%H:%M:%S')}")
    print(f"Open mazar_martin_app.html to see updated data.")
    print('='*60)


if __name__ == '__main__':
    main()
