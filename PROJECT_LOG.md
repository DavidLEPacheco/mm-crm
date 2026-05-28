# Mazar Martin CRM — Project Log

**Purpose:** Persistent memory of the architecture migration project. Captures
technical context, decisions, progress, and next steps so this work survives
across Claude Code sessions or chat compactions. Commercial/engagement terms
(pricing, billing, proposals) are deliberately kept OUT of this file — they live
in the local-only `ENGAGEMENT_NOTES.md` (gitignored).

---

## 1. The client and the system

- **Client:** Mazar Martin (Lower North Shore Sydney real estate agency).
- **Primary contact on the client side:** Gerard ("gf" in paths), business owner / agent. Not a developer; uses Terminal manually but doesn't code.
- **Consultant:** David Pacheco (you). (Engagement/commercial terms kept in local-only `ENGAGEMENT_NOTES.md`.)
- **The product:** A property CRM hosted at `mazarmartin.github.io/mm-crm/` via GitHub Pages, repo at `github.com/MazarMartin/mm-crm`.
- **What the app actually IS:** A single 5 MB `index.html` file with all data embedded as JavaScript objects inside `<script>` tags. No backend, no database. Every screen reads from those embedded JS objects.
- **Auxiliary HTML on his Mac:** The "master" file is `mazar_martin_app.html` (5 MB). His Python pipeline edits THAT, then a `cp` step copies it to `mazar-martin-deploy/index.html` (his deploy clone) before `git push`.

## 2. Original problems Gerard reported

1. **Staff data not saving across devices.** When his staff opens the app on their browser and adds a client/note, it disappears. Only Gerard's edits "stick" (and even his only because he manually re-bakes them).
2. **Gmail scrape not running automatically.** He has to run scripts in Terminal manually each morning. The macOS LaunchAgent that's supposed to run it daily isn't firing.
3. **(Diagnosed by us, not originally reported)** A force-push collision wiped out our Stage 1 cleanup work two weeks ago.

## 3. Architectural understanding (what we figured out)

### Folder layout on Gerard's Mac
```
~/Downloads/
├── mazar_martin_app.html          ← MASTER (not in any git repo)
├── proping_history.json           ← runtime data
├── domain_forsale_lns.json        ← runtime data
├── (~25 other JSONs)              ← runtime data
├── lns_agents_scripts/            ← all Python scripts
└── mazar-martin-deploy/           ← git clone (only the frontend files)
```

### Data flow
1. Scrapers (Python) hit Gmail (IMAP), Domain.com.au, OnTheHouse, agency websites, NSW Valuer General → write JSON files
2. Injectors find marker comments like `/* __PROPING_HIST_START__ */` in the master HTML and replace blocks between them
3. Wash step fills missing beds/baths/landSize from cached JSONs
4. `cp master.html → deploy/index.html`
5. `git add index.html && git commit && git push`
6. GitHub Pages serves the new HTML to users

### The localStorage problem (root cause of staff issue)
The SPA stores ALL user-entered data (clients, whiteboard, notes) in `localStorage` of whoever's browser is open. Each device has its own private copy. The pipeline can't see browser state, so:
- Gerard's edits live in HIS browser only
- Staff edits live in THEIR browsers only
- Refreshing or clearing cache wipes everything
- The "workaround" `inject_whiteboard.py` only knows about JSON files Gerard manually exports from his browser
- Staff edits NEVER get back to Gerard or anyone else

### The force-push problem (root cause of cleanup loss)
- Apr 29 18:22 — David pushed `a6cf9b8` (Stage 1 cleanup) to `MazarMartin/mm-crm` main
- Apr 29 23:41 — Gerard's manual `.command` button created a "Daily update" commit on his deploy clone
- His deploy clone was synced to `e4fabc2` (Apr 19) — pre-cleanup
- Plain push got rejected (non-fast-forward); he then ran `git push --force` manually to "fix" it
- Wiped David's cleanup commit from origin
- Identical pattern would happen again next time, until the pipeline architecture changes

### The TCC problem (root cause of automatic scraping failure)
- macOS LaunchAgent is configured correctly (6 AM + 9 AM Mon-Fri)
- But `launchd_stderr.log` shows hundreds of `Operation not permitted` errors
- macOS TCC blocks launchd-spawned bash from running scripts in `~/Downloads/`
- Gerard's manual Terminal runs work because Terminal has the necessary permissions

## 4. Key decisions made

| Decision | Why |
|---|---|
| Migrate to Railway + Supabase architecture | Both problems (staff sync, scheduled scraping) have the same root cause and same fix |
| Phased migration (3 stages, not big-bang) | Manageable risk, sign-off points, validate each step |
| Fork the repo rather than push to live | Gerard's pipeline would clobber any push to live |
| Keep `pythonfiles/` as untouched reference, build clean `pipeline/` | Don't lose fidelity with original; build canonical going forward |
| Defer index.html dead-code cleanup until Stage 3 | The HTML changed too much; mechanical replay would break things; better to redo against current code |
| Keep frontend at repo root (don't subfolder it) | GitHub Pages config + deploy.yml expect it there; no value in moving |
| Don't bring `loose_files/*.py` over | Older versions / one-off patches; not canonical |

## 5. Three-stage migration plan

**Stage 1 — Pipeline to Railway**
Lift Python scripts off Gerard's Mac. Run on Railway cron. Persistent volume for state. Solves the auto-scraping problem and removes force-push fights between machines.

**Stage 2 — Supabase database**
Stand up Postgres. Pipeline writes scraped data to tables instead of JSON files. Pipeline still updates HTML for now.

**Stage 3 — Frontend connected to Supabase**
Replace localStorage with Supabase client calls. Add Supabase Auth (Google sign-in). Solves staff-sync problem. Real-time channels for live updates. Add user accounts.

## 6. Commercial / engagement notes

Pricing, billing, quoting strategy, and the client proposal are intentionally
kept OUT of this committed log. See the local-only `ENGAGEMENT_NOTES.md`
(gitignored) on David's machine.

## 7. Scope-gating (process)

Each stage gets a written estimate + sign-off before starting, with a checkpoint
between stages. (Commercial details in `ENGAGEMENT_NOTES.md`.)

## 8. Key paths, URLs, and credentials

| Resource | Location |
|---|---|
| Live frontend (Gerard) | `mazarmartin.github.io/mm-crm/` |
| Live repo (Gerard) | `github.com/MazarMartin/mm-crm` |
| Sandbox fork (David) | `github.com/DavidLEPacheco/mm-crm` |
| Sandbox Pages (David) | `davidlepacheco.github.io/mm-crm/` |
| Local clone | `c:\Users\dlepa\Documents\00_AgenticWorkflowProjects\00_Clients\Mazar Martin\LIVE_ClientRepo\mm-crm\` |
| Gmail account | `mazarmartinapp@gmail.com` |
| Auth method | IMAP App Password (16 chars), NOT OAuth |
| Master HTML on his Mac | `~/Downloads/mazar_martin_app.html` |
| Scripts on his Mac | `~/Downloads/lns_agents_scripts/` |
| Deploy clone on his Mac | `~/Downloads/mazar-martin-deploy/` |
| Credentials file on his Mac | `~/Downloads/lns_agents_scripts/.mm_credentials` (NOT in our backup — dotfiles excluded) |

## 9. Local repo structure

```
mm-crm/
├── .git/
├── .github/workflows/deploy.yml         (auto-deploys to Pages on push)
├── .gitignore
├── PROJECT_LOG.md                       (this file — gitignored)
│
├── (frontend at root — what GitHub Pages serves)
├── index.html                           (5 MB SPA)
├── manifest.json
├── sw.js
├── client_report_prototype.html
├── icon-*.png
│
├── pipeline/                            (TRACKED in git — sandbox working area)
│   ├── scripts/                         57 .py files
│   ├── .venv/                           (gitignored — Python venv)
│   ├── *.json                           (gitignored — runtime data)
│   ├── mazar_martin_app.html            (gitignored — master HTML)
│   ├── requirements.txt                 (playwright, openpyxl)
│   ├── .env.example
│   ├── .mm_credentials                  (gitignored — actual Gmail App Pwd, when we get it)
│   └── README.md
│
├── pythonfiles/                         (gitignored — Gerard's untouched backup)
│   ├── lns_agents_scripts/              ~96 files (full)
│   ├── loose_files/                     ~56 files (older versions + JSONs)
│   ├── mazar-martin-deploy/             duplicate of frontend
│   └── mazar_martin_app.html
│
└── data/                                (gitignored — leftover from old session)
```

## 10. Git branch state

| Branch / ref | Position | Meaning |
|---|---|---|
| `main` (local) | `cbf7541` | Latest commit (pipeline/ added) |
| `origin/main` (your fork) | `cbf7541` | Same as local — synced |
| `upstream/main` (Gerard's repo) | `4c27081` (or newer) | Gerard's live |
| `cleanup-reference` (local only) | `a6cf9b8` | Original Stage 1 cleanup commit, preserved |
| `stage-1-cleanup` (local only) | `a6cf9b8` | Backup of cleanup commit |
| `v1.0.0` tag (local + fork) | `0aa3555` | Sandbox baseline = Gerard's state + PWA fixes |

## 11. Commits on the fork's main

```
cbf7541  Add pipeline/ folder with Python scripts from Gerard's backup
0aa3555  Apply infrastructure fixes from Stage 1 cleanup  ← v1.0.0
4c27081  Daily update 13 May 2026 08:30  (Gerard's last push at fork time)
b9e8224  Daily update 12 May 2026 09:23  (Gerard's earlier daily update)
... (Gerard's other daily updates back to e4fabc2)
```

## 12. Where we are now

**Last known state (2026-05-28):** Pipeline is runnable end-to-end on Windows.
App Password received and working; scrape verified; all hardcoded paths fixed;
a cross-platform orchestrator built. Have NOT yet executed a full live run.

**What's working:**
- Fork is set up and deployable to Pages
- Pipeline scripts are version-controlled; `main` now tracks `origin/main` (fork)
- Python venv built; Playwright Chromium installed
- `scrape_gmail.py` verified against real Gmail — pulled 323 properties (2026-05-28)
- All 34 scripts with hardcoded `/Users/gf/Downloads/` paths fixed → `__file__`-relative
- `run_pipeline.py` orchestrator mirrors `_run_scrape_wash_deploy.command`

**What's blocked / open:**
- Full live run (scrape→inject→wash→fill→deploy) not yet executed
- Supabase-vs-Railway sequencing needs a decision (see §16)
- Gmail auth is fragile — depends on 2FA staying ON (see §16)

## 13. What to do when password arrives — DONE (2026-05-28)

1. ✅ Created `pipeline/scripts/.mm_credentials` (gitignored) with `GMAIL_APP_PASSWORD=...`
2. ✅ Ran `scrape_gmail.py` — needs `PYTHONUTF8=1` on Windows (emoji output crashes cp1252)
3. ✅ `pipeline/proping_history.json` populated (323 properties, 411 KB)
4. ✅ Pass B (path fixes) done — see §14

## 14. Pass B plan (hardcoded path fixes) — DONE (2026-05-28)

Applied across 34 files (72 occurrences). Bases resolve from each script's
location (`SCRIPT_DIR` where present, else `Path(__file__).resolve()`):

| Pattern | Replacement |
|---|---|
| `/Users/gf/Downloads/mazar_martin_app.html` | `…parent.parent / 'mazar_martin_app.html'` (= `pipeline/`) |
| `/Users/gf/Downloads/X.json` | `…parent.parent / 'X.json'` (= `pipeline/`) |
| `/Users/gf/Downloads/lns_agents_scripts/X` | `…parent / 'X'` (= `pipeline/scripts/`) |
| `/Users/gf/Downloads/mazar-martin-deploy/index.html` | `…parent.parent.parent / 'index.html'` (= repo root) |
| `/Users/gf/Downloads/mazar-martin-deploy` | `…parent.parent.parent` (= repo root) |

Verified: `grep` clean, `compileall` passes, runtime path arithmetic confirmed.
Committed `28cc8d7`. `scrape_onthehouse.py` + `inject_email_data.py` were already
relative (no fix needed).

## 15. Long-term goals reminder

- Get the sandbox working end-to-end with real Gmail data
- Resolve the Supabase-vs-Railway sequencing (see §16)
- Phased delivery, validated/signed off per stage
- (Commercial milestones — proposal, invoicing — tracked in `ENGAGEMENT_NOTES.md`)

## 16. Context from client's own Claude chat log (absorbed 2026-05-28)

Gerard pasted his Mac-side development chat. It's history/context only — no
action taken — but it clarifies several things and flags open questions.

**Canonical runner confirmed.** `_run_scrape_wash_deploy.command` is the real
runner (scrape → inject → wash → fill → deploy, WITH enrichment). `daily_update.py`
/ `daily_refresh.py` are divergent "basic" runners that SKIP the `fill_*`
enrichment steps — which is exactly why bath/car/type/land were blank for the
client. Our `run_pipeline.py` mirrors the correct `.command`, so we're aligned.

**Direction tension to resolve.** The client's chat lands on **Supabase first**
(staff sync — shared login for Jeremy/Mon/Chelsea, phone access, edit briefs +
property comments, all cloud-synced) and **rules out Railway for now** (only
needed if the scrape later moves off the Mac). Our staging here had Railway as
Stage 1. Needs an explicit call on sequencing. Hard requirement from client:
the app must look/behave EXACTLY the same — zero visual change — through any
cloud migration.

**Gmail auth is fragile.** Client's chat shows it was DOWN (he turned 2FA off,
which invalidated the App Password → `AUTHENTICATIONFAILED`). As of 2026-05-28
the App Password works for us, so 2FA is back on — but if scraping suddenly
fails with that error, the cause is 2FA being disabled again. Fix path:
re-enable 2FA → regenerate App Password → update `.mm_credentials`. (OAuth
migration ~1 hr, not done.)

**Frontend / inject landmines (for Stage 3 / any HTML edits):**
- Inject before the **last** `</body>` — the first `</body>` appears inside a JS
  string in the property-intelligence-report code.
- `propingHistory` is sorted **oldest-first** — use max-by-date, not `[0]`.
- Date-dedup must be scoped to the `propingHistory` array, not the whole HTML
  (a settlement `"date"` once falsely matched and skipped an inject).
- Clients live in a **separate inline data object**, not `D.xlsxClients`
  (which is empty at runtime).
- Features were added as additive runtime `<script>` blocks that monkey-patch
  render functions and persist to `localStorage` (per-device → no sync). This
  additive-patch style is the root cause of most past bugs.

**Useful reference (from the chat):**
- localStorage keys: `mmCommissionUnlocked`, `mmClientEdits`, `mmDismissedProps`,
  `mmSavedMatches`, `mmDomainEnrich`, `mmCallStatus`, `mmDeleted`.
- Client schema: `{section, ba, referrer, name, budget, spec, locations, target,
  commission, exp, status, notes, date}`; sections "Active Buyer" / "Pipeline".
- Proping emails carry: address, suburb, beds, days_listed, price, agent, agency,
  source, date — NO baths/parking/type/land (those come from enrichment steps).
- macOS automation (launchd/cron) never worked — TCC blocks `~/Downloads` access
  from launchd context. Client runs the `.command` manually. (Moot for us — we
  run on Windows / heading to cloud.)

---

## Session timeline

### 2026-05-15 — Initial deep-dive and sandbox setup
- Started session with `git pull` failing — discovered force-push and divergence
- Diagnosed the full system: master HTML, deploy clone, JSONs, Python pipeline, localStorage architecture
- Reconstructed the timeline of how cleanup commit got wiped
- Identified all 8 data sources, 3-stage data flow, marker-comment injection scheme
- Decided on Railway + Supabase migration architecture
- Drafted the architecture/migration proposal (content kept in local-only `ENGAGEMENT_NOTES.md`)
- Decided on quoting/pricing strategy (details in local-only `ENGAGEMENT_NOTES.md`)
- Created `cleanup-reference` branch preserving `a6cf9b8`
- Forked `MazarMartin/mm-crm` to `DavidLEPacheco/mm-crm`
- Repointed local origin to fork; reset main to fork's main
- Applied PWA fixes (manifest.json + sw.js v4) as commit `0aa3555`
- Tagged `v1.0.0` as sandbox baseline
- Enabled GitHub Pages on the fork
- Built `pipeline/` folder structure: copied 57 Python scripts, 26 data JSONs, master HTML
- Updated `.gitignore` for pipeline runtime artifacts
- Created `requirements.txt`, `.env.example`, `README.md`
- Committed `cbf7541` and pushed
- Created Python venv, installed dependencies (playwright + openpyxl)
- Verified `scrape_gmail.py` loads correctly
- Discovered `.mm_credentials` was excluded from Gerard's backup zip (macOS Finder skips dotfiles)
- Drafted message to Gerard asking him to read the file via Terminal
- Paused, waiting on his response with the App Password

### 2026-05-28 — Pipeline made runnable on Windows + orchestrator
- Confirmed remotes: `origin` = `DavidLEPacheco/mm-crm` (fork), `upstream` =
  `MazarMartin/mm-crm` (client). Found `main` was tracking `upstream/main` (would
  push to client's live repo); repointed `main` → `origin/main`.
- Gmail App Password received. Was briefly pasted into `pipeline/.env.example`
  (tracked!) — moved it to gitignored `pipeline/scripts/.mm_credentials`, reverted
  the template. Confirmed secret never reached git history or either remote.
- Ran `scrape_gmail.py` against real Gmail: 57 emails → 323 properties into
  `pipeline/proping_history.json`. Discovered the Windows UTF-8 gotcha
  (`PYTHONUTF8=1` needed; scripts print emoji, cp1252 console crashes).
- Committed `.gitignore` change to ignore `PROJECT_LOG.md` (`17d9d03`).
- Fixed hardcoded `/Users/gf/Downloads/` paths across 34 scripts (72 spots) →
  `__file__`-relative. Verified (grep clean, `compileall` ok, runtime checked).
  Committed `28cc8d7`, pushed to fork.
- Learned from client that `_run_scrape_wash_deploy.command` is the real runner.
  Built `run_pipeline.py` (cross-platform port): runs all 13 steps as subprocesses
  in that order, forces UTF-8, then cp master → index.html + `git push origin main`.
  Flags: `--no-deploy`, `--skip-scrapers`, `--dry-run`. Committed `4ccc010`, pushed.
- Installed Playwright Chromium (for agency + Domain scrapers).
- MISTAKE + recovery: smoke-tested orchestrator with `--skip-scrapers`, not
  realizing that still runs inject/wash/fill — partially mutated the local master
  HTML. No deploy, no push happened. Restored master from canonical backup
  `pythonfiles/mazar_martin_app.html` (md5 verified). Added `--dry-run` after.
- Absorbed client's Mac-side chat log (see §16): canonical runner, Supabase-first
  direction tension, Gmail/2FA fragility, frontend inject landmines, data schemas.
- NOT yet done: first full live pipeline run (recommend `--no-deploy` first to
  eyeball the master, then push).

### (next session — append below)
