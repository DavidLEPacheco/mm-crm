// mm-supabase.js — Stage 2 integration block (STEP 1: auth + smoke test)
//
// Loaded as a module via `<script type="module" src="./mm-supabase.js"></script>`
// at the end of index.html. Shows a login overlay; on sign-in, runs a smoke-test
// query against Supabase to verify the connection works under RLS.
//
// Does NOT yet reroute localStorage — that's step 2 onwards.

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const SUPABASE_URL = 'https://phkmwcimpyvmxbpdmuvw.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_aJddeid2D0-0kDWclrNRgQ_nt_kQih5';

if (window._mmSupabaseInit) {
  console.warn('[MM-Supabase] already initialised, skipping');
} else {
  window._mmSupabaseInit = true;
  boot();
}

function boot() {
  const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
  window._mmSupabase = supabase; // exposed for console debugging

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

  // 1. Check for an existing session — skip the login step if signed in.
  supabase.auth.getSession().then(async ({ data: { session } }) => {
    if (session) {
      setStatus(`Signed in as ${session.user.email}`);
      await afterLogin();
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
    await afterLogin();
  });

  // 3. After login, run a smoke-test query that exercises RLS.
  async function afterLogin() {
    setStatus('Connecting to your data…');
    try {
      const result = await smokeTest(supabase);
      setStatus(`✅ Connected — ${result.orgs} org · ${result.members} member`, '#2E7D32');
      console.log('[MM-Supabase] smoke test passed', result);
      // Brief celebration, then drop the overlay so the underlying app shows.
      setTimeout(() => overlay.remove(), 1000);
    } catch (e) {
      console.error('[MM-Supabase] smoke test failed', e);
      showError('Connection test failed: ' + (e.message || e));
      setStatus('Connected (with errors) — see console.', '#C62828');
    }
  }
}

async function smokeTest(supabase) {
  // Step 1 validation only: prove we can read through RLS as a 'staff' member.
  // Step 2+ will replace this with a full cache hydration across all tables.
  const { data: orgs, error: orgErr } = await supabase
    .from('orgs').select('id, name');
  if (orgErr) throw orgErr;

  const { data: members, error: memErr } = await supabase
    .from('org_members').select('user_id, role');
  if (memErr) throw memErr;

  return { orgs: orgs.length, members: members.length, orgsList: orgs };
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
