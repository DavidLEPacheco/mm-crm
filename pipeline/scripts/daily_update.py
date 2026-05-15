#!/usr/bin/env python3
"""
daily_update.py — One-command daily Proping pipeline
=====================================================
Run this each morning after Proping emails arrive.

Steps:
  1. Parse Proping emails from Gmail -> proping_data.json + proping_history.json
  2. Inject history into mazar_martin_app.html (propingHistory, D.sampleListings, etc.)
  3. Off-market scrape (OTH + Domain/REA via Playwright + agency sites) + inject
  4. Wash properties: fill blank propertyType/beds/baths/parking/landSize/url
     against the freshly-scraped local Domain caches
  5. Copy updated app to mazar-martin-deploy/index.html
  6. Print summary

Usage:
  python3 daily_update.py              # Full pipeline
  python3 daily_update.py --skip-email # Skip Gmail extraction, use existing history
  python3 daily_update.py --dry-run    # Parse emails but don't write to app
"""

import sys
import shutil
import argparse
import traceback
from datetime import datetime
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
DOWNLOADS   = SCRIPT_DIR.parent
APP_PATH    = DOWNLOADS / 'mazar_martin_app.html'
DEPLOY_PATH = DOWNLOADS / 'mazar-martin-deploy' / 'index.html'
HISTORY_FILE = DOWNLOADS / 'proping_history.json'

sys.path.insert(0, str(SCRIPT_DIR))


def step_banner(num, title):
    print(f"\n{'─'*60}")
    print(f"  Step {num}: {title}")
    print(f"{'─'*60}")


def main():
    parser = argparse.ArgumentParser(description='Daily Proping update pipeline')
    parser.add_argument('--skip-email', action='store_true',
                        help='Skip Gmail email extraction, use existing history file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse emails but do not modify app files')
    args = parser.parse_args()

    print("=" * 60)
    print("  MAZAR MARTIN — Daily Proping Pipeline")
    print(f"  {datetime.today().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    errors = []

    # ── Step 1: Parse Proping emails ─────────────────────────────────────
    if not args.skip_email:
        step_banner(1, "Extract & Parse Proping Emails from Gmail")
        try:
            import subprocess as _sp
            _sp.run([sys.executable, 'scrape_gmail.py', '--proping-only', '--days', '7'], check=True)
            print("  [OK] Email parsing complete.")
        except Exception as e:
            msg = f"Email parsing failed: {e}"
            print(f"  [ERROR] {msg}")
            traceback.print_exc()
            errors.append(msg)
            if not HISTORY_FILE.exists():
                print("  No history file exists. Cannot continue.")
                return 1
            print("  Continuing with existing history file...")
    else:
        step_banner(1, "Skipping email extraction (--skip-email)")
        if HISTORY_FILE.exists():
            print(f"  Using existing: {HISTORY_FILE}")
        else:
            print(f"  [ERROR] No history file found at {HISTORY_FILE}")
            return 1

    # ── Step 2: Inject into app HTML ─────────────────────────────────────
    if args.dry_run:
        step_banner(2, "Dry run — skipping injection")
        print("  Would inject into:", APP_PATH)
    else:
        step_banner(2, "Inject Proping Data into App")
        try:
            import inject_proping_data
            inject_proping_data.main()
            summary = {}
            print("  [OK] Injection complete.")
        except Exception as e:
            msg = f"Injection failed: {e}"
            print(f"  [ERROR] {msg}")
            traceback.print_exc()
            errors.append(msg)

    # ── Step 3: Off-Market Scrape + Inject ──────────────────────────────
    if args.dry_run:
        step_banner(3, "Dry run — skipping off-market scrape")
        print("  Would scrape OTH + Domain and inject new off-markets")
    else:
        step_banner(3, "Off-Market Scrape + Dedup + Inject")
        try:
            import inject_offmarket
            om_summary = inject_offmarket.inject(app_path=APP_PATH, scrape=True)
            new_om = om_summary.get('new', 0)
            deduped = om_summary.get('deduped_off', 0)
            print(f"  [OK] Off-market: {new_om} new, {deduped} duplicates removed")
        except Exception as e:
            msg = f"Off-market injection failed: {e}"
            print(f"  [WARN] {msg}")
            traceback.print_exc()
            errors.append(msg)

    # ── Step 4: Wash properties against Domain/REA/OTH caches ───────────
    if args.dry_run:
        step_banner(4, "Dry run — skipping wash")
        print("  Would run wash_properties.py against local Domain/REA/OTH caches")
    else:
        step_banner(4, "Wash Properties (fill blanks from local caches)")
        try:
            import wash_properties
            saved_argv = sys.argv[:]
            sys.argv = ['wash_properties.py']
            try:
                wash_properties.main()
                print("  [OK] Wash complete.")
            finally:
                sys.argv = saved_argv
        except Exception as e:
            msg = f"Wash failed: {e}"
            print(f"  [WARN] {msg}")
            traceback.print_exc()
            errors.append(msg)

    # ── Step 5: Deploy ───────────────────────────────────────────────────
    if args.dry_run:
        step_banner(5, "Dry run — skipping deploy")
        print("  Would copy to:", DEPLOY_PATH)
    else:
        step_banner(5, "Deploy to mazar-martin-deploy")
        try:
            if APP_PATH.exists():
                DEPLOY_PATH.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(APP_PATH, DEPLOY_PATH)
                app_size = APP_PATH.stat().st_size
                print(f"  [OK] Copied {app_size:,} bytes -> {DEPLOY_PATH}")

                deploy_script = DEPLOY_PATH.parent / 'deploy.sh'
                if deploy_script.exists():
                    import subprocess
                    result = subprocess.run(
                        ['bash', str(deploy_script)],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.stdout:
                        for line in result.stdout.strip().split('\n'):
                            print(f"  {line}")
                    if result.returncode != 0:
                        print(f"  [WARN] deploy.sh exited {result.returncode}")
                        if result.stderr:
                            print(f"  {result.stderr.strip()}")
            else:
                msg = f"App file not found: {APP_PATH}"
                print(f"  [ERROR] {msg}")
                errors.append(msg)
        except Exception as e:
            msg = f"Deploy failed: {e}"
            print(f"  [ERROR] {msg}")
            errors.append(msg)

    # ── Step 6: Summary ──────────────────────────────────────────────────
    step_banner(6, "Summary")

    try:
        import json
        if HISTORY_FILE.exists():
            history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            print(f"  History: {len(history)} day(s)")
            if history:
                from datetime import datetime as _dt
                def _dk(e):
                    try: return _dt.strptime(e.get("date","01/01/1900"), "%d/%m/%Y")
                    except: return _dt(1900,1,1)
                latest = max(history, key=_dk)
                date = latest.get('date', '?')
                pc = len(latest.get('price_changes', []))
                nl = len(latest.get('newly_listed', []))
                sd = len(latest.get('sold', []))
                ac = len(latest.get('auction_changes', []))
                ul = len(latest.get('unlisted', []))
                o9 = len(latest.get('over_90_days', []))
                total = pc + nl + sd + ac + ul + o9
                print(f"\n  Latest day ({date}):")
                print(f"    Price Changes   : {pc}")
                print(f"    Newly Listed    : {nl}")
                print(f"    Sold            : {sd}")
                print(f"    Auction Changes : {ac}")
                print(f"    Unlisted        : {ul}")
                print(f"    Over 90 Days    : {o9}")
                print(f"    Total           : {total}")
    except Exception:
        pass

    if errors:
        print(f"\n  WARNINGS/ERRORS ({len(errors)}):")
        for err in errors:
            print(f"    - {err}")
        print()
        return 1

    print(f"\n  All steps completed successfully.")
    print(f"  App: {APP_PATH}")
    print(f"  Deploy: {DEPLOY_PATH}")
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
