// Keeps a copy of the songbook on the device (see sw.js), so it also opens
// offline, e.g. from the home screen in airplane mode. Needs https (GitHub
// Pages) or localhost; does nothing when index.html is opened as a file.

if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("sw.js").catch(() => {});
    });
}
