/* ========================================
   NAVBAR JS
   File ini khusus script untuk area navbar.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initUserDropdown();
    initNotificationDropdown();
});

/* ========================================
   GENERIC DROPDOWN
======================================== */
function initSimpleDropdown(rootId, toggleId, openClass) {
    const root = document.getElementById(rootId);
    const toggle = document.getElementById(toggleId);

    if (!root || !toggle) {
        return;
    }

    function setDropdownState(isOpen) {
        root.classList.toggle(openClass, isOpen);
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }

    toggle.addEventListener('click', function (event) {
        event.stopPropagation();
        setDropdownState(!root.classList.contains(openClass));
    });

    document.addEventListener('click', function (event) {
        if (!root.contains(event.target)) {
            setDropdownState(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            setDropdownState(false);
        }
    });
}

/* ========================================
   USER DROPDOWN
   Menangani buka dan tutup dropdown profil pengguna.
======================================== */
function initUserDropdown() {
    initSimpleDropdown('userDropdown', 'userDropdownToggle', 'open');
}

/* ========================================
   NOTIFICATION DROPDOWN
   Menangani buka dan tutup panel notifikasi navbar.
======================================== */
function initNotificationDropdown() {
    initSimpleDropdown('notificationDropdown', 'notificationDropdownToggle', 'open');
}
