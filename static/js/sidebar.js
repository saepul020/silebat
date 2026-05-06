/* ========================================
   SIDEBAR JS
   JS untuk area sidebar.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initSidebarToggle();
    initSidebarNavigation();
});

/* ========================================
   SIDEBAR MOBILE
   Toggle sidebar pada layar kecil.
======================================== */
function initSidebarToggle() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileBreakpoint = 992;

    if (!menuToggle || !sidebar) {
        return;
    }

    function setSidebarState(isOpen) {
        sidebar.classList.toggle('show', isOpen);
        menuToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }

    menuToggle.addEventListener('click', function (event) {
        event.stopPropagation();
        setSidebarState(!sidebar.classList.contains('show'));
    });

    document.addEventListener('click', function (event) {
        const isClickInsideSidebar = sidebar.contains(event.target);
        const isClickToggle = menuToggle.contains(event.target);

        if (!isClickInsideSidebar && !isClickToggle && window.innerWidth <= mobileBreakpoint) {
            setSidebarState(false);
        }
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > mobileBreakpoint) {
            setSidebarState(false);
        }
    });
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
