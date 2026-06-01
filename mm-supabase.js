// mm-supabase.js — Stage 2 integration block
//
// STEP 2 active: routes one localStorage key (mmCommissionUnlocked) through
// the user_kv table. Every other localStorage key still passes through to
// the browser's native storage untouched. Add keys by extending the relevant
// set (USER_KV_KEYS for simple per-user flags, more sets later for keys
// that map to proper relational tables).
//
// Loaded as a module via `<script type="module" src="./mm-supabase.js"></script>`
// at the end of index.html.

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = 'https://phkmwcimpyvmxbpdmuvw.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_aJddeid2D0-0kDWclrNRgQ_nt_kQih5';

// Keys whose reads/writes we route to the user_kv table.
// These are simple per-user values (boolean flags, UI prefs, etc.).
// See LOCALSTORAGE_AUDIT.md for the full mm* key inventory.
const USER_KV_KEYS = new Set([
  'mmCommissionUnlocked',
]);

// Module state
let supabase = null;
let currentUserId = null;
let userKvCache = {};

if (window._mmSupabaseInit) {
  console.warn('[MM-Supabase] already initialised, skipping');
} else {
  window._mmSupabaseInit = true;
  boot();
}

function boot() {
  supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
  window._mmSupabase = supabase; // debug handle for the browser console

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

  // 1. Skip the login step if a session already exists.
  supabase.auth.getSession().then(async ({ data: { session } }) => {
    if (session) {
      setStatus(`Signed in as ${session.user.email}`);
      await afterLogin(session);
    } else {
      setStatus('Sign in to load your data:');
      form.style.display = 'block';
    }
  });

  // 2. Handle login submit.
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

  // 3. Hydrate cache and install overrides, then drop the overlay.
  async function afterLogin(session) {
    currentUserId = session.user.id;
    setStatus('Loading your settings…');
    try {
      userKvCache = await hydrateUserKv();
      installLocalStorageOverrides();
      const n = Object.keys(userKvCache).length;
      setStatus(`✅ Loaded ${n} setting${n === 1 ? '' : 's'} — opening app…`, '#2E7D32');
      console.log('[MM-Supabase] hydrated user_kv:', userKvCache);
      setTimeout(() => overlay.remove(), 700);
    } catch (e) {
      console.error('[MM-Supabase] hydrate failed', e);
      showError('Hydration failed: ' + (e.message || e));
      setStatus('Connected (with errors) — see console.', '#C62828');
    }
  }
}

async function hydrateUserKv() {
  const { data, error } = await supabase
    .from('user_kv')
    .select('key, value')
    .eq('user_id', currentUserId);
  if (error) throw error;
  const cache = {};
  for (const row of data) {
    // localStorage values are always strings; coerce for compat.
    cache[row.key] = typeof row.value === 'string' ? row.value : JSON.stringify(row.value);
  }
  window._mmCache = cache; // debug
  return cache;
}

function installLocalStorageOverrides() {
  // Save originals so we can pass through non-managed keys unchanged.
  const realGet = localStorage.getItem.bind(localStorage);
  const realSet = localStorage.setItem.bind(localStorage);
  const realRem = localStorage.removeItem.bind(localStorage);

  localStorage.getItem = function(key) {
    if (USER_KV_KEYS.has(key)) {
      return Object.prototype.hasOwnProperty.call(userKvCache, key)
        ? userKvCache[key]
        : null;
    }
    return realGet(key);
  };

  localStorage.setItem = function(key, value) {
    if (USER_KV_KEYS.has(key)) {
      const str = String(value);
      userKvCache[key] = str;
      // Fire-and-forget upsert (cache update is sync; cloud sync is async).
      supabase.from('user_kv')
        .upsert(
          { user_id: currentUserId, key, value: str },
          { onConflict: 'user_id,key' }
        )
        .then(({ error }) => {
          if (error) console.error(`[MM-Supabase] write failed for ${key}:`, error);
          else console.log(`[MM-Supabase] saved ${key} = ${JSON.stringify(str)}`);
        });
      return;
    }
    return realSet(key, value);
  };

  localStorage.removeItem = function(key) {
    if (USER_KV_KEYS.has(key)) {
      delete userKvCache[key];
      supabase.from('user_kv')
        .delete()
        .eq('user_id', currentUserId)
        .eq('key', key)
        .then(({ error }) => {
          if (error) console.error(`[MM-Supabase] delete failed for ${key}:`, error);
          else console.log(`[MM-Supabase] removed ${key}`);
        });
      return;
    }
    return realRem(key);
  };

  console.log('[MM-Supabase] localStorage overrides installed for', [...USER_KV_KEYS]);
}

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
