// Mazar Martin — self-unregistering service worker.
//
// We've moved off PWA caching: the data layer is now Supabase-backed and
// the previously-aggressive offline support was causing more confusion
// (stale `mm-supabase.js`, stale `index.html`) than value. This file ships
// only to clean up any previously-installed v4 SW on existing users'
// browsers. When their browser checks sw.js for updates, it sees this
// version, installs it (skipWaiting), and on activate it unregisters
// itself and deletes all caches. After that visit, the browser is SW-free
// and all subsequent loads fetch fresh code from GitHub Pages.

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const names = await caches.keys();
      await Promise.all(names.map((n) => caches.delete(n)));
    } catch (e) {
      console.warn('[mm-sw] failed to clear caches:', e);
    }
    try {
      await self.registration.unregister();
    } catch (e) {
      console.warn('[mm-sw] failed to unregister:', e);
    }
  })());
});

self.addEventListener('fetch', () => {
  // No-op — let the browser handle all fetches natively from now on.
});
