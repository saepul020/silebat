/* ========================================
   LANDING MANAGEMENT JS - SILEBAT
   Validasi realtime form konten peralatan landing page.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initLandingEquipmentOrderValidation();
    initLandingEquipmentGalleryUpload();
});

function initLandingEquipmentGalleryUpload() {
    const control = document.querySelector('[data-gallery-upload]');
    if (!control) {
        return;
    }

    const input = control.querySelector('[data-gallery-input]');
    const removeInputs = Array.from(control.querySelectorAll('[data-gallery-remove]'));
    const preview = control.querySelector('[data-gallery-new]');
    const empty = control.querySelector('[data-gallery-empty]');
    const trigger = control.querySelector('[data-gallery-trigger]');
    const status = control.querySelector('[data-gallery-status]');
    const error = control.querySelector('[data-gallery-error]');
    const form = control.closest('form');
    const maxFiles = Number(control.getAttribute('data-gallery-max') || 5);
    const maxSize = 7 * 1024 * 1024;
    const allowed = ['jpg', 'jpeg', 'png'];
    let selectedFiles = [];
    let previewUrls = [];

    if (!input || !preview || !empty || !trigger || !status || !error || !form) {
        return;
    }

    function activeExistingCount() {
        return removeInputs.filter(function (item) { return !item.checked; }).length;
    }

    function clearPreviewUrls() {
        previewUrls.forEach(URL.revokeObjectURL);
        previewUrls = [];
    }

    function showError(message) {
        error.textContent = '*' + message;
        error.hidden = false;
        control.classList.add('has-error');
    }

    function clearError() {
        error.textContent = '';
        error.hidden = true;
        control.classList.remove('has-error');
    }

    function selectedCount() {
        return activeExistingCount() + selectedFiles.length;
    }

    function syncInput() {
        const transfer = new DataTransfer();
        selectedFiles.forEach(function (file) {
            transfer.items.add(file);
        });
        input.files = transfer.files;
    }

    function updateState() {
        const count = selectedCount();
        const isFull = count >= maxFiles;
        status.textContent = count + '/' + maxFiles + ' foto dipilih' + (isFull ? ' \u00b7 Batas maksimal tercapai' : ' \u00b7 Tambah foto lagi');
        trigger.classList.toggle('is-full', isFull);
        trigger.setAttribute('aria-disabled', String(isFull));
        empty.hidden = count > 0;
    }

    function validateFiles(files) {
        if (activeExistingCount() + selectedFiles.length + files.length > maxFiles) {
            return 'Total foto maksimal ' + maxFiles + '. Hapus foto lama atau kurangi foto baru.';
        }
        for (const file of files) {
            const extension = String(file.name || '').split('.').pop().toLowerCase();
            if (!allowed.includes(extension)) {
                return 'Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.';
            }
            if (file.size > maxSize) {
                return 'Ukuran setiap Foto Barang maksimal 7 MB.';
            }
        }
        return '';
    }

    function renderSelection() {
        clearPreviewUrls();
        preview.replaceChildren();
        selectedFiles.forEach(function (file, index) {
            const url = URL.createObjectURL(file);
            const item = document.createElement('div');
            const image = document.createElement('img');
            const remove = document.createElement('button');
            const label = document.createElement('span');
            previewUrls.push(url);
            item.className = 'landing-gallery-thumb';
            image.src = url;
            image.alt = 'Preview foto baru ' + (index + 1);
            remove.type = 'button';
            remove.className = 'landing-gallery-remove';
            remove.setAttribute('aria-label', 'Hapus ' + file.name);
            remove.title = 'Hapus foto';
            remove.innerHTML = '<i class="bi bi-x-lg"></i>';
            remove.addEventListener('click', function () {
                selectedFiles.splice(index, 1);
                syncInput();
                clearError();
                renderSelection();
            });
            label.className = 'landing-gallery-name';
            label.textContent = file.name;
            item.append(image, remove, label);
            preview.appendChild(item);
        });
        updateState();
    }

    function addSelection() {
        const files = Array.from(input.files || []);
        const message = validateFiles(files);
        if (message) {
            syncInput();
            showError(message);
            return;
        }
        selectedFiles.push(...files);
        syncInput();
        clearError();
        renderSelection();
    }

    input.addEventListener('change', addSelection);
    removeInputs.forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            clearError();
            updateState();
        });
    });
    form.addEventListener('submit', function (event) {
        const message = validateFiles([]);
        if (message) {
            event.preventDefault();
            showError(message);
            control.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
    renderSelection();
}

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
