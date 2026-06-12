(function () {
    'use strict';

    const SHOW_DELAY = 180;
    const NAV_TIMEOUT = 12000;
    let activeCount = 0;
    let showTimer = null;
    let overlay = null;
    let message = null;

    function getOverlay() {
        overlay = overlay || document.querySelector('[data-app-loader]');
        message = message || overlay?.querySelector('[data-app-loader-text]');
        return overlay;
    }

    function reveal(text) {
        const loader = getOverlay();
        if (!loader || activeCount < 1) {
            return;
        }
        if (message) {
            message.textContent = text || 'Mohon tunggu sebentar...';
        }
        loader.hidden = false;
        loader.setAttribute('aria-hidden', 'false');
        requestAnimationFrame(function () {
            loader.classList.add('is-visible');
            document.body.classList.add('is-app-loading');
        });
    }

    function hide() {
        const loader = getOverlay();
        window.clearTimeout(showTimer);
        showTimer = null;
        if (!loader) {
            return;
        }
        loader.classList.remove('is-visible');
        loader.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('is-app-loading');
        window.setTimeout(function () {
            if (activeCount < 1) {
                loader.hidden = true;
            }
        }, 190);
    }

    function start(text, options) {
        activeCount += 1;
        const token = { stopped: false };
        const config = options || {};
        if (!showTimer && !getOverlay()?.classList.contains('is-visible')) {
            showTimer = window.setTimeout(function () {
                showTimer = null;
                reveal(text);
            }, Number.isFinite(config.delay) ? config.delay : SHOW_DELAY);
        } else if (message && text) {
            message.textContent = text;
        }
        return token;
    }

    function stop(token) {
        if (!token || token.stopped) {
            return;
        }
        token.stopped = true;
        activeCount = Math.max(0, activeCount - 1);
        if (activeCount === 0) {
            hide();
        }
    }

    function startNavigation(text) {
        const token = start(text || 'Menyiapkan halaman...', { delay: 120 });
        window.setTimeout(function () {
            stop(token);
        }, NAV_TIMEOUT);
        return token;
    }

    function startTimed(text, duration) {
        const token = start(text, { delay: 120 });
        window.setTimeout(function () {
            stop(token);
        }, duration || 2500);
        return token;
    }

    function track(promise, text) {
        const token = start(text);
        return Promise.resolve(promise).finally(function () {
            stop(token);
        });
    }

    function isNavigableLink(link) {
        if (
            !link
            || link.hasAttribute('download')
            || link.target === '_blank'
            || link.dataset.loadingIgnore === 'true'
        ) {
            return false;
        }
        const href = link.getAttribute('href') || '';
        if (!href || href.startsWith('#') || /^(mailto:|tel:|javascript:)/i.test(href)) {
            return false;
        }
        const url = new URL(link.href, window.location.href);
        return ['http:', 'https:'].includes(url.protocol)
            && url.origin === window.location.origin
            && url.href !== window.location.href;
    }

    function isDownloadLink(link) {
        const url = new URL(link.href, window.location.href);
        return link.hasAttribute('download')
            || /\/(pdf|export)(\/|$)/i.test(url.pathname)
            || /\.(pdf|xlsx?|csv|docx?|zip)$/i.test(url.pathname);
    }

    function initNavigationLoading() {
        document.addEventListener('click', function (event) {
            if (
                event.button !== 0
                || event.ctrlKey
                || event.metaKey
                || event.shiftKey
                || event.altKey
            ) {
                return;
            }
            const link = event.target.closest?.('a[href]');
            if (!link || link.target === '_blank' || link.dataset.loadingIgnore === 'true') {
                return;
            }
            if (isDownloadLink(link)) {
                window.setTimeout(function () {
                    if (!event.defaultPrevented) {
                        startTimed('Menyiapkan dokumen...', 3000);
                    }
                });
                return;
            }
            if (!isNavigableLink(link)) {
                return;
            }
            window.setTimeout(function () {
                if (!event.defaultPrevented) {
                    startNavigation('Menyiapkan halaman...');
                }
            });
        });

        document.addEventListener('submit', function (event) {
            const form = event.target;
            if (
                !(form instanceof HTMLFormElement)
                || form.dataset.loadingIgnore === 'true'
                || form.target === '_blank'
                || form.method.toLowerCase() === 'dialog'
            ) {
                return;
            }
            window.setTimeout(function () {
                if (!event.defaultPrevented) {
                    startNavigation(form.dataset.loadingText || 'Memproses data...');
                }
            });
        });

        window.addEventListener('pageshow', function () {
            activeCount = 0;
            hide();
        });
    }

    function initFetchLoading() {
        if (typeof window.fetch !== 'function') {
            return;
        }
        const nativeFetch = window.fetch.bind(window);
        window.fetch = function () {
            const token = start('Mengambil data terbaru...');
            try {
                return nativeFetch.apply(window, arguments).finally(function () {
                    stop(token);
                });
            } catch (error) {
                stop(token);
                throw error;
            }
        };
    }

    function initXhrLoading() {
        if (typeof window.XMLHttpRequest !== 'function') {
            return;
        }
        const nativeSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.send = function () {
            const token = start('Mengambil data terbaru...');
            this.addEventListener('loadend', function () {
                stop(token);
            }, { once: true });
            try {
                return nativeSend.apply(this, arguments);
            } catch (error) {
                stop(token);
                throw error;
            }
        };
    }

    window.SilebatLoading = { start, stop, track, startNavigation, startTimed };
    initFetchLoading();
    initXhrLoading();
    document.addEventListener('DOMContentLoaded', initNavigationLoading);
})();
