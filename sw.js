// Chords service worker: the app works offline; song data syncs through Supabase when online.
const VERSION = "szk-v58";
const SHELL = ["./", "./index.html", "./config.js", "./manifest.webmanifest", "./songs-seed.json",
  "./icons/icon-180.png", "./icons/icon-192.png", "./icons/icon-512.png", "./icons/icon-maskable-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL.map(u => new Request(u, { cache: "reload" })))).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isFont = url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
  const isOwn = url.origin === self.location.origin;
  if (!isOwn && !isFont) return; // Supabase and everything else: straight to network
  if (/\/(rest|auth)\/v1\//.test(url.pathname)) return;

  // Stale-while-revalidate: open instantly from cache, refresh the cache in the background.
  e.respondWith(caches.open(VERSION).then(async cache => {
    const key = req.mode === "navigate" ? "./index.html" : req;
    const cached = await cache.match(key, { ignoreSearch: req.mode === "navigate" });
    const fresh = fetch(req).then(res => {
      if (res && (res.ok || res.type === "opaque")) cache.put(key, res.clone());
      return res;
    }).catch(() => null);
    return cached || (await fresh) || new Response("Offline", { status: 503 });
  }));
});
