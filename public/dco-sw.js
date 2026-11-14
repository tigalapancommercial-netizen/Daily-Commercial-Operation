/* DCO v28: cache only the public app shell for offline reopening.
 * Never cache Supabase calls, cross-origin responses or user-uploaded media.
 */
const CACHE = 'dco-app-shell-v28-20261114';
const APP = self.registration.scope;
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.add(APP)).catch(() => undefined));
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(Promise.all([
    caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('dco-app-shell-') && k !== CACHE).map(k => caches.delete(k)))),
    self.clients.claim(),
  ]));
});
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.href.startsWith(APP)) return;
  const cacheable = req.mode === 'navigate' || /\.(js|css|svg|png|webp|woff2?)$/.test(url.pathname);
  if (!cacheable) return;
  event.respondWith((async () => {
    const cached = await caches.match(req);
    // Online prefers current assets; offline will use the last successfully loaded shell.
    try {
      const response = await fetch(req);
      if (response.ok && response.type === 'basic') {
        const cache = await caches.open(CACHE);cache.put(req,response.clone()).catch(()=>{});
      }
      return response;
    } catch (error) {
      if (cached) return cached;
      if (req.mode === 'navigate') {
        const fallback = await caches.match(APP);
        if (fallback) return fallback;
      }
      throw error;
    }
  })());
});
