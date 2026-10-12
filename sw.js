// Offline copy of the songbook, so it also opens from the home screen with no
// connection (registered by web/js/offline.js).
//
// Online: the latest page from the server, saved for later.
// Offline, or when the network takes too long: the saved copy.

const CACHE = "cancionero-pagano-v1";
const PAGE = new URL("./", self.location).href; // the songbook (index.html)
const TIMEOUT_MS = 4000;

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE)
            .then((cache) => cache.add(PAGE))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") return;
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return; // Spotify, YouTube, ...

    // Every page of the site is the one songbook page (#song-id is not sent).
    const isPage = request.mode === "navigate"
        || url.href === PAGE
        || url.href === PAGE + "index.html";
    const key = isPage ? PAGE : request;

    const network = fetch(request);
    const saved = network.then(async (response) => {
        // A redirected response can't be served for a page later.
        if (response.ok && !response.redirected) {
            const copy = response.clone(); // before the page starts reading it
            const cache = await caches.open(CACHE);
            await cache.put(key, copy);
        }
    }).catch(() => {}); // offline: keep the saved copy
    event.waitUntil(saved);
    event.respondWith(networkFirst(network, key));
});

async function networkFirst(network, key) {
    const slow = new Promise((resolve) => setTimeout(resolve, TIMEOUT_MS));
    try {
        const response = await Promise.race([network, slow]);
        if (response) return response;
    } catch {
        // offline: fall through to the saved copy
    }
    const cached = await caches.match(key);
    return cached || network; // nothing saved yet: wait for the network
}
