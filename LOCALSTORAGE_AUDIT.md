# Mazar Martin CRM — localStorage Audit (Stage 2 prep)

**Purpose:** Map every localStorage touchpoint in `index.html` so the Supabase migration intercepts cleanly with zero visual change.

## TL;DR

- **34** direct `localStorage.*` calls. **134** wrapper-helper calls. ~80% of usage funnels through 1–2 wrappers, but they all bottom out at `window.localStorage.getItem/setItem`.
- **~33 distinct `mm*` keys** in use — much richer than the 7 the chat log named.
- **Two wrapper layers exist:** a top-level `lsGet`/`lsSet` (defined line 30669) and per-block helpers (e.g. the Commission Tracker's own `getJSON`/`setJSON` at line 43305).
- **Cleanest intercept = monkey-patch `window.localStorage.getItem`/`setItem`.** Catches all wrapper and direct usage with zero callsite edits and zero visual change.
- **Initial Supabase schema can be a single `kv_store` table** that preserves behaviour 1:1. Proper relational tables can come later, transparently.

## Wrapper layer

- Line 30669 — `function lsGet(key, def)` — JSON.parse with fallback.
- Line 30670 — `function lsSet(key, val)` — JSON.stringify wrap.
- Line 43305–43309 — Commission Tracker's own `getJSON`/`setJSON` (same shape, scoped to that block).
- Plus a few inline `JSON.parse(localStorage.getItem(...))` patterns.

## Key inventory

### Client management
| Key | Shape | Notes |
|---|---|---|
| `mmClientEdits` | `{[name]: {section, settledDate, signedDate, addedDate, pipelineAddedDate, MAP, notes, [field]: value, ...}}` | Field-level mutations per client. **High value — must migrate.** |
| `mmClients` | array (snapshot of `D.xlsxClients`?) | Probably regenerable from base data. |
| `mmDeletedClients` | `[name, ...]` | Soft-delete list. Must migrate. |
| `mmClientActivity` | `{[name]: [...]}` | Activity/history log. High value. |
| `mmClientComments` | `{[name]: [...]}` | Comments on clients. Must migrate. |
| `mmBuyerTemp` / `mmBuyerTemps` / `mmTemps` | per-client temperature (hot/warm/cold) | Three variants — canonical TBD when we see real data. |

### Property management
| Key | Shape | Notes |
|---|---|---|
| `mmPropComments` | `{[address]: [...]}` | Comments on properties. |
| `mmDismissedProps` | `{[clientName]: [address, ...]}` | Dismissed-for-this-client. |
| `mmBlacklist` | `[address, ...]` | Permanently-deleted for-sale items. |
| `mmDeletedFS` | `[address, ...]` | Soft-deleted for-sale items. |
| `mmForSaleEdits` | edits to for-sale listings. |
| `mmSoldEdits` | edits to sold listings. |
| `mmNewSale` | manually added for-sale entries. |
| `mmNewOff` | manually added off-market entries. |
| `mmPresented` | properties presented to clients (swipe-deck history). |

### Matching engine
- `mmSavedMatches` — `{[clientName]: [{address, suburb, price, type, note, savedAt}]}`.
- `mmAutoMatches` — auto-generated matches.
- `mmAutoMatchLastRun` / `mmAutoMatchTs` — timestamps.

### Call tracking
- `mmCallStatus` — `{[agentKey]: {called: bool, ...}}`.
- `mmCallComments` — `{[agentKey]: [...]}` comments.

### Stats / UI flags
- `mmCommissionUnlocked` — `"1"` / `"0"` string flag (the 5-tap unlock).
- `mmStatOverrides` — manual top-card stat tweaks.
- `mmWeek` — current-week marker (for weekly resets).
- `mm_news_dismissed` — dismissed news items (note: snake-case, not camel).

### Caches — probably skip migration (derived/regenerable)
`mmGeoCache`, `mmZoningCache2`, `mmPropImgCache`, `mmDomainEnrich`, `mmMatchSummary`, `mmSwipeDeckMount`, `mmSwipeQueue_*`.

### Special — needs separate handling
- `mmClaudeKey` — a Claude API key stored in localStorage. Do **not** put this in Supabase on a public repo/site. Either keep it browser-local (re-prompt per device) or route through a backend env var via Supabase Edge Function.

### Non-mm keys also used
- `page_<n>` — pagination state. Skip.

## Baked vs runtime client data

Two baked sources in the HTML:
- `D.xlsxClients` (~line 30252) — full schema (`section, ba, referrer, name, budget, spec, locations, target, commission, exp, status, notes, date`), ~40+ records.
- `MM_CLIENTS` (line 43286, inside `MM_COMMISSION_TRACKER`) — simplified `{name, section}` subset (~60 records). Used only by the Commission Tracker.

Runtime overrides come from `mmClientEdits` in localStorage; renderers (`buildActiveBuyersSection`, `buildPipelineSection`) merge baked + edits.

## Feature blocks (marked `<!-- MM_*_START/END -->`)

| Block | Lines | Keys |
|---|---|---|
| MM_AC_DROPDOWN | 31257–31284 | (UI only — Auction Changes dropdown) |
| MM_LEGEND | 31690 | (single-line marker — color legend) |
| MM_OFFMARKETS_RUNTIME | 43236–43279 | `mmNewOff`, `mmForSaleEdits` |
| MM_COMMISSION_TRACKER | 43280–43735 | `mmCommissionUnlocked`, `mmClientEdits`, `mmDeletedClients`, `mmStatOverrides`, `MM_CLIENTS` (baked) |
| MM_KEEP_EDIT_OPEN | 43736–43810 | (UI patch — re-opens inline edit panel after re-render) |

Several un-marked feature blocks are embedded in the main `<script>` (lines 30000–43000). They cover: agent call tracking, matching engine, comments, swipe deck, zoning lookup, etc.

## Integration strategy — monkey-patch `localStorage`

The big win: a **single injected `<script>` block at the top of `<body>`** that overrides `window.localStorage.getItem`/`setItem`. Pattern:

1. **On load**, render a tiny login screen (Supabase email/password). After auth, hide it.
2. **Hydrate** an in-memory cache from a `kv_store` table (one fetch on init).
3. **Override** `localStorage.getItem(key)` → read from cache (synchronous, matches existing contract).
4. **Override** `localStorage.setItem(key, val)` → write cache synchronously + async upsert to Supabase.
5. **Optionally subscribe** to Supabase Realtime → push other-device updates into the cache live.

Zero callsite edits. Zero visual change after login. Works for direct `localStorage.*`, wrapped `lsGet`/`lsSet`, and each feature block's own JSON wrappers — they all bottom out at the same primitives we're overriding.

### Caveats
- `localStorage` is synchronous; Supabase is async. The cache-on-init pattern bridges that — every read is fast (cache hit). Writes return immediately.
- App must **wait for cache hydration before rendering**. Easy with `await load(); renderApp();` gate.
- `mmClaudeKey` excluded from the override (kept browser-local).

## Supabase schema — minimal for behaviour-preserving migration

```sql
create table kv_store (
  user_id    uuid not null references auth.users(id),
  key        text not null,
  value      jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, key)
);

alter table kv_store enable row level security;
create policy "owner reads"  on kv_store for select using (auth.uid() = user_id);
create policy "owner writes" on kv_store for all    using (auth.uid() = user_id);
```

With ONE shared login, `auth.uid()` is the same for everyone → effectively a single `(key, value)` table shared across all devices. Realtime pushes changes between devices live.

**Later evolution:** as we add real features, migrate specific keys to proper relational tables (e.g. `clients`, `comments`, `calls`) and read those directly — without breaking existing JS, because the migration is transparent to it.

## Implementation order (when Supabase is unblocked)

1. Create `kv_store` table + RLS + the shared auth user.
2. Build the injected `<script>` block: auth screen + cache hydration + `localStorage` overrides + Realtime subscription.
3. Test on the fork with test rows.
4. Capture Gerard's localStorage (screen-share or DevTools) + a fresh whiteboard export.
5. Run a one-off Python script (service-role key, local) to import everything into `kv_store`.
6. Deploy the Supabase-block-enabled `index.html` to the fork; eyeball every section.
7. Transplant to client's repo + decommission Gerard's Mac scripts.

## Open questions / TBD

- Exact value shapes for the less-used keys (will resolve when we see Gerard's actual localStorage snapshot).
- Whether to migrate `mmClientActivity` history or start fresh.
- `mmClaudeKey` — keep browser-local, or stand up an Edge Function to proxy Claude calls server-side?
- Realtime vs polling for cross-device sync — Realtime is preferred but adds a small dependency.
