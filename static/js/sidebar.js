/* ========================================
   SIDEBAR JS
   JS untuk area sidebar.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initSidebarToggle();
    initSidebarNavigation();
});

/* ========================================
   SIDEBAR TOGGLE
   Mengatur sidebar off-canvas mobile dan hide/unhide desktop.
======================================== */
function initSidebarToggle() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileMedia = window.matchMedia('(max-width: 992px)');
    const storageKey = 'silebat:sidebar-hidden';
    let desktopHidden = readDesktopState();

    if (!menuToggle || !sidebar) {
        return;
    }

    function readDesktopState() {
        try {
            return window.localStorage.getItem(storageKey) === 'true';
        } catch (error) {
            return false;
        }
    }

    function saveDesktopState(isHidden) {
        try {
            window.localStorage.setItem(storageKey, String(isHidden));
        } catch (error) {
            console.warn('Preferensi sidebar tidak dapat disimpan.', error);
        }
    }

    function notifyLayoutChange() {
        window.setTimeout(function () {
            window.dispatchEvent(new Event('resize'));
        }, 320);
    }

    function syncMenuToggle() {
        const icon = menuToggle.querySelector('i');

        if (mobileMedia.matches) {
            const isOpen = sidebar.classList.contains('show');
            menuToggle.setAttribute('aria-expanded', String(isOpen));
            menuToggle.setAttribute('aria-label', isOpen ? 'Tutup menu' : 'Buka menu');
            menuToggle.title = isOpen ? 'Tutup menu' : 'Buka menu';
            if (icon) {
                icon.className = isOpen ? 'bi bi-x-lg' : 'bi bi-list';
            }
            return;
        }

        menuToggle.setAttribute('aria-expanded', String(!desktopHidden));
        menuToggle.setAttribute('aria-label', desktopHidden ? 'Tampilkan sidebar' : 'Sembunyikan sidebar');
        menuToggle.title = desktopHidden ? 'Tampilkan sidebar' : 'Sembunyikan sidebar';
        if (icon) {
            icon.className = desktopHidden ? 'bi bi-layout-sidebar-inset' : 'bi bi-list';
        }
    }

    function setMobileState(isOpen) {
        sidebar.classList.toggle('show', isOpen);
        sidebar.setAttribute('aria-hidden', String(!isOpen));
        syncMenuToggle();
    }

    function setDesktopState(isHidden, persist, notifyChange) {
        desktopHidden = isHidden;
        document.body.classList.toggle('sidebar-hidden', isHidden);
        sidebar.setAttribute('aria-hidden', String(isHidden));
        if (persist) {
            saveDesktopState(isHidden);
        }
        syncMenuToggle();
        if (notifyChange) {
            notifyLayoutChange();
        }
    }

    function syncViewportState() {
        sidebar.classList.remove('show');
        if (mobileMedia.matches) {
            document.body.classList.remove('sidebar-hidden');
            setMobileState(false);
            return;
        }

        setDesktopState(desktopHidden, false, false);
    }

    menuToggle.addEventListener('click', function (event) {
        event.stopPropagation();
        if (mobileMedia.matches) {
            setMobileState(!sidebar.classList.contains('show'));
            return;
        }

        setDesktopState(!desktopHidden, true, true);
    });

    document.addEventListener('click', function (event) {
        const isClickInsideSidebar = sidebar.contains(event.target);
        const isClickToggle = menuToggle.contains(event.target);

        if (!isClickInsideSidebar && !isClickToggle && mobileMedia.matches) {
            setMobileState(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && mobileMedia.matches && sidebar.classList.contains('show')) {
            setMobileState(false);
            menuToggle.focus({ preventScroll: true });
        }
    });

    if (typeof mobileMedia.addEventListener === 'function') {
        mobileMedia.addEventListener('change', syncViewportState);
    } else {
        mobileMedia.addListener(syncViewportState);
    }
    syncViewportState();
}

/* ========================================
   SIDEBAR NAVIGATION
   Menandai menu aktif dan mengatur accordion submenu.
======================================== */
function initSidebarNavigation() {
    const sidebarNav = document.querySelector('.sidebar-nav');
    const navGroups = document.querySelectorAll('.nav-group');

    if (!sidebarNav) {
        return;
    }

    function normalizePath(path) {
        if (!path) {
            return '/';
        }

        const cleanedPath = path.replace(/\/+$/, '');
        return cleanedPath === '' ? '/' : cleanedPath;
    }

    function isRealLink(href) {
        return href && href !== '#' && href.trim() !== '';
    }

    const currentPath = normalizePath(window.location.pathname);
    const directNavLinks = sidebarNav.querySelectorAll(':scope > a.nav-link');

    directNavLinks.forEach(function (link) {
        const rawHref = link.getAttribute('href');

        if (!isRealLink(rawHref)) {
            return;
        }

        const href = normalizePath(rawHref);

        if (isPathMatch(href, currentPath)) {
            link.classList.add('active');
        }
    });

    function isPathMatch(href, path) {
        if (href === '/') {
            return path === '/';
        }

        return path === href || path.startsWith(href + '/');
    }

    function getBestActiveSubLink(subLinks) {
        let activeLink = null;
        let activeHrefLength = -1;

        subLinks.forEach(function (link) {
            const rawHref = link.getAttribute('href');

            if (!isRealLink(rawHref)) {
                return;
            }

            const href = normalizePath(rawHref);

            if (isPathMatch(href, currentPath) && href.length > activeHrefLength) {
                activeLink = link;
                activeHrefLength = href.length;
            }
        });

        return activeLink;
    }

    navGroups.forEach(function (group) {
        const toggleButton = group.querySelector('.nav-toggle');
        const subLinks = group.querySelectorAll('.sub-link');
        const activeChild = getBestActiveSubLink(subLinks);

        if (activeChild) {
            activeChild.classList.add('active');
            group.classList.add('active');
        }

        if (toggleButton) {
            toggleButton.setAttribute('aria-expanded', group.classList.contains('active') ? 'true' : 'false');
            toggleButton.addEventListener('click', function () {
                const isActive = group.classList.contains('active');

                navGroups.forEach(function (otherGroup) {
                    otherGroup.classList.remove('active');
                    const otherToggle = otherGroup.querySelector('.nav-toggle');

                    if (otherToggle) {
                        otherToggle.setAttribute('aria-expanded', 'false');
                    }
                });

                group.classList.toggle('active', !isActive);
                toggleButton.setAttribute('aria-expanded', !isActive ? 'true' : 'false');
            });
        }
    });

}
