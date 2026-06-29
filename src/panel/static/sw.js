/* Aigram service worker — NETWORK-FIRST shell + offline fallback.
 *
 * The app shell (index.html/app.css/app.js/icons) is served network-first so a
 * browser ALWAYS runs the latest assets when online; the cache is only an
 * offline safety net. (A previous cache-first shell could pin stale app.css/
 * app.js against a fresh index.html — never again.) Bump SHELL to force a purge
 * of any old cache on the next visit. */
const SHELL = "aigram-shell-v15";
const ASSETS = [
  "/", "/index.html", "/app.css", "/app.js", "/manifest.webmanifest",
  "/icons/icon-192.png", "/icons/icon-512.png", "/icons/icon-maskable-512.png",
  "/fonts/inter-400.woff2", "/fonts/inter-500.woff2", "/fonts/inter-600.woff2",
  "/fonts/inter-700.woff2", "/fonts/vazirmatn-400.woff2", "/fonts/vazirmatn-500.woff2",
  "/fonts/vazirmatn-700.woff2", "/vendor/lottie.min.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(SHELL)
      .then((c) => c.addAll(ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return; // never touch POST/PUT/DELETE (commands, mutations)
  const url = new URL(req.url);

  // Self-hosted fonts + vendored libs are immutable — serve cache-first.
  if (url.pathname.startsWith("/fonts/") || url.pathname.startsWith("/vendor/")) {
    e.respondWith(
      caches.match(req).then((r) => r || fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(SHELL).then((c) => c.put(req, copy)); }
        return res;
      }))
    );
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    // Commands, media, and the SSE stream are always live — never SW-cache them.
    if (url.pathname.startsWith("/api/cmd/") || url.pathname.includes("/media/")
        || url.pathname === "/api/events") return;
    // Network-first; cache only the cheap idempotent reads for an offline shell.
    const cacheable = url.pathname === "/api/status" || url.pathname.startsWith("/api/dialogs");
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (cacheable && res.ok) {
            const copy = res.clone();
            caches.open(SHELL).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // App shell (html/css/js/icons/manifest): NETWORK-FIRST. Fetch fresh, refresh
  // the cache, and only fall back to cache (or the cached index) when offline.
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(SHELL).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then(
          (r) => r || (req.mode === "navigate" ? caches.match("/index.html") : undefined)
        )
      )
  );
});
