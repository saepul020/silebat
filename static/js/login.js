/* ========================================
   LOGIN JS
   JS halaman login.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    const firstInput = document.querySelector('.login-form input:not([type="hidden"])');
    if (firstInput) {
        firstInput.focus({ preventScroll: true });
    }

    document.querySelectorAll('[data-password-toggle]').forEach(function (button) {
        const targetId = button.getAttribute('data-password-target');
        const input = targetId ? document.getElementById(targetId) : null;
        const icon = button.querySelector('i');
        if (!input) {
            return;
        }

        button.addEventListener('click', function () {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.setAttribute('aria-label', show ? 'Sembunyikan password' : 'Tampilkan password');
            button.setAttribute('aria-pressed', show ? 'true' : 'false');
            if (icon) {
                icon.className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
            }
            input.focus({ preventScroll: true });
        });
    });
});
