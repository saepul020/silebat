document.addEventListener('DOMContentLoaded', function () {
    const modal = document.querySelector('#drh-modal');
    const trigger = document.querySelector('[data-drh-open]');
    if (!modal || !trigger) return;
    const form = modal.querySelector('form');
    const { parseDisplayDate } = initUserDatePickers(form);
    const calendar = form.querySelector('.date-picker-popup');
    const control = calendar.closest('.date-picker-control');
    const date = form.querySelector('[name="tanggal"]');

    function fitCalendar() {
        if (calendar.hidden || !modal.open) return;
        const bounds = modal.getBoundingClientRect();
        const field = date.getBoundingClientRect();
        const below = bounds.bottom - field.bottom - 20;
        const above = field.top - bounds.top - 20;
        if (field.top < bounds.top + 8 || field.bottom > bounds.bottom - 8
            || Math.max(below, above) < 100) {
            calendar.hidden = true;
            control.classList.remove('is-open');
            return;
        }
        const upwards = below < 240 && above > below;
        calendar.style.top = upwards ? 'auto' : 'calc(100% + 8px)';
        calendar.style.bottom = upwards ? 'calc(100% + 8px)' : 'auto';
        calendar.style.maxHeight = Math.max(0, upwards ? above : below) + 'px';
    }

    new MutationObserver(fitCalendar).observe(calendar, {
        attributes: true, attributeFilter: ['hidden'], childList: true, subtree: true,
    });
    new ResizeObserver(fitCalendar).observe(modal);
    modal.addEventListener('scroll', fitCalendar);
    window.addEventListener('resize', fitCalendar);
    window.visualViewport?.addEventListener('resize', fitCalendar);
    initUserValidation(form, {
        validate(field) {
            if (field.name === 'tanggal' && field.value.trim() && !parseDisplayDate(field.value)) {
                return 'Masukkan tanggal DRH yang valid.';
            }
            return '';
        },
    });
    trigger.addEventListener('click', () => modal.showModal());
    modal.addEventListener('close', function () {
        calendar.hidden = true;
        control.classList.remove('is-open');
        trigger.focus();
    });
    modal.querySelectorAll('[data-drh-close]').forEach(button => {
        button.addEventListener('click', () => modal.close());
    });
    modal.addEventListener('click', function (event) {
        if (event.target !== modal) return;
        const rect = modal.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right
            || event.clientY < rect.top || event.clientY > rect.bottom) modal.close();
    });
    form.addEventListener('submit', function (event) {
        if (!event.defaultPrevented) modal.close();
    });
});
