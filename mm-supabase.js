// mm-supabase.js — Stage 2 integration block
//
// STEPS DONE:
//   1. login overlay + Supabase auth
//   2. mmCommissionUnlocked  → user_kv  (boolean flag, per-user)
//   3. mmCallStatus           → agent_calls  (per-row upsert pattern)
//
// Refactored to an adapter pattern: managed keys are read from a cache that's
// bulk-hydrated on login. Writes go through per-key adapters that translate
// the localStorage shape into proper table operations. All other keys still
// pass through to the browser's native storage untouched.
//
// Loaded as a module via `<script type="module" src="./mm-supabase.js"></script>`
// at the end of index.html.

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = 'https://phkmwcimpyvmxbpdmuvw.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_aJddeid2D0-0kDWclrNRgQ_nt_kQih5';

// Keys we manage. Reads come from the cache; writes go through WRITE_ADAPTERS.
const MANAGED_KEYS = new Set([
  'mmCommissionUnlocked',
  'mmCallStatus',
]);

// Module state
let supabase = null;
let currentUserId = null;
let currentOrgId = null;
let cache = {}; // {mmKey: localStorage-shaped string}

if (window._mmSupabaseInit) {
  console.warn('[MM-Supabase] already initialised, skipping');
} else {
  window._mmSupabaseInit = true;
  boot();
}

function boot() {
  supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
  window._mmSupabase = supabase;

  const overlay = buildOverlay();
  const statusEl = overlay.querySelector('#mm-sb-status');
  const form     = overlay.querySelector('#mm-sb-login');
  const errEl    = overlay.querySelector('#mm-sb-error');

  const setStatus = (msg, color) => {
    statusEl.textContent = msg;
    statusEl.style.color = color || '#555';
  };
  const showError = (msg) => {
    errEl.textContent = msg;
    errEl.style.display = 'block';
  };

  supabase.auth.getSession().then(async ({ data: { session } }) => {
    if (session) {
      setStatus(`Signed in as ${session.user.email}`);
      await afterLogin(session);
    } else {
      setStatus('Sign in to load your data:');
      form.style.display = 'block';
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errEl.style.display = 'none';
    setStatus('Signing in…');
    const email = overlay.querySelector('#mm-sb-email').value.trim();
    const password = overlay.querySelector('#mm-sb-pass').value;
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      showError(error.message);
      setStatus('Sign in to load your data:');
      return;
    }
    setStatus(`Signed in as ${data.user.email}`);
    await afterLogin(data.session);
  });

  async function afterLogin(session) {
    currentUserId = session.user.id;
    setStatus('Loading your data…');
    try {
      currentOrgId = await fetchOrgId();
      cache = await hydrateAll();
      installLocalStorageOverrides();
      const n = Object.keys(cache).length;
      setStatus(`✅ Loaded ${n} setting${n === 1 ? '' : 's'} — opening app…`, '#2E7D32');
      console.log('[MM-Supabase] hydrated cache:', cache);
      setTimeout(() => overlay.remove(), 700);
    } catch (e) {
      console.error('[MM-Supabase] init failed', e);
      showError('Init failed: ' + (e.message || e));
      setStatus('Connected (with errors) — see console.', '#C62828');
    }
  }
}

// ─── Login-time lookups ───────────────────────────────────────────────────

async function fetchOrgId() {
  const { data, error } = await supabase
    .from('org_members')
    .select('org_id')
    .eq('user_id', currentUserId)
    .eq('role', 'staff')
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  if (!data) throw new Error('no staff membership found for this user');
  console.log('[MM-Supabase] org_id =', data.org_id);
  return data.org_id;
}

// ─── Bulk hydration ───────────────────────────────────────────────────────

async function hydrateAll() {
  const c = {};

  // user_kv (per-user simple values)
  const { data: kvRows, error: kvErr } = await supabase
    .from('user_kv')
    .select('key, value')
    .eq('user_id', currentUserId);
  if (kvErr) throw kvErr;
  for (const row of kvRows || []) {
    c[row.key] = typeof row.value === 'string' ? row.value : JSON.stringify(row.value);
  }

  // agent_calls → reshape into mmCallStatus's localStorage format
  const { data: callRows, error: callErr } = await supabase
    .from('agent_calls')
    .select('agent_key, called, voicemail')
    .eq('org_id', currentOrgId);
  if (callErr) throw callErr;
  if (callRows && callRows.length) {
    const obj = {};
    for (const row of callRows) {
      obj[row.agent_key] = { called: row.called, voicemail: row.voicemail };
    }
    c['mmCallStatus'] = JSON.stringify(obj);
  }

  window._mmCache = c; // debug
  return c;
}

// ─── Write adapters: key → table operation ───────────────────────────────

const WRITE_ADAPTERS = {
  mmCommissionUnlocked: {
    write:  (v) => userKvUpsert('mmCommissionUnlocked', v),
    remove: ()  => userKvDelete('mmCommissionUnlocked'),
  },
  mmCallStatus: {
    write:  writeMmCallStatus,
    remove: removeMmCallStatus,
  },
};

async function userKvUpsert(key, value) {
  const { error } = await supabase.from('user_kv').upsert(
    { user_id: currentUserId, key, value },
    { onConflict: 'user_id,key' }
  );
  if (error) throw error;
}

async function userKvDelete(key) {
  const { error } = await supabase.from('user_kv').delete()
    .eq('user_id', currentUserId)
    .eq('key', key);
  if (error) throw error;
}

async function writeMmCallStatus(valueStr) {
  // valueStr is a JSON string like '{"agentA":{"called":true},"agentB":{...}}'
  let obj;
  try { obj = JSON.parse(valueStr || '{}'); }
  catch { throw new Error('mmCallStatus value is not valid JSON'); }

  const rows = Object.entries(obj).map(([agent_key, s]) => ({
    org_id: currentOrgId,
    agent_key,
    called:    !!(s && s.called),
    voicemail: !!(s && s.voicemail),
  }));

  if (rows.length === 0) return;

  const { error } = await supabase.from('agent_calls')
    .upsert(rows, { onConflict: 'org_id,agent_key' });
  if (error) throw error;
}

async function removeMmCallStatus() {
  // Rare path — but if the app clears mmCallStatus, blow the org's rows away.
  const { error } = await supabase.from('agent_calls').delete()
    .eq('org_id', currentOrgId);
  if (error) throw error;
}

// ─── localStorage overrides ──────────────────────────────────────────────

function installLocalStorageOverrides() {
  const realGet = localStorage.getItem.bind(localStorage);
  const realSet = localStorage.setItem.bind(localStorage);
  const realRem = localStorage.removeItem.bind(localStorage);

  localStorage.getItem = function(key) {
    if (MANAGED_KEYS.has(key)) {
      return Object.prototype.hasOwnProperty.call(cache, key) ? cache[key] : null;
    }
    return realGet(key);
  };

  localStorage.setItem = function(key, value) {
    if (MANAGED_KEYS.has(key)) {
      const str = String(value);
      cache[key] = str;
      const a = WRITE_ADAPTERS[key];
      if (a && a.write) {
        a.write(str).then(
          () => console.log(`[MM-Supabase] saved ${key}`),
          (e) => console.error(`[MM-Supabase] write failed for ${key}:`, e)
        );
      }
      return;
    }
    return realSet(key, value);
  };

  localStorage.removeItem = function(key) {
    if (MANAGED_KEYS.has(key)) {
      delete cache[key];
      const a = WRITE_ADAPTERS[key];
      if (a && a.remove) {
        a.remove().then(
          () => console.log(`[MM-Supabase] removed ${key}`),
          (e) => console.error(`[MM-Supabase] delete failed for ${key}:`, e)
        );
      }
      return;
    }
    return realRem(key);
  };

  console.log('[MM-Supabase] localStorage overrides installed for', [...MANAGED_KEYS]);
}

// ─── Login overlay UI ────────────────────────────────────────────────────

function buildOverlay() {
  const o = document.createElement('div');
  o.id = 'mm-supabase-overlay';
  o.style.cssText = [
    'position:fixed', 'inset:0', 'background:#1C3A2A',
    'z-index:99999', 'display:flex',
    'align-items:center', 'justify-content:center',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
  ].join(';');

  o.innerHTML = `
    <div style="background:white;padding:32px;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,0.35);min-width:320px;max-width:380px;color:#1C3A2A;">
      <div style="font-size:20px;font-weight:600;margin-bottom:4px;">Mazar Martin</div>
      <div style="font-size:13px;color:#777;margin-bottom:20px;">Property Intelligence</div>
      <div id="mm-sb-status" style="padding:10px 12px;background:#f5f5f5;border-radius:6px;font-size:13px;color:#555;margin-bottom:16px;">Connecting…</div>
      <form id="mm-sb-login" style="display:none;">
        <input id="mm-sb-email" type="email" placeholder="Email" required autocomplete="email"
          style="display:block;width:100%;padding:10px;margin-bottom:8px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;font-size:14px;">
        <input id="mm-sb-pass" type="password" placeholder="Password" required autocomplete="current-password"
          style="display:block;width:100%;padding:10px;margin-bottom:12px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;font-size:14px;">
        <button type="submit"
          style="width:100%;padding:11px;background:#1C3A2A;color:white;border:0;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;">Sign In</button>
        <div id="mm-sb-error" style="margin-top:12px;color:#C62828;font-size:13px;display:none;"></div>
      </form>
    </div>
  `;
  document.body.appendChild(o);
  return o;
}
