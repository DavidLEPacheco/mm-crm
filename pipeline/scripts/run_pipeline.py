#!/usr/bin/env python3
"""Run the full Mazar Martin scrape -> inject -> wash -> fill -> deploy pipeline.

Cross-platform replacement for Gerard's _run_scrape_wash_deploy.command. Each
step runs as its own subprocess (matching the original), reading the master
HTML that the previous step wrote. After the steps, the updated master is
copied to the repo-root index.html and pushed to the fork's main branch, which
GitHub Pages deploys.

Usage:
    python run_pipeline.py                 # full run incl. cp + git push
    python run_pipeline.py --no-deploy     # run steps only; skip cp + push
    python run_pipeline.py --skip-scrapers # skip the 4 scraper steps (offline)
    python run_pipeline.py --dry-run       # print the plan; run nothing
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Force UTF-8 so the scripts' emoji status output doesn't crash on a Windows
# console (cp1252). Set before spawning children so they inherit it.
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPTS = Path(__file__).resolve().parent       # pipeline/scripts
PIPELINE = SCRIPTS.parent                        # pipeline/  (master HTML + JSONs)
REPO_ROOT = PIPELINE.parent                      # repo root  (deploy target)
MASTER = PIPELINE / "mazar_martin_app.html"
INDEX = REPO_ROOT / "index.html"

# (label, filename) in the exact order Gerard's .command runs them.
STEPS = [
    ("0  scrape_gmail",             "scrape_gmail.py"),
    ("0b scrape_agency_websites",   "scrape_agency_websites.py"),
    ("1  scrape_onthehouse",        "scrape_onthehouse.py"),
    ("2  scrape_domain_realestate", "scrape_domain_realestate.py"),
    ("3  inject_email_data",        "inject_email_data.py"),
    ("4  wash_properties",          "wash_properties.py"),
    ("4b fill_forsale",             "fill_forsale.py"),
    ("4c fill_sold_prices",         "fill_sold_prices.py"),
    ("4d fill_sold_fields",         "fill_sold_fields.py"),
    ("4h fill_last_sold",           "fill_last_sold.py"),
    ("4e fill_proping_fields",      "fill_proping_fields.py"),
    ("4f inject_agency_offmarket",  "inject_agency_offmarket.py"),
    ("4g dedup_offmarket",          "dedup_offmarket.py"),
]

SCRAPERS = {
    "scrape_gmail.py",
    "scrape_agency_websites.py",
    "scrape_onthehouse.py",
    "scrape_domain_realestate.py",
}


def run_step(label, script):
    path = SCRIPTS / script
    if not path.exists():
        print(f"  WARNING: skipping {label} - {script} not found")
        return
    print(f"\n--- Step {label} ---", flush=True)
    result = subprocess.run([sys.executable, str(path)], cwd=str(SCRIPTS))
    if result.returncode != 0:
        print(f"\n  FAILED: {script} exited with code {result.returncode}")
        sys.exit(result.returncode)


def deploy():
    print("\n--- Step 5: Copy + Deploy ---", flush=True)
    shutil.copy(MASTER, INDEX)
    print(f"  Copied {MASTER.name} -> {INDEX}")

    def git(*args):
        return subprocess.run(["git", "-C", str(REPO_ROOT), *args])

    git("add", "index.html")
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("  No change to index.html - nothing to deploy.")
        return
    stamp = datetime.now().strftime("%d %b %Y %H:%M")
    if git("commit", "-m", f"Daily update {stamp}").returncode != 0:
        print("  FAILED: git commit")
        sys.exit(1)
    if git("push", "origin", "main").returncode != 0:
        print("  FAILED: git push")
        sys.exit(1)
    print("  Deployed: pushed index.html to origin/main (fork) -> GitHub Pages")


def main():
    skip_scrapers = "--skip-scrapers" in sys.argv
    do_deploy = "--no-deploy" not in sys.argv
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - the full run would execute, in order:")
        for label, script in STEPS:
            skipped = " (skipped: --skip-scrapers)" if skip_scrapers and script in SCRAPERS else ""
            print(f"  Step {label}{skipped}")
        print(f"  Step 5  deploy: cp master -> index.html + git push origin main"
              if do_deploy else "  Step 5  deploy: DISABLED (--no-deploy)")
        return

    if not MASTER.exists():
        print(f"ERROR: master HTML not found at {MASTER}")
        sys.exit(1)

    print(f"Pipeline start {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  master: {MASTER}")
    print(f"  deploy: {INDEX} (push to origin/main)" if do_deploy
          else "  deploy: DISABLED (--no-deploy)")

    for label, script in STEPS:
        if skip_scrapers and script in SCRAPERS:
            print(f"\n--- Step {label}: SKIPPED (--skip-scrapers) ---")
            continue
        run_step(label, script)

    if do_deploy:
        deploy()
    else:
        print("\n  (--no-deploy) Master HTML updated in place; cp + push skipped.")

    print(f"\nDONE at {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
