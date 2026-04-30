/* ========================================
   LOGIN JS
   JS halaman login.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    const firstInput = document.querySelector('.login-form input:not([type="hidden"])');
    if (firstInput) {
        firstInput.focus({ preventScroll: true });
    }
});
