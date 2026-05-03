/* ========================================
   LANDING MANAGEMENT JS - SILEBAT
   Validasi realtime form konten peralatan landing page.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initLandingEquipmentOrderValidation();
});

function initLandingEquipmentOrderValidation() {
    const form = document.querySelector('[data-landing-equipment-form="true"]');
    if (!form) {
        return;
    }

    const orderInput = form.querySelector('#id_urutan');
    const checkUrl = String(form.getAttribute('data-order-check-url') || '').trim();
    const currentId = String(form.getAttribute('data-current-id') || '').trim();
    const duplicateMessage = 'Urutan tampil sudah digunakan oleh konten lain.';
    let validationTimer = null;
    let lastRequestId = 0;
    let hasDuplicateOrder = false;

    if (!orderInput || !checkUrl) {
        return;
    }

    function getGroup() {
        return orderInput.closest('[data-landing-order-group]') || orderInput.closest('.form-group');
    }

    function normalizeMessage(message) {
        return String(message || '').replace(/^\*/, '').trim();
    }

    function removeDuplicateMessages(group) {
        if (!group) {
            return;
        }

        group.querySelectorAll('.input-error-text').forEach(function (node) {
            const message = normalizeMessage(node.textContent);
            if (node.hasAttribute('data-landing-order-error') || message === duplicateMessage) {
                node.hidden = node.hasAttribute('data-landing-order-error');
                node.textContent = '';
                if (!node.hasAttribute('data-landing-order-error')) {
                    node.remove();
                }
            }
        });

        const hasVisibleError = Array.from(group.querySelectorAll('.input-error-text')).some(function (node) {
            return !node.hidden && normalizeMessage(node.textContent);
        });
        group.classList.toggle('has-error', hasVisibleError);
    }

    function showDuplicateMessage(message) {
        const group = getGroup();
        if (!group) {
            return;
        }

        let errorNode = group.querySelector('[data-landing-order-error]');
        if (!errorNode) {
            errorNode = document.createElement('p');
            errorNode.className = 'input-error-text';
            errorNode.setAttribute('data-landing-order-error', 'true');
            orderInput.insertAdjacentElement('afterend', errorNode);
        }

        group.querySelectorAll('.input-error-text').forEach(function (node) {
            if (node !== errorNode && normalizeMessage(node.textContent) === duplicateMessage) {
                node.remove();
            }
        });

        errorNode.hidden = false;
        errorNode.textContent = '*' + normalizeMessage(message || duplicateMessage);
        group.classList.add('has-error');
    }

    function clearDuplicateState() {
        hasDuplicateOrder = false;
        removeDuplicateMessages(getGroup());
    }

    function buildCheckUrl(value) {
        const url = new URL(checkUrl, window.location.origin);
        url.searchParams.set('urutan', value);
        if (currentId) {
            url.searchParams.set('exclude_pk', currentId);
        }
        return url.toString();
    }

    async function validateOrderValue() {
        const value = String(orderInput.value || '').trim();
        const requestId = ++lastRequestId;

        if (!value || Number(value) < 1) {
            clearDuplicateState();
            return true;
        }

        try {
            const response = await fetch(buildCheckUrl(value), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                return !hasDuplicateOrder;
            }

            const payload = await response.json();
            if (requestId !== lastRequestId) {
                return !hasDuplicateOrder;
            }

            hasDuplicateOrder = Boolean(payload.is_used);
            if (hasDuplicateOrder) {
                showDuplicateMessage(payload.message || duplicateMessage);
                return false;
            }

            clearDuplicateState();
            return true;
        } catch (error) {
            console.error('Gagal mengecek urutan tampil.', error);
            return !hasDuplicateOrder;
        }
    }

    function scheduleValidation() {
        window.clearTimeout(validationTimer);
        validationTimer = window.setTimeout(validateOrderValue, 320);
    }

    orderInput.addEventListener('input', scheduleValidation);
    orderInput.addEventListener('change', validateOrderValue);
    orderInput.addEventListener('blur', validateOrderValue);

    form.addEventListener('submit', function (event) {
        if (hasDuplicateOrder) {
            event.preventDefault();
            showDuplicateMessage(duplicateMessage);
            orderInput.focus();
        }
    });
}
