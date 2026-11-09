// Offline support. App files are cached. API reads use the network first and fall back to the last copy.
const CACHE = "vigil-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icons/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  const networkFirst = url.pathname.startsWith("/api/") || e.request.mode === "navigate";
  e.respondWith(networkFirst ? fromNetwork(e.request) : fromCache(e.request));
});

async function fromNetwork(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const fallback = (await cache.match(request)) || (request.mode === "navigate" ? await cache.match("/index.html") : null);
    if (!fallback) throw err;
    const headers = new Headers(fallback.headers);
    headers.set("X-Vigil-Offline", "1");
    return new Response(fallback.body, { status: fallback.status, headers });
  }
}

async function fromCache(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}
