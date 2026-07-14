/* ========================================
   APP CACHE JS
   Membersihkan storage browser saat versi deploy berubah.
======================================== */
(function () {
    const meta = document.querySelector('meta[name="silebat-cache-version"]');
    const version = meta ? String(meta.content || '').trim() : '';
    const versionKey = 'silebat:cache-version';

    if (!version) {
        return;
    }

    let storedVersion = '';
    try {
        storedVersion = window.localStorage.getItem(versionKey) || '';
    } catch (error) {
        storedVersion = '';
    }

    if (storedVersion === version) {
        return;
    }

    if ('caches' in window) {
        window.caches.keys()
            .then(function (keys) {
                return Promise.all(keys.map(function (key) {
                    return window.caches.delete(key);
                }));
            })
            .catch(function () {});
    }

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations()
            .then(function (registrations) {
                return Promise.all(registrations.map(function (registration) {
                    return registration.unregister();
                }));
            })
            .catch(function () {});
    }

    try {
        window.sessionStorage.clear();
    } catch (error) {}

    try {
        window.localStorage.clear();
        window.localStorage.setItem(versionKey, version);
    } catch (error) {}
})();
