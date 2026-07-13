/* ========================================
   GLOBAL JS
   Script global exclude (dashboard; login; navbar; sidebar).
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    [
        initSuccessPopups,
        initReadonlyPasswordUnlock,
        initPasswordVisibilityToggle,
        initSelectPlaceholderState,
        initDigitsOnlyInputs,
        initDeleteUserModal,
        initMasterDataDeleteModal,
        initAnnouncementDeleteModal,
        initBarangLaboratoriumImportModal,
        initOperasionalDeleteModal,
        initPeminjamanDeleteModal,
        initVerificationActionModal,
        typeof initPengembalianFormBehavior === 'function' ? initPengembalianFormBehavior : null,
        initUploadPreviewControls,
        initInlineImageSourceButtons,
        initInlineFileProxyControls,
        initMasterDataFormBehavior,
        initKomponenRutin,
        initMasterDataFormValidation,
        initOperasionalFormValidation,
        initPenggunaCreateFormValidation,
        initPelatihanFormBehavior,
        initGlobalQtyStepperBehavior,
        initPeminjamanFormBehavior,
        initNotificationAnnouncementFormBehavior,
        initConfirmSubmitForms,
        initSortableListTables,
        initLocalListSearch,
        initMasterShowEntriesControl,
        initListNavigationState,
        initUnsavedFormGuard,
    ].forEach(function (initializer) {
        if (typeof initializer !== 'function') {
            return;
        }

        try {
            initializer();
        } catch (error) {
            console.error('Gagal menjalankan inisialisasi halaman.', error);
        }
    });
});

function normalizeSearchText(value) {
    return String(value || '').trim().toLocaleLowerCase('id-ID').replace(/\s+/g, ' ');
}

function initSuccessPopups() {
    const stack = document.querySelector('[data-success-popup-stack]');
    const popups = stack?.querySelectorAll('[data-success-popup]');

    if (!stack || !popups?.length) {
        stack?.remove();
        return;
    }

    function removePopup(popup) {
        popup.remove();
        if (!stack.querySelector('[data-success-popup]')) {
            stack.remove();
        }
    }

    popups.forEach(function (popup) {
        window.setTimeout(function () {
            popup.classList.add('is-hiding');
            window.setTimeout(function () {
                removePopup(popup);
            }, 250);
        }, 4000);
    });
}

/* ========================================
   GLOBAL FORM
   Mengaktifkan field password readonly saat pengguna mulai berinteraksi.
======================================== */
function initReadonlyPasswordUnlock() {
    const protectedFields = document.querySelectorAll('[data-unlock-readonly]');

    if (!protectedFields.length) {
        return;
    }

    protectedFields.forEach(function (field) {
        const unlockField = function () {
            field.removeAttribute('readonly');
        };

        ['focus', 'click', 'keydown', 'touchstart'].forEach(function (eventName) {
            field.addEventListener(eventName, unlockField, { once: true });
        });
    });
}


function initPasswordVisibilityToggle() {
    const buttons = document.querySelectorAll('[data-password-toggle]');

    buttons.forEach(function (button) {
        const targetId = button.getAttribute('data-password-target');
        const input = targetId ? document.getElementById(targetId) : null;
        const icon = button.querySelector('i');

        if (!input) {
            return;
        }

        button.addEventListener('click', function () {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            if (icon) {
                icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
            }
        });
    });
}

function initSelectPlaceholderState() {
    const selects = document.querySelectorAll('select');

    function getPlaceholderText(select) {
        const label = select.id ? document.querySelector('label[for="' + select.id + '"]') : null;
        const rawText = String(select.getAttribute('data-placeholder-label') || (label ? label.textContent : '') || 'opsi')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/:$/, '');
        return 'Pilih ' + rawText.toLowerCase();
    }

    function syncState(select) {
        select.classList.toggle('is-placeholder-state', !select.value);
    }

    selects.forEach(function (select) {
        if (select.multiple || select.disabled || select.dataset.skipPlaceholder === 'true') {
            return;
        }

        const placeholderText = getPlaceholderText(select);
        const firstOption = select.options[0];

        if (!firstOption || firstOption.value !== '') {
            const option = new Option(placeholderText, '');
            select.insertBefore(option, firstOption || null);
        } else if (select.dataset.preservePlaceholder !== 'true') {
            firstOption.textContent = placeholderText;
        }

        syncState(select);
        select.addEventListener('change', function () {
            syncState(select);
        });
    });
}


function initPenggunaCreateFormValidation() {
    const form = document.querySelector('[data-pengguna-create-form="true"]');

    if (!form) {
        return;
    }

    const fieldConfigs = [
        { id: 'id_username', message: 'Username wajib diisi.' },
        { id: 'id_nama_lengkap', message: 'Nama lengkap dan gelar wajib diisi.' },
        { id: 'id_email', message: 'Email wajib diisi.', type: 'email' },
        { id: 'id_nip', message: 'NIP / NIK wajib diisi.', digitsOnly: true, invalidMessage: 'NIP / NIK hanya boleh berisi angka.' },
        { id: 'id_no_hp', message: 'Nomor HP wajib diisi.', digitsOnly: true, invalidMessage: 'Nomor HP hanya boleh berisi angka.' },
        { id: 'id_password1', message: 'Kata sandi wajib diisi.' },
        { id: 'id_password2', message: 'Konfirmasi kata sandi wajib diisi.', matchTargetId: 'id_password1', matchMessage: 'Konfirmasi kata sandi tidak sama.' },
        { id: 'id_role', message: 'Peran wajib dipilih.' },
    ];

    function getGroup(element) {
        return element ? element.closest('.form-group') : null;
    }

    function normalizeMessage(text) {
        return String(text || '').replace(/^\*/, '').trim();
    }

    function clearMessages(group, clearableMessages, clearAllMessages) {
        if (!group) {
            return;
        }

        const normalizedMessages = (clearableMessages || []).map(function (message) {
            return normalizeMessage(message);
        });

        group.querySelectorAll('.input-error-text').forEach(function (node) {
            const message = normalizeMessage(node.textContent);
            if (
                clearAllMessages
                || node.dataset.clientError === 'true'
                || normalizedMessages.includes(message)
            ) {
                node.remove();
            }
        });

        if (!group.querySelector('.input-error-text')) {
            group.classList.remove('has-error');
        }
    }

    function showMessage(group, message, clearableMessages) {
        if (!group || !message) {
            return;
        }

        clearMessages(group, (clearableMessages || []).concat([message]));
        group.classList.add('has-error');

        const messageNode = document.createElement('p');
        messageNode.className = 'input-error-text';
        messageNode.dataset.clientError = 'true';
        messageNode.textContent = '*' + message;
        group.appendChild(messageNode);
    }

    function clearGroupWhenValid(group, clearableMessages) {
        if (!group) {
            return;
        }

        clearMessages(group, clearableMessages);
    }

    function validateField(config) {
        const input = document.getElementById(config.id);
        if (!input || input.disabled) {
            return true;
        }

        const group = getGroup(input);
        const value = String(input.value || '').trim();
        const matchTarget = config.matchTargetId ? document.getElementById(config.matchTargetId) : null;
        const clearableMessages = [config.message, 'Masukkan alamat email yang valid.', config.matchMessage || 'Data tidak sama.', config.invalidMessage || ''];

        clearMessages(group, clearableMessages, true);

        if (!value) {
            showMessage(group, config.message, clearableMessages);
            return false;
        }

        if (config.type === 'email' && input.validity && input.validity.typeMismatch) {
            showMessage(group, 'Masukkan alamat email yang valid.', clearableMessages);
            return false;
        }

        if (config.digitsOnly && /\D/.test(value)) {
            showMessage(group, config.invalidMessage || 'Input hanya boleh berisi angka.', clearableMessages);
            return false;
        }

        if (matchTarget && value !== String(matchTarget.value || '').trim()) {
            showMessage(group, config.matchMessage || 'Data tidak sama.', clearableMessages);
            return false;
        }

        clearGroupWhenValid(group, clearableMessages);
        return true;
    }

    fieldConfigs.forEach(function (config) {
        const input = document.getElementById(config.id);
        if (!input) {
            return;
        }

        const eventName = input.tagName === 'SELECT' ? 'change' : 'input';
        input.addEventListener(eventName, function () {
            validateField(config);

            if (config.matchTargetId) {
                const target = document.getElementById(config.matchTargetId);
                if (target) {
                    validateField(config);
                }
            }
        });

        if (config.id === 'id_password1') {
            input.addEventListener('input', function () {
                const confirmConfig = fieldConfigs.find(function (item) {
                    return item.id === 'id_password2';
                });
                if (confirmConfig) {
                    validateField(confirmConfig);
                }
            });
        }
    });

    form.addEventListener('submit', function (event) {
        let isValid = true;

        fieldConfigs.forEach(function (config) {
            if (!validateField(config)) {
                isValid = false;
            }
        });

        if (!isValid) {
            event.preventDefault();
            const firstError = form.querySelector('.form-group.has-error .input-error-text');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}


function initDigitsOnlyInputs() {
    const inputs = document.querySelectorAll('[data-digits-only="true"]');

    if (!inputs.length) {
        return;
    }

    const allowedKeys = [
        'Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight',
        'ArrowUp', 'ArrowDown', 'Home', 'End', 'Escape', 'Enter'
    ];

    inputs.forEach(function (input) {
        input.addEventListener('input', function () {
            const sanitizedValue = input.value.replace(/\D+/g, '');
            if (input.value !== sanitizedValue) {
                input.value = sanitizedValue;
            }
        });

        input.addEventListener('keydown', function (event) {
            const isShortcut = event.ctrlKey || event.metaKey;
            const isAllowedNumber = /^[0-9]$/.test(event.key);

            if (isShortcut || isAllowedNumber || allowedKeys.includes(event.key)) {
                return;
            }

            event.preventDefault();
        });

        input.addEventListener('paste', function (event) {
            const pastedText = (event.clipboardData || window.clipboardData).getData('text');
            if (/\D/.test(pastedText)) {
                event.preventDefault();
                const sanitizedValue = pastedText.replace(/\D+/g, '');
                const start = input.selectionStart || 0;
                const end = input.selectionEnd || 0;
                input.value = input.value.slice(0, start) + sanitizedValue + input.value.slice(end);
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    });
}

function bindDeleteModal(config) {
    const modal = document.getElementById(config.modalId);
    const modalBackdrop = document.getElementById(config.backdropId);
    const modalClose = document.getElementById(config.closeId);
    const modalCancel = document.getElementById(config.cancelId);
    const deleteForm = document.getElementById(config.formId);
    const primaryField = document.getElementById(config.primaryFieldId);
    const secondaryField = document.getElementById(config.secondaryFieldId);
    const buttonSelector = '.js-delete-btn[data-delete-modal="' + config.type + '"]';

    if (!modal || !deleteForm || !primaryField || !secondaryField) {
        return;
    }

    function openModal(button) {
        const deleteUrl = new URL(button.getAttribute('data-delete-url') || '', window.location.href);
        const returnUrl = button.getAttribute('data-return-url') || '';
        if (returnUrl) {
            deleteUrl.searchParams.set('next', returnUrl);
        }
        deleteForm.action = deleteUrl.toString();
        primaryField.textContent = button.getAttribute(config.primaryDataAttr) || '-';
        secondaryField.textContent = button.getAttribute(config.secondaryDataAttr) || '-';
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
    }

    function closeModal() {
        modal.classList.remove('show');
        document.body.classList.remove('is-scroll-locked');
        deleteForm.action = '';
        primaryField.textContent = '-';
        secondaryField.textContent = '-';
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest?.(buttonSelector);
        if (button) {
            openModal(button);
        }
    });

    [modalBackdrop, modalClose, modalCancel].forEach(function (element) {
        if (element) {
            element.addEventListener('click', closeModal);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });
}

/* ========================================
   HALAMAN PENGGUNA - MODAL HAPUS
   Menangani buka/tutup modal hapus pengguna.
======================================== */
function initDeleteUserModal() {
    bindDeleteModal({
        type: 'user',
        modalId: 'deleteModal',
        backdropId: 'deleteModalBackdrop',
        closeId: 'deleteModalClose',
        cancelId: 'deleteModalCancel',
        formId: 'deleteForm',
        primaryFieldId: 'deleteUserName',
        secondaryFieldId: 'deleteUsername',
        primaryDataAttr: 'data-user-name',
        secondaryDataAttr: 'data-username'
    });
}


/* ========================================
   HALAMAN MASTER DATA - MODAL HAPUS
   Menangani buka/tutup modal hapus pada data master.
======================================== */
function initMasterDataDeleteModal() {
    bindDeleteModal({
        type: 'master',
        modalId: 'masterDeleteModal',
        backdropId: 'masterDeleteModalBackdrop',
        closeId: 'masterDeleteModalClose',
        cancelId: 'masterDeleteModalCancel',
        formId: 'masterDeleteForm',
        primaryFieldId: 'masterDeleteItemName',
        secondaryFieldId: 'masterDeleteItemMeta',
        primaryDataAttr: 'data-item-name',
        secondaryDataAttr: 'data-item-meta'
    });
}

/* ========================================
   GLOBAL LIST STATE
   Memulihkan filter, urutan, dan posisi daftar setelah aksi data.
======================================== */
function initListNavigationState() {
    const listSelector = '.table-scroll--list, .notif-list-card';
    if (!document.querySelector(listSelector)) {
        return;
    }

    const storageKey = 'list-state:' + window.location.pathname;
    const currentUrl = window.location.pathname + window.location.search;
    let restoring = false;

    function readState() {
        try {
            return JSON.parse(sessionStorage.getItem(storageKey) || 'null');
        } catch (error) {
            sessionStorage.removeItem(storageKey);
            console.error('State daftar tidak dapat dibaca.', error);
            return null;
        }
    }

    function writeState(state) {
        try {
            sessionStorage.setItem(storageKey, JSON.stringify(state));
        } catch (error) {
            console.error('State daftar tidak dapat disimpan.', error);
        }
    }

    function getSortState() {
        return Array.from(document.querySelectorAll('.table-scroll--list .table-data')).flatMap(function (table, tableIndex) {
            const active = table.querySelector('.table-sort-button[data-sort-direction="asc"], .table-sort-button[data-sort-direction="desc"]');
            if (!active) {
                return [];
            }
            return [{
                table: tableIndex,
                column: Number(active.dataset.columnIndex || 0),
                direction: active.dataset.sortDirection,
            }];
        });
    }

    function getSearchState() {
        return Array.from(document.querySelectorAll('[data-local-list-search-input]')).map(function (input) {
            return input.value;
        });
    }

    function getLists() {
        return Array.from(document.querySelectorAll(listSelector));
    }

    function buildState(pending) {
        return {
            url: window.location.pathname + window.location.search,
            top: window.scrollY,
            left: getLists().map(function (list) { return list.scrollLeft; }),
            sort: getSortState(),
            search: getSearchState(),
            pending: Boolean(pending),
        };
    }

    function saveState(pending) {
        if (!restoring) {
            writeState(buildState(pending));
        }
    }

    function sameListPath(url) {
        try {
            return new URL(url, window.location.origin).pathname === window.location.pathname;
        } catch (error) {
            return false;
        }
    }

    function getNoticeMarkup() {
        return Array.from(document.querySelectorAll('.message-wrapper, [data-success-popup-stack]')).map(function (node) {
            return node.outerHTML;
        }).join('');
    }

    function restoreNotice(markup) {
        const content = document.querySelector('.app-content');
        if (!markup || !content || content.querySelector('.message-wrapper, [data-success-popup-stack]')) {
            return;
        }
        content.insertAdjacentHTML('afterbegin', markup);
        initSuccessPopups();
    }

    function restoreState(state) {
        restoring = true;
        restoreNotice(state.notice);
        (state.search || []).forEach(function (value, index) {
            const input = document.querySelectorAll('[data-local-list-search-input]')[index];
            if (input) {
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });

        const tables = document.querySelectorAll('.table-scroll--list .table-data');
        (state.sort || []).forEach(function (sort) {
            const table = tables[Number(sort.table)];
            const button = table?.querySelector('.table-sort-button[data-column-index="' + Number(sort.column) + '"]');
            if (!button) {
                return;
            }
            button.click();
            if (sort.direction === 'desc') {
                button.click();
            }
        });

        window.requestAnimationFrame(function () {
            window.requestAnimationFrame(function () {
                getLists().forEach(function (list, index) {
                    list.scrollLeft = Number((state.left || [])[index] || 0);
                });
                window.scrollTo(0, Number(state.top || 0));
                restoring = false;
                writeState(buildState(false));
            });
        });
    }

    const saved = readState();
    if (saved?.pending && saved.url && sameListPath(saved.url) && saved.url !== currentUrl) {
        saved.notice = getNoticeMarkup();
        writeState(saved);
        window.location.replace(saved.url);
        return;
    }

    if (saved?.pending && saved.url === currentUrl) {
        restoreState(saved);
    } else {
        writeState(buildState(false));
    }

    document.addEventListener('click', function (event) {
        const sortButton = event.target.closest?.('.table-sort-button');
        if (sortButton) {
            window.requestAnimationFrame(function () { saveState(false); });
            return;
        }

        const link = event.target.closest?.('a[href]');
        const linkLabel = String(link?.getAttribute('title') || link?.textContent || '').toLowerCase();
        if (
            !link
            || event.defaultPrevented
            || !link.closest(listSelector)
            || link.target === '_blank'
            || link.hasAttribute('download')
            || /unduh|download|export|pdf/.test(linkLabel)
            || event.button !== 0
            || event.ctrlKey
            || event.metaKey
            || event.shiftKey
            || event.altKey
        ) {
            return;
        }

        const target = new URL(link.href, window.location.href);
        if (target.origin === window.location.origin && target.pathname !== window.location.pathname) {
            saveState(true);
        }
    });

    document.addEventListener('submit', function (event) {
        const form = event.target;
        if (event.defaultPrevented || !(form instanceof HTMLFormElement)) {
            return;
        }
        const method = String(form.method || 'get').toLowerCase();
        const action = new URL(form.action || window.location.href, window.location.href);
        saveState(method !== 'get' || action.pathname !== window.location.pathname);
    });

    document.addEventListener('input', function (event) {
        if (event.target.matches?.('[data-local-list-search-input]')) {
            saveState(false);
        }
    });
}

/* ========================================
   HALAMAN NOTIFIKASI - MODAL HAPUS PENGUMUMAN
   Menangani buka/tutup modal hapus riwayat pengumuman.
======================================== */
function initAnnouncementDeleteModal() {
    bindDeleteModal({
        type: 'announcement',
        modalId: 'announcementDeleteModal',
        backdropId: 'announcementDeleteModalBackdrop',
        closeId: 'announcementDeleteModalClose',
        cancelId: 'announcementDeleteModalCancel',
        formId: 'announcementDeleteForm',
        primaryFieldId: 'announcementDeleteTitle',
        secondaryFieldId: 'announcementDeleteMeta',
        primaryDataAttr: 'data-announcement-title',
        secondaryDataAttr: 'data-announcement-meta'
    });
}



/* ========================================
   HALAMAN OPERASIONAL - MODAL HAPUS
   Menangani buka/tutup modal hapus pada data operasional.
======================================== */
function initOperasionalDeleteModal() {
    bindDeleteModal({
        type: 'operasional',
        modalId: 'operasionalDeleteModal',
        backdropId: 'operasionalDeleteModalBackdrop',
        closeId: 'operasionalDeleteModalClose',
        cancelId: 'operasionalDeleteModalCancel',
        formId: 'operasionalDeleteForm',
        primaryFieldId: 'operasionalDeleteItemName',
        secondaryFieldId: 'operasionalDeleteItemMeta',
        primaryDataAttr: 'data-item-name',
        secondaryDataAttr: 'data-item-meta'
    });
}

/* ========================================
   HALAMAN VERIFIKASI - MODAL TINDAK LANJUT
   Menangani aksi verifikasi, termasuk input catatan dan submit form.
======================================== */
function initVerificationActionModal() {
    const modal = document.getElementById('verificationNoteModal');
    const form = document.getElementById('verificationActionForm');
    const actionInput = document.getElementById('verificationActionInput');
    const modalTitle = document.getElementById('verificationNoteModalTitle');
    const noteLabel = document.getElementById('verificationNoteLabel');
    const noteInput = document.getElementById('verificationCatatanInput');
    const noteHelp = document.getElementById('verificationNoteHelp');
    const submitButton = document.getElementById('verificationModalSubmitButton');
    const closeButton = document.getElementById('verificationNoteModalClose');
    const cancelButton = document.getElementById('verificationNoteModalCancel');
    const backdrop = document.getElementById('verificationNoteModalBackdrop');
    const actionButtons = document.querySelectorAll('.js-verify-action[data-action]');

    if (!modal || !form || !actionInput || !actionButtons.length) {
        return;
    }

    const submitClassCandidates = ['btn-primary', 'btn-secondary', 'btn-warning', 'btn-danger', 'btn-success'];
    const noteGroup = noteInput ? noteInput.closest('.form-group') : null;

    function clearNoteErrors() {
        if (!noteGroup) {
            return;
        }

        noteGroup.classList.remove('has-error');
        noteGroup.querySelectorAll('.verify-note-error').forEach(function (errorNode) {
            errorNode.remove();
        });
    }

    function showNoteError(message) {
        if (!noteGroup || !message) {
            return;
        }

        clearNoteErrors();
        noteGroup.classList.add('has-error');

        const errorNode = document.createElement('p');
        errorNode.className = 'input-error-text verify-note-error';
        errorNode.textContent = message.startsWith('*') ? message : '*' + message;
        noteGroup.appendChild(errorNode);
    }

    function getRequiredNoteMessage() {
        const labelText = noteLabel ? String(noteLabel.textContent || '').replace(/:/g, '').trim() : 'Catatan';
        return `*${labelText || 'Catatan'} wajib diisi.`;
    }

    function setSubmitClass(className) {
        if (!submitButton) {
            return;
        }
        submitClassCandidates.forEach(function (candidate) {
            submitButton.classList.remove(candidate);
        });
        submitButton.classList.add(className || 'btn-primary');
    }

    function openModal() {
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
        if (noteInput) {
            window.setTimeout(function () {
                noteInput.focus();
                noteInput.setSelectionRange(noteInput.value.length, noteInput.value.length);
            }, 10);
        }
    }

    function closeModal() {
        modal.classList.remove('show');
        document.body.classList.remove('is-scroll-locked');
    }

    function applyAction(button) {
        const action = button.getAttribute('data-action') || '';
        const requiresNote = button.getAttribute('data-requires-note') === 'true';
        const title = button.getAttribute('data-modal-title') || 'Input Catatan';
        const submitLabel = button.getAttribute('data-submit-label') || 'Kirim';
        const label = button.getAttribute('data-note-label') || 'Catatan / Alasan';
        const placeholder = button.getAttribute('data-note-placeholder') || 'Tulis catatan verifikasi di sini.';
        const helpText = button.getAttribute('data-note-help') || '';
        const submitClass = button.getAttribute('data-submit-class') || 'btn-primary';

        actionInput.value = action;

        if (modalTitle) {
            modalTitle.textContent = title;
        }
        if (noteLabel) {
            noteLabel.textContent = label;
        }
        if (noteInput) {
            noteInput.placeholder = placeholder;
            noteInput.required = requiresNote;
        }
        clearNoteErrors();
        if (noteHelp) {
            noteHelp.textContent = helpText;
            noteHelp.hidden = !helpText;
        }
        if (submitButton) {
            submitButton.textContent = submitLabel;
        }

        setSubmitClass(submitClass);
    }

    actionButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            applyAction(button);
            openModal();
        });
    });

    [closeButton, cancelButton, backdrop].forEach(function (element) {
        if (!element) {
            return;
        }
        element.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });

    if (noteInput) {
        ['input', 'change'].forEach(function (eventName) {
            noteInput.addEventListener(eventName, function () {
                if (String(noteInput.value || '').trim()) {
                    clearNoteErrors();
                }
            });
        });
    }

    form.addEventListener('submit', function (event) {
        if (!noteInput || !noteInput.required) {
            return;
        }

        if (!String(noteInput.value || '').trim()) {
            event.preventDefault();
            showNoteError(getRequiredNoteMessage());
            noteInput.focus();
        }
    });

    if (modal.getAttribute('data-open-on-load') === 'true') {
        openModal();
    }
}

function initUploadPreviewControls() {
    const uploadControls = document.querySelectorAll('[data-upload-control]');

    if (!uploadControls.length) {
        return;
    }

    uploadControls.forEach(function (control) {
        const input = control.querySelector('input[type="file"]');
        const legacyPreviewCard = control.querySelector('[data-preview-card]');
        const legacyPreviewImage = control.querySelector('[data-preview-image]');
        const storedPreviewSection = control.querySelector('[data-stored-preview-section]');
        const storedPreviewCard = control.querySelector('[data-stored-preview-card]');
        const storedPreviewImage = control.querySelector('[data-stored-preview-image]');
        const selectedPreviewSection = control.querySelector('[data-selected-preview-section]');
        const selectedPreviewCard = control.querySelector('[data-selected-preview-card]');
        const selectedPreviewImage = control.querySelector('[data-selected-preview-image]');
        const fileState = control.querySelector('[data-file-state]');
        const fileStateText = control.querySelector('[data-file-state-text]');
        const fileStateAction = control.querySelector('[data-file-state-action]');
        const actionText = fileStateAction ? fileStateAction.querySelector('span') : null;
        const hiddenInputId = control.dataset.hiddenInputId;
        const hiddenInputName = (control.dataset.hiddenInputName || '').trim();
        const hiddenInput = (function resolveHiddenInput() {
            if (hiddenInputId) {
                const byId = document.getElementById(hiddenInputId);
                if (byId) {
                    return byId;
                }
            }

            const localHiddenInput = control.querySelector('input[type="hidden"]');
            if (localHiddenInput) {
                return localHiddenInput;
            }

            const parentForm = control.closest('form');
            if (parentForm && hiddenInputName) {
                return parentForm.querySelector('input[type="hidden"][name="' + hiddenInputName + '"]');
            }

            return null;
        }());
        const existingFileLinkWrap = control.querySelector('[data-existing-file-link-wrap]');
        const existingFileTitle = existingFileLinkWrap ? existingFileLinkWrap.querySelector('[data-existing-file-title]') : null;
        const existingLink = existingFileLinkWrap ? existingFileLinkWrap.querySelector('[data-existing-file-link]') : null;
        const existingPreviewUrl = legacyPreviewImage ? (legacyPreviewImage.getAttribute('src') || '').trim() : '';
        const existingStoredPreviewUrl = storedPreviewImage ? (storedPreviewImage.getAttribute('src') || '').trim() : '';
        const existingUrl = (control.dataset.existingUrl || existingStoredPreviewUrl || existingPreviewUrl || (existingLink && existingLink.getAttribute('href') ? existingLink.getAttribute('href') : '') || '').trim();
        const fileLabel = control.dataset.fileLabel || 'File';
        const replaceOnlyMode = (control.dataset.uploadMode || '').trim() === 'replace-only';
        const allowedExtensions = String(input.getAttribute('data-inline-file-extensions') || '')
            .split(',')
            .map(function (value) { return String(value || '').trim().toLowerCase(); })
            .filter(Boolean);
        const invalidMessage = String(input.getAttribute('data-inline-file-error') || 'Format file tidak didukung.').trim() || 'Format file tidak didukung.';
        const maxSize = Number.parseInt(input.getAttribute('data-inline-file-max-size') || '', 10);
        const maxSizeMessage = String(input.getAttribute('data-inline-file-max-size-error') || 'Ukuran file maksimal 7 MB.').trim() || 'Ukuran file maksimal 7 MB.';
        const formGroup = control.closest('.form-group') || control.closest('.upload-card') || control;
        let errorNode = null;
        const hasSplitImagePreview = Boolean(storedPreviewCard && storedPreviewImage && selectedPreviewCard && selectedPreviewImage);
        const hasLegacyImagePreview = Boolean(legacyPreviewCard && legacyPreviewImage);
        const hasAnyImagePreview = hasSplitImagePreview || hasLegacyImagePreview;

        if (!input || !fileState || !fileStateAction) {
            return;
        }

        function getOrCreateErrorNode() {
            if (errorNode && errorNode.isConnected) {
                return errorNode;
            }

            if (formGroup) {
                errorNode = formGroup.querySelector('[data-inline-file-error-node]');
                if (errorNode) {
                    return errorNode;
                }
            }

            errorNode = document.createElement('p');
            errorNode.className = 'input-error-text';
            errorNode.setAttribute('data-inline-file-error-node', 'true');
            errorNode.hidden = true;

            const anchor = control.querySelector('[data-inline-file-proxy]') || control;
            if (anchor && anchor.parentNode) {
                anchor.parentNode.insertBefore(errorNode, anchor.nextSibling);
            }

            return errorNode;
        }

        function syncErrorGroupState() {
            if (!formGroup) {
                return;
            }

            const hasVisibleError = Array.from(formGroup.querySelectorAll('.input-error-text')).some(function (node) {
                return !node.hidden && String(node.textContent || '').trim();
            });
            formGroup.classList.toggle('has-error', hasVisibleError);
        }

        function getPersistedFieldErrorNodes() {
            if (!formGroup) {
                return [];
            }

            return Array.from(formGroup.querySelectorAll('.input-error-text')).filter(function (node) {
                return !node.hasAttribute('data-inline-file-error-node');
            });
        }

        function hidePersistedFieldErrors() {
            getPersistedFieldErrorNodes().forEach(function (node) {
                node.hidden = true;
                node.style.display = 'none';
            });
        }

        function clearOnlyInlineError() {
            const node = getOrCreateErrorNode();
            if (node) {
                node.textContent = '';
                node.hidden = true;
                node.style.display = 'none';
            }
            syncErrorGroupState();
        }

        function clearInlineError() {
            clearOnlyInlineError();
            hidePersistedFieldErrors();
            syncErrorGroupState();
        }

        function showInlineError(message) {
            const node = getOrCreateErrorNode();
            hidePersistedFieldErrors();
            node.textContent = '*' + String(message || '').replace(/^\*/, '').trim();
            node.hidden = false;
            node.style.display = '';
            if (formGroup) {
                formGroup.classList.add('has-error');
            }
        }

        function queueInlineError(message) {
            window.setTimeout(function () {
                showInlineError(message);
            }, 0);
        }

        function setCardEmpty(card, image) {
            if (!card || !image) {
                return;
            }

            card.classList.add('is-empty');
            image.removeAttribute('src');
        }

        function setCardSource(card, image, src) {
            if (!card || !image) {
                return;
            }

            if (!src) {
                setCardEmpty(card, image);
                return;
            }

            card.classList.remove('is-empty');
            image.src = src;
        }

        function setSectionVisibility(section, visible) {
            if (!section) {
                return;
            }

            section.classList.toggle('is-hidden', !visible);
        }

        function setStoredPreview(src) {
            if (hasSplitImagePreview) {
                setSectionVisibility(storedPreviewSection, Boolean(src));
                setCardSource(storedPreviewCard, storedPreviewImage, src);
                return;
            }

            if (hasLegacyImagePreview) {
                setCardSource(legacyPreviewCard, legacyPreviewImage, src);
            }
        }

        function clearStoredPreview() {
            if (hasSplitImagePreview) {
                setCardEmpty(storedPreviewCard, storedPreviewImage);
                setSectionVisibility(storedPreviewSection, false);
                return;
            }

            if (hasLegacyImagePreview) {
                setCardEmpty(legacyPreviewCard, legacyPreviewImage);
            }
        }

        function setSelectedPreview(src) {
            if (hasSplitImagePreview) {
                setSectionVisibility(selectedPreviewSection, true);
                setCardSource(selectedPreviewCard, selectedPreviewImage, src);
                return;
            }

            if (hasLegacyImagePreview) {
                setCardSource(legacyPreviewCard, legacyPreviewImage, src);
            }
        }

        function clearSelectedPreview() {
            if (hasSplitImagePreview) {
                setSectionVisibility(selectedPreviewSection, true);
                setCardEmpty(selectedPreviewCard, selectedPreviewImage);
                return;
            }

            if (hasLegacyImagePreview) {
                setCardEmpty(legacyPreviewCard, legacyPreviewImage);
            }
        }

        function setExistingLinkVisibility(visible) {
            if (!existingFileLinkWrap) {
                return;
            }

            existingFileLinkWrap.classList.toggle('is-disabled', !visible);
            existingFileLinkWrap.classList.toggle('has-file', visible);

            if (existingFileTitle) {
                existingFileTitle.textContent = visible ? 'Dokumen IK Saat Ini' : 'Dokumen IK Belum Tersedia';
            }

            if (!existingLink) {
                return;
            }

            existingLink.classList.toggle('document-file-link--disabled', !visible);

            if (existingLink.tagName === 'A') {
                if (visible && existingUrl) {
                    existingLink.setAttribute('href', existingUrl);
                    existingLink.setAttribute('target', '_blank');
                    existingLink.setAttribute('rel', 'noopener');
                    existingLink.setAttribute('aria-disabled', 'false');
                    existingLink.removeAttribute('tabindex');
                } else {
                    existingLink.removeAttribute('href');
                    existingLink.removeAttribute('target');
                    existingLink.removeAttribute('rel');
                    existingLink.setAttribute('aria-disabled', 'true');
                    existingLink.setAttribute('tabindex', '-1');
                }
            }
        }

        function hideFileState() {
            fileState.classList.add('is-hidden');
            if (fileStateText) {
                fileStateText.textContent = '';
            }
            fileStateAction.dataset.mode = '';

            if (actionText) {
                actionText.textContent = replaceOnlyMode ? 'Batalkan Upload' : 'Hapus file';
            }
        }

        function showFileState(textValue, actionLabel, mode) {
            fileState.classList.remove('is-hidden');
            if (fileStateText) {
                fileStateText.textContent = textValue;
            }
            fileStateAction.dataset.mode = mode;

            if (actionText) {
                actionText.textContent = actionLabel;
            }
        }

        function applyIdleVisualState() {
            if (hiddenInput) {
                hiddenInput.value = '';
            }

            if (replaceOnlyMode && existingUrl) {
                setStoredPreview(existingUrl);
                setExistingLinkVisibility(true);
            } else if (existingUrl) {
                setStoredPreview(existingUrl);
                setExistingLinkVisibility(true);
            } else {
                clearStoredPreview();
                setExistingLinkVisibility(false);
            }

            clearSelectedPreview();
            hideFileState();
        }

        function showEmptyState() {
            clearOnlyInlineError();
            input.value = '';
            if (hiddenInput) {
                hiddenInput.value = '';
            }

            if (replaceOnlyMode && existingUrl) {
                setStoredPreview(existingUrl);
                setExistingLinkVisibility(true);
            } else {
                clearStoredPreview();
                setExistingLinkVisibility(false);
            }

            clearSelectedPreview();
            hideFileState();
        }

        function showStoredState(src) {
            clearOnlyInlineError();
            input.value = '';
            if (hiddenInput) {
                hiddenInput.value = '';
            }

            if (src) {
                setStoredPreview(src);
                clearSelectedPreview();
                setExistingLinkVisibility(true);

                if (replaceOnlyMode) {
                    hideFileState();
                    return;
                }

                showFileState(fileLabel + ' sudah tersimpan', 'Hapus file', 'delete-stored');
            } else {
                showEmptyState();
            }
        }

        function isAllowedFile(file) {
            if (!file || !allowedExtensions.length) {
                return true;
            }

            const fileName = String(file.name || '').trim().toLowerCase();
            if (!fileName || fileName.indexOf('.') === -1) {
                return false;
            }

            const extension = fileName.split('.').pop();
            return allowedExtensions.includes(extension);
        }

        function showSelectedState(file) {
            clearInlineError();
            if (hiddenInput) {
                hiddenInput.value = '';
            }

            if (existingUrl) {
                setStoredPreview(existingUrl);
                setExistingLinkVisibility(true);
            } else {
                clearStoredPreview();
                setExistingLinkVisibility(false);
            }

            if (hasAnyImagePreview && file && file.type && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function (loadEvent) {
                    setSelectedPreview(loadEvent.target.result);
                };
                reader.readAsDataURL(file);
            } else if (hasAnyImagePreview) {
                clearSelectedPreview();
            }

            const replacementText = existingUrl
                ? fileLabel + ' baru dipilih. File terpasang akan diganti otomatis saat data disimpan'
                : fileLabel + ' baru dipilih';
            showFileState(replacementText, replaceOnlyMode ? 'Batalkan Upload' : 'Batalkan', 'clear-selected');
        }

        function showMarkedDeleteState() {
            clearInlineError();
            if (replaceOnlyMode) {
                showStoredState(existingUrl);
                return;
            }

            input.value = '';
            if (hiddenInput) {
                hiddenInput.value = '1';
            }
            clearSelectedPreview();
            clearStoredPreview();
            setExistingLinkVisibility(false);
            showFileState(fileLabel + ' akan dihapus saat data disimpan', 'Batalkan hapus', 'restore-stored');
        }

        input.addEventListener('change', function (event) {
            const file = event.target.files && event.target.files[0];

            if (!file) {
                if (hiddenInput && hiddenInput.value === '1') {
                    showMarkedDeleteState();
                    return;
                }

                if (existingUrl) {
                    showStoredState(existingUrl);
                    return;
                }

                showEmptyState();
                return;
            }

            if (!isAllowedFile(file)) {
                input.value = '';
                input.dataset.inlineFileSkipValidationOnce = 'true';
                input.dataset.inlineFilePreserveError = 'true';
                applyIdleVisualState();
                queueInlineError(invalidMessage);
                return;
            }

            if (file && Number.isFinite(maxSize) && maxSize > 0 && Number(file.size || 0) > maxSize) {
                input.value = '';
                input.dataset.inlineFileSkipValidationOnce = 'true';
                input.dataset.inlineFilePreserveError = 'true';
                applyIdleVisualState();
                queueInlineError(maxSizeMessage);
                return;
            }

            showSelectedState(file);
        });

        fileStateAction.addEventListener('click', function () {
            const mode = fileStateAction.dataset.mode || '';

            if (mode === 'delete-stored') {
                showMarkedDeleteState();
                return;
            }

            if (mode === 'clear-selected') {
                input.value = '';
                if (existingUrl) {
                    showStoredState(existingUrl);
                } else {
                    showEmptyState();
                }
                return;
            }

            if (mode === 'restore-stored') {
                if (hiddenInput) {
                    hiddenInput.value = '';
                }
                showStoredState(existingUrl);
            }
        });

        function validateRequiredFileSelection() {
            const requiredMessage = String(input.getAttribute('data-inline-file-required-message') || 'Kolom ini wajib diisi.').trim() || 'Kolom ini wajib diisi.';
            const hasSelectedFile = Boolean(input.files && input.files[0]);
            const hasExistingFile = Boolean(existingUrl) && !(hiddenInput && hiddenInput.value === '1');

            if (input.required && !hasSelectedFile && !hasExistingFile) {
                showInlineError(requiredMessage);
                return false;
            }

            if (hasSelectedFile || hasExistingFile) {
                clearInlineError();
            }

            return true;
        }

        const parentForm = control.closest('form');
        if (parentForm) {
            parentForm.addEventListener('submit', function (event) {
                if (!validateRequiredFileSelection()) {
                    event.preventDefault();
                    control.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        }

        if (hiddenInput && hiddenInput.value === '1') {
            if (replaceOnlyMode) {
                hiddenInput.value = '';
            } else {
                showMarkedDeleteState();
                return;
            }
        }

        if (existingUrl) {
            showStoredState(existingUrl);
            return;
        }

        showEmptyState();
    });
}


function initInlineFileProxyControls() {
    const controls = document.querySelectorAll('[data-inline-file-proxy]');

    if (!controls.length) {
        return;
    }

    controls.forEach(function (control) {
        const input = control.querySelector('[data-inline-file-input]');
        const textNode = control.querySelector('[data-inline-file-text]');
        const stateNode = control.querySelector('[data-inline-file-state]');
        const clearButton = control.querySelector('[data-inline-file-clear]');

        if (!input || !textNode) {
            return;
        }

        const placeholder = String(input.getAttribute('data-inline-file-placeholder') || 'Pilih file').trim() || 'Pilih file';
        const initialText = String(textNode.textContent || '').trim();
        const allowedExtensions = String(input.getAttribute('data-inline-file-extensions') || '').split(',').map(function (value) {
            return String(value || '').trim().toLowerCase();
        }).filter(Boolean);
        const invalidMessage = String(input.getAttribute('data-inline-file-error') || 'Format file tidak didukung.').trim() || 'Format file tidak didukung.';
        const maxSize = Number.parseInt(input.getAttribute('data-inline-file-max-size') || '', 10);
        const maxSizeMessage = String(input.getAttribute('data-inline-file-max-size-error') || 'Ukuran file maksimal 7 MB.').trim() || 'Ukuran file maksimal 7 MB.';
        const formGroup = control.closest('.form-group') || control.closest('.upload-card');
        let errorNode = null;

        function getOrCreateErrorNode() {
            if (errorNode && errorNode.isConnected) {
                return errorNode;
            }

            if (formGroup) {
                errorNode = formGroup.querySelector('[data-inline-file-error-node]');
                if (errorNode) {
                    return errorNode;
                }
            }

            errorNode = document.createElement('p');
            errorNode.className = 'input-error-text';
            errorNode.setAttribute('data-inline-file-error-node', 'true');
            errorNode.hidden = true;

            if (control.parentNode) {
                control.parentNode.insertBefore(errorNode, control.nextSibling);
            } else {
                const anchor = stateNode || control;
                if (anchor && anchor.parentNode) {
                    anchor.parentNode.insertBefore(errorNode, anchor.nextSibling);
                }
            }

            return errorNode;
        }

        function syncErrorGroupState() {
            if (!formGroup) {
                return;
            }

            const hasVisibleError = Array.from(formGroup.querySelectorAll('.input-error-text')).some(function (node) {
                return !node.hidden && String(node.textContent || '').trim();
            });
            formGroup.classList.toggle('has-error', hasVisibleError);
        }

        function getPersistedFieldErrorNodes() {
            if (!formGroup) {
                return [];
            }

            return Array.from(formGroup.querySelectorAll('.input-error-text')).filter(function (node) {
                return !node.hasAttribute('data-inline-file-error-node');
            });
        }

        function hidePersistedFieldErrors() {
            getPersistedFieldErrorNodes().forEach(function (node) {
                node.hidden = true;
                node.style.display = 'none';
            });
        }

        function clearOnlyInlineError() {
            const node = getOrCreateErrorNode();
            if (node) {
                node.textContent = '';
                node.hidden = true;
                node.style.display = 'none';
            }
            syncErrorGroupState();
        }

        function clearInlineError() {
            clearOnlyInlineError();
            hidePersistedFieldErrors();
            syncErrorGroupState();
        }

        function showInlineError(message) {
            const node = getOrCreateErrorNode();
            hidePersistedFieldErrors();
            node.textContent = '*' + String(message || '').replace(/^\*/, '').trim();
            node.hidden = false;
            node.style.display = '';
            if (formGroup) {
                formGroup.classList.add('has-error');
            }
        }

        function queueInlineError(message) {
            window.setTimeout(function () {
                showInlineError(message);
            }, 0);
        }

        function updateText() {
            const file = input.files && input.files[0] ? input.files[0].name : '';
            const nextText = file || initialText || placeholder;
            textNode.textContent = nextText;
            const normalizedPlaceholder = String(placeholder || '').trim();
            const normalizedText = String(nextText || '').trim();
            textNode.classList.toggle('is-placeholder', !file && normalizedText === normalizedPlaceholder);

            if (stateNode) {
                stateNode.classList.toggle('is-hidden', !file);
            }
        }

        function isAllowedFile(fileName) {
            if (!allowedExtensions.length) {
                return true;
            }

            const normalizedName = String(fileName || '').trim().toLowerCase();
            if (!normalizedName || normalizedName.indexOf('.') === -1) {
                return false;
            }

            const extension = normalizedName.split('.').pop();
            return allowedExtensions.includes(extension);
        }

        if (clearButton) {
            clearButton.addEventListener('click', function () {
                clearInlineError();
                input.value = '';
                updateText();
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        function handleRealtimeFileValidation() {
            const selectedFile = input.files && input.files[0] ? input.files[0] : null;
            const fileName = selectedFile ? selectedFile.name : '';

            if (!selectedFile) {
                clearInlineError();
                updateText();
                return;
            }

            if (fileName && !isAllowedFile(fileName)) {
                input.value = '';
                updateText();
                queueInlineError(invalidMessage);
                return;
            }

            if (selectedFile && Number.isFinite(maxSize) && maxSize > 0 && Number(selectedFile.size || 0) > maxSize) {
                input.value = '';
                updateText();
                queueInlineError(maxSizeMessage);
                return;
            }

            clearInlineError();
            updateText();
        }

        input.addEventListener('change', function () {
            if (input.dataset.inlineFileSkipValidationOnce === 'true') {
                const preserveError = input.dataset.inlineFilePreserveError === 'true';
                delete input.dataset.inlineFileSkipValidationOnce;
                delete input.dataset.inlineFilePreserveError;
                updateText();
                if (!preserveError) {
                    clearInlineError();
                }
                return;
            }

            handleRealtimeFileValidation();
        });

        const parentForm = control.closest('form');
        if (parentForm) {
            parentForm.addEventListener('submit', function (event) {
                const requiredMessage = String(input.getAttribute('data-inline-file-required-message') || 'Kolom ini wajib diisi.').trim() || 'Kolom ini wajib diisi.';
                const hasSelectedFile = Boolean(input.files && input.files[0]);
                const existingUploadControl = control.closest('[data-upload-control]');
                const existingUrl = existingUploadControl ? String(existingUploadControl.getAttribute('data-existing-url') || '').trim() : '';
                const hasExistingFile = Boolean(existingUrl);

                if (input.required && !hasSelectedFile && !hasExistingFile) {
                    showInlineError(requiredMessage);
                    event.preventDefault();
                    if (formGroup) {
                        formGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    return;
                }

                if (hasSelectedFile || hasExistingFile) {
                    clearInlineError();
                }
            });
        }

        updateText();
    });
}


function initInlineImageSourceButtons() {
    const openButtons = document.querySelectorAll('[data-file-source-open]');
    const buttons = document.querySelectorAll('[data-file-source-select]');
    const modals = document.querySelectorAll('[data-file-source-modal]');

    if (!openButtons.length && !buttons.length && !modals.length) {
        return;
    }

    function closeModal(modal) {
        if (!modal) {
            return;
        }

        modal.classList.remove('show');
        document.body.classList.remove('is-scroll-locked');
    }

    function openModal(modal) {
        if (!modal) {
            return;
        }

        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
        window.setTimeout(function () {
            const firstButton = modal.querySelector('[data-file-source-select]');
            if (firstButton) {
                firstButton.focus();
            }
        }, 10);
    }

    openButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            if (button.disabled) {
                return;
            }

            const modalId = button.getAttribute('data-file-source-open');
            openModal(modalId ? document.getElementById(modalId) : null);
        });
    });

    modals.forEach(function (modal) {
        modal.querySelectorAll('[data-file-source-close]').forEach(function (element) {
            element.addEventListener('click', function () {
                closeModal(modal);
            });
        });
    });

    buttons.forEach(function (button) {
        button.addEventListener('click', function () {
            if (button.disabled) {
                return;
            }

            const targetId = button.getAttribute('data-file-source-target');
            const input = targetId ? document.getElementById(targetId) : null;

            if (!input || input.disabled) {
                return;
            }

            if (button.getAttribute('data-file-source-select') === 'camera') {
                input.setAttribute('capture', 'environment');
            } else {
                input.removeAttribute('capture');
            }

            closeModal(button.closest('[data-file-source-modal]'));
            input.click();
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }

        modals.forEach(function (modal) {
            if (modal.classList.contains('show')) {
                closeModal(modal);
            }
        });
    });
}




/* ========================================
   HALAMAN DATA PELATIHAN
   Menangani lock field berdasarkan Tipe Pelatihan,
   validasi realtime, dan date-picker dengan style global.
======================================== */
function initPelatihanFormBehavior() {
    const form = document.querySelector('[data-pelatihan-form="true"]');
    if (!form) {
        return;
    }

    const typeField = form.querySelector('[data-training-type-field="true"]');
    const dependentGroups = form.querySelectorAll('[data-training-dependent-group="true"]');
    const startDateInput = form.querySelector('[data-training-start-date="true"]');
    const endDateInput = form.querySelector('[data-training-end-date="true"]');
    const dateInputs = form.querySelectorAll('[data-training-date-picker="true"]');
    const monthNamesLongId = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
    const monthNamesShortId = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const dayNamesShortId = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
    const monthLookup = {
        jan: 0, januari: 0, january: 0,
        feb: 1, februari: 1, february: 1,
        mar: 2, maret: 2, march: 2,
        apr: 3, april: 3,
        mei: 4, may: 4,
        jun: 5, juni: 5, june: 5,
        jul: 6, juli: 6, july: 6,
        agu: 7, agustus: 7, aug: 7, august: 7,
        sep: 8, sept: 8, september: 8,
        okt: 9, oktober: 9, oct: 9, october: 9,
        nov: 10, november: 10,
        des: 11, desember: 11, dec: 11, december: 11,
    };

    const dependentFields = [];
    dependentGroups.forEach(function (group) {
        group.querySelectorAll('input, select, textarea, button').forEach(function (field) {
            if (field.type === 'hidden') {
                return;
            }
            if (!dependentFields.includes(field)) {
                dependentFields.push(field);
            }
        });
    });

    function getFormGroup(element) {
        return element ? element.closest('.form-group') : null;
    }

    function clearGroupErrors(group) {
        if (!group) {
            return;
        }
        group.classList.remove('has-error');
        group.querySelectorAll('.input-error-text').forEach(function (errorNode) {
            if (!errorNode.hasAttribute('data-inline-file-error-node')) {
                errorNode.remove();
            } else {
                errorNode.hidden = true;
                errorNode.textContent = '';
            }
        });
    }

    function addGroupError(group, message) {
        if (!group || !message) {
            return;
        }
        clearGroupErrors(group);
        group.classList.add('has-error');
        const errorNode = document.createElement('p');
        errorNode.className = 'input-error-text';
        errorNode.textContent = String(message).trim().startsWith('*') ? String(message).trim() : `*${String(message).trim()}`;
        group.appendChild(errorNode);
    }

    function setFieldDisabledState(field, disabled) {
        if (!field) {
            return;
        }
        field.disabled = disabled;
        if (disabled) {
            field.setAttribute('aria-disabled', 'true');
        } else {
            field.removeAttribute('aria-disabled');
        }
    }

    function hasTypeValue() {
        return Boolean(typeField && String(typeField.value || '').trim());
    }

    function syncDependentLock() {
        const unlocked = hasTypeValue();
        dependentGroups.forEach(function (group) {
            group.classList.toggle('is-locked', !unlocked);
            group.setAttribute('aria-disabled', unlocked ? 'false' : 'true');
        });
        dependentFields.forEach(function (field) {
            setFieldDisabledState(field, !unlocked);
        });
        setFieldDisabledState(typeField, false);
    }

    function createDateAtMidday(year, monthIndex, day) {
        const date = new Date(year, monthIndex, day, 12, 0, 0, 0);
        if (
            Number.isNaN(date.getTime()) ||
            date.getFullYear() !== year ||
            date.getMonth() !== monthIndex ||
            date.getDate() !== day
        ) {
            return null;
        }
        return date;
    }

    function parseDisplayDate(value) {
        const rawValue = String(value || '').trim();
        if (!rawValue) {
            return null;
        }

        let match = rawValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
        if (match) {
            return createDateAtMidday(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        }

        match = rawValue.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
        if (match) {
            return createDateAtMidday(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
        }

        match = rawValue.match(/^(\d{1,2})\s+([A-Za-zÀ-ÿ.]+)\s+(\d{4})$/);
        if (match) {
            const monthKey = String(match[2] || '').toLowerCase().replace(/\.$/, '');
            const monthIndex = monthLookup[monthKey];
            if (monthIndex === undefined) {
                return null;
            }
            return createDateAtMidday(Number(match[3]), monthIndex, Number(match[1]));
        }

        return null;
    }

    function formatDateForInput(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = monthNamesShortId[date.getMonth()] || String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day} ${month} ${year}`;
    }

    function formatDateForCalendarLabel(year, monthIndex) {
        return `${monthNamesLongId[monthIndex]} ${year}`;
    }

    function dateOnlyKey(date) {
        return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
    }

    function setInputDateValue(input, date) {
        if (!input || !date) {
            return;
        }
        input.value = formatDateForInput(date);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function getMinimumDateForInput(input) {
        if (!input || input !== endDateInput || !startDateInput) {
            return null;
        }
        return parseDisplayDate(startDateInput.value);
    }

    function setupDatePicker(input) {
        if (!input || input.dataset.datePickerReady === 'true') {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'date-picker-control';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'date-picker-toggle';
        toggleButton.setAttribute('aria-label', `Pilih ${input.getAttribute('placeholder') || 'tanggal'}`);
        toggleButton.innerHTML = '<i class="bi bi-calendar3"></i>';
        wrapper.appendChild(toggleButton);

        const popup = document.createElement('div');
        popup.className = 'date-picker-popup date-picker-popup--training';
        popup.hidden = true;
        popup.innerHTML = `
            <div class="date-picker-header">
                <button type="button" class="date-picker-nav" data-calendar-nav="prev" aria-label="Bulan sebelumnya">&lsaquo;</button>
                <div class="date-picker-title" data-calendar-title="true"></div>
                <button type="button" class="date-picker-nav" data-calendar-nav="next" aria-label="Bulan berikutnya">&rsaquo;</button>
            </div>
            <div class="date-picker-weekdays" data-calendar-weekdays="true"></div>
            <div class="date-picker-grid" data-calendar-grid="true"></div>
            <div class="date-picker-footer">
                <button type="button" class="date-picker-footer-btn" data-calendar-action="today">Hari ini</button>
                <button type="button" class="date-picker-footer-btn" data-calendar-action="clear">Kosongkan</button>
            </div>
        `;
        wrapper.appendChild(popup);

        const title = popup.querySelector('[data-calendar-title="true"]');
        const weekdays = popup.querySelector('[data-calendar-weekdays="true"]');
        const grid = popup.querySelector('[data-calendar-grid="true"]');
        const prevButton = popup.querySelector('[data-calendar-nav="prev"]');
        const nextButton = popup.querySelector('[data-calendar-nav="next"]');
        const todayButton = popup.querySelector('[data-calendar-action="today"]');
        const clearButton = popup.querySelector('[data-calendar-action="clear"]');
        const initialDate = parseDisplayDate(input.value) || new Date();
        const state = { year: initialDate.getFullYear(), month: initialDate.getMonth() };

        weekdays.innerHTML = dayNamesShortId.map(function (dayName) {
            return `<span class="date-picker-weekday">${dayName}</span>`;
        }).join('');

        function renderCalendar() {
            grid.innerHTML = '';
            title.textContent = formatDateForCalendarLabel(state.year, state.month);

            const firstDay = new Date(state.year, state.month, 1, 12, 0, 0, 0);
            const startOffset = firstDay.getDay();
            const daysInMonth = new Date(state.year, state.month + 1, 0, 12, 0, 0, 0).getDate();
            const selectedDate = parseDisplayDate(input.value);
            const minimumDate = getMinimumDateForInput(input);
            const today = new Date();
            const todayKey = dateOnlyKey(today);

            for (let index = 0; index < 42; index += 1) {
                const dayButton = document.createElement('button');
                dayButton.type = 'button';
                dayButton.className = 'date-picker-day';

                const dayNumber = index - startOffset + 1;
                if (dayNumber < 1 || dayNumber > daysInMonth) {
                    dayButton.classList.add('is-empty');
                    dayButton.tabIndex = -1;
                    dayButton.disabled = true;
                    grid.appendChild(dayButton);
                    continue;
                }

                const candidate = createDateAtMidday(state.year, state.month, dayNumber);
                if (!candidate) {
                    continue;
                }

                dayButton.textContent = String(dayNumber);
                if (selectedDate && dateOnlyKey(candidate) === dateOnlyKey(selectedDate)) {
                    dayButton.classList.add('is-selected');
                }
                if (dateOnlyKey(candidate) === todayKey) {
                    dayButton.classList.add('is-today');
                }
                if (minimumDate && candidate.getTime() < minimumDate.getTime()) {
                    dayButton.disabled = true;
                    dayButton.classList.add('is-disabled');
                    dayButton.setAttribute('aria-disabled', 'true');
                    grid.appendChild(dayButton);
                    continue;
                }

                dayButton.addEventListener('click', function () {
                    setInputDateValue(input, candidate);
                    closePopup();
                    input.focus();
                });
                grid.appendChild(dayButton);
            }
        }

        function adjustPopupPosition() {
            popup.style.left = '0';
            popup.style.right = 'auto';
            const viewportPadding = 12;
            const rect = popup.getBoundingClientRect();
            const wrapperRect = wrapper.getBoundingClientRect();

            if (rect.right > window.innerWidth - viewportPadding) {
                const overflowRight = rect.right - (window.innerWidth - viewportPadding);
                popup.style.left = `${Math.min(0, -overflowRight)}px`;
            }

            const updatedRect = popup.getBoundingClientRect();
            if (updatedRect.left < viewportPadding) {
                popup.style.left = `${viewportPadding - wrapperRect.left}px`;
            }
        }

        function openPopup() {
            if (input.disabled) {
                return;
            }
            const selectedDate = parseDisplayDate(input.value);
            const baseDate = selectedDate || new Date();
            state.year = baseDate.getFullYear();
            state.month = baseDate.getMonth();
            renderCalendar();
            popup.hidden = false;
            wrapper.classList.add('is-open');
            adjustPopupPosition();
            window.setTimeout(adjustPopupPosition, 0);
        }

        function closePopup() {
            popup.hidden = true;
            wrapper.classList.remove('is-open');
            popup.style.left = '';
            popup.style.right = '';
        }

        toggleButton.addEventListener('click', function (event) {
            event.preventDefault();
            if (input.disabled) {
                return;
            }
            if (popup.hidden) {
                openPopup();
                return;
            }
            closePopup();
        });

        prevButton.addEventListener('click', function () {
            state.month = state.month === 0 ? 11 : state.month - 1;
            state.year = state.month === 11 ? state.year - 1 : state.year;
            renderCalendar();
        });

        nextButton.addEventListener('click', function () {
            state.month = state.month === 11 ? 0 : state.month + 1;
            state.year = state.month === 0 ? state.year + 1 : state.year;
            renderCalendar();
        });

        todayButton.addEventListener('click', function () {
            setInputDateValue(input, new Date());
            closePopup();
            input.focus();
        });

        clearButton.addEventListener('click', function () {
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
            input.focus();
        });

        input.addEventListener('input', renderCalendar);
        document.addEventListener('click', function (event) {
            if (!wrapper.contains(event.target)) {
                closePopup();
            }
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !popup.hidden) {
                closePopup();
            }
        });

        input.dataset.datePickerReady = 'true';
    }

    function validateRequiredField(field, message) {
        if (!field || field.disabled) {
            return true;
        }
        const hasValue = field.type === 'file'
            ? Boolean(field.files && field.files.length)
            : Boolean(String(field.value || '').trim());
        if (!hasValue) {
            addGroupError(getFormGroup(field), message);
            return false;
        }
        clearGroupErrors(getFormGroup(field));
        return true;
    }

    function validateDateRange() {
        if (!startDateInput || !endDateInput || startDateInput.disabled || endDateInput.disabled) {
            return true;
        }
        const startRawValue = String(startDateInput.value || '').trim();
        const endRawValue = String(endDateInput.value || '').trim();
        if (!startRawValue || !endRawValue) {
            return true;
        }

        const startDate = parseDisplayDate(startRawValue);
        const endDate = parseDisplayDate(endRawValue);
        if (startRawValue && !startDate) {
            addGroupError(getFormGroup(startDateInput), 'Format mulai tanggal tidak valid.');
            return false;
        }
        if (endRawValue && !endDate) {
            addGroupError(getFormGroup(endDateInput), 'Format selesai tanggal tidak valid.');
            return false;
        }
        if (startDate && endDate && endDate < startDate) {
            addGroupError(getFormGroup(endDateInput), 'Selesai tanggal tidak boleh lebih awal dari mulai tanggal.');
            return false;
        }

        clearGroupErrors(getFormGroup(startDateInput));
        clearGroupErrors(getFormGroup(endDateInput));
        return true;
    }

    function validateTrainingForm() {
        let isValid = true;
        if (!validateRequiredField(typeField, 'Tipe pelatihan wajib dipilih.')) {
            isValid = false;
        }
        if (!hasTypeValue()) {
            return isValid;
        }

        [
            [form.querySelector('#id_jenis_pelatihan'), 'Jenis pelatihan wajib dipilih.'],
            [form.querySelector('#id_nama_pelatihan'), 'Nama pelatihan wajib diisi.'],
            [startDateInput, 'Mulai tanggal pelatihan wajib diisi.'],
            [endDateInput, 'Selesai tanggal pelatihan wajib diisi.'],
            [form.querySelector('#id_lokasi_pelatihan'), 'Lokasi pelatihan wajib diisi.'],
            [form.querySelector('#id_uraian_pelatihan'), 'Uraian pelatihan wajib diisi.'],
        ].forEach(function (item) {
            if (!validateRequiredField(item[0], item[1])) {
                isValid = false;
            }
        });

        if (!validateDateRange()) {
            isValid = false;
        }
        return isValid;
    }

    dateInputs.forEach(setupDatePicker);
    syncDependentLock();

    if (typeField) {
        typeField.addEventListener('change', function () {
            clearGroupErrors(getFormGroup(typeField));
            syncDependentLock();
        });
    }

    form.querySelectorAll('input, select, textarea').forEach(function (field) {
        field.addEventListener('input', function () {
            if (field.value || field.files?.length) {
                clearGroupErrors(getFormGroup(field));
            }
            validateDateRange();
        });
        field.addEventListener('change', function () {
            if (field.value || field.files?.length) {
                clearGroupErrors(getFormGroup(field));
            }
            validateDateRange();
        });
    });

    form.addEventListener('submit', function (event) {
        syncDependentLock();
        if (!validateTrainingForm()) {
            event.preventDefault();
            const firstError = form.querySelector('.form-group.has-error .input-error-text');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}


/* ========================================
   HALAMAN MASTER DATA
   Menangani aturan dinamis untuk form master data.
======================================== */
function initMasterDataFormBehavior() {
    const form = document.querySelector('.master-data-form');
    const statusField = form ? form.querySelector('[data-status-field="true"]') : document.querySelector('[data-status-field="true"]');
    const bervolumeFields = Array.from(form ? form.querySelectorAll('[data-bervolume-field="true"]') : document.querySelectorAll('[data-bervolume-field="true"]'));
    const bervolumeWrapper = form ? form.querySelector('[data-bervolume-wrapper="true"]') : document.querySelector('[data-bervolume-wrapper="true"]');
    const bmnCodeField = form ? form.querySelector('[data-bmn-code-field="true"]') : document.querySelector('[data-bmn-code-field="true"]');
    const bmnCodeWrapper = form ? form.querySelector('[data-bmn-code-wrapper="true"]') : document.querySelector('[data-bmn-code-wrapper="true"]');
    const kondisiField = form ? form.querySelector('#id_kondisi_barang') : document.getElementById('id_kondisi_barang');
    const volumeField = form ? form.querySelector('#id_volume') : document.getElementById('id_volume');
    const volumeRusakField = form ? form.querySelector('#id_volume_rusak') : document.getElementById('id_volume_rusak');
    const totalVolumeField = form ? form.querySelector('#id_total_volume_info') : document.getElementById('id_total_volume_info');
    const stokMinimumField = form ? form.querySelector('#id_stok_minimum') : document.getElementById('id_stok_minimum');
    const ketersediaanField = form ? form.querySelector('#id_ketersediaan_info') : document.getElementById('id_ketersediaan_info');
    const statusDependentGroups = form ? form.querySelectorAll('[data-status-dependent-group="true"]') : document.querySelectorAll('[data-status-dependent-group="true"]');

    if (!statusField && !kondisiField && !volumeField && !stokMinimumField) {
        return;
    }

    const alwaysDisabledFieldIds = new Set([
        'id_total_volume_info',
        'id_ketersediaan_info',
        'id_tanggal_pemeliharaan_info',
        'id_tanggal_perbaikan_info'
    ]);

    function getDependentFields() {
        const fields = [];

        statusDependentGroups.forEach(function (group) {
            const interactiveFields = group.querySelectorAll('input, select, textarea, button');

            interactiveFields.forEach(function (field) {
                if (field.type === 'hidden') {
                    return;
                }

                if (!fields.includes(field)) {
                    fields.push(field);
                }
            });
        });

        return fields;
    }

    function hasStatusValue() {
        return Boolean(statusField && (statusField.value || '').trim());
    }

    function isBmnStatus() {
        return Boolean(statusField && (statusField.value || '').trim() === 'BMN');
    }

    function isNonBmnStatus() {
        return Boolean(statusField && (statusField.value || '').trim() === 'Non BMN');
    }

    function getVolumeChoice() {
        const selected = bervolumeFields.find(function (field) {
            return field.checked;
        });
        return selected ? selected.value : '';
    }

    function hasVolumeChoice() {
        return Boolean(getVolumeChoice());
    }

    function usesManualVolume() {
        return isNonBmnStatus() && getVolumeChoice() === 'true';
    }

    function usesAutoVolume() {
        return isBmnStatus() || (isNonBmnStatus() && getVolumeChoice() === 'false');
    }

    function isInputReady() {
        return hasStatusValue() && (!isNonBmnStatus() || !bervolumeFields.length || hasVolumeChoice());
    }

    function setFieldDisabledState(field, disabled) {
        if (!field) {
            return;
        }

        const locked = field.getAttribute('data-transaction-locked') === 'true';
        const shouldDisable = disabled || locked;
        field.disabled = shouldDisable;
        if (shouldDisable) {
            field.setAttribute('aria-disabled', 'true');
        } else {
            field.removeAttribute('aria-disabled');
        }
    }

    function syncDependentFieldLock() {
        if (!statusField || !statusDependentGroups.length) {
            return;
        }

        const unlocked = isInputReady();

        statusDependentGroups.forEach(function (group) {
            group.classList.toggle('is-locked', !unlocked);
            group.setAttribute('aria-disabled', unlocked ? 'false' : 'true');
        });

        getDependentFields().forEach(function (field) {
            const shouldStayDisabled = alwaysDisabledFieldIds.has(field.id) || field.getAttribute('data-volume-locked') === 'true';
            setFieldDisabledState(field, !unlocked || shouldStayDisabled);
        });

        setFieldDisabledState(statusField, false);
    }

    function syncBmnFieldVisibility() {
        if (!bmnCodeField || !bmnCodeWrapper) {
            return;
        }

        const unlocked = isInputReady();
        const isBMN = isBmnStatus();

        bmnCodeWrapper.classList.toggle('is-hidden', !isBMN);
        bmnCodeWrapper.setAttribute('aria-hidden', isBMN ? 'false' : 'true');

        if (isBMN) {
            bmnCodeField.required = true;
            bmnCodeField.setAttribute('required', 'required');
            setFieldDisabledState(bmnCodeField, !unlocked);
            return;
        }

        bmnCodeField.value = '';
        bmnCodeField.required = false;
        bmnCodeField.removeAttribute('required');
        setFieldDisabledState(bmnCodeField, true);
    }

    function syncStatusSpecificAssetFields() {
        const isUnlocked = isInputReady();
        const isNonBmn = isNonBmnStatus();
        const isManual = usesManualVolume();
        const autoVolumeFields = form ? form.querySelectorAll('[data-auto-volume-only="true"]') : document.querySelectorAll('[data-auto-volume-only="true"]');
        const metadataFields = form ? form.querySelectorAll('[data-volume-metadata="true"]') : document.querySelectorAll('[data-volume-metadata="true"]');

        if (bervolumeWrapper && bervolumeFields.length) {
            bervolumeWrapper.classList.toggle('is-hidden', !isNonBmn);
            bervolumeWrapper.setAttribute('aria-hidden', isNonBmn ? 'false' : 'true');
            bervolumeFields.forEach(function (field) {
                setFieldDisabledState(field, !hasStatusValue() || !isNonBmn);
            });
            if (!isNonBmn) {
                bervolumeFields.forEach(function (field) {
                    field.checked = false;
                });
            }
        }

        autoVolumeFields.forEach(function (field) {
            const wrapper = field.closest('.form-group');
            const showField = usesAutoVolume();

            if (wrapper) {
                wrapper.classList.toggle('is-hidden', !showField);
                wrapper.setAttribute('aria-hidden', showField ? 'false' : 'true');
            }

            setFieldDisabledState(field, !isUnlocked || !showField);
            if (showField) {
                field.setAttribute('required', 'required');
                field.required = true;
            } else {
                field.removeAttribute('required');
                field.required = false;
            }
        });

        metadataFields.forEach(function (field) {
            const wrapper = field.closest('[data-field-wrapper]') || field.closest('.form-group');
            if (wrapper) {
                wrapper.classList.toggle('is-hidden', isManual);
                wrapper.setAttribute('aria-hidden', isManual ? 'true' : 'false');
            }
            setFieldDisabledState(field, !isUnlocked || isManual || alwaysDisabledFieldIds.has(field.id));
            if (['id_kode_laboratorium', 'id_lokasi_barang'].includes(field.id)) {
                field.required = isUnlocked && !isManual && isBmnStatus();
                field.toggleAttribute('required', field.required);
            }
        });

        const historyGroup = form?.querySelector('[data-field-group="Riwayat Terakhir"]');
        if (historyGroup) {
            historyGroup.classList.toggle('is-hidden', isManual);
            historyGroup.setAttribute('aria-hidden', isManual ? 'true' : 'false');
        }
    }

    function getNormalizedValue(field) {
        return field ? (field.value || '').trim() : '';
    }

    function setReadonlyVisualState(field, readonly) {
        if (!field) {
            return;
        }

        const fieldGroup = field.closest('.form-group');

        if (readonly) {
            field.readOnly = true;
            field.setAttribute('readonly', 'readonly');
            field.setAttribute('aria-readonly', 'true');
            field.classList.add('is-readonly-field');
            if (fieldGroup) {
                fieldGroup.classList.add('is-readonly-field-group');
            }
            return;
        }

        field.readOnly = false;
        field.removeAttribute('readonly');
        field.removeAttribute('aria-readonly');
        field.classList.remove('is-readonly-field');
        if (fieldGroup) {
            fieldGroup.classList.remove('is-readonly-field-group');
        }
    }
    function getBmnVolumeByKondisi() {
        const kondisiValue = getNormalizedValue(kondisiField);

        if (kondisiValue === 'Baik') {
            return { volumeBaik: 1, volumeRusak: 0 };
        }

        if (kondisiValue === 'Hilang') {
            return { volumeBaik: 0, volumeRusak: 0 };
        }

        return { volumeBaik: 0, volumeRusak: 1 };
    }

    function applyBmnVolumeValues() {
        if (!volumeField || !volumeRusakField) {
            return;
        }

        const values = getBmnVolumeByKondisi();

        volumeField.value = String(values.volumeBaik);
        volumeRusakField.value = String(values.volumeRusak);

        if (totalVolumeField) {
            totalVolumeField.value = String(values.volumeBaik + values.volumeRusak);
        }
    }

    function applySingleLockedVolumeValue() {
        if (!volumeField || volumeRusakField || volumeField.getAttribute('data-volume-locked') !== 'true') {
            return;
        }

        const kondisiValue = getNormalizedValue(kondisiField);
        volumeField.value = kondisiValue === 'Hilang' ? '0' : '1';
    }

    function syncBmnAutoVolumeFields() {
        const hasAutoVolumeFields = Boolean(
            volumeField &&
            volumeRusakField &&
            volumeField.getAttribute('data-bmn-auto-volume-field') === 'true' &&
            volumeRusakField.getAttribute('data-bmn-auto-volume-field') === 'true'
        );

        if (!hasAutoVolumeFields) {
            return;
        }

        const isUnlocked = isInputReady();
        const isAutoVolume = usesAutoVolume();
        const isManual = usesManualVolume();
        const autoFields = [volumeField, volumeRusakField];

        autoFields.forEach(function (field) {
            if (!field) {
                return;
            }

            field.setAttribute('min', '0');

            if (isAutoVolume) {
                field.disabled = !isUnlocked;
                setReadonlyVisualState(field, true);
                field.setAttribute('max', '1');
                field.setAttribute('title', 'Otomatis diisi sistem berdasarkan Kondisi Barang.');
                field.removeAttribute('required');
                field.required = false;
                return;
            }

            field.disabled = !isUnlocked;
            setReadonlyVisualState(field, false);
            field.removeAttribute('max');
            field.removeAttribute('title');

            if (isManual && isUnlocked) {
                field.setAttribute('required', 'required');
                field.required = true;
            } else {
                field.removeAttribute('required');
                field.required = false;
            }
        });

        if (totalVolumeField) {
            if (isAutoVolume) {
                totalVolumeField.setAttribute('min', '0');
                totalVolumeField.setAttribute('max', '1');
            } else {
                totalVolumeField.setAttribute('min', '0');
                totalVolumeField.removeAttribute('max');
            }
        }

        if (isAutoVolume && isUnlocked) {
            applyBmnVolumeValues();
        }
    }

    function syncKetersediaanPreview() {
        const volumeBaik = Number(volumeField ? (volumeField.value || 0) : 0);
        const volumeRusak = Number(volumeRusakField ? (volumeRusakField.value || 0) : 0);
        const hasAutoVolumeFields = Boolean(
            volumeField &&
            volumeRusakField &&
            volumeField.getAttribute('data-bmn-auto-volume-field') === 'true' &&
            volumeRusakField.getAttribute('data-bmn-auto-volume-field') === 'true'
        );

        if (totalVolumeField) {
            if (usesAutoVolume() && hasAutoVolumeFields) {
                const values = getBmnVolumeByKondisi();
                totalVolumeField.value = String(values.volumeBaik + values.volumeRusak);
            } else {
                totalVolumeField.value = Math.max(volumeBaik, 0) + Math.max(volumeRusak, 0);
            }
        }

        if (!ketersediaanField) {
            return;
        }

        const isManualAsset = Boolean(volumeRusakField && usesManualVolume());

        if (kondisiField && !isManualAsset) {
            const kondisiValue = kondisiField.value || '';
            ketersediaanField.value = kondisiValue === 'Baik' ? 'Tersedia' : 'Tidak Tersedia';
            return;
        }

        if (volumeField && stokMinimumField) {
            const volume = Number(volumeField.value || 0);
            const stokMinimum = Number(stokMinimumField.value || 0);

            if (volume === 0) {
                ketersediaanField.value = 'Habis';
                return;
            }

            if (stokMinimum > 0 && volume <= stokMinimum) {
                ketersediaanField.value = 'Kurang';
                return;
            }

            if (stokMinimum > 0 && volume >= stokMinimum * 3) {
                ketersediaanField.value = 'Baik';
                return;
            }

            ketersediaanField.value = 'Cukup';
            return;
        }

        if (volumeField) {
            const volume = Number(volumeField.value || 0);
            ketersediaanField.value = volume > 0 ? 'Tersedia' : 'Tidak Tersedia';
        }
    }

    function syncKomponenVisibility() {
        const fieldset = form?.querySelector('[data-komponen-fieldset="true"]');
        if (!fieldset) {
            return;
        }

        const showFieldset = !bervolumeFields.length || usesAutoVolume();
        fieldset.classList.toggle('is-hidden', !showFieldset);
        fieldset.setAttribute('aria-hidden', showFieldset ? 'false' : 'true');
        fieldset.querySelector('[data-komponen]')?.dispatchEvent(
            new CustomEvent('komponenvisibilitychange')
        );
    }

    function refreshMasterDataDynamicFields() {
        syncDependentFieldLock();
        syncBmnFieldVisibility();
        syncStatusSpecificAssetFields();
        syncBmnAutoVolumeFields();
        applySingleLockedVolumeValue();
        syncKetersediaanPreview();
        syncKomponenVisibility();
    }

    refreshMasterDataDynamicFields();

    if (statusField) {
        ['change', 'input'].forEach(function (eventName) {
            statusField.addEventListener(eventName, refreshMasterDataDynamicFields);
        });
    }

    if (bervolumeFields.length) {
        ['change', 'input'].forEach(function (eventName) {
            bervolumeFields.forEach(function (field) {
                field.addEventListener(eventName, refreshMasterDataDynamicFields);
            });
        });
    }

    if (kondisiField) {
        ['change', 'input'].forEach(function (eventName) {
            kondisiField.addEventListener(eventName, refreshMasterDataDynamicFields);
        });
    }

    if (form) {
        ['change', 'input', 'keyup'].forEach(function (eventName) {
            form.addEventListener(eventName, function (event) {
                if (event.target === statusField || event.target === kondisiField || bervolumeFields.includes(event.target)) {
                    refreshMasterDataDynamicFields();
                    return;
                }

                syncBmnAutoVolumeFields();
                syncKetersediaanPreview();
            });
        });

        form.addEventListener('submit', function () {
            refreshMasterDataDynamicFields();
        });
    }

    window.setTimeout(refreshMasterDataDynamicFields, 0);

    if (volumeField) {
        volumeField.addEventListener('input', syncKetersediaanPreview);
    }

    if (volumeRusakField) {
        volumeRusakField.addEventListener('input', syncKetersediaanPreview);
    }

    if (stokMinimumField) {
        stokMinimumField.addEventListener('input', syncKetersediaanPreview);
    }
}

function initKomponenRutin() {
    const groups = document.querySelectorAll('[data-komponen]');

    if (!groups.length) {
        return;
    }

    groups.forEach(function (group) {
        const list = group.querySelector('[data-komponen-list]');
        const addButton = group.querySelector('[data-komponen-add]');
        const fieldName = group.getAttribute('data-komponen-field') || 'komponen_pemeliharaan';
        const fieldId = group.getAttribute('data-komponen-id') || 'id_komponen_pemeliharaan';
        const maxLength = Number(group.getAttribute('data-komponen-max') || 100);
        const minRows = Math.max(Number(group.getAttribute('data-komponen-min') || 1), 1);
        const labelId = fieldId + '_label';
        const isGroupLocked = group.getAttribute('data-komponen-locked-all') === 'true';
        const lockMessage = group.getAttribute('data-komponen-lock-message') || 'Komponen sedang digunakan pada pengajuan pemeliharaan aktif';

        if (!list || !addButton) {
            return;
        }

        function createRemoveButton() {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'komponen-rutin__remove';
            button.setAttribute('data-komponen-remove', 'true');
            button.setAttribute('title', 'Hapus komponen');
            button.setAttribute('aria-label', 'Hapus komponen');

            const icon = document.createElement('i');
            icon.className = 'bi bi-trash';
            button.appendChild(icon);

            return button;
        }

        function createRow(value) {
            const row = document.createElement('div');
            row.className = 'komponen-rutin__row';
            row.setAttribute('data-komponen-row', 'true');

            const input = document.createElement('input');
            input.type = 'text';
            input.name = fieldName;
            input.value = value || '';
            input.className = 'form-control';
            input.maxLength = maxLength;
            input.autocomplete = 'off';
            input.setAttribute('aria-labelledby', labelId);
            input.setAttribute('data-status-dependent', 'true');
            input.setAttribute('data-komponen-input', 'true');

            row.appendChild(input);
            row.appendChild(createRemoveButton());
            return row;
        }

        function getRows() {
            return Array.from(list.querySelectorAll('[data-komponen-row]'));
        }

        function syncRows() {
            const rows = getRows();
            const conditionalLocked = Boolean(
                group.closest('[data-komponen-fieldset="true"]')?.classList.contains('is-hidden')
            );

            rows.forEach(function (row, index) {
                const input = row.querySelector('[data-komponen-input]');
                const removeButton = row.querySelector('[data-komponen-remove]');

                if (input) {
                    input.name = fieldName;
                    input.id = fieldId + '_' + index;
                    input.placeholder = 'Komponen ' + (index + 1);
                    input.maxLength = maxLength;
                    input.setAttribute('aria-labelledby', labelId);
                }

                if (removeButton) {
                    const transactionLocked = isGroupLocked || row.dataset.komponenLocked === 'true';
                    const isLocked = transactionLocked || conditionalLocked;
                    removeButton.disabled = isLocked || rows.length <= minRows;
                    removeButton.classList.toggle('komponen-rutin__remove--locked', isLocked);
                    removeButton.title = isLocked ? lockMessage : 'Hapus komponen';
                    removeButton.setAttribute('aria-disabled', String(isLocked || rows.length <= minRows));
                    removeButton.toggleAttribute('data-transaction-locked', transactionLocked);
                }

                if (input) {
                    const transactionLocked = isGroupLocked || row.dataset.komponenLocked === 'true';
                    const isLocked = transactionLocked || conditionalLocked;
                    input.disabled = isLocked;
                    input.readOnly = isLocked;
                    input.toggleAttribute('readonly', isLocked);
                    input.toggleAttribute('data-transaction-locked', transactionLocked);
                    input.classList.toggle('is-readonly-field', isLocked);
                    input.setAttribute('aria-disabled', String(isLocked));
                    input.setAttribute('aria-readonly', String(isLocked));
                }
            });

            const addLocked = isGroupLocked || conditionalLocked;
            addButton.disabled = addLocked;
            addButton.classList.toggle('btn-disabled', addLocked);
            addButton.setAttribute('aria-disabled', String(addLocked));
            addButton.toggleAttribute('data-transaction-locked', isGroupLocked);
            if (isGroupLocked) {
                addButton.title = lockMessage;
            }
        }

        function focusAfterRemove(index) {
            const rows = getRows();
            const start = Math.min(index, rows.length - 1);
            const orderedRows = rows.slice(start).concat(rows.slice(0, start).reverse());
            const targetInput = orderedRows
                .map(function (item) {
                    return item.querySelector('[data-komponen-input]');
                })
                .find(function (input) {
                    return input && !input.disabled && !input.readOnly;
                });

            if (targetInput) {
                targetInput.focus();
                return;
            }

            addButton.focus();
        }

        while (getRows().length < minRows) {
            list.appendChild(createRow(''));
        }

        syncRows();
        group.addEventListener('komponenvisibilitychange', syncRows);

        addButton.addEventListener('click', function () {
            if (isGroupLocked || addButton.disabled) {
                return;
            }

            const row = createRow('');
            list.appendChild(row);
            syncRows();
            row.querySelector('[data-komponen-input]')?.focus();
        });

        list.addEventListener('click', function (event) {
            const removeButton = event.target.closest('[data-komponen-remove]');

            if (!removeButton || !list.contains(removeButton)) {
                return;
            }

            event.preventDefault();

            const rows = getRows();
            const row = removeButton.closest('[data-komponen-row]');
            const rowIndex = rows.indexOf(row);

            if (!row) {
                return;
            }

            if (isGroupLocked || row.dataset.komponenLocked === 'true') {
                return;
            }

            if (rows.length <= minRows) {
                const input = row.querySelector('[data-komponen-input]');
                if (input) {
                    input.value = '';
                    input.focus();
                }
                return;
            }

            row.remove();
            syncRows();
            focusAfterRemove(Math.max(rowIndex, 0));
        });
    });
}

function initMasterDataFormValidation() {
    const form = document.querySelector('[data-master-data-form="true"]');

    if (!form) {
        return;
    }

    const fields = Array.from(form.querySelectorAll('input, select, textarea'));

    function normalizeMessage(text) {
        return String(text || '').replace(/^\*/, '').trim();
    }

    function getGroup(field) {
        return field ? field.closest('.form-group') : null;
    }

    function isFieldIgnored(field) {
        if (!field) {
            return true;
        }

        const type = String(field.type || '').toLowerCase();
        return type === 'hidden' || type === 'file' || type === 'checkbox' || type === 'radio';
    }

    function isFieldVisible(field) {
        if (!field || field.disabled || isFieldIgnored(field)) {
            return false;
        }

        const wrapper = field.closest('.is-hidden');
        if (wrapper) {
            return false;
        }

        return true;
    }

    function clearMessages(group) {
        if (!group) {
            return;
        }

        group.querySelectorAll('.input-error-text').forEach(function (node) {
            node.remove();
        });
        group.classList.remove('has-error');
    }

    function showMessage(group, message) {
        if (!group || !message) {
            return;
        }

        clearMessages(group);
        group.classList.add('has-error');

        const errorNode = document.createElement('p');
        errorNode.className = 'input-error-text';
        errorNode.dataset.clientError = 'true';
        errorNode.textContent = '*' + normalizeMessage(message);
        group.appendChild(errorNode);
    }

    function getLabelText(field) {
        const label = field.id ? form.querySelector('label[for="' + field.id + '"]') : null;
        return String(label ? label.textContent : field.getAttribute('aria-label') || 'Kolom')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/:$/, '');
    }

    function getRequiredMessage(field) {
        const labelText = getLabelText(field);
        return field.tagName === 'SELECT'
            ? labelText + ' wajib dipilih.'
            : labelText + ' wajib diisi.';
    }

    function getMinimumMessage(field, minValue) {
        const labelText = getLabelText(field);
        return labelText + ' minimal ' + minValue + '.';
    }

    function validateField(field) {
        const group = getGroup(field);

        if (!group) {
            return true;
        }

        if (!isFieldVisible(field)) {
            clearMessages(group);
            return true;
        }

        const value = String(field.value || '').trim();

        if (field.required && !value) {
            showMessage(group, getRequiredMessage(field));
            return false;
        }

        if (value && String(field.type || '').toLowerCase() === 'number') {
            const minAttr = field.getAttribute('min');
            const numericValue = Number(value);

            if (!Number.isFinite(numericValue)) {
                showMessage(group, getLabelText(field) + ' harus berupa angka yang valid.');
                return false;
            }

            if (minAttr !== null && minAttr !== '' && numericValue < Number(minAttr)) {
                showMessage(group, getMinimumMessage(field, minAttr));
                return false;
            }
        }

        clearMessages(group);
        return true;
    }

    fields.forEach(function (field) {
        if (isFieldIgnored(field)) {
            return;
        }

        const inputEvents = field.tagName === 'SELECT' ? ['change', 'input'] : ['input', 'change'];
        inputEvents.forEach(function (eventName) {
            field.addEventListener(eventName, function () {
                validateField(field);
            });
        });
    });

    form.addEventListener('submit', function (event) {
        let isValid = true;

        fields.forEach(function (field) {
            if (!validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            event.preventDefault();
            const firstError = form.querySelector('.form-group.has-error .input-error-text');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}


function initOperasionalFormValidation() {
    const form = document.querySelector('[data-operasional-form="true"]');

    if (!form) {
        return;
    }

    const fields = Array.from(form.querySelectorAll('input, select, textarea'));

    function normalizeMessage(text) {
        return String(text || '').replace(/^\*/, '').trim();
    }

    function getGroup(field) {
        return field ? field.closest('.form-group') : null;
    }

    function isIgnoredField(field) {
        if (!field) {
            return true;
        }

        const type = String(field.type || '').toLowerCase();
        return type === 'hidden' || type === 'file' || type === 'checkbox' || type === 'radio';
    }

    function getLabelText(field) {
        const label = field.id ? form.querySelector('label[for="' + field.id + '"]') : null;
        return String(label ? label.textContent : field.getAttribute('aria-label') || 'Kolom')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/:$/, '');
    }

    function getRequiredMessage(field) {
        const labelText = getLabelText(field);
        return field.tagName === 'SELECT'
            ? labelText + ' wajib dipilih.'
            : labelText + ' wajib diisi.';
    }

    function clearMessages(group, clearableMessages) {
        if (!group) {
            return;
        }

        const normalizedMessages = (clearableMessages || []).map(function (message) {
            return normalizeMessage(message);
        });

        group.querySelectorAll('.input-error-text').forEach(function (node) {
            const nodeMessage = normalizeMessage(node.textContent);
            if (node.dataset.clientError === 'true' || normalizedMessages.includes(nodeMessage)) {
                node.remove();
            }
        });

        if (!group.querySelector('.input-error-text')) {
            group.classList.remove('has-error');
        }
    }

    function showMessage(group, message, clearableMessages) {
        if (!group || !message) {
            return;
        }

        clearMessages(group, (clearableMessages || []).concat([message]));
        group.classList.add('has-error');

        const errorNode = document.createElement('p');
        errorNode.className = 'input-error-text';
        errorNode.dataset.clientError = 'true';
        errorNode.textContent = '*' + normalizeMessage(message);
        group.appendChild(errorNode);
    }

    function validateField(field) {
        if (!field || isIgnoredField(field) || field.disabled) {
            return true;
        }

        const group = getGroup(field);
        const value = String(field.value || '').trim();
        const clearableMessages = [
            'Kolom ini wajib diisi.',
            getRequiredMessage(field),
        ];

        if (field.required && !value) {
            showMessage(group, getRequiredMessage(field), clearableMessages);
            return false;
        }

        clearMessages(group, clearableMessages);
        return true;
    }

    fields.forEach(function (field) {
        if (isIgnoredField(field)) {
            return;
        }

        const inputEvents = field.tagName === 'SELECT' ? ['change', 'input'] : ['input', 'change'];
        inputEvents.forEach(function (eventName) {
            field.addEventListener(eventName, function () {
                validateField(field);
            });
        });
    });

    form.addEventListener('submit', function (event) {
        let isValid = true;

        fields.forEach(function (field) {
            if (!validateField(field)) {
                isValid = false;
            }
        });

        if (!isValid) {
            event.preventDefault();
            const firstError = form.querySelector('.form-group.has-error .input-error-text');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}


/* ========================================
   HALAMAN PEMINJAMAN - MODAL HAPUS
======================================== */
function initPeminjamanDeleteModal() {
    bindDeleteModal({
        type: 'peminjaman',
        modalId: 'peminjamanDeleteModal',
        backdropId: 'peminjamanDeleteModalBackdrop',
        closeId: 'peminjamanDeleteModalClose',
        cancelId: 'peminjamanDeleteModalCancel',
        formId: 'peminjamanDeleteForm',
        primaryFieldId: 'peminjamanDeleteItemName',
        secondaryFieldId: 'peminjamanDeleteItemMeta',
        primaryDataAttr: 'data-item-name',
        secondaryDataAttr: 'data-item-meta'
    });
}

function isEmptyQtyInput(input) {
    return Boolean(
        input
        && input.hasAttribute('data-allow-empty')
        && String(input.value || '').trim() === ''
    );
}

function getNumericInputValue(input) {
    const parsed = Number.parseInt(String(input && input.value ? input.value : '0').trim(), 10);
    return Number.isFinite(parsed) ? parsed : 0;
}

function getNumericInputLimit(input, attributeName, fallbackValue) {
    const rawValue = input ? input.getAttribute(attributeName) : null;
    if (rawValue === null || rawValue === '') {
        return fallbackValue;
    }
    const parsed = Number.parseInt(String(rawValue).trim(), 10);
    return Number.isFinite(parsed) ? parsed : fallbackValue;
}

function clampQtyInputValue(input) {
    if (!input) {
        return;
    }
    if (isEmptyQtyInput(input)) {
        return;
    }
    const min = getNumericInputLimit(input, 'min', 0);
    const max = getNumericInputLimit(input, 'max', Number.MAX_SAFE_INTEGER);
    let nextValue = getNumericInputValue(input);
    nextValue = Math.max(min, Math.min(max, nextValue));
    input.value = String(nextValue);
}

function syncQtyStepperState(input) {
    if (!input) {
        return;
    }
    const stepper = input.closest('[data-qty-stepper]');
    if (!stepper) {
        return;
    }
    const decreaseButton = stepper.querySelector('[data-qty-step="down"]');
    const increaseButton = stepper.querySelector('[data-qty-step="up"]');
    const min = getNumericInputLimit(input, 'min', 0);
    const max = getNumericInputLimit(input, 'max', Number.MAX_SAFE_INTEGER);
    const value = getNumericInputValue(input);
    const isDisabled = input.disabled;

    if (decreaseButton) {
        decreaseButton.disabled = isDisabled || value <= min;
    }
    if (increaseButton) {
        increaseButton.disabled = isDisabled || value >= max;
    }
}

function bindQtyStepper(stepper) {
    const input = stepper ? stepper.querySelector('.input-qty') : null;
    if (!input || stepper.dataset.qtyStepperBound === 'true') {
        return;
    }

    clampQtyInputValue(input);
    syncQtyStepperState(input);

    stepper.dataset.qtyStepperBound = 'true';

    input.addEventListener('input', function () {
        clampQtyInputValue(input);
        syncQtyStepperState(input);
    });

    input.addEventListener('change', function () {
        clampQtyInputValue(input);
        syncQtyStepperState(input);
    });

    stepper.addEventListener('click', function (event) {
        const button = event.target.closest('[data-qty-step]');
        if (!button || button.disabled || input.disabled) {
            return;
        }
        event.preventDefault();
        const direction = button.getAttribute('data-qty-step') === 'down' ? -1 : 1;
        const min = getNumericInputLimit(input, 'min', 0);
        const max = getNumericInputLimit(input, 'max', Number.MAX_SAFE_INTEGER);
        const nextValue = Math.max(min, Math.min(max, getNumericInputValue(input) + direction));
        input.value = String(nextValue);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.focus({ preventScroll: true });
    });
}

function initGlobalQtyStepperBehavior(scope) {
    const root = scope || document;
    root.querySelectorAll('[data-qty-stepper]').forEach(function (stepper) {
        bindQtyStepper(stepper);
    });
}

window.refreshQtyStepper = function (input) {
    syncQtyStepperState(input);
};


function initPengembalianFormBehavior() {
    const form = document.querySelector('[data-pengembalian-form="true"]');

    if (!form) {
        return;
    }

    const noteGroup = form.querySelector('[data-return-note-group="true"]');
    const noteInput = form.querySelector('[data-return-note-input="true"]');
    const approvalInputs = form.querySelectorAll('input[name="aksi"]');

    function clearReturnNoteErrors() {
        if (!noteGroup) {
            return;
        }

        noteGroup.classList.remove('has-error');
        noteGroup.querySelectorAll('.return-note-error').forEach(function (errorNode) {
            errorNode.remove();
        });
    }

    function getReturnFieldGroup(element) {
        return element ? element.closest('[data-return-field-group="true"]') : null;
    }

    function getReturnMainRow(element) {
        return element ? element.closest('[data-return-main-row="true"]') : null;
    }

    function getReturnErrorRow(elementOrRow) {
        const row = elementOrRow && elementOrRow.matches && elementOrRow.matches('[data-return-main-row="true"]')
            ? elementOrRow
            : getReturnMainRow(elementOrRow);
        if (!row) {
            return null;
        }

        const rowId = String(row.getAttribute('data-return-row-id') || '').trim();
        if (!rowId) {
            return null;
        }

        return form.querySelector('[data-return-error-row="true"][data-return-row-id="' + rowId + '"]');
    }

    function getReturnErrorStack(errorRow) {
        return errorRow ? errorRow.closest('[data-return-error-stack="true"]') : null;
    }

    function syncReturnErrorStackVisibility(errorRow) {
        const errorStack = getReturnErrorStack(errorRow);
        if (!errorStack) {
            return;
        }

        const hasVisibleRow = Array.from(errorStack.querySelectorAll('[data-return-error-row="true"]')).some(function (rowNode) {
            return !rowNode.hidden;
        });
        errorStack.hidden = !hasVisibleRow;
    }

    function syncReturnErrorRowVisibility(elementOrRow) {
        const errorRow = getReturnErrorRow(elementOrRow);
        if (!errorRow) {
            return;
        }

        let hasMessage = false;
        errorRow.querySelectorAll('[data-return-error-key]').forEach(function (cell) {
            const hasCellMessage = Boolean(cell.querySelector('.input-error-text'));
            cell.hidden = !hasCellMessage;
            if (hasCellMessage) {
                hasMessage = true;
            }
        });

        errorRow.hidden = !hasMessage;
        syncReturnErrorStackVisibility(errorRow);
    }

    function clearReturnErrorCells(element, keys) {
        const errorRow = getReturnErrorRow(element);
        if (!errorRow) {
            return;
        }

        const normalizedKeys = (Array.isArray(keys) ? keys : [keys]).filter(Boolean);
        normalizedKeys.forEach(function (key) {
            const cell = errorRow.querySelector('[data-return-error-key="' + key + '"]');
            if (!cell) {
                return;
            }
            cell.querySelectorAll('.input-error-text').forEach(function (errorNode) {
                errorNode.remove();
            });
            cell.hidden = true;
        });

        syncReturnErrorRowVisibility(element);
    }

    function appendReturnErrorMessage(element, key, message) {
        if (!message) {
            return;
        }

        const errorRow = getReturnErrorRow(element);
        if (!errorRow) {
            return;
        }

        const cell = errorRow.querySelector('[data-return-error-key="' + key + '"]');
        if (!cell) {
            return;
        }

        const normalizedMessage = String(message || '').replace(/^\*/, '').trim();
        const exists = Array.from(cell.querySelectorAll('.input-error-text')).some(function (node) {
            return String(node.textContent || '').replace(/^\*/, '').trim() === normalizedMessage;
        });

        if (exists) {
            syncReturnErrorRowVisibility(element);
            return;
        }

        const messageNode = document.createElement('p');
        messageNode.className = 'input-error-text';
        messageNode.dataset.clientError = 'true';
        messageNode.textContent = '*' + normalizedMessage;
        cell.appendChild(messageNode);
        cell.hidden = false;
        syncReturnErrorRowVisibility(element);
    }

    function markReturnFieldError(element, key, message) {
        const group = getReturnFieldGroup(element);
        if (group) {
            group.classList.add('has-error');
        }
        appendReturnErrorMessage(element, key, message);
    }

    function clearReturnFieldErrors(element, extraKeys) {
        const group = getReturnFieldGroup(element);
        const errorKeys = [];

        if (group && group.dataset.errorKey) {
            errorKeys.push(group.dataset.errorKey);
        }

        if (Array.isArray(extraKeys)) {
            extraKeys.forEach(function (key) {
                if (key) {
                    errorKeys.push(key);
                }
            });
        } else if (extraKeys) {
            errorKeys.push(extraKeys);
        }

        if (group) {
            group.classList.remove('has-error');
            group.querySelectorAll('.input-error-text').forEach(function (errorNode) {
                errorNode.remove();
            });
        }

        if (errorKeys.length) {
            clearReturnErrorCells(element, Array.from(new Set(errorKeys)));
        }
    }

    if (noteInput) {
        noteInput.addEventListener('input', function () {
            if (String(noteInput.value || '').trim()) {
                clearReturnNoteErrors();
            }
        });
    }

    approvalInputs.forEach(function (input) {
        input.addEventListener('change', function () {
            if (input.checked && input.value === 'setujui') {
                clearReturnNoteErrors();
            }
        });
    });

    function getRowTotal(row) {
        const parsedTotal = Number.parseInt(String(row?.getAttribute('data-borrowed-total') || '0').trim(), 10);
        return Number.isFinite(parsedTotal) ? Math.max(parsedTotal, 0) : 0;
    }

    function getQtyInputs(row) {
        return Array.from(row.querySelectorAll('.js-return-qty'));
    }

    function getEnabledQtyInputs(row) {
        return getQtyInputs(row).filter(function (input) {
            return !input.disabled;
        });
    }


    function syncReturnPlaceholderState(select) {
        if (!select) {
            return;
        }
        select.classList.toggle('is-placeholder-state', !select.value);
    }

    function updateIndicator(row, currentTotal, maxTotal) {
        const indicator = row.querySelector('.js-total-indicator');
        if (!indicator) {
            return;
        }
        indicator.textContent = currentTotal + '/' + maxTotal;
        indicator.classList.remove('is-complete', 'is-over');
        if (currentTotal > maxTotal) {
            indicator.classList.add('is-over');
            return;
        }
        if (currentTotal === maxTotal) {
            indicator.classList.add('is-complete');
        }
    }

    function syncQtyLimits(row) {
        if (!row) {
            return;
        }

        const maxTotal = getRowTotal(row);
        const enabledInputs = getEnabledQtyInputs(row);

        enabledInputs.forEach(function (input) {
            const otherSum = enabledInputs.reduce(function (sum, otherInput) {
                if (otherInput === input) {
                    return sum;
                }
                return sum + getNumericInputValue(otherInput);
            }, 0);
            const dynamicMax = Math.max(0, maxTotal - otherSum);
            input.setAttribute('max', String(dynamicMax));
            clampQtyInputValue(input);
            syncQtyStepperState(input);
        });

        getQtyInputs(row).forEach(function (input) {
            if (!input.disabled) {
                return;
            }
            input.setAttribute('max', String(maxTotal));
            syncQtyStepperState(input);
        });

        const totalProcessed = getQtyInputs(row).reduce(function (sum, input) {
            return sum + getNumericInputValue(input);
        }, 0);
        updateIndicator(row, totalProcessed, maxTotal);
    }

    function syncTransferRow(row) {
        const toggle = row.querySelector('.js-transfer-toggle');
        if (!toggle) {
            syncQtyLimits(row);
            return;
        }

        const isChecked = Boolean(toggle.checked);
        const isEditable = !toggle.disabled;
        const toggleLabel = toggle.closest('.return-transfer-toggle, .return-transfer-check');
        const qtyPanel = row.querySelector('[data-transfer-panel="qty"]');
        const targetPanel = row.querySelector('[data-transfer-panel="target"]');
        const qtyInput = row.querySelector('.js-transfer-qty');
        const targetSelect = row.querySelector('.js-transfer-target');

        if (toggleLabel) {
            toggleLabel.classList.toggle('is-active', isChecked);
        }
        if (qtyPanel) {
            qtyPanel.hidden = !isChecked;
        }
        if (targetPanel) {
            targetPanel.hidden = !isChecked;
        }
        if (qtyInput) {
            qtyInput.disabled = !(isChecked && isEditable);
            if (!isChecked) {
                qtyInput.value = '';
            }
            syncQtyStepperState(qtyInput);
        }
        if (targetSelect) {
            targetSelect.disabled = !(isChecked && isEditable);
            if (!isChecked) {
                targetSelect.value = '';
            }
            syncReturnPlaceholderState(targetSelect);
        }

        syncQtyLimits(row);
    }

    form.querySelectorAll('.js-lab-status').forEach(function (select) {
        const targetId = select.getAttribute('data-target-id');
        const transferBox = targetId ? document.getElementById(targetId) : null;
        const transferSelect = transferBox ? transferBox.querySelector('.js-lab-transfer-target') : null;

        function syncLabTransferState() {
            const isTransfer = select.value === 'transfer';
            if (transferBox) {
                transferBox.hidden = !isTransfer;
            }
            if (transferSelect) {
                transferSelect.disabled = !(isTransfer && !select.disabled);
                if (!isTransfer) {
                    transferSelect.value = '';
                }
                syncReturnPlaceholderState(transferSelect);
            }
        }

        select.addEventListener('change', function () {
            clearReturnFieldErrors(select, ['transfer_target']);
            syncLabTransferState();
        });

        if (transferSelect) {
            transferSelect.addEventListener('change', function () {
                syncReturnPlaceholderState(transferSelect);
                clearReturnFieldErrors(transferSelect);
            });
        }

        syncReturnPlaceholderState(select);
        syncLabTransferState();
    });

    form.querySelectorAll('.js-penunjang-row, .js-peralatan-lab-row, .js-bahan-row').forEach(function (row) {
        row.querySelectorAll('.js-return-qty').forEach(function (input) {
            function getRelatedErrorKeys() {
                const role = String(input.dataset.role || '').trim();
                const keys = [];

                if (role === 'transfer') {
                    keys.push('transfer_qty');
                } else if (role) {
                    keys.push(role);
                }

                keys.push('validation');
                return keys;
            }

            input.addEventListener('input', function () {
                clearReturnFieldErrors(input, getRelatedErrorKeys());
                syncQtyLimits(row);
            });
            input.addEventListener('change', function () {
                clearReturnFieldErrors(input, getRelatedErrorKeys());
                syncQtyLimits(row);
            });
        });

        row.querySelectorAll('.js-transfer-target').forEach(function (select) {
            select.addEventListener('change', function () {
                syncReturnPlaceholderState(select);
                clearReturnFieldErrors(select);
            });
        });

        const toggle = row.querySelector('.js-transfer-toggle');
        if (toggle) {
            toggle.addEventListener('change', function () {
                clearReturnFieldErrors(toggle, ['transfer_qty', 'transfer_target', 'validation']);
                const targetSelect = row.querySelector('.js-transfer-target');
                if (!toggle.checked && targetSelect) {
                    clearReturnFieldErrors(targetSelect);
                }
                syncTransferRow(row);
            });
        }

        row.querySelectorAll('.js-transfer-target').forEach(function (select) {
            syncReturnPlaceholderState(select);
        });
        syncTransferRow(row);
        syncReturnErrorRowVisibility(row);
    });

    form.querySelectorAll('[data-return-main-row="true"]').forEach(function (row) {
        const note = row.querySelector('.js-return-note');
        if (note) {
            note.addEventListener('input', function () {
                clearReturnFieldErrors(note, ['note']);
                syncReturnErrorRowVisibility(row);
            });
        }
        syncReturnErrorRowVisibility(row);
    });

    function validateLabRow(row) {
        const statusSelect = row ? row.querySelector('.js-lab-status') : null;
        const targetSelect = row ? row.querySelector('.js-lab-transfer-target') : null;
        let isValid = true;

        if (!statusSelect || statusSelect.disabled) {
            return true;
        }

        clearReturnFieldErrors(statusSelect, ['transfer_target']);
        if (targetSelect) {
            clearReturnFieldErrors(targetSelect);
        }

        const statusValue = String(statusSelect.value || '').trim();
        if (!statusValue) {
            markReturnFieldError(statusSelect, 'status', 'Status pengembalian wajib dipilih.');
            isValid = false;
        }

        if (statusValue === 'transfer') {
            const targetValue = String(targetSelect && targetSelect.value ? targetSelect.value : '').trim();
            if (!targetValue) {
                markReturnFieldError(targetSelect || statusSelect, 'transfer_target', 'Tujuan transfer wajib dipilih.');
                isValid = false;
            }
        }

        syncReturnErrorRowVisibility(row);
        return isValid;
    }

    function validatePenunjangRow(row) {
        if (!row) {
            return true;
        }

        const sectionPrefix = row.classList.contains('js-peralatan-lab-row') ? 'peralatan_lab' : 'penunjang';
        const dikembalikanInput = row.querySelector('input[name^="' + sectionPrefix + '_dikembalikan_"]');
        const rusakInput = row.querySelector('input[name^="' + sectionPrefix + '_rusak_"]');
        const hilangInput = row.querySelector('input[name^="' + sectionPrefix + '_hilang_"]');
        const transferInput = row.querySelector('input[name^="' + sectionPrefix + '_transfer_"]');
        const transferToggle = row.querySelector('.js-transfer-toggle');
        const targetSelect = row.querySelector('.js-transfer-target');
        const maxQty = getRowTotal(row);
        let isValid = true;

        [dikembalikanInput, rusakInput, hilangInput, transferInput].forEach(function (input) {
            if (input) {
                clampQtyInputValue(input);
            }
        });

        clearReturnFieldErrors(dikembalikanInput, ['validation']);
        clearReturnFieldErrors(rusakInput);
        clearReturnFieldErrors(hilangInput);
        clearReturnFieldErrors(transferInput, ['validation', 'transfer_target']);
        if (targetSelect) {
            clearReturnFieldErrors(targetSelect);
        }

        const qtyDikembalikan = getNumericInputValue(dikembalikanInput);
        const qtyRusak = getNumericInputValue(rusakInput);
        const qtyHilang = getNumericInputValue(hilangInput);
        const qtyTransfer = getNumericInputValue(transferInput);
        const transferEnabled = Boolean(transferToggle && transferToggle.checked);

        [
            ['dikembalikan', dikembalikanInput, qtyDikembalikan, 'Jumlah dikembalikan (baik) tidak boleh melebihi jumlah dipinjam (' + maxQty + ').'],
            ['rusak', rusakInput, qtyRusak, 'Jumlah rusak tidak boleh melebihi jumlah dipinjam (' + maxQty + ').'],
            ['hilang', hilangInput, qtyHilang, 'Jumlah hilang tidak boleh melebihi jumlah dipinjam (' + maxQty + ').'],
            ['transfer_qty', transferInput, qtyTransfer, 'Jumlah transfer tidak boleh melebihi jumlah dipinjam (' + maxQty + ').'],
        ].forEach(function (entry) {
            const key = entry[0];
            const input = entry[1];
            const value = entry[2];
            const message = entry[3];
            if (input && value > maxQty) {
                markReturnFieldError(input, key, message);
                isValid = false;
            }
        });

        if (transferEnabled) {
            if (qtyTransfer <= 0) {
                markReturnFieldError(transferInput || transferToggle, 'transfer_qty', 'Jumlah transfer wajib diisi jika checkbox transfer aktif.');
                isValid = false;
            }
            if (!String(targetSelect && targetSelect.value ? targetSelect.value : '').trim()) {
                markReturnFieldError(targetSelect || transferInput || transferToggle, 'transfer_target', 'Tujuan transfer wajib dipilih.');
                isValid = false;
            }
        }

        const totalProcessed = qtyDikembalikan + qtyRusak + qtyHilang + (transferEnabled ? qtyTransfer : 0);
        if (totalProcessed !== maxQty) {
            markReturnFieldError(dikembalikanInput || row, 'validation', 'Total pengembalian harus ' + maxQty + '/' + maxQty + ' sesuai volume peminjaman.');
            isValid = false;
        }

        syncQtyLimits(row);
        syncReturnErrorRowVisibility(row);
        return isValid;
    }

    function validateBahanRow(row) {
        if (!row) {
            return true;
        }

        const dikembalikanInput = row.querySelector('input[name^="bahan_dikembalikan_"]');
        const transferInput = row.querySelector('input[name^="bahan_transfer_"]');
        const transferToggle = row.querySelector('.js-transfer-toggle');
        const targetSelect = row.querySelector('.js-transfer-target');
        const maxQty = getRowTotal(row);
        let isValid = true;

        [dikembalikanInput, transferInput].forEach(function (input) {
            if (input) {
                clampQtyInputValue(input);
            }
        });

        clearReturnFieldErrors(dikembalikanInput, ['validation']);
        clearReturnFieldErrors(transferInput, ['validation', 'transfer_target']);
        if (targetSelect) {
            clearReturnFieldErrors(targetSelect);
        }

        const qtyDikembalikan = getNumericInputValue(dikembalikanInput);
        const qtyTransfer = getNumericInputValue(transferInput);
        const transferEnabled = Boolean(transferToggle && transferToggle.checked);

        if (dikembalikanInput && qtyDikembalikan > maxQty) {
            markReturnFieldError(dikembalikanInput, 'dikembalikan', 'Jumlah dikembalikan tidak boleh melebihi jumlah dipinjam (' + maxQty + ').');
            isValid = false;
        }
        if (transferInput && qtyTransfer > maxQty) {
            markReturnFieldError(transferInput, 'transfer_qty', 'Jumlah transfer tidak boleh melebihi jumlah dipinjam (' + maxQty + ').');
            isValid = false;
        }

        if (transferEnabled) {
            if (qtyTransfer <= 0) {
                markReturnFieldError(transferInput || transferToggle, 'transfer_qty', 'Jumlah transfer wajib diisi jika checkbox transfer aktif.');
                isValid = false;
            }
            if (!String(targetSelect && targetSelect.value ? targetSelect.value : '').trim()) {
                markReturnFieldError(targetSelect || transferInput || transferToggle, 'transfer_target', 'Tujuan transfer wajib dipilih.');
                isValid = false;
            }
        }

        const totalProcessed = qtyDikembalikan + (transferEnabled ? qtyTransfer : 0);
        if (totalProcessed > maxQty) {
            markReturnFieldError(dikembalikanInput || row, 'validation', 'Total dikembalikan dan transfer tidak boleh melebihi jumlah dipinjam (' + maxQty + ').');
            isValid = false;
        }

        syncQtyLimits(row);
        syncReturnErrorRowVisibility(row);
        return isValid;
    }

    function validatePengembalianRows() {
        let isValid = true;
        let firstInvalidTarget = null;

        form.querySelectorAll('tr[data-return-row-id^="lab_"]').forEach(function (row) {
            if (!validateLabRow(row)) {
                isValid = false;
                if (!firstInvalidTarget) {
                    firstInvalidTarget = row;
                }
            }
        });

        form.querySelectorAll('.js-penunjang-row, .js-peralatan-lab-row').forEach(function (row) {
            if (!validatePenunjangRow(row)) {
                isValid = false;
                if (!firstInvalidTarget) {
                    firstInvalidTarget = row;
                }
            }
        });

        form.querySelectorAll('.js-bahan-row').forEach(function (row) {
            if (!validateBahanRow(row)) {
                isValid = false;
                if (!firstInvalidTarget) {
                    firstInvalidTarget = row;
                }
            }
        });

        if (!isValid && firstInvalidTarget) {
            firstInvalidTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        return isValid;
    }

    const returnDateModal = document.getElementById('returnDateModal');
    const returnDateModalBackdrop = document.getElementById('returnDateModalBackdrop');
    const returnDateModalClose = document.getElementById('returnDateModalClose');
    const returnDateModalCancel = document.getElementById('returnDateModalCancel');
    const returnDateModalOpenButtons = document.querySelectorAll('[data-return-date-modal-open="true"]');

    function openReturnDateModal() {
        if (!returnDateModal) {
            return;
        }
        returnDateModal.classList.add('show');
        document.body.classList.add('modal-open');
    }

    function closeReturnDateModal() {
        if (!returnDateModal) {
            return;
        }
        returnDateModal.classList.remove('show');
        if (!summaryModal || !summaryModal.classList.contains('show')) {
            document.body.classList.remove('modal-open');
        }
    }

    returnDateModalOpenButtons.forEach(function (button) {
        button.addEventListener('click', openReturnDateModal);
    });

    [returnDateModalBackdrop, returnDateModalClose, returnDateModalCancel].forEach(function (element) {
        if (!element) {
            return;
        }
        element.addEventListener('click', closeReturnDateModal);
    });

    if (returnDateModal && String(returnDateModal.getAttribute('data-open-initial') || '').trim() === '1') {
        openReturnDateModal();
    }

    const summaryModal = document.getElementById('pengembalianSummaryModal');
    const summaryModalBackdrop = document.getElementById('pengembalianSummaryModalBackdrop');
    const summaryModalClose = document.getElementById('pengembalianSummaryModalClose');
    const summaryModalCancel = document.getElementById('pengembalianSummaryModalCancel');
    const openSummaryButton = document.getElementById('openPengembalianSummaryModal');
    const confirmSummaryButton = document.getElementById('confirmPengembalianSubmit');
    const summaryStepActionInput = form.querySelector('input[type="hidden"][name="step_action"]');
    const summaryMetaGrid = document.getElementById('summaryPengembalianMetaGrid');
    const summarySections = document.getElementById('summaryPengembalianSections');
    const summaryConfirmedInput = document.getElementById('pengembalianSummaryConfirmed');

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getDisplayValue(value) {
        const normalized = String(value == null ? '' : value).trim();
        if (!normalized || normalized === '0' || normalized === '0.0') {
            return '-';
        }
        return normalized;
    }

    function getOptionalNumericDisplayValue(value) {
        const normalized = String(value == null ? '' : value).trim();
        if (!normalized) {
            return '-';
        }
        const numericValue = Number(normalized);
        if (!Number.isNaN(numericValue) && numericValue === 0) {
            return '-';
        }
        return normalized;
    }

    function getSelectedText(select, fallbackValue) {
        if (select && select.selectedOptions && select.selectedOptions[0]) {
            const text = String(select.selectedOptions[0].text || '').trim();
            if (text && !/^pilih\b/i.test(text)) {
                return text;
            }
        }
        return getDisplayValue(fallbackValue || '-');
    }

    function buildSummaryGrid(items) {
        return (items || []).map(function (item) {
            return '<div class="' + escapeHtml(item.classes || 'detail-item') + '"><label>'
                + escapeHtml(item.label || '-') + '</label><p>' + escapeHtml(item.value || '-') + '</p></div>';
        }).join('');
    }

    function getSummaryTableClass(title) {
        const normalized = String(title || '').toLowerCase();
        if (normalized.includes('laboratorium')) {
            return 'table-mobile-scroll tbl-scroll--sum-lab';
        }
        if (normalized.includes('penunjang')) {
            return 'table-mobile-scroll tbl-scroll--sum-support';
        }
        if (normalized.includes('bahan')) {
            return 'table-mobile-scroll tbl-scroll--sum-material';
        }
        return 'table-mobile-scroll';
    }

    function buildSummaryTable(title, headers, rows) {
        if (!rows || !rows.length) {
            return '';
        }

        const tableClassName = getSummaryTableClass(title);
        const headerHtml = headers.map(function (header) {
            return '<th>' + escapeHtml(header) + '</th>';
        }).join('');

        const bodyHtml = rows.map(function (row) {
            return '<tr>' + row.map(function (cell) {
                return '<td>' + escapeHtml(getDisplayValue(cell)) + '</td>';
            }).join('') + '</tr>';
        }).join('');

        return '<div class="card loan-summary-section"><h3 class="card-title">' + escapeHtml(title)
            + '</h3><div class="table-scroll compact-table loan-summary-table-scroll"><table class="' + tableClassName + '"><thead><tr>' + headerHtml
            + '</tr></thead><tbody>' + bodyHtml + '</tbody></table></div></div>';
    }

    function getSummaryMetaItems() {
        const nomorPengajuan = document.querySelector('.detail-header-number')?.innerText.trim() || '-';
        const detailRows = Array.from(document.querySelectorAll('.detail-header-primary .detail-row'));
        const tanggalPeminjaman = detailRows[0]?.querySelector('.detail-value')?.innerText.trim() || '-';
        const tanggalPengembalian = detailRows[1]?.querySelector('.detail-value')?.innerText.trim() || '-';
        const prosesPengembalian = document.querySelectorAll('.detail-state .status-badge')[1]?.innerText.trim() || '-';
        const statusPengembalian = document.querySelector('.detail-state.detail-stat .detail-header-tile-value')?.innerText.trim() || '-';

        return [
            { label: 'Nomor Peminjaman', value: nomorPengajuan, classes: 'detail-item detail-item--span-2' },
            { label: 'Tanggal Peminjaman', value: tanggalPeminjaman, classes: 'detail-item detail-item--span-2' },
            { label: 'Tanggal Pengembalian', value: tanggalPengembalian, classes: 'detail-item detail-item--span-2' },
            { label: 'Proses Pengembalian', value: prosesPengembalian, classes: 'detail-item detail-item--span-3' },
            { label: 'Status Pengembalian Tercatat', value: statusPengembalian, classes: 'detail-item detail-item--span-3' },
        ];
    }

    function getLabSummaryRows() {
        return Array.from(form.querySelectorAll('tr[data-return-row-id^="lab_"]')).map(function (row) {
            const cells = row.querySelectorAll('td');
            const statusSelect = row.querySelector('.js-lab-status');
            const targetSelect = row.querySelector('.js-lab-transfer-target');
            return [
                cells[0] ? cells[0].innerText.trim() : '-',
                cells[6] ? cells[6].innerText.trim() : '-',
                cells[7] ? cells[7].innerText.trim() : '-',
                getSelectedText(statusSelect, '-'),
                statusSelect && statusSelect.value === 'transfer' ? getSelectedText(targetSelect, '-') : '-',
                cells[12] ? cells[12].innerText.trim() : '-',
                getReturnNote(row),
            ];
        });
    }

    function getQtyValueByRole(row, role) {
        const selector = '.js-return-qty[data-role="' + String(role || '').trim() + '"]';
        const input = row ? row.querySelector(selector) : null;
        return getDisplayValue(input && !input.disabled ? input.value : (input ? input.value : '-'));
    }

    function getTransferQtyValue(row) {
        const toggle = row ? row.querySelector('.js-transfer-toggle') : null;
        const input = row ? row.querySelector('.js-transfer-qty') : null;

        if (!toggle || !toggle.checked) {
            return '-';
        }

        return getDisplayValue(input && !input.disabled ? input.value : (input ? input.value : '-'));
    }

    function getTransferTargetText(row) {
        const targetSelect = row.querySelector('.js-transfer-target');
        const toggle = row.querySelector('.js-transfer-toggle');
        return toggle && toggle.checked ? getSelectedText(targetSelect, '-') : '-';
    }

    function getReturnNote(row) {
        const input = row ? row.querySelector('.js-return-note') : null;
        return getDisplayValue(input ? input.value : '-');
    }

    function getPenunjangSummaryRows() {
        return Array.from(form.querySelectorAll('.js-penunjang-row')).map(function (row) {
            const cells = row.querySelectorAll('td');
            return [
                cells[0] ? cells[0].innerText.trim() : '-',
                cells[3] ? cells[3].innerText.trim() : '-',
                cells[4] ? cells[4].innerText.trim() : '-',
                getQtyValueByRole(row, 'dikembalikan'),
                getQtyValueByRole(row, 'rusak'),
                getQtyValueByRole(row, 'hilang'),
                getTransferQtyValue(row),
                getTransferTargetText(row),
                cells[10] ? cells[10].innerText.trim() : '-',
                getReturnNote(row),
            ];
        });
    }


    function getPeralatanLabSummaryRows() {
        return Array.from(form.querySelectorAll('.js-peralatan-lab-row')).map(function (row) {
            const cells = row.querySelectorAll('td');
            return [
                cells[0] ? cells[0].innerText.trim() : '-',
                cells[3] ? cells[3].innerText.trim() : '-',
                cells[4] ? cells[4].innerText.trim() : '-',
                getQtyValueByRole(row, 'dikembalikan'),
                getQtyValueByRole(row, 'rusak'),
                getQtyValueByRole(row, 'hilang'),
                getTransferQtyValue(row),
                getTransferTargetText(row),
                cells[10] ? cells[10].innerText.trim() : '-',
                getReturnNote(row),
            ];
        });
    }

    function getBahanSummaryRows() {
        return Array.from(form.querySelectorAll('.js-bahan-row')).map(function (row) {
            const cells = row.querySelectorAll('td');
            return [
                cells[0] ? cells[0].innerText.trim() : '-',
                cells[1] ? cells[1].innerText.trim() : '-',
                cells[2] ? cells[2].innerText.trim() : '-',
                getQtyValueByRole(row, 'dikembalikan'),
                getTransferQtyValue(row),
                getTransferTargetText(row),
                cells[6] ? cells[6].innerText.trim() : '-',
                getReturnNote(row),
            ];
        });
    }

    function getPengukuranSummaryRows() {
        return Array.from(form.querySelectorAll('.pengukuran-grid .field-group')).map(function (group) {
            const label = group.querySelector('label');
            const input = group.querySelector('input');
            return [
                label ? label.innerText.trim() : '-',
                getOptionalNumericDisplayValue(input ? input.value : '-'),
            ];
        });
    }

    function populateSummaryModal() {
        if (summaryMetaGrid) {
            summaryMetaGrid.innerHTML = buildSummaryGrid(getSummaryMetaItems());
        }

        if (summarySections) {
            let html = '';
            html += buildSummaryTable('Data Peralatan Survei Lapangan', ['Nama Barang', 'Volume', 'Satuan', 'Status Pengembalian', 'Tujuan Transfer', 'Asal Peminjaman', 'Catatan Pengembalian'], getLabSummaryRows());
            html += buildSummaryTable('Data Barang Penunjang Lapangan', ['Nama Barang', 'Volume Dipinjam', 'Satuan', 'Dikembalikan', 'Rusak', 'Hilang', 'Transfer', 'Tujuan Transfer', 'Asal Peminjaman', 'Catatan Pengembalian'], getPenunjangSummaryRows());
            html += buildSummaryTable('Data Bahan Operasional', ['Nama Barang', 'Volume Dipinjam', 'Satuan', 'Dikembalikan', 'Transfer', 'Tujuan Transfer', 'Asal Peminjaman', 'Catatan Pengembalian'], getBahanSummaryRows());
            html += buildSummaryTable('Data Peralatan Laboratorium', ['Nama Barang', 'Volume Dipinjam', 'Satuan', 'Dikembalikan', 'Rusak', 'Hilang', 'Transfer', 'Tujuan Transfer', 'Asal Peminjaman', 'Catatan Pengembalian'], getPeralatanLabSummaryRows());
            html += buildSummaryTable('Data Pengukuran Lapangan', ['Jenis Pengukuran', 'Jumlah Titik/Lintasan'], getPengukuranSummaryRows());
            if (!html) {
                html = '<div class="card loan-summary-empty"><div class="empty-state">Belum ada data pengembalian yang dapat diringkas.</div></div>';
            }
            summarySections.innerHTML = html;
        }
    }

    function openSummaryModal() {
        if (!summaryModal) {
            return;
        }
        populateSummaryModal();
        summaryModal.classList.add('show');
        document.body.classList.add('modal-open');
    }

    function closeSummaryModal() {
        if (!summaryModal) {
            return;
        }
        summaryModal.classList.remove('show');
        document.body.classList.remove('modal-open');
    }

    [summaryModalBackdrop, summaryModalClose, summaryModalCancel].forEach(function (element) {
        if (!element) {
            return;
        }
        element.addEventListener('click', closeSummaryModal);
    });

    if (confirmSummaryButton) {
        confirmSummaryButton.addEventListener('click', function () {
            if (confirmSummaryButton.disabled) {
                return;
            }
            if (summaryConfirmedInput) {
                summaryConfirmedInput.value = '1';
            }
            closeSummaryModal();
            if (summaryStepActionInput && !String(summaryStepActionInput.value || '').trim()) {
                summaryStepActionInput.value = 'ajukan_pengembalian';
            }
            confirmSummaryButton.disabled = true;
            confirmSummaryButton.setAttribute('aria-busy', 'true');
            form.dispatchEvent(new CustomEvent('unsaved:submitted'));
            HTMLFormElement.prototype.submit.call(form);
        });
    }

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }
        if (summaryModal && summaryModal.classList.contains('show')) {
            closeSummaryModal();
        }
        if (returnDateModal && returnDateModal.classList.contains('show')) {
            closeReturnDateModal();
        }
    });

    const globalErrorsCard = document.getElementById('pengembalianGlobalErrors');
    const globalErrorsBody = document.getElementById('pengembalianGlobalErrorsBody');
    let summaryValidationInFlight = false;

    function reportFirstNativeInvalidField() {
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
            const firstInvalidField = form.querySelector(':invalid');
            if (firstInvalidField && typeof firstInvalidField.reportValidity === 'function') {
                firstInvalidField.reportValidity();
            } else if (typeof form.reportValidity === 'function') {
                form.reportValidity();
            }
            return false;
        }
        return true;
    }

    function clearGlobalReturnErrors() {
        if (!globalErrorsCard || !globalErrorsBody) {
            return;
        }
        globalErrorsBody.innerHTML = '';
        globalErrorsCard.hidden = true;
    }

    function renderGlobalReturnErrors(messages) {
        if (!globalErrorsCard || !globalErrorsBody) {
            return;
        }

        const items = Array.isArray(messages) ? messages.filter(Boolean) : [];
        globalErrorsBody.innerHTML = items.map(function (message) {
            return '<p class="input-error-text">*' + escapeHtml(String(message || '').replace(/^\*/, '').trim()) + '</p>';
        }).join('');
        globalErrorsCard.hidden = items.length === 0;
    }

    function clearAllReturnErrors() {
        clearGlobalReturnErrors();
        form.querySelectorAll('[data-return-field-group="true"]').forEach(function (group) {
            group.classList.remove('has-error');
        });
        form.querySelectorAll('[data-return-error-key]').forEach(function (cell) {
            cell.querySelectorAll('.input-error-text').forEach(function (node) {
                node.remove();
            });
            cell.hidden = true;
        });
        form.querySelectorAll('[data-return-error-row="true"]').forEach(function (errorRow) {
            errorRow.hidden = true;
        });
        form.querySelectorAll('[data-return-error-stack="true"]').forEach(function (stack) {
            stack.hidden = true;
        });
    }

    function getRowFieldElement(row, fieldKey) {
        if (!row) {
            return null;
        }

        switch (String(fieldKey || '').trim()) {
        case 'status':
            return row.querySelector('.js-lab-status') || row;
        case 'transfer_target':
            return row.querySelector('.js-lab-transfer-target, .js-transfer-target') || row;
        case 'dikembalikan':
            return row.querySelector('input[data-role="dikembalikan"]') || row;
        case 'rusak':
            return row.querySelector('input[data-role="rusak"]') || row;
        case 'hilang':
            return row.querySelector('input[data-role="hilang"]') || row;
        case 'transfer_qty':
            return row.querySelector('input[data-role="transfer"]') || row.querySelector('.js-transfer-toggle') || row;
        case 'note':
            return row.querySelector('.js-return-note') || row;
        case 'validation':
            return row.querySelector('.js-total-indicator') || row;
        default:
            return row;
        }
    }

    function applyServerValidationErrors(errorPayload) {
        clearAllReturnErrors();

        const payload = errorPayload || {};
        const globalMessages = []
            .concat(Array.isArray(payload.global) ? payload.global : [])
            .concat(Array.isArray(payload.catatan) ? payload.catatan : []);
        renderGlobalReturnErrors(globalMessages);

        let firstInvalidTarget = globalMessages.length && globalErrorsCard ? globalErrorsCard : null;
        const rows = payload.rows || {};

        Object.keys(rows).forEach(function (rowId) {
            const row = form.querySelector('[data-return-main-row="true"][data-return-row-id="' + rowId + '"]');
            const fieldMap = rows[rowId] || {};
            Object.keys(fieldMap).forEach(function (fieldKey) {
                const target = getRowFieldElement(row, fieldKey);
                const messages = Array.isArray(fieldMap[fieldKey]) ? fieldMap[fieldKey] : [];
                messages.forEach(function (message) {
                    markReturnFieldError(target, fieldKey, message);
                    if (!firstInvalidTarget) {
                        firstInvalidTarget = target;
                    }
                });
            });
            if (row) {
                syncReturnErrorRowVisibility(row);
            }
        });

        if (firstInvalidTarget && typeof firstInvalidTarget.scrollIntoView === 'function') {
            firstInvalidTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    async function validateBeforeOpeningSummary() {
        form.querySelectorAll('.js-penunjang-row, .js-peralatan-lab-row, .js-bahan-row').forEach(function (row) {
            syncQtyLimits(row);
        });

        if (!reportFirstNativeInvalidField()) {
            return false;
        }

        if (summaryStepActionInput && !String(summaryStepActionInput.value || '').trim()) {
            summaryStepActionInput.value = (openSummaryButton && openSummaryButton.dataset && openSummaryButton.dataset.stepActionValue)
                ? String(openSummaryButton.dataset.stepActionValue || '').trim()
                : 'ajukan_pengembalian';
        }

        const formData = new FormData(form);
        formData.set('validate_only', '1');

        try {
            const response = await fetch(form.getAttribute('action') || window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                throw new Error('VALIDATION_REQUEST_FAILED');
            }

            const payload = await response.json();
            if (!payload || payload.is_valid !== true) {
                applyServerValidationErrors(payload && payload.errors ? payload.errors : {});
                return false;
            }

            clearAllReturnErrors();
            return true;
        } catch (error) {
            console.error('Gagal memvalidasi pengembalian sebelum membuka ringkasan.', error);
            clearAllReturnErrors();
            renderGlobalReturnErrors(['Validasi pengembalian tidak dapat diproses. Silakan coba lagi.']);
            if (globalErrorsCard && typeof globalErrorsCard.scrollIntoView === 'function') {
                globalErrorsCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return false;
        }
    }

    function shouldBypassSummary() {
        return String(summaryConfirmedInput && summaryConfirmedInput.value || '0') === '1';
    }

    function hasSummaryFlow() {
        return Boolean(summaryModal && summaryConfirmedInput && openSummaryButton && summaryStepActionInput);
    }

    if (openSummaryButton) {
        openSummaryButton.addEventListener('click', async function (event) {
            if (!summaryModal || !summaryConfirmedInput || summaryValidationInFlight) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            summaryConfirmedInput.value = '0';
            summaryValidationInFlight = true;
            openSummaryButton.disabled = true;

            try {
                if (!await validateBeforeOpeningSummary()) {
                    return;
                }

                openSummaryModal();
            } finally {
                summaryValidationInFlight = false;
                openSummaryButton.disabled = false;
            }
        });
    }

    form.addEventListener('submit', async function (event) {
        if (!hasSummaryFlow()) {
            return;
        }

        if (shouldBypassSummary()) {
            return;
        }

        event.preventDefault();
        if (summaryValidationInFlight) {
            return;
        }

        summaryConfirmedInput.value = '0';
        summaryValidationInFlight = true;
        if (openSummaryButton) {
            openSummaryButton.disabled = true;
        }

        try {
            if (!await validateBeforeOpeningSummary()) {
                return;
            }

            openSummaryModal();
        } finally {
            summaryValidationInFlight = false;
            if (openSummaryButton) {
                openSummaryButton.disabled = false;
            }
        }
    });
}

/* ========================================
   HALAMAN PEMINJAMAN - FORM DINAMIS
======================================== */
function initPeminjamanFormBehavior() {
    const form = document.querySelector('[data-peminjaman-form="true"]');

    if (!form) {
        return;
    }

    const peminjamSelect = document.getElementById('id_peminjam_user');
    const peminjamOptionsScript = document.getElementById('peminjam-options-data');
    const peminjamDetailNodes = {
        nama: document.getElementById('peminjamDetailNama'),
        no_hp: document.getElementById('peminjamDetailNoHp'),
        email: document.getElementById('peminjamDetailEmail'),
        alamat: document.getElementById('peminjamDetailAlamat'),
    };
    const peminjamOptions = {};

    if (peminjamOptionsScript) {
        try {
            JSON.parse(peminjamOptionsScript.textContent || '[]').forEach(function (item) {
                if (item && item.id) {
                    peminjamOptions[String(item.id)] = item;
                }
            });
        } catch (error) {
            console.error('Data peminjam tidak dapat dibaca.', error);
        }
    }

    const surveiToggle = document.getElementById('id_gunakan_survei_lainnya');
    const surveiPanel = form.querySelector('[data-conditional-panel="survei-lainnya"]');
    const surveiInput = document.getElementById('id_survei_lainnya');
    const kegiatanSurveiGroup = form.querySelector('[name="kegiatan_survei"]')?.closest('.form-group')
        || form.querySelector('.choice-grid-list')?.closest('.form-group');
    const kegiatanSurveiInputs = form.querySelectorAll('input[name="kegiatan_survei"]');
    const labItemRows = form.querySelectorAll('[data-lab-item-row]');
    const labCategoryRows = form.querySelectorAll('[data-lab-category-group]');
    const labFilterEmptyRow = form.querySelector('[data-lab-filter-empty]');
    const inventorySheet = form.querySelector('[data-inventory-sheet]');
    const inventoryTabsWrap = form.querySelector('.inventory-sheet-tabs');
    const inventoryTabs = Array.from(form.querySelectorAll('[data-inventory-tab]'));
    const inventoryPanels = Array.from(form.querySelectorAll('[data-inventory-panel]'));
    const inventorySearch = form.querySelector('[data-inventory-search]');
    const inventorySearchClear = form.querySelector('[data-inventory-search-clear]');
    const inventorySearchResult = form.querySelector('[data-inventory-search-result]');
    const inventoryBacktop = form.querySelector('[data-inventory-backtop]');
    const alwaysVisibleLabCategories = new Set(['Pendukung Survei Lapangan']);
    const surveyToLabCategoryMap = {
        'borehole camera': ['Borehole Camera'],
        'drone rtk': ['Drone'],
        'drone video': ['Drone'],
        'geolistrik 1d': ['Geolistrik'],
        'geolistrik 2d': ['Geolistrik'],
        'kualitas air': ['Instrumen Keairan'],
        'debit air': ['Instrumen Keairan'],
        'mat (muka air tanah)': ['Instrumen Keairan'],
        'pumping test': ['Instrumen Keairan'],
        topografi: ['Topografi (TS)'],
        'logging test': ['Logging'],
        infiltrasi: ['Infiltrasi'],
    };

    const instansiSelect = document.getElementById('id_instansi_tujuan');
    const instansiToggle = document.getElementById('id_gunakan_instansi_lainnya');
    const instansiPanel = form.querySelector('[data-conditional-panel="instansi-lainnya"]');
    const instansiInput = document.getElementById('id_instansi_tujuan_lainnya');

    const layananInput = document.getElementById('id_layanan_kegiatan');
    const layananOtherInput = document.getElementById('id_layanan_kegiatan_lainnya');
    const layananOtherField = form.querySelector('[data-layanan-other-field]');
    const layananOtherResetButton = form.querySelector('[data-layanan-other-reset]');
    const layananOtherValue = layananInput ? (layananInput.dataset.otherValue || '__lainnya__') : '__lainnya__';
    const timInput = document.getElementById('id_tim_kegiatan');
    const tanggalMulaiInput = document.getElementById('id_tanggal_mulai');
    const tanggalSelesaiInput = document.getElementById('id_tanggal_selesai');

    const monthNamesLongId = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
    const monthNamesShortId = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const dayNamesShortId = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
    const monthLookup = {
        jan: 0, januari: 0, january: 0,
        feb: 1, februari: 1, february: 1,
        mar: 2, maret: 2, march: 2,
        apr: 3, april: 3,
        mei: 4, may: 4,
        jun: 5, juni: 5, june: 5,
        jul: 6, juli: 6, july: 6,
        agu: 7, agustus: 7, aug: 7, august: 7,
        sep: 8, sept: 8, september: 8,
        okt: 9, oktober: 9, oct: 9, october: 9,
        nov: 10, november: 10,
        des: 11, desember: 11, dec: 11, december: 11,
    };

    function getFormGroup(element) {
        return element ? element.closest('.form-group') : null;
    }

    function clearGroupErrors(group) {
        if (!group) {
            return;
        }

        group.classList.remove('has-error');
        group.querySelectorAll('.input-error-text').forEach(function (errorElement) {
            errorElement.remove();
        });
    }


    function addGroupError(group, message) {
        if (!group || !message) {
            return;
        }

        clearGroupErrors(group);
        group.classList.add('has-error');

        const normalizedMessage = String(message || '').trim();
        const errorElement = document.createElement('p');
        errorElement.className = 'input-error-text';
        errorElement.textContent = normalizedMessage.startsWith('*') ? normalizedMessage : `*${normalizedMessage}`;
        group.appendChild(errorElement);
    }

    function getSelectedPeminjamData() {
        if (!peminjamSelect) {
            return null;
        }

        return peminjamOptions[String(peminjamSelect.value || '')] || null;
    }

    function setPeminjamDetailValue(key, value) {
        const node = peminjamDetailNodes[key];
        if (node) {
            node.textContent = String(value || '-').trim() || '-';
        }
    }

    function syncPeminjamDetail() {
        if (!peminjamSelect) {
            return;
        }

        const data = getSelectedPeminjamData();
        setPeminjamDetailValue('nama', data ? data.nama : '-');
        setPeminjamDetailValue('no_hp', data ? data.no_hp : '-');
        setPeminjamDetailValue('email', data ? data.email : '-');
        setPeminjamDetailValue('alamat', data ? data.alamat : '-');
    }

    function validatePeminjamField() {
        if (!peminjamSelect) {
            return true;
        }

        const hasSelectedPeminjam = Boolean(String(peminjamSelect.value || '').trim());
        if (!hasSelectedPeminjam) {
            addGroupError(getFormGroup(peminjamSelect), 'Data peminjam wajib dipilih.');
            return false;
        }

        clearGroupErrors(getFormGroup(peminjamSelect));
        return true;
    }

    function createDateAtMidday(year, monthIndex, day) {
        const date = new Date(year, monthIndex, day, 12, 0, 0, 0);
        if (
            Number.isNaN(date.getTime()) ||
            date.getFullYear() !== year ||
            date.getMonth() !== monthIndex ||
            date.getDate() !== day
        ) {
            return null;
        }
        return date;
    }

    function parseDisplayDate(value) {
        const rawValue = String(value || '').trim();
        if (!rawValue) {
            return null;
        }

        let match = rawValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
        if (match) {
            return createDateAtMidday(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        }

        match = rawValue.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
        if (match) {
            return createDateAtMidday(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
        }

        match = rawValue.match(/^(\d{1,2})\s+([A-Za-zÀ-ÿ.]+)\s+(\d{4})$/);
        if (match) {
            const monthKey = String(match[2] || '').toLowerCase().replace(/\.$/, '');
            const monthIndex = monthLookup[monthKey];
            if (monthIndex === undefined) {
                return null;
            }
            return createDateAtMidday(Number(match[3]), monthIndex, Number(match[1]));
        }

        return null;
    }

    function formatDateForInput(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = monthNamesShortId[date.getMonth()] || monthNamesLongId[date.getMonth()] || String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day} ${month} ${year}`;
    }

    function formatDateForCalendarLabel(year, monthIndex) {
        return `${monthNamesLongId[monthIndex]} ${year}`;
    }

    function formatDateForComparison(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function getComparableDateInputValue(value) {
        const rawValue = String(value || '').trim();
        if (!rawValue) {
            return '';
        }

        const parsedDate = parseDisplayDate(rawValue);
        if (parsedDate) {
            return formatDateForComparison(parsedDate);
        }

        return `raw:${rawValue}`;
    }

    function clearTanggalSelesaiValue(options) {
        if (!tanggalSelesaiInput) {
            return;
        }

        const config = options || {};
        tanggalSelesaiInput.value = '';
        tanggalSelesaiInput.setCustomValidity('');
        clearGroupErrors(getFormGroup(tanggalSelesaiInput));

        if (!config.silent) {
            tanggalSelesaiInput.dispatchEvent(new Event('input', { bubbles: true }));
            tanggalSelesaiInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function getMinimumDateForInput(input) {
        if (!input || input !== tanggalSelesaiInput || !tanggalMulaiInput) {
            return null;
        }

        return parseDisplayDate(tanggalMulaiInput.value);
    }

    function setInputDateValue(input, date, options) {
        if (!input || !date) {
            return;
        }

        const config = options || {};
        input.value = formatDateForInput(date);

        if (!config.silent) {
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function normalizeDateInputValue(input) {
        if (!input) {
            return null;
        }

        const parsedDate = parseDisplayDate(input.value);
        if (parsedDate) {
            input.value = formatDateForInput(parsedDate);
        }
        return parsedDate;
    }

    function syncConditionalPanel(toggle, panel, input) {
        if (!toggle || !panel || !input) {
            return;
        }

        const shouldShow = toggle.checked || Boolean((input.value || '').trim());
        panel.classList.toggle('is-active', shouldShow);
        input.disabled = !shouldShow;
    }

    function syncInstansiState() {
        if (!instansiSelect || !instansiToggle || !instansiPanel || !instansiInput) {
            return;
        }

        const hasSelectedInstansi = Boolean(instansiSelect.value);
        const hasManualInstansi = instansiToggle.checked || Boolean((instansiInput.value || '').trim());

        if (hasSelectedInstansi) {
            instansiToggle.checked = false;
            instansiToggle.disabled = true;
            instansiInput.value = '';
        } else {
            instansiToggle.disabled = false;
        }

        syncConditionalPanel(instansiToggle, instansiPanel, instansiInput);

        if (!hasSelectedInstansi) {
            instansiSelect.disabled = hasManualInstansi;
        } else {
            instansiSelect.disabled = false;
        }
    }

    function isLayananOtherMode() {
        if (!layananInput) {
            return false;
        }
        return String(layananInput.value || '') === layananOtherValue;
    }

    function syncSelectPlaceholderClass(select) {
        if (!select) {
            return;
        }
        select.classList.toggle('is-placeholder-state', !select.value);
    }

    function syncLayananOtherState(options) {
        if (!layananInput || !layananOtherInput || !layananOtherField) {
            return;
        }

        const config = options || {};
        const hasManualValue = Boolean(String(layananOtherInput.value || '').trim());
        const manualMode = isLayananOtherMode() || hasManualValue;

        if (manualMode && layananInput.value !== layananOtherValue) {
            layananInput.value = layananOtherValue;
        }

        layananOtherField.classList.toggle('is-manual-mode', manualMode);
        layananOtherInput.disabled = !manualMode;

        if (!manualMode) {
            layananOtherInput.value = '';
        } else if (config.focusInput) {
            layananOtherInput.focus();
        }

        syncSelectPlaceholderClass(layananInput);
    }

    function resetLayananToDropdown() {
        if (!layananInput || !layananOtherInput) {
            return;
        }
        layananInput.value = '';
        layananOtherInput.value = '';
        syncLayananOtherState();
        layananInput.dispatchEvent(new Event('change', { bubbles: true }));
        layananInput.focus();
    }

    function getLayananDisplayText() {
        const manualValue = String(layananOtherInput ? layananOtherInput.value : '').trim();
        if (manualValue) {
            return manualValue;
        }
        if (!layananInput || !layananInput.selectedOptions || !layananInput.selectedOptions[0]) {
            return '-';
        }
        const selectedText = String(layananInput.selectedOptions[0].text || '').trim();
        if (!selectedText || String(layananInput.value || '') === layananOtherValue) {
            return '-';
        }
        return selectedText;
    }

    function hasLayananValue() {
        const manualValue = String(layananOtherInput ? layananOtherInput.value : '').trim();
        const selectedValue = String(layananInput ? layananInput.value : '').trim();
        return Boolean(manualValue || (selectedValue && selectedValue !== layananOtherValue));
    }

    function hasSelectedKegiatanSurvei() {
        return Array.from(kegiatanSurveiInputs || []).some(function (checkbox) {
            return checkbox.checked;
        });
    }

    function normalizeSurveyLabel(value) {
        return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
    }

    function getSurveyChoiceLabel(checkbox) {
        if (!checkbox) {
            return '';
        }
        const card = checkbox.closest('.survey-choice-card');
        return card ? String(card.querySelector('span')?.innerText || '').trim() : '';
    }

    function getAllowedLabCategoriesBySurvey() {
        const allowedCategories = new Set(alwaysVisibleLabCategories);
        kegiatanSurveiInputs.forEach(function (checkbox) {
            if (!checkbox.checked) {
                return;
            }
            const categories = surveyToLabCategoryMap[normalizeSurveyLabel(getSurveyChoiceLabel(checkbox))] || [];
            categories.forEach(function (category) {
                allowedCategories.add(category);
            });
        });
        return allowedCategories;
    }

    function syncLabInventoryBySurvey(options) {
        const config = options || {};
        const allowedCategories = getAllowedLabCategoriesBySurvey();
        const visibleCategories = new Set();
        let visibleRowCount = 0;

        labItemRows.forEach(function (row) {
            const category = String(row.dataset.labCategory || '').trim();
            const shouldShow = allowedCategories.has(category);
            const checkbox = row.querySelector('input[name="lab_item_ids"]');

            row.classList.toggle('is-hidden', !shouldShow);
            if (shouldShow) {
                visibleRowCount += 1;
                visibleCategories.add(category);
            }

            if (!checkbox) {
                return;
            }

            const baseDisabled = checkbox.dataset.baseDisabled === 'true';
            if (!shouldShow && checkbox.checked) {
                checkbox.checked = false;
                if (!config.silent) {
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
            checkbox.disabled = !shouldShow || baseDisabled;
        });

        labCategoryRows.forEach(function (row) {
            const category = String(row.dataset.labCategory || '').trim();
            row.classList.toggle('is-hidden', !visibleCategories.has(category));
        });

        if (labFilterEmptyRow) {
            labFilterEmptyRow.classList.toggle('is-hidden', visibleRowCount > 0);
        }

        filterActiveInventory();
    }

    function getActiveInventoryPanel() {
        return inventoryPanels.find(function (panel) {
            return !panel.hidden;
        }) || null;
    }

    function filterActiveInventory() {
        const panel = getActiveInventoryPanel();
        if (!panel) {
            return;
        }

        const term = normalizeSearchText(inventorySearch?.value);
        const rows = Array.from(panel.querySelectorAll('[data-inventory-row]'));
        const groups = Array.from(panel.querySelectorAll('[data-inventory-group]'));
        const searchEmpty = panel.querySelector('[data-inventory-search-empty]');
        let baseVisibleCount = 0;
        let visibleCount = 0;

        rows.forEach(function (row) {
            const baseVisible = !row.classList.contains('is-hidden');
            const matches = !term || normalizeSearchText(row.textContent).includes(term);
            row.classList.toggle('is-search-hidden', !matches);
            if (baseVisible) {
                baseVisibleCount += 1;
                if (matches) {
                    visibleCount += 1;
                }
            }
        });

        groups.forEach(function (group) {
            let row = group.nextElementSibling;
            let hasVisibleItem = false;
            while (row && !row.matches('[data-inventory-group]')) {
                if (row.matches('[data-inventory-row]')
                    && !row.classList.contains('is-hidden')
                    && !row.classList.contains('is-search-hidden')) {
                    hasVisibleItem = true;
                    break;
                }
                row = row.nextElementSibling;
            }
            group.classList.toggle('is-search-hidden', !hasVisibleItem);
        });

        if (searchEmpty) {
            searchEmpty.classList.toggle('is-hidden', !term || baseVisibleCount === 0 || visibleCount > 0);
        }
        if (inventorySearchClear) {
            inventorySearchClear.hidden = !term;
        }
        if (inventorySearchResult) {
            inventorySearchResult.textContent = term
                ? `${visibleCount} item ditemukan`
                : `${baseVisibleCount} item tersedia`;
        }
    }

    function updateInventorySearchLabel(key) {
        if (!inventorySearch) {
            return;
        }
        const activeTab = inventoryTabs.find(function (tab) {
            return tab.dataset.inventoryTab === key;
        });
        const label = String(activeTab?.textContent || 'item barang').trim();
        inventorySearch.placeholder = `Cari ${label}...`;
        inventorySearch.setAttribute('aria-label', `Cari item pada kategori ${label}`);
    }

    function updateInventoryBacktop() {
        if (!inventorySheet || !inventoryTabsWrap || !inventoryBacktop) {
            return;
        }
        const sheetRect = inventorySheet.getBoundingClientRect();
        const tabsRect = inventoryTabsWrap.getBoundingClientRect();
        const visible = tabsRect.bottom < 80 && sheetRect.bottom > 150;
        inventoryBacktop.style.setProperty('--inventory-backtop-left', `${sheetRect.left + (sheetRect.width / 2)}px`);
        inventoryBacktop.classList.toggle('is-visible', visible);
    }

    function activateInventoryTab(key, focusTab) {
        inventoryTabs.forEach(function (tab) {
            const active = tab.dataset.inventoryTab === key;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-selected', String(active));
            tab.tabIndex = active ? 0 : -1;
            if (active && focusTab) {
                tab.focus();
            }
        });

        inventoryPanels.forEach(function (panel) {
            const active = panel.dataset.inventoryPanel === key;
            panel.classList.toggle('is-active', active);
            panel.hidden = !active;
        });

        updateInventorySearchLabel(key);
        filterActiveInventory();
    }

    function initInventorySheet() {
        if (!inventoryTabs.length || !inventoryPanels.length) {
            return;
        }

        const initialTab = inventoryTabs.find(function (tab) {
            return tab.getAttribute('aria-selected') === 'true';
        }) || inventoryTabs[0];

        activateInventoryTab(initialTab.dataset.inventoryTab, false);

        inventoryTabs.forEach(function (tab, index) {
            tab.addEventListener('click', function () {
                activateInventoryTab(tab.dataset.inventoryTab, false);
            });

            tab.addEventListener('keydown', function (event) {
                let nextIndex = null;
                if (event.key === 'ArrowRight') {
                    nextIndex = (index + 1) % inventoryTabs.length;
                } else if (event.key === 'ArrowLeft') {
                    nextIndex = (index - 1 + inventoryTabs.length) % inventoryTabs.length;
                } else if (event.key === 'Home') {
                    nextIndex = 0;
                } else if (event.key === 'End') {
                    nextIndex = inventoryTabs.length - 1;
                }

                if (nextIndex === null) {
                    return;
                }

                event.preventDefault();
                activateInventoryTab(inventoryTabs[nextIndex].dataset.inventoryTab, true);
            });
        });

        inventorySearch?.addEventListener('input', filterActiveInventory);
        inventorySearchClear?.addEventListener('click', function () {
            inventorySearch.value = '';
            filterActiveInventory();
            inventorySearch.focus();
        });
        inventoryBacktop?.addEventListener('click', function () {
            inventoryTabsWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
            const activeTab = inventoryTabs.find(function (tab) {
                return tab.getAttribute('aria-selected') === 'true';
            });
            window.setTimeout(function () {
                activeTab?.focus({ preventScroll: true });
            }, 350);
        });
        window.addEventListener('scroll', updateInventoryBacktop, { passive: true });
        window.addEventListener('resize', updateInventoryBacktop);
        if (typeof ResizeObserver === 'function' && inventorySheet) {
            new ResizeObserver(updateInventoryBacktop).observe(inventorySheet);
        }
        updateInventoryBacktop();
    }

    function validateTanggalRange() {
        if (!tanggalMulaiInput || !tanggalSelesaiInput) {
            return {
                mulaiValid: true,
                selesaiValid: true,
                tanggalMulai: null,
                tanggalSelesai: null,
            };
        }

        const mulaiText = String(tanggalMulaiInput.value || '').trim();
        const selesaiText = String(tanggalSelesaiInput.value || '').trim();
        const tanggalMulai = normalizeDateInputValue(tanggalMulaiInput);
        const tanggalSelesai = normalizeDateInputValue(tanggalSelesaiInput);
        const mulaiKosong = mulaiText.length === 0;
        const selesaiKosong = selesaiText.length === 0;

        tanggalMulaiInput.setCustomValidity('');
        tanggalSelesaiInput.setCustomValidity('');

        let mulaiValid = true;
        let selesaiValid = true;

        if (!mulaiKosong && !tanggalMulai) {
            mulaiValid = false;
            tanggalMulaiInput.setCustomValidity('Gunakan format tanggal yang sah. Contoh: 01 Januari 2026 atau 01/01/2026.');
        }

        const shouldEnableTanggalSelesai = Boolean(tanggalMulai);
        tanggalSelesaiInput.disabled = !shouldEnableTanggalSelesai;

        if (!shouldEnableTanggalSelesai) {
            tanggalSelesaiInput.value = '';
            return { mulaiValid, selesaiValid, tanggalMulai, tanggalSelesai: null };
        }

        if (tanggalMulai) {
            tanggalSelesaiInput.dataset.minDate = formatDateForComparison(tanggalMulai);
        } else {
            delete tanggalSelesaiInput.dataset.minDate;
        }

        if (selesaiKosong) {
            return { mulaiValid, selesaiValid, tanggalMulai, tanggalSelesai: null };
        }

        if (!tanggalSelesai) {
            selesaiValid = false;
            tanggalSelesaiInput.setCustomValidity('Gunakan format tanggal yang sah. Contoh: 01 Januari 2026 atau 01/01/2026.');
            return { mulaiValid, selesaiValid, tanggalMulai, tanggalSelesai };
        }

        if (tanggalMulai && tanggalSelesai && tanggalSelesai < tanggalMulai) {
            selesaiValid = false;
            tanggalSelesaiInput.setCustomValidity('Tanggal selesai tidak boleh lebih awal dari tanggal mulai.');
        }

        return { mulaiValid, selesaiValid, tanggalMulai, tanggalSelesai };
    }

    function validateActivityFields() {
        let isValid = true;

        if (!validatePeminjamField()) {
            isValid = false;
        }

        if (layananInput) {
            if (isLayananOtherMode()) {
                const layananOtherValueText = String(layananOtherInput ? layananOtherInput.value : '').trim();
                if (!layananOtherValueText) {
                    addGroupError(getFormGroup(layananInput), 'Silakan isi layanan kegiatan lainnya.');
                    isValid = false;
                }
            } else if (!hasLayananValue()) {
                addGroupError(getFormGroup(layananInput), 'Layanan kegiatan wajib dipilih.');
                isValid = false;
            }
        }

        if (timInput) {
            const timValue = String(timInput.value || '').trim();
            if (!timValue) {
                addGroupError(getFormGroup(timInput), 'Tim kegiatan pelaksana wajib dipilih.');
                isValid = false;
            }
        }

        const tanggalState = validateTanggalRange();
        const tanggalMulaiValue = String(tanggalMulaiInput ? tanggalMulaiInput.value : '').trim();
        const tanggalSelesaiValue = String(tanggalSelesaiInput ? tanggalSelesaiInput.value : '').trim();

        if (tanggalMulaiInput && !tanggalMulaiValue) {
            addGroupError(getFormGroup(tanggalMulaiInput), 'Mulai tanggal wajib diisi.');
            isValid = false;
        } else if (tanggalMulaiInput && !tanggalState.mulaiValid) {
            addGroupError(getFormGroup(tanggalMulaiInput), tanggalMulaiInput.validationMessage || 'Mulai tanggal tidak valid.');
            isValid = false;
        }

        if (tanggalSelesaiInput && !tanggalSelesaiValue) {
            addGroupError(getFormGroup(tanggalSelesaiInput), 'Selesai tanggal wajib diisi.');
            isValid = false;
        } else if (tanggalSelesaiInput && !tanggalState.selesaiValid) {
            addGroupError(getFormGroup(tanggalSelesaiInput), tanggalSelesaiInput.validationMessage || 'Selesai tanggal tidak valid.');
            isValid = false;
        }

        const surveiLainnyaValue = String(surveiInput ? surveiInput.value : '').trim();
        if (!hasSelectedKegiatanSurvei() && !surveiLainnyaValue) {
            addGroupError(kegiatanSurveiGroup, 'Pilih minimal satu kegiatan survei atau isi survei lainnya.');
            isValid = false;
        }
        if (surveiToggle && surveiToggle.checked && !surveiLainnyaValue) {
            addGroupError(getFormGroup(surveiInput), 'Silakan isi kegiatan survei lainnya.');
            isValid = false;
        }

        const instansiValue = String(instansiSelect ? instansiSelect.value : '').trim();
        const instansiLainnyaValue = String(instansiInput ? instansiInput.value : '').trim();
        if (!instansiValue && !instansiLainnyaValue) {
            addGroupError(getFormGroup(instansiSelect), 'Pilih instansi tujuan atau isi instansi lainnya.');
            isValid = false;
        }
        if (instansiToggle && instansiToggle.checked && !instansiLainnyaValue) {
            addGroupError(getFormGroup(instansiInput), 'Silakan isi instansi tujuan lainnya.');
            isValid = false;
        }
        if (instansiValue && instansiLainnyaValue) {
            addGroupError(getFormGroup(instansiSelect), 'Pilih salah satu: instansi dari daftar atau isi instansi lainnya.');
            addGroupError(getFormGroup(instansiInput), 'Kosongkan kolom instansi lainnya jika sudah memilih dari daftar.');
            isValid = false;
        }

        return isValid;
    }

    function updateRealtimeErrorState() {
        if (peminjamSelect && peminjamSelect.value) {
            clearGroupErrors(getFormGroup(peminjamSelect));
        }

        if (layananInput && hasLayananValue()) {
            clearGroupErrors(getFormGroup(layananInput));
        }

        if (timInput && timInput.value) {
            clearGroupErrors(getFormGroup(timInput));
        }

        const tanggalState = validateTanggalRange();
        if (tanggalState.mulaiValid && tanggalState.tanggalMulai) {
            clearGroupErrors(getFormGroup(tanggalMulaiInput));
        }
        if (tanggalState.selesaiValid && (!tanggalSelesaiInput.value || tanggalState.tanggalSelesai)) {
            clearGroupErrors(getFormGroup(tanggalSelesaiInput));
        }

        const surveiLainnyaValue = String(surveiInput ? surveiInput.value : '').trim();
        const kegiatanSurveiValid = hasSelectedKegiatanSurvei() || Boolean(surveiLainnyaValue);
        if (kegiatanSurveiValid) {
            clearGroupErrors(kegiatanSurveiGroup);
        }
        if (!surveiToggle || !surveiToggle.checked || surveiLainnyaValue) {
            clearGroupErrors(getFormGroup(surveiInput));
        }

        const instansiValue = String(instansiSelect ? instansiSelect.value : '').trim();
        const instansiLainnyaValue = String(instansiInput ? instansiInput.value : '').trim();
        const instansiValid = (Boolean(instansiValue) && !instansiLainnyaValue) || (!instansiValue && Boolean(instansiLainnyaValue));
        if (instansiValid) {
            clearGroupErrors(getFormGroup(instansiSelect));
            clearGroupErrors(getFormGroup(instansiInput));
        }
        if (!instansiToggle || !instansiToggle.checked || instansiLainnyaValue) {
            clearGroupErrors(getFormGroup(instansiInput));
        }
    }

    function setupDatePicker(input) {
        if (!input || input.dataset.datePickerReady === 'true') {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'date-picker-control';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'date-picker-toggle';
        toggleButton.setAttribute('aria-label', `Pilih ${input.getAttribute('aria-label') || input.getAttribute('placeholder') || 'tanggal'}`);
        toggleButton.innerHTML = '<i class="bi bi-calendar3"></i>';
        wrapper.appendChild(toggleButton);

        const popup = document.createElement('div');
        popup.className = 'date-picker-popup';
        popup.hidden = true;
        popup.innerHTML = `
            <div class="date-picker-header">
                <button type="button" class="date-picker-nav" data-calendar-nav="prev" aria-label="Bulan sebelumnya">&lsaquo;</button>
                <div class="date-picker-title" data-calendar-title="true"></div>
                <button type="button" class="date-picker-nav" data-calendar-nav="next" aria-label="Bulan berikutnya">&rsaquo;</button>
            </div>
            <div class="date-picker-weekdays" data-calendar-weekdays="true"></div>
            <div class="date-picker-grid" data-calendar-grid="true"></div>
            <div class="date-picker-footer">
                <button type="button" class="date-picker-footer-btn" data-calendar-action="today">Hari ini</button>
                <button type="button" class="date-picker-footer-btn" data-calendar-action="clear">Kosongkan</button>
            </div>
        `;
        wrapper.appendChild(popup);

        const title = popup.querySelector('[data-calendar-title="true"]');
        const weekdays = popup.querySelector('[data-calendar-weekdays="true"]');
        const grid = popup.querySelector('[data-calendar-grid="true"]');
        const prevButton = popup.querySelector('[data-calendar-nav="prev"]');
        const nextButton = popup.querySelector('[data-calendar-nav="next"]');
        const todayButton = popup.querySelector('[data-calendar-action="today"]');
        const clearButton = popup.querySelector('[data-calendar-action="clear"]');

        dayNamesShortId.forEach(function (dayName) {
            const dayElement = document.createElement('span');
            dayElement.className = 'date-picker-weekday';
            dayElement.textContent = dayName;
            weekdays.appendChild(dayElement);
        });

        const currentValue = parseDisplayDate(input.value);
        const initialDate = currentValue || new Date();
        const state = {
            year: initialDate.getFullYear(),
            month: initialDate.getMonth(),
        };

        function renderCalendar() {
            grid.innerHTML = '';
            title.textContent = formatDateForCalendarLabel(state.year, state.month);

            const firstDay = new Date(state.year, state.month, 1, 12, 0, 0, 0);
            const startOffset = firstDay.getDay();
            const daysInMonth = new Date(state.year, state.month + 1, 0, 12, 0, 0, 0).getDate();
            const selectedDate = parseDisplayDate(input.value);
            const minimumDate = getMinimumDateForInput(input);
            const today = new Date();
            const todayKey = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`;

            for (let index = 0; index < 42; index += 1) {
                const dayButton = document.createElement('button');
                dayButton.type = 'button';
                dayButton.className = 'date-picker-day';

                const dayNumber = index - startOffset + 1;
                if (dayNumber < 1 || dayNumber > daysInMonth) {
                    dayButton.classList.add('is-empty');
                    dayButton.tabIndex = -1;
                    dayButton.disabled = true;
                    grid.appendChild(dayButton);
                    continue;
                }

                const candidate = createDateAtMidday(state.year, state.month, dayNumber);
                if (!candidate) {
                    continue;
                }

                dayButton.textContent = String(dayNumber);
                dayButton.dataset.dateValue = formatDateForInput(candidate);

                const candidateKey = `${candidate.getFullYear()}-${candidate.getMonth()}-${candidate.getDate()}`;
                if (selectedDate && candidateKey === `${selectedDate.getFullYear()}-${selectedDate.getMonth()}-${selectedDate.getDate()}`) {
                    dayButton.classList.add('is-selected');
                }
                if (candidateKey === todayKey) {
                    dayButton.classList.add('is-today');
                }
                if (minimumDate && candidate.getTime() < minimumDate.getTime()) {
                    dayButton.disabled = true;
                    dayButton.classList.add('is-disabled');
                    dayButton.setAttribute('aria-disabled', 'true');
                    grid.appendChild(dayButton);
                    continue;
                }

                dayButton.addEventListener('click', function () {
                    setInputDateValue(input, candidate);
                    closePopup();
                    input.focus();
                });
                grid.appendChild(dayButton);
            }
        }

        function adjustPopupPosition() {
            popup.style.left = '0';
            popup.style.right = 'auto';

            const viewportPadding = 12;
            const rect = popup.getBoundingClientRect();
            const wrapperRect = wrapper.getBoundingClientRect();

            if (rect.right > window.innerWidth - viewportPadding) {
                const overflowRight = rect.right - (window.innerWidth - viewportPadding);
                popup.style.left = `${Math.min(0, -overflowRight)}px`;
            }

            const updatedRect = popup.getBoundingClientRect();
            if (updatedRect.left < viewportPadding) {
                popup.style.left = `${viewportPadding - wrapperRect.left}px`;
            }

            const finalRect = popup.getBoundingClientRect();
            if (finalRect.bottom > window.innerHeight - viewportPadding) {
                window.scrollBy({
                    top: finalRect.bottom - window.innerHeight + viewportPadding + 20,
                    behavior: 'smooth',
                });
            }
        }

        function openPopup() {
            const selectedDate = parseDisplayDate(input.value);
            const baseDate = selectedDate || new Date();
            state.year = baseDate.getFullYear();
            state.month = baseDate.getMonth();
            renderCalendar();
            popup.hidden = false;
            wrapper.classList.add('is-open');
            adjustPopupPosition();
            window.setTimeout(adjustPopupPosition, 0);
        }

        function closePopup() {
            popup.hidden = true;
            wrapper.classList.remove('is-open');
            popup.style.left = '';
            popup.style.right = '';
        }

        toggleButton.addEventListener('click', function (event) {
            event.preventDefault();
            if (popup.hidden) {
                openPopup();
                return;
            }
            closePopup();
        });

        prevButton.addEventListener('click', function () {
            if (state.month === 0) {
                state.month = 11;
                state.year -= 1;
            } else {
                state.month -= 1;
            }
            renderCalendar();
        });

        nextButton.addEventListener('click', function () {
            if (state.month === 11) {
                state.month = 0;
                state.year += 1;
            } else {
                state.month += 1;
            }
            renderCalendar();
        });

        todayButton.addEventListener('click', function () {
            setInputDateValue(input, new Date());
            closePopup();
            input.focus();
        });

        clearButton.addEventListener('click', function () {
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
            input.focus();
        });

        input.addEventListener('focus', function () {
            renderCalendar();
        });

        input.addEventListener('input', function () {
            renderCalendar();
        });

        document.addEventListener('click', function (event) {
            if (!wrapper.contains(event.target)) {
                closePopup();
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !popup.hidden) {
                closePopup();
            }
        });

        input.dataset.datePickerReady = 'true';
    }

    let lastTanggalMulaiComparableValue = getComparableDateInputValue(tanggalMulaiInput ? tanggalMulaiInput.value : '');

    syncPeminjamDetail();
    syncConditionalPanel(surveiToggle, surveiPanel, surveiInput);
    syncInstansiState();
    syncLayananOtherState();
    validateTanggalRange();
    updateRealtimeErrorState();

    [tanggalMulaiInput, tanggalSelesaiInput].forEach(function (dateInput) {
        setupDatePicker(dateInput);
    });

    if (peminjamSelect) {
        peminjamSelect.addEventListener('change', function () {
            syncPeminjamDetail();
            updateRealtimeErrorState();
        });
    }

    if (surveiToggle && surveiPanel && surveiInput) {
        surveiToggle.addEventListener('change', function () {
            if (!surveiToggle.checked) {
                surveiInput.value = '';
            }
            syncConditionalPanel(surveiToggle, surveiPanel, surveiInput);
            updateRealtimeErrorState();
        });

        surveiInput.addEventListener('input', function () {
            syncConditionalPanel(surveiToggle, surveiPanel, surveiInput);
            updateRealtimeErrorState();
        });
    }

    if (instansiToggle && instansiPanel && instansiInput) {
        instansiToggle.addEventListener('change', function () {
            if (!instansiToggle.checked) {
                instansiInput.value = '';
            }
            syncInstansiState();
            updateRealtimeErrorState();
        });

        instansiInput.addEventListener('input', function () {
            syncInstansiState();
            updateRealtimeErrorState();
        });
    }

    kegiatanSurveiInputs.forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            syncLabInventoryBySurvey();
            updateRealtimeErrorState();
        });
    });

    if (instansiSelect) {
        instansiSelect.addEventListener('change', function () {
            syncInstansiState();
            updateRealtimeErrorState();
        });
    }

    if (layananInput) {
        layananInput.addEventListener('change', function () {
            syncLayananOtherState({ focusInput: isLayananOtherMode() });
            updateRealtimeErrorState();
        });
    }

    if (layananOtherInput) {
        layananOtherInput.addEventListener('input', function () {
            syncLayananOtherState();
            updateRealtimeErrorState();
        });
    }

    if (layananOtherResetButton) {
        layananOtherResetButton.addEventListener('click', function () {
            resetLayananToDropdown();
            updateRealtimeErrorState();
        });
    }

    if (timInput) {
        timInput.addEventListener('change', updateRealtimeErrorState);
    }

    Array.from(form.querySelectorAll('input[name="lab_item_ids"], input[name^="penunjang_qty_"], input[name^="peralatan_lab_qty_"], input[name^="bahan_qty_"]')).forEach(function (input) {
        const handler = function () {
            if (hasInventorySelection()) {
                clearInventorySelectionError();
                return;
            }
            if (inventorySelectionError && !inventorySelectionError.hidden) {
                validateInventorySelection();
            }
        };
        input.addEventListener('change', handler);
        input.addEventListener('input', handler);
    });

    function setupQtySteppers() {
        initGlobalQtyStepperBehavior(form);
    }

    setupQtySteppers();

    if (tanggalMulaiInput && tanggalSelesaiInput) {
        ['input', 'change', 'blur'].forEach(function (eventName) {
            tanggalMulaiInput.addEventListener(eventName, function () {
                const currentTanggalMulaiComparableValue = getComparableDateInputValue(tanggalMulaiInput.value);
                if (currentTanggalMulaiComparableValue !== lastTanggalMulaiComparableValue) {
                    clearTanggalSelesaiValue({ silent: true });
                }

                validateTanggalRange();
                updateRealtimeErrorState();
                lastTanggalMulaiComparableValue = getComparableDateInputValue(tanggalMulaiInput.value);
            });

            tanggalSelesaiInput.addEventListener(eventName, function () {
                validateTanggalRange();
                updateRealtimeErrorState();
            });
        });
    }

    const summaryModal = document.getElementById('pengajuanSummaryModal');
    const summaryModalBackdrop = document.getElementById('pengajuanSummaryModalBackdrop');
    const summaryModalClose = document.getElementById('pengajuanSummaryModalClose');
    const summaryModalCancel = document.getElementById('pengajuanSummaryModalCancel');
    const openSummaryButton = document.getElementById('openPengajuanSummaryModal');
    const confirmSummaryButton = document.getElementById('confirmPengajuanSubmit');
    const summaryBorrowerGrid = document.getElementById('summaryBorrowerGrid');
    const summaryActivityGrid = document.getElementById('summaryActivityGrid');
    const summaryInventorySections = document.getElementById('summaryInventorySections');
    const inventorySelectionError = document.getElementById('inventorySelectionError');
    let isConfirmedSubmission = false;

    initInventorySheet();
    syncLabInventoryBySurvey({ silent: true });

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getSummaryTableClass(title) {
        const normalized = String(title || '').toLowerCase();
        if (normalized.includes('laboratorium')) {
            return 'table-mobile-scroll tbl-scroll--sum-lab';
        }
        if (normalized.includes('penunjang')) {
            return 'table-mobile-scroll tbl-scroll--sum-support';
        }
        if (normalized.includes('bahan')) {
            return 'table-mobile-scroll tbl-scroll--sum-material';
        }
        return 'table-mobile-scroll';
    }

    function buildSummaryTable(title, headers, rows) {
        if (!rows || !rows.length) {
            return '';
        }

        const tableClassName = getSummaryTableClass(title);
        const headerHtml = headers.map(function (header) {
            return `<th>${escapeHtml(header)}</th>`;
        }).join('');

        const bodyHtml = rows.map(function (row) {
            return `<tr>${row.map(function (cell) { return `<td>${escapeHtml(cell)}</td>`; }).join('')}</tr>`;
        }).join('');

        return `
            <div class="card loan-summary-section">
                <h3 class="card-title">${escapeHtml(title)}</h3>
                <div class="table-scroll compact-table loan-summary-table-scroll">
                    <table class="${tableClassName}">
                        <thead><tr>${headerHtml}</tr></thead>
                        <tbody>${bodyHtml}</tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function getSelectedLabRows() {
        return Array.from(form.querySelectorAll('input[name="lab_item_ids"]:checked')).map(function (input) {
            const row = input.closest('tr');
            const cells = row ? row.querySelectorAll('td') : [];
            return [
                cells[1] ? cells[1].innerText.trim() : '-',
                cells[2] ? cells[2].innerText.trim() : '-',
                cells[3] ? cells[3].innerText.trim() : '-',
                '1',
                cells[7] ? cells[7].innerText.trim() : '-',
            ];
        });
    }

    function getSelectedPenunjangRows() {
        return Array.from(form.querySelectorAll('input[name^="penunjang_qty_"]')).map(function (input) {
            const qty = Number.parseInt(String(input.value || '').trim(), 10);
            if (!qty || qty <= 0) {
                return null;
            }
            const row = input.closest('tr');
            const cells = row ? row.querySelectorAll('td') : [];
            return [
                cells[1] ? cells[1].innerText.trim() : '-',
                cells[2] ? cells[2].innerText.trim() : '-',
                String(qty),
            ];
        }).filter(Boolean);
    }


    function getSelectedPeralatanLabRows() {
        return Array.from(form.querySelectorAll('input[name^="peralatan_lab_qty_"]')).map(function (input) {
            const qty = Number.parseInt(String(input.value || '').trim(), 10);
            if (!qty || qty <= 0) {
                return null;
            }
            const row = input.closest('tr');
            const cells = row ? row.querySelectorAll('td') : [];
            return [
                cells[1] ? cells[1].innerText.trim() : '-',
                cells[2] ? cells[2].innerText.trim() : '-',
                cells[3] ? cells[3].innerText.trim() : '-',
                String(qty),
            ];
        }).filter(Boolean);
    }

    function getSelectedBahanRows() {
        return Array.from(form.querySelectorAll('input[name^="bahan_qty_"]')).map(function (input) {
            const qty = Number.parseInt(String(input.value || '').trim(), 10);
            if (!qty || qty <= 0) {
                return null;
            }
            const row = input.closest('tr');
            const cells = row ? row.querySelectorAll('td') : [];
            return [
                cells[1] ? cells[1].innerText.trim() : '-',
                String(qty),
                cells[3] ? cells[3].innerText.trim() : '-',
            ];
        }).filter(Boolean);
    }

    function hasInventorySelection() {
        return getSelectedLabRows().length > 0 || getSelectedPenunjangRows().length > 0 || getSelectedPeralatanLabRows().length > 0 || getSelectedBahanRows().length > 0;
    }

    function clearInventorySelectionError() {
        if (!inventorySelectionError) {
            return;
        }
        inventorySelectionError.innerHTML = '';
        inventorySelectionError.hidden = true;
        inventorySelectionError.classList.add('is-hidden');
    }

    function showInventorySelectionError(message) {
        if (!inventorySelectionError) {
            return;
        }
        inventorySelectionError.innerHTML = `<p class="input-error-text">*${escapeHtml(message)}</p>`;
        inventorySelectionError.hidden = false;
        inventorySelectionError.classList.remove('is-hidden');
    }

    function validateInventorySelection() {
        if (!hasInventorySelection()) {
            showInventorySelectionError('Pilih minimal satu barang atau bahan operasional untuk diajukan.');
            return false;
        }
        clearInventorySelectionError();
        return true;
    }


    function getTotalHariValue() {
        const tanggalMulai = normalizeDateInputValue(tanggalMulaiInput);
        const tanggalSelesai = normalizeDateInputValue(tanggalSelesaiInput);

        if (!tanggalMulai || !tanggalSelesai || tanggalSelesai < tanggalMulai) {
            return '-';
        }

        const millisecondsPerDay = 24 * 60 * 60 * 1000;
        const totalHari = Math.floor((tanggalSelesai.getTime() - tanggalMulai.getTime()) / millisecondsPerDay) + 1;
        return `${totalHari} hari`;
    }

    function buildSummaryActivityItems() {
        const layananLabel = form.querySelector(`label[for="${layananInput ? layananInput.id : ''}"]`)?.innerText.trim() || 'Layanan Kegiatan';
        const timLabel = form.querySelector(`label[for="${timInput ? timInput.id : ''}"]`)?.innerText.trim() || 'Tim Kegiatan Pelaksana';
        const berkasInput = form.querySelector('input[name="berkas_pendukung"]');
        const berkasLabel = form.querySelector(`label[for="${berkasInput ? berkasInput.id : ''}"]`)?.innerText.trim() || 'Berkas Pendukung';
        const instansiLabel = form.querySelector(`label[for="${instansiSelect ? instansiSelect.id : ''}"]`)?.innerText.trim() || 'Instansi Tujuan Kegiatan';
        const mulaiLabel = form.querySelector(`label[for="${tanggalMulaiInput ? tanggalMulaiInput.id : ''}"]`)?.innerText.trim() || 'Mulai Tanggal';
        const selesaiLabel = form.querySelector(`label[for="${tanggalSelesaiInput ? tanggalSelesaiInput.id : ''}"]`)?.innerText.trim() || 'Selesai Tanggal';

        const surveiValues = [];
        kegiatanSurveiInputs.forEach(function (checkbox) {
            if (checkbox.checked) {
                const card = checkbox.closest('.survey-choice-card');
                const labelText = card ? card.querySelector('span')?.innerText.trim() : '';
                if (labelText) {
                    surveiValues.push(labelText);
                }
            }
        });
        const surveiLainnyaValue = String(surveiInput ? surveiInput.value : '').trim();
        if (surveiLainnyaValue) {
            surveiValues.push(`Lainnya: ${surveiLainnyaValue}`);
        }

        const layananText = getLayananDisplayText();
        const timText = timInput && timInput.selectedOptions && timInput.selectedOptions[0] ? timInput.selectedOptions[0].text.trim() : '-';
        const currentBerkasName = form.querySelector('.document-file-link-wrap__title')?.innerText.trim() || '';
        const uploadedBerkasName = berkasInput && berkasInput.files && berkasInput.files[0] ? berkasInput.files[0].name : '';
        const berkasText = uploadedBerkasName || currentBerkasName || '-';
        const instansiText = String(instansiInput && instansiInput.value ? instansiInput.value : (instansiSelect && instansiSelect.selectedOptions && instansiSelect.selectedOptions[0] ? instansiSelect.selectedOptions[0].text.trim() : '-')).trim() || '-';

        return [
            { label: layananLabel, value: layananText, classes: 'detail-item detail-item--span-2' },
            { label: timLabel, value: timText, classes: 'detail-item detail-item--span-2' },
            { label: berkasLabel, value: berkasText, classes: 'detail-item detail-item--span-2' },
            { label: 'Kegiatan Survei', value: surveiValues.length ? surveiValues.join(', ') : '-', classes: 'detail-item detail-item-full' },
            { label: instansiLabel, value: instansiText, classes: 'detail-item detail-item-full' },
            { label: mulaiLabel, value: String(tanggalMulaiInput ? tanggalMulaiInput.value : '').trim() || '-', classes: 'detail-item detail-item--span-2' },
            { label: selesaiLabel, value: String(tanggalSelesaiInput ? tanggalSelesaiInput.value : '').trim() || '-', classes: 'detail-item detail-item--span-2' },
            { label: 'Total Hari', value: getTotalHariValue(), classes: 'detail-item detail-item--span-2' },
        ];
    }

    function populateSummaryModal() {
        if (summaryBorrowerGrid) {
            const borrowerItems = Array.from(form.querySelectorAll('[data-peminjam-detail-grid] .detail-item')).map(function (item) {
                const label = item.querySelector('label')?.innerText.trim() || '-';
                const value = item.querySelector('p')?.innerText.trim() || '-';
                return `<div class="detail-item"><label>${escapeHtml(label)}</label><p>${escapeHtml(value)}</p></div>`;
            });
            summaryBorrowerGrid.innerHTML = borrowerItems.join('');
        }

        if (summaryActivityGrid) {
            const activityItems = buildSummaryActivityItems().map(function (item) {
                return `<div class="${escapeHtml(item.classes)}"><label>${escapeHtml(item.label)}</label><p>${escapeHtml(item.value)}</p></div>`;
            });
            summaryActivityGrid.innerHTML = activityItems.join('');
        }

        if (summaryInventorySections) {
            const labRows = getSelectedLabRows();
            const penunjangRows = getSelectedPenunjangRows();
            const peralatanLabRows = getSelectedPeralatanLabRows();
            const bahanRows = getSelectedBahanRows();
            let html = '';

            html += buildSummaryTable('Data Peralatan Survei Lapangan yang Dipinjam', ['Nama Barang', 'Tipe / Merek', 'Kode Laboratorium', 'Volume', 'Tgl Perbaikan'], labRows);
            html += buildSummaryTable('Data Barang Penunjang Lapangan yang Dipinjam', ['Nama Barang', 'Tipe / Merek', 'Volume'], penunjangRows);
            html += buildSummaryTable('Data Bahan Operasional yang Dipinjam', ['Nama Barang', 'Volume', 'Satuan'], bahanRows);
            html += buildSummaryTable('Data Peralatan Laboratorium yang Dipinjam', ['Nama Barang', 'Tipe / Merek', 'Kode Laboratorium', 'Volume'], peralatanLabRows);

            if (!html) {
                html = '<div class="card loan-summary-empty"><div class="empty-state">Belum ada barang yang dipilih.</div></div>';
            }
            summaryInventorySections.innerHTML = html;
        }
    }

    function openSummaryModal() {
        if (!summaryModal) {
            return;
        }
        populateSummaryModal();
        summaryModal.classList.add('show');
        document.body.classList.add('modal-open');
    }

    function closeSummaryModal() {
        if (!summaryModal) {
            return;
        }
        summaryModal.classList.remove('show');
        document.body.classList.remove('modal-open');
    }

    if (openSummaryButton) {
        openSummaryButton.addEventListener('click', function () {
            updateRealtimeErrorState();
            const isActivityValid = validateActivityFields();
            const isInventoryValid = validateInventorySelection();
            if (!isActivityValid || !isInventoryValid) {
                const firstError = form.querySelector('.form-group.has-error .input-error-text');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return;
                }
                if (!isInventoryValid && inventorySelectionError) {
                    inventorySelectionError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return;
            }
            openSummaryModal();
        });
    }

    [summaryModalBackdrop, summaryModalClose, summaryModalCancel].forEach(function (element) {
        if (!element) {
            return;
        }
        element.addEventListener('click', closeSummaryModal);
    });

    if (confirmSummaryButton) {
        confirmSummaryButton.addEventListener('click', function () {
            clearInventorySelectionError();
            isConfirmedSubmission = true;
            closeSummaryModal();
            form.requestSubmit();
        });
    }

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && summaryModal && summaryModal.classList.contains('show')) {
            closeSummaryModal();
        }
    });

    form.addEventListener('submit', function (event) {
        if (isConfirmedSubmission) {
            isConfirmedSubmission = false;
            return;
        }

        const tanggalState = validateTanggalRange();
        updateRealtimeErrorState();
        const isActivityValid = validateActivityFields();
        const isInventoryValid = validateInventorySelection();

        if (!tanggalState.mulaiValid || !tanggalState.selesaiValid || !isActivityValid || !isInventoryValid) {
            event.preventDefault();
            const firstError = form.querySelector('.form-group.has-error .input-error-text');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else if (!isInventoryValid && inventorySelectionError) {
                inventorySelectionError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        event.preventDefault();
        openSummaryModal();
    });
}


function initUnsavedFormGuard() {
    const modal = document.getElementById('unsavedChangesModal');
    const backdrop = document.getElementById('unsavedChangesModalBackdrop');
    const closeButton = document.getElementById('unsavedChangesModalClose');
    const cancelButton = document.getElementById('unsavedChangesModalCancel');
    const confirmButton = document.getElementById('unsavedChangesModalConfirm');
    const title = document.getElementById('unsavedChangesModalTitle');
    const message = document.getElementById('unsavedChangesModalMessage');
    const warning = document.getElementById('unsavedChangesModalWarning');
    const editableSelector = 'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]), select, textarea';

    if (!modal) {
        return;
    }

    const forms = Array.from(document.forms).filter(function (form) {
        return String(form.method || '').toLowerCase() === 'post'
            && !form.matches('[data-unsaved-ignore]')
            && Boolean(form.querySelector(editableSelector));
    });
    if (!forms.length) {
        return;
    }

    let pendingNav = null;
    let leaving = false;
    let historyGuarded = false;
    const navType = window.performance.getEntriesByType?.('navigation')?.[0]?.type || '';
    const states = forms.map(function (form, index) {
        const identity = form.id || form.getAttribute('data-unsaved-key') || String(index);
        const action = form.getAttribute('action') || window.location.pathname;
        return {
            form: form,
            dirty: false,
            key: `silebat:form-draft:${window.location.pathname}:${action}:${identity}`,
        };
    });

    function getControls(form) {
        return Array.from(form.elements).filter(function (control) {
            return control.name
                && !control.disabled
                && control.name !== 'csrfmiddlewaretoken'
                && !['button', 'file', 'hidden', 'password', 'reset', 'submit'].includes(control.type);
        });
    }

    function saveDraft(state) {
        const controls = getControls(state.form).map(function (control) {
            return {
                name: control.name,
                type: control.type,
                value: control.value,
                checked: control.checked,
            };
        });
        try {
            window.sessionStorage.setItem(state.key, JSON.stringify({ controls: controls }));
        } catch (error) {
            console.warn('Draft form tidak dapat disimpan.', error);
        }
    }

    function clearDraft(state) {
        try {
            window.sessionStorage.removeItem(state.key);
        } catch (error) {
            console.warn('Draft form tidak dapat dihapus.', error);
        }
    }

    function clearAllDrafts() {
        states.forEach(clearDraft);
    }

    function restoreDraft(state) {
        if (navType !== 'reload') {
            clearDraft(state);
            return false;
        }

        let draft = null;
        try {
            draft = JSON.parse(window.sessionStorage.getItem(state.key) || 'null');
        } catch (error) {
            clearDraft(state);
            return false;
        }
        if (!draft || !Array.isArray(draft.controls)) {
            return false;
        }

        const controls = getControls(state.form);
        draft.controls.forEach(function (item, index) {
            const control = controls[index];
            if (!control || control.name !== item.name || control.type !== item.type) {
                return;
            }
            if (control.type === 'checkbox' || control.type === 'radio') {
                control.checked = Boolean(item.checked);
                return;
            }
            control.value = item.value;
        });
        controls.forEach(function (control) {
            control.dispatchEvent(new Event('change', { bubbles: true }));
        });
        state.dirty = true;
        return true;
    }

    function hasDirtyForm() {
        return states.some(function (state) {
            return state.dirty;
        });
    }

    function setModalMode(type) {
        const restored = type === 'restored';
        const reload = type === 'reload';
        title.textContent = restored ? 'Input Dipulihkan Setelah Reload' : (reload ? 'Konfirmasi Reload Halaman' : 'Konfirmasi Tinggalkan Halaman');
        message.textContent = restored
            ? 'Halaman telah direload. Data input yang belum disubmit berhasil dipulihkan.'
            : (reload
                ? 'Data yang sudah diinput belum disubmit. Draft akan dipulihkan setelah halaman direload.'
                : 'Data yang sudah diinput belum disimpan. Jika meninggalkan halaman, seluruh perubahan akan hilang.');
        warning.textContent = restored
            ? 'File dan kata sandi yang sebelumnya dipilih perlu diinput kembali.'
            : (reload ? 'Apakah Anda yakin ingin mereload halaman ini?' : 'Apakah Anda yakin ingin meninggalkan halaman ini?');
        cancelButton.textContent = restored ? 'Lanjutkan Input' : (reload ? 'Batalkan Reload' : 'Tetap di Halaman');
        confirmButton.textContent = restored ? 'Hapus Draft' : (reload ? 'Ya, Reload' : 'Ya, Tinggalkan');
    }

    function openModal(nav) {
        pendingNav = nav;
        setModalMode(nav?.type);
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        cancelButton.focus();
    }

    function closeModal() {
        modal.classList.remove('show');
        document.body.classList.remove('modal-open');
        pendingNav = null;
    }

    function restoreHistoryGuard() {
        if (historyGuarded && !leaving) {
            window.history.pushState({ unsavedFormGuard: true }, '', window.location.href);
        }
    }

    function markDirty(state) {
        state.dirty = true;
        saveDraft(state);
        if (!historyGuarded) {
            window.history.pushState({ unsavedFormGuard: true }, '', window.location.href);
            historyGuarded = true;
        }
    }

    let restored = false;
    states.forEach(function (state) {
        restored = restoreDraft(state) || restored;
    });
    if (restored) {
        window.history.pushState({ unsavedFormGuard: true }, '', window.location.href);
        historyGuarded = true;
        openModal({ type: 'restored' });
    }

    states.forEach(function (state) {
        state.form.addEventListener('input', function (event) {
            if (event.target.closest('[data-unsaved-ignore-field]')) {
                return;
            }
            markDirty(state);
        });
        state.form.addEventListener('change', function (event) {
            if (event.target.closest('[data-unsaved-ignore-field]')) {
                return;
            }
            markDirty(state);
        });
        state.form.addEventListener('submit', function (event) {
            queueMicrotask(function () {
                if (event.defaultPrevented) {
                    return;
                }
                states.forEach(function (item) {
                    item.dirty = false;
                });
                clearAllDrafts();
                leaving = true;
            });
        });
        state.form.addEventListener('unsaved:reset', function () {
            state.dirty = false;
            clearDraft(state);
        });
        state.form.addEventListener('unsaved:submitted', function () {
            states.forEach(function (item) {
                item.dirty = false;
            });
            clearAllDrafts();
            leaving = true;
        });
    });

    document.addEventListener('click', function (event) {
        if (!hasDirtyForm() || leaving || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }
        const link = event.target.closest('a[href]');
        if (!link || link.hasAttribute('download') || link.target === '_blank') {
            return;
        }
        const url = new URL(link.href, window.location.href);
        const sameDocument = url.pathname === window.location.pathname
            && url.search === window.location.search
            && url.hash !== window.location.hash;
        if (!['http:', 'https:'].includes(url.protocol) || sameDocument || url.href === window.location.href) {
            return;
        }
        event.preventDefault();
        openModal({ type: 'link', url: url.href });
    });

    window.addEventListener('popstate', function () {
        if (hasDirtyForm() && !leaving) {
            openModal({ type: 'back' });
        }
    });

    window.addEventListener('beforeunload', function (event) {
        if (!hasDirtyForm() || leaving) {
            return;
        }
        event.preventDefault();
        event.returnValue = '';
    });

    [backdrop, closeButton, cancelButton].forEach(function (element) {
        element.addEventListener('click', function () {
            if (pendingNav?.type === 'back') {
                restoreHistoryGuard();
            }
            closeModal();
        });
    });

    confirmButton.addEventListener('click', function () {
        const nav = pendingNav;
        if (nav?.type === 'restored') {
            clearAllDrafts();
            leaving = true;
            closeModal();
            window.location.reload();
            return;
        }

        leaving = true;
        closeModal();
        if (nav?.type === 'back') {
            clearAllDrafts();
            window.history.back();
            return;
        }
        if (nav?.type === 'reload') {
            window.location.reload();
            return;
        }
        if (nav?.url) {
            clearAllDrafts();
            window.location.assign(nav.url);
        }
    });

    document.addEventListener('keydown', function (event) {
        const reloadShortcut = event.key === 'F5'
            || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'r');
        if (reloadShortcut && hasDirtyForm() && !leaving) {
            event.preventDefault();
            openModal({ type: 'reload' });
            return;
        }
        if (event.key !== 'Escape' || !modal.classList.contains('show')) {
            return;
        }
        if (pendingNav?.type === 'back') {
            restoreHistoryGuard();
        }
        closeModal();
    });
}

function initConfirmSubmitForms() {
    const forms = document.querySelectorAll('[data-confirm-submit]');

    forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            const message = form.getAttribute('data-confirm-submit') || 'Apakah Anda yakin ingin melanjutkan?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
}



function initSortableListTables(root = document) {
    const selector = root.matches?.('.table-scroll--list') ? '.table-data' : '.table-scroll--list .table-data';
    const tables = root.querySelectorAll(selector);

    if (!tables.length) {
        return;
    }

    const monthMap = {
        jan: 0,
        feb: 1,
        mar: 2,
        apr: 3,
        mei: 4,
        jun: 5,
        jul: 6,
        agu: 7,
        ags: 7,
        aug: 7,
        sep: 8,
        okt: 9,
        oct: 9,
        nov: 10,
        des: 11,
        dec: 11,
    };

    function normalizeText(value) {
        return String(value || '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function parseLocalizedDate(text) {
        const normalized = normalizeText(text).toLowerCase();
        const match = normalized.match(/(\d{1,2})\s+([a-z]{3})\s+(\d{4})/i);

        if (!match) {
            return null;
        }

        const day = Number(match[1]);
        const month = monthMap[match[2]];
        const year = Number(match[3]);

        if (!Number.isFinite(day) || !Number.isFinite(year) || typeof month !== 'number') {
            return null;
        }

        return new Date(year, month, day).getTime();
    }

    function parseNumericValue(text) {
        const normalized = normalizeText(text);

        if (!normalized || normalized === '-') {
            return null;
        }

        const compact = normalized.replace(/\s+/g, '');

        if (/^-?\d+(?:[.,]\d+)?$/.test(compact)) {
            return Number(compact.replace(',', '.'));
        }

        return null;
    }

    function getCellRawValue(cell) {
        if (!cell) {
            return '';
        }

        const explicitValue = cell.getAttribute('data-sort-value');
        if (explicitValue !== null) {
            return explicitValue;
        }

        return normalizeText(cell.innerText || cell.textContent || '');
    }

    function inferSortType(rows, columnIndex) {
        const values = rows
            .map(function (row) {
                return getCellRawValue(row.cells[columnIndex]);
            })
            .filter(function (value) {
                return value && value !== '-';
            });

        if (!values.length) {
            return 'text';
        }

        const allNumeric = values.every(function (value) {
            return parseNumericValue(value) !== null;
        });

        if (allNumeric) {
            return 'number';
        }

        const allDates = values.every(function (value) {
            return parseLocalizedDate(value) !== null;
        });

        if (allDates) {
            return 'date';
        }

        return 'text';
    }

    function compareValues(valueA, valueB, sortType, direction) {
        const multiplier = direction === 'desc' ? -1 : 1;

        if (sortType === 'number') {
            const numberA = parseNumericValue(valueA);
            const numberB = parseNumericValue(valueB);

            if (numberA === null && numberB === null) {
                return 0;
            }
            if (numberA === null) {
                return 1;
            }
            if (numberB === null) {
                return -1;
            }

            if (numberA === numberB) {
                return 0;
            }

            return numberA > numberB ? multiplier : -multiplier;
        }

        if (sortType === 'date') {
            const dateA = parseLocalizedDate(valueA);
            const dateB = parseLocalizedDate(valueB);

            if (dateA === null && dateB === null) {
                return 0;
            }
            if (dateA === null) {
                return 1;
            }
            if (dateB === null) {
                return -1;
            }

            if (dateA === dateB) {
                return 0;
            }

            return dateA > dateB ? multiplier : -multiplier;
        }

        return valueA.localeCompare(valueB, 'id', { numeric: true, sensitivity: 'base' }) * multiplier;
    }

    tables.forEach(function (table, tableIndex) {
        const thead = table.tHead;
        const tbody = table.tBodies[0];

        if (!thead || !tbody || !thead.rows.length) {
            return;
        }

        const allRows = Array.from(tbody.rows);
        const sortableRows = allRows.filter(function (row) {
            return !row.querySelector('.empty-state');
        });

        sortableRows.forEach(function (row, rowIndex) {
            if (!row.dataset.originalIndex) {
                row.dataset.originalIndex = String(rowIndex);
            }
        });

        const headerCells = Array.from(thead.rows[0].cells);

        headerCells.forEach(function (th, columnIndex) {
            if (th.classList.contains('cell-action') || th.dataset.sortable === 'false') {
                return;
            }

            const headerLabel = normalizeText(th.textContent);
            if (!headerLabel) {
                return;
            }

            th.classList.add('is-sortable');
            th.removeAttribute('aria-sort');

            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'table-sort-button';
            button.setAttribute('aria-label', 'Urutkan kolom ' + headerLabel);
            button.dataset.sortDirection = 'none';
            button.dataset.columnIndex = String(columnIndex);
            button.dataset.tableIndex = String(tableIndex);

            const label = document.createElement('span');
            label.className = 'table-sort-button__label';
            label.textContent = headerLabel;

            const icon = document.createElement('span');
            icon.className = 'table-sort-button__icon';
            icon.innerHTML = '<i class="bi bi-arrow-down-up" aria-hidden="true"></i>';

            button.appendChild(label);
            button.appendChild(icon);

            th.textContent = '';
            th.appendChild(button);

            button.addEventListener('click', function () {
                const currentDirection = button.dataset.sortDirection || 'none';
                const nextDirection = currentDirection === 'asc' ? 'desc' : 'asc';
                const sortType = inferSortType(sortableRows, columnIndex);

                headerCells.forEach(function (headerCell) {
                    const headerButton = headerCell.querySelector('.table-sort-button');
                    const headerIcon = headerCell.querySelector('.table-sort-button__icon i');

                    if (!headerButton) {
                        return;
                    }

                    headerButton.dataset.sortDirection = 'none';
                    headerCell.removeAttribute('aria-sort');
                    headerCell.classList.remove('is-sorted-asc', 'is-sorted-desc');

                    if (headerIcon) {
                        headerIcon.className = 'bi bi-arrow-down-up';
                    }
                });

                button.dataset.sortDirection = nextDirection;
                th.setAttribute('aria-sort', nextDirection === 'asc' ? 'ascending' : 'descending');
                th.classList.add(nextDirection === 'asc' ? 'is-sorted-asc' : 'is-sorted-desc');

                const sortedRows = sortableRows.slice().sort(function (rowA, rowB) {
                    const valueA = getCellRawValue(rowA.cells[columnIndex]);
                    const valueB = getCellRawValue(rowB.cells[columnIndex]);
                    const comparison = compareValues(valueA, valueB, sortType, nextDirection);

                    if (comparison !== 0) {
                        return comparison;
                    }

                    return Number(rowA.dataset.originalIndex || 0) - Number(rowB.dataset.originalIndex || 0);
                });

                const activeIcon = button.querySelector('.table-sort-button__icon i');
                if (activeIcon) {
                    activeIcon.className = nextDirection === 'asc' ? 'bi bi-sort-down-alt' : 'bi bi-sort-up';
                }

                sortedRows.forEach(function (row) {
                    tbody.appendChild(row);
                });
            });
        });
    });
}

function initLocalListSearch() {
    const controls = document.querySelectorAll('[data-local-list-search]');

    controls.forEach(function (control) {
        const panel = control.closest('.table-panel');
        const table = panel?.querySelector('.table-scroll--list .table-data');
        const tbody = table?.tBodies[0];
        const input = control.querySelector('[data-local-list-search-input]');
        const clearButton = control.querySelector('[data-local-list-search-clear]');
        const result = control.querySelector('[data-local-list-search-result]');

        if (!table || !tbody || !input || !clearButton || !result) {
            return;
        }

        const rows = Array.from(tbody.rows).filter(function (row) {
            return !row.querySelector('.empty-state');
        });
        const columnCount = table.tHead?.rows[0]?.cells.length || 1;
        const emptyRow = document.createElement('tr');
        emptyRow.className = 'is-list-search-empty';
        emptyRow.hidden = true;
        emptyRow.innerHTML = `<td colspan="${columnCount}"><div class="empty-state">Data yang dicari tidak ditemukan.</div></td>`;
        tbody.appendChild(emptyRow);

        function filterRows() {
            const term = normalizeSearchText(input.value);
            let visibleCount = 0;

            rows.forEach(function (row) {
                const matches = !term || normalizeSearchText(row.textContent).includes(term);
                row.classList.toggle('is-list-search-hidden', !matches);
                visibleCount += matches ? 1 : 0;
            });

            clearButton.hidden = !term;
            emptyRow.hidden = !term || visibleCount > 0 || rows.length === 0;
            result.textContent = term
                ? `${visibleCount} data ditemukan`
                : `${rows.length} data tersedia`;
        }

        input.addEventListener('input', filterRows);
        clearButton.addEventListener('click', function () {
            input.value = '';
            filterRows();
            input.focus();
        });
        filterRows();
    });
}


/* ========================================
   IMPORT EXCEL MODAL (GLOBAL)
   Menangani buka/tutup, validasi, dan simpan import Excel untuk semua app.
======================================== */
function initBarangLaboratoriumImportModal() {
    const modals = Array.from(document.querySelectorAll('.import-data-modal[data-import-modal]'));

    if (!modals.length) {
        return;
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function initImportModal(modal) {
        const modalTarget = modal.id ? '#' + modal.id : '';
        const openButtons = Array.from(document.querySelectorAll('.js-import-data-btn')).filter(function (button) {
            const target = button.getAttribute('data-import-target');
            return target ? target === modalTarget : modals.length === 1;
        });
        const closeButton = modal.querySelector('[data-import-modal-close]');
        const cancelButton = modal.querySelector('[data-import-modal-cancel]');
        const backdrop = modal.querySelector('[data-import-modal-backdrop]');
        const form = modal.querySelector('[data-import-form]');
        const fileInput = modal.querySelector('[data-import-file-input], input[name="file_import"]');
        const feedback = modal.querySelector('[data-import-feedback]');
        const saveButton = form ? form.querySelector('button[name="import_action"][value="save"]') : null;
        const validateButton = form ? form.querySelector('button[name="import_action"][value="validate"]') : null;

        function openModal() {
            modal.classList.add('show');
            document.body.classList.add('body-verification-modal-open');
            modal.dataset.importModalOpen = 'true';
        }

        function closeModal() {
            modal.classList.remove('show');
            document.body.classList.remove('body-verification-modal-open');
            modal.dataset.importModalOpen = 'false';
        }

        function getImportFileGroup() {
            return fileInput ? fileInput.closest('.form-group') : null;
        }

        function getImportFileErrorNode() {
            const group = getImportFileGroup();
            if (!group) {
                return null;
            }

            let message = group.querySelector('[data-inline-file-error-node]');
            if (!message) {
                message = document.createElement('p');
                message.className = 'input-error-text';
                message.setAttribute('data-inline-file-error-node', 'true');
                group.appendChild(message);
            }
            return message;
        }

        function clearImportFileError() {
            const group = getImportFileGroup();
            const message = getImportFileErrorNode();
            if (message) {
                message.textContent = '';
                message.hidden = true;
                message.style.display = 'none';
            }
            if (group) {
                group.classList.remove('has-error');
            }
        }

        function showImportFileError(text) {
            const group = getImportFileGroup();
            const message = getImportFileErrorNode();
            if (!message) {
                return;
            }
            message.textContent = '*' + String(text || '').replace(/^\*/, '').trim();
            message.hidden = false;
            message.style.display = '';
            if (group) {
                group.classList.add('has-error');
            }
        }

        function renderFeedback(type, title, message, errors) {
            if (!feedback) {
                return;
            }

            const isSuccess = type === 'success';
            const items = Array.isArray(errors) ? errors : [];
            const listHtml = items.length
                ? '<ul>' + items.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>'
                : '';
            const messageHtml = message ? '<span>' + escapeHtml(message) + '</span>' : '';

            feedback.innerHTML = '<div class="import-validation-box ' + (isSuccess ? 'import-validation-success' : 'import-validation-error') + '">' +
                '<strong>' + escapeHtml(title) + '</strong>' +
                messageHtml +
                listHtml +
                '</div>';
        }

        function resetImportModalState(options) {
            const shouldClearFile = !options || options.clearFile !== false;
            const shouldClearFeedback = !options || options.clearFeedback !== false;

            if (shouldClearFile && fileInput) {
                fileInput.value = '';
                if (!shouldClearFeedback) {
                    fileInput.dataset.importKeepFeedbackOnce = 'true';
                }
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            }

            if (feedback && shouldClearFeedback) {
                feedback.innerHTML = '';
            }

            if (saveButton) {
                saveButton.disabled = true;
            }
        }

        function requestCancelValidation() {
            if (!form) {
                return;
            }
            const formData = new FormData();
            const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
            formData.append('import_action', 'cancel');
            if (csrfInput) {
                formData.append('csrfmiddlewaretoken', csrfInput.value);
            }

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
            }).catch(function () {});
        }

        function cancelAndCloseModal() {
            resetImportModalState({ clearFile: true });
            form?.dispatchEvent(new CustomEvent('unsaved:reset'));
            requestCancelValidation();
            closeModal();
        }

        function setButtonLoading(button, loading) {
            if (!button) {
                return;
            }
            button.classList.toggle('is-loading', Boolean(loading));
            if (loading) {
                button.disabled = true;
            }
        }

        openButtons.forEach(function (button) {
            button.addEventListener('click', openModal);
        });

        [closeButton, cancelButton, backdrop].forEach(function (element) {
            if (!element) {
                return;
            }
            element.addEventListener('click', cancelAndCloseModal);
        });

        if (modal.dataset.importModalOpen === 'true') {
            openModal();
        }

        if (fileInput) {
            fileInput.addEventListener('change', function () {
                clearImportFileError();
                const keepFeedbackOnce = fileInput.dataset.importKeepFeedbackOnce === 'true';
                if (keepFeedbackOnce) {
                    delete fileInput.dataset.importKeepFeedbackOnce;
                } else if (feedback) {
                    feedback.innerHTML = '';
                }
                if (saveButton) {
                    saveButton.disabled = true;
                }
            });
        }

        if (!form) {
            return;
        }

        form.addEventListener('submit', function (event) {
            const submitter = event.submitter;
            if (!submitter || !['validate', 'save'].includes(submitter.value)) {
                return;
            }

            event.preventDefault();

            if (submitter.value === 'validate' && (!fileInput || !fileInput.files || !fileInput.files.length)) {
                showImportFileError('File Excel wajib diupload.');
                if (feedback) {
                    feedback.innerHTML = '';
                }
                if (saveButton) {
                    saveButton.disabled = true;
                }
                return;
            }

            clearImportFileError();
            const formData = new FormData(form);
            formData.set('import_action', submitter.value);
            setButtonLoading(submitter, true);

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
            })
                .then(function (response) {
                    return response.json().catch(function () {
                        throw new Error('Respons server tidak valid.');
                    });
                })
                .then(function (payload) {
                    if (submitter.value === 'validate') {
                        if (payload.ok && payload.can_save) {
                            renderFeedback('success', 'Validasi berhasil.', payload.message || ((payload.total_rows || 0) + ' data siap disimpan.'), []);
                            if (saveButton) {
                                saveButton.disabled = false;
                            }
                        } else {
                            renderFeedback('error', 'Validasi belum berhasil.', payload.message || 'Periksa kembali file Excel import.', payload.errors || []);
                            if (saveButton) {
                                saveButton.disabled = true;
                            }
                        }
                        return;
                    }

                    if (submitter.value === 'save') {
                        if (payload.ok && payload.saved) {
                            renderFeedback('success', 'Simpan data berhasil.', payload.message || 'Data berhasil diimport.', []);
                            resetImportModalState({ clearFile: true, clearFeedback: false });
                            form.dispatchEvent(new CustomEvent('unsaved:submitted'));
                            window.setTimeout(function () {
                                window.location.href = payload.redirect_url || window.location.href;
                            }, 700);
                        } else {
                            renderFeedback('error', 'Simpan data belum berhasil.', payload.message || 'Data belum dapat disimpan.', payload.errors || []);
                            if (saveButton) {
                                saveButton.disabled = true;
                            }
                        }
                    }
                })
                .catch(function (error) {
                    renderFeedback('error', 'Proses import belum berhasil.', error.message || 'Terjadi kendala saat memproses file Excel.', []);
                    if (saveButton) {
                        saveButton.disabled = true;
                    }
                })
                .finally(function () {
                    submitter.classList.remove('is-loading');
                    if (submitter.value === 'validate' && validateButton) {
                        validateButton.disabled = false;
                    }
                });
        });
    }

    modals.forEach(initImportModal);

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }
        modals.forEach(function (modal) {
            if (!modal.classList.contains('show')) {
                return;
            }
            const cancelButton = modal.querySelector('[data-import-modal-cancel]');
            if (cancelButton) {
                cancelButton.click();
            }
        });
    });
}


/* ========================================
   NOTIFIKASI - FORM PENGUMUMAN
   Menyamakan field tanggal/waktu pengumuman dengan date picker form peminjaman.
======================================== */
function initNotificationAnnouncementFormBehavior() {
    const form = document.querySelector('[data-notif-announcement-form="true"]');

    if (!form) {
        return;
    }

    const startInput = document.getElementById('id_publish_start_at');
    const endInput = document.getElementById('id_publish_end_at');
    const monthNamesLongId = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
    const monthNamesShortId = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const dayNamesShortId = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
    const monthLookup = {
        jan: 0, januari: 0, january: 0,
        feb: 1, februari: 1, february: 1,
        mar: 2, maret: 2, march: 2,
        apr: 3, april: 3,
        mei: 4, may: 4,
        jun: 5, juni: 5, june: 5,
        jul: 6, juli: 6, july: 6,
        agu: 7, agustus: 7, aug: 7, august: 7,
        sep: 8, sept: 8, september: 8,
        okt: 9, oktober: 9, oct: 9, october: 9,
        nov: 10, november: 10,
        des: 11, desember: 11, dec: 11, december: 11,
    };

    function getFormGroup(element) {
        return element ? element.closest('.form-group') : null;
    }

    function clearGroupErrors(group) {
        if (!group) {
            return;
        }

        group.classList.remove('has-error');
        group.querySelectorAll('.input-error-text').forEach(function (errorElement) {
            errorElement.remove();
        });
    }

    function addGroupError(group, message) {
        if (!group || !message) {
            return;
        }

        clearGroupErrors(group);
        group.classList.add('has-error');

        const errorElement = document.createElement('p');
        errorElement.className = 'input-error-text';
        errorElement.dataset.clientError = 'true';
        errorElement.textContent = String(message || '').trim().startsWith('*') ? message : `*${message}`;
        group.appendChild(errorElement);
    }

    function getRequiredFields() {
        return Array.from(form.querySelectorAll('input[required], textarea[required], select[required]')).filter(function (field) {
            return field.type !== 'hidden' && !field.disabled;
        });
    }

    function getFieldLabel(field) {
        const label = field && field.id ? form.querySelector(`label[for="${field.id}"]`) : null;
        return label ? String(label.textContent || '').trim() : '';
    }

    function getRequiredMessage(field) {
        if (field && field.dataset.requiredMessage) {
            return field.dataset.requiredMessage;
        }

        const label = getFieldLabel(field);
        return label ? `${label} wajib diisi.` : 'Kolom ini wajib diisi.';
    }

    function validateRequiredFields(options) {
        const config = options || {};
        let isValid = true;

        getRequiredFields().forEach(function (field) {
            const group = getFormGroup(field);
            const value = String(field.value || '').trim();

            if (!config.silent) {
                clearGroupErrors(group);
                field.setCustomValidity('');
            }

            if (!value) {
                isValid = false;
                field.setCustomValidity(getRequiredMessage(field));
                if (!config.silent) {
                    addGroupError(group, field.validationMessage || getRequiredMessage(field));
                }
            }
        });

        return isValid;
    }

    function clearFieldErrorOnChange(field) {
        if (!field) {
            return;
        }

        field.setCustomValidity('');
        clearGroupErrors(getFormGroup(field));
    }

    function createDateAtMidday(year, monthIndex, day) {
        const date = new Date(year, monthIndex, day, 12, 0, 0, 0);
        if (
            Number.isNaN(date.getTime()) ||
            date.getFullYear() !== year ||
            date.getMonth() !== monthIndex ||
            date.getDate() !== day
        ) {
            return null;
        }
        return date;
    }

    function parseDatePart(value) {
        const rawValue = String(value || '').trim();
        if (!rawValue) {
            return null;
        }

        let match = rawValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
        if (match) {
            return createDateAtMidday(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        }

        match = rawValue.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
        if (match) {
            return createDateAtMidday(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
        }

        match = rawValue.match(/^(\d{1,2})\s+([A-Za-zÀ-ÿ.]+)\s+(\d{4})$/);
        if (match) {
            const monthKey = String(match[2] || '').toLowerCase().replace(/\.$/, '');
            const monthIndex = monthLookup[monthKey];
            if (monthIndex === undefined) {
                return null;
            }
            return createDateAtMidday(Number(match[3]), monthIndex, Number(match[1]));
        }

        return null;
    }

    function parseDateTime(value) {
        const rawValue = String(value || '').trim().replace(/,/g, ' ');
        if (!rawValue) {
            return null;
        }

        let match = rawValue.match(/^(.*?)[ T]+(\d{1,2}):(\d{2})(?::\d{2})?$/);
        if (!match) {
            return null;
        }

        const datePart = parseDatePart(match[1]);
        const hour = Number(match[2]);
        const minute = Number(match[3]);
        if (!datePart || hour < 0 || hour > 23 || minute < 0 || minute > 59) {
            return null;
        }

        return new Date(datePart.getFullYear(), datePart.getMonth(), datePart.getDate(), hour, minute, 0, 0);
    }

    function parseDisplayDate(value) {
        const parsedDateTime = parseDateTime(value);
        if (parsedDateTime) {
            return createDateAtMidday(parsedDateTime.getFullYear(), parsedDateTime.getMonth(), parsedDateTime.getDate());
        }
        return parseDatePart(value);
    }

    function formatDateForInput(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = monthNamesShortId[date.getMonth()] || String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day} ${month} ${year}`;
    }

    function formatDateTimeForInput(date, timeValue) {
        const timeText = timeValue || formatTimeFromDate(date) || '08:00';
        return `${formatDateForInput(date)} ${timeText}`;
    }

    function formatTimeFromDate(date) {
        if (!date) {
            return '';
        }
        const hour = String(date.getHours()).padStart(2, '0');
        const minute = String(date.getMinutes()).padStart(2, '0');
        return `${hour}:${minute}`;
    }

    function formatDateForCalendarLabel(year, monthIndex) {
        return `${monthNamesLongId[monthIndex]} ${year}`;
    }

    function dateOnlyKey(date) {
        return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
    }

    function getDefaultTimeForInput(input) {
        const parsed = parseDateTime(input ? input.value : '');
        if (parsed) {
            return formatTimeFromDate(parsed);
        }

        if (input === endInput) {
            const startDateTime = parseDateTime(startInput ? startInput.value : '');
            return startDateTime ? formatTimeFromDate(startDateTime) : '17:00';
        }

        return '08:00';
    }

    function getMinimumDateForInput(input) {
        if (!input || input !== endInput || !startInput) {
            return null;
        }
        return parseDisplayDate(startInput.value);
    }

    function setInputDateTimeValue(input, date, timeValue) {
        if (!input || !date) {
            return;
        }
        input.value = formatDateTimeForInput(date, timeValue || getDefaultTimeForInput(input));
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function normalizeDateTimeInputValue(input) {
        const parsedDateTime = parseDateTime(input ? input.value : '');
        if (input && parsedDateTime) {
            input.value = formatDateTimeForInput(parsedDateTime, formatTimeFromDate(parsedDateTime));
        }
        return parsedDateTime;
    }

    function getComparableDateTimeValue(value) {
        const parsedDateTime = parseDateTime(value);
        if (!parsedDateTime) {
            return String(value || '').trim() ? `raw:${String(value || '').trim()}` : '';
        }
        const year = parsedDateTime.getFullYear();
        const month = String(parsedDateTime.getMonth() + 1).padStart(2, '0');
        const day = String(parsedDateTime.getDate()).padStart(2, '0');
        const hour = String(parsedDateTime.getHours()).padStart(2, '0');
        const minute = String(parsedDateTime.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hour}:${minute}`;
    }

    function clearEndDateTimeValue() {
        if (!endInput) {
            return;
        }
        endInput.value = '';
        endInput.setCustomValidity('');
        clearGroupErrors(getFormGroup(endInput));
        endInput.dispatchEvent(new Event('input', { bubbles: true }));
        endInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function setupDateTimePicker(input) {
        if (!input || input.dataset.datePickerReady === 'true') {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'date-picker-control date-time-picker-control';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'date-picker-toggle';
        toggleButton.setAttribute('aria-label', 'Pilih tanggal dan waktu');
        toggleButton.innerHTML = '<i class="bi bi-calendar-event"></i>';
        wrapper.appendChild(toggleButton);

        const popup = document.createElement('div');
        popup.className = 'date-picker-popup date-time-picker-popup';
        popup.hidden = true;
        popup.innerHTML = `
            <div class="date-picker-header">
                <button type="button" class="date-picker-nav" data-date-prev aria-label="Bulan sebelumnya"><i class="bi bi-chevron-left"></i></button>
                <strong class="date-picker-title"></strong>
                <button type="button" class="date-picker-nav" data-date-next aria-label="Bulan berikutnya"><i class="bi bi-chevron-right"></i></button>
            </div>
            <div class="date-picker-weekdays"></div>
            <div class="date-picker-grid"></div>
            <div class="date-picker-time-row">
                <label>Waktu</label>
                <input type="time" class="date-picker-time-input" step="60">
            </div>
            <div class="date-picker-footer">
                <button type="button" class="date-picker-footer-btn" data-date-today>Hari Ini</button>
                <button type="button" class="date-picker-footer-btn" data-date-clear>Bersihkan</button>
            </div>
        `;
        wrapper.appendChild(popup);

        const title = popup.querySelector('.date-picker-title');
        const weekdays = popup.querySelector('.date-picker-weekdays');
        const grid = popup.querySelector('.date-picker-grid');
        const prevButton = popup.querySelector('[data-date-prev]');
        const nextButton = popup.querySelector('[data-date-next]');
        const todayButton = popup.querySelector('[data-date-today]');
        const clearButton = popup.querySelector('[data-date-clear]');
        const timeInput = popup.querySelector('.date-picker-time-input');
        const state = { year: new Date().getFullYear(), month: new Date().getMonth() };

        weekdays.innerHTML = dayNamesShortId.map(function (dayName) {
            return `<span class="date-picker-weekday">${dayName}</span>`;
        }).join('');

        function renderCalendar() {
            title.textContent = formatDateForCalendarLabel(state.year, state.month);
            grid.innerHTML = '';
            timeInput.value = getDefaultTimeForInput(input);

            const firstDay = new Date(state.year, state.month, 1);
            const startOffset = firstDay.getDay();
            const daysInMonth = new Date(state.year, state.month + 1, 0).getDate();
            const selectedDate = parseDisplayDate(input.value);
            const minimumDate = getMinimumDateForInput(input);
            const today = new Date();
            const todayKey = dateOnlyKey(today);

            for (let index = 0; index < 42; index += 1) {
                const dayButton = document.createElement('button');
                dayButton.type = 'button';
                dayButton.className = 'date-picker-day';

                const dayNumber = index - startOffset + 1;
                if (dayNumber < 1 || dayNumber > daysInMonth) {
                    dayButton.classList.add('is-empty');
                    dayButton.tabIndex = -1;
                    dayButton.disabled = true;
                    grid.appendChild(dayButton);
                    continue;
                }

                const candidate = createDateAtMidday(state.year, state.month, dayNumber);
                if (!candidate) {
                    continue;
                }

                dayButton.textContent = String(dayNumber);

                if (selectedDate && dateOnlyKey(candidate) === dateOnlyKey(selectedDate)) {
                    dayButton.classList.add('is-selected');
                }
                if (dateOnlyKey(candidate) === todayKey) {
                    dayButton.classList.add('is-today');
                }
                if (minimumDate && candidate.getTime() < minimumDate.getTime()) {
                    dayButton.disabled = true;
                    dayButton.classList.add('is-disabled');
                    dayButton.setAttribute('aria-disabled', 'true');
                    grid.appendChild(dayButton);
                    continue;
                }

                dayButton.addEventListener('click', function () {
                    setInputDateTimeValue(input, candidate, timeInput.value || getDefaultTimeForInput(input));
                    closePopup();
                    input.focus();
                });
                grid.appendChild(dayButton);
            }
        }

        function adjustPopupPosition() {
            popup.style.left = '0';
            popup.style.right = 'auto';

            const viewportPadding = 12;
            const rect = popup.getBoundingClientRect();
            const wrapperRect = wrapper.getBoundingClientRect();

            if (rect.right > window.innerWidth - viewportPadding) {
                const overflowRight = rect.right - (window.innerWidth - viewportPadding);
                popup.style.left = `${Math.min(0, -overflowRight)}px`;
            }

            const updatedRect = popup.getBoundingClientRect();
            if (updatedRect.left < viewportPadding) {
                popup.style.left = `${viewportPadding - wrapperRect.left}px`;
            }

            const finalRect = popup.getBoundingClientRect();
            if (finalRect.bottom > window.innerHeight - viewportPadding) {
                window.scrollBy({
                    top: finalRect.bottom - window.innerHeight + viewportPadding + 20,
                    behavior: 'smooth',
                });
            }
        }

        function openPopup() {
            const selectedDate = parseDisplayDate(input.value);
            const baseDate = selectedDate || new Date();
            state.year = baseDate.getFullYear();
            state.month = baseDate.getMonth();
            renderCalendar();
            popup.hidden = false;
            wrapper.classList.add('is-open');
            adjustPopupPosition();
            window.setTimeout(adjustPopupPosition, 0);
        }

        function closePopup() {
            popup.hidden = true;
            wrapper.classList.remove('is-open');
            popup.style.left = '';
            popup.style.right = '';
        }

        toggleButton.addEventListener('click', function (event) {
            event.preventDefault();
            if (popup.hidden) {
                openPopup();
                return;
            }
            closePopup();
        });

        prevButton.addEventListener('click', function () {
            if (state.month === 0) {
                state.month = 11;
                state.year -= 1;
            } else {
                state.month -= 1;
            }
            renderCalendar();
        });

        nextButton.addEventListener('click', function () {
            if (state.month === 11) {
                state.month = 0;
                state.year += 1;
            } else {
                state.month += 1;
            }
            renderCalendar();
        });

        todayButton.addEventListener('click', function () {
            setInputDateTimeValue(input, new Date(), timeInput.value || getDefaultTimeForInput(input));
            closePopup();
            input.focus();
        });

        clearButton.addEventListener('click', function () {
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            closePopup();
            input.focus();
        });

        timeInput.addEventListener('change', function () {
            const selectedDate = parseDisplayDate(input.value);
            if (selectedDate) {
                setInputDateTimeValue(input, selectedDate, timeInput.value || getDefaultTimeForInput(input));
            }
        });

        input.addEventListener('focus', renderCalendar);
        input.addEventListener('input', renderCalendar);
        window.addEventListener('resize', function () {
            if (!popup.hidden) {
                adjustPopupPosition();
            }
        });

        document.addEventListener('click', function (event) {
            if (!wrapper.contains(event.target)) {
                closePopup();
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !popup.hidden) {
                closePopup();
            }
        });

        input.dataset.datePickerReady = 'true';
    }

    function validateDateTimeRange(options) {
        const config = options || {};
        const startText = String(startInput ? startInput.value : '').trim();
        const endText = String(endInput ? endInput.value : '').trim();
        const startDate = normalizeDateTimeInputValue(startInput);
        const endDate = normalizeDateTimeInputValue(endInput);
        let isValid = true;

        if (startInput) {
            startInput.setCustomValidity('');
        }
        if (endInput) {
            endInput.setCustomValidity('');
        }

        if (!config.silent) {
            clearGroupErrors(getFormGroup(startInput));
            clearGroupErrors(getFormGroup(endInput));
        }

        if (!startText) {
            isValid = false;
            if (!config.silent) {
                addGroupError(getFormGroup(startInput), 'Mulai ditampilkan wajib diisi.');
            }
        } else if (!startDate) {
            isValid = false;
            startInput.setCustomValidity('Gunakan format tanggal dan waktu yang sah. Contoh: 01 Januari 2026 08:30 atau 01/01/2026 08:30.');
            if (!config.silent) {
                addGroupError(getFormGroup(startInput), startInput.validationMessage);
            }
        }

        if (endInput) {
            endInput.disabled = !startDate;
        }

        if (endText && !endDate) {
            isValid = false;
            endInput.setCustomValidity('Gunakan format tanggal dan waktu yang sah. Contoh: 01 Januari 2026 17:00 atau 01/01/2026 17:00.');
            if (!config.silent) {
                addGroupError(getFormGroup(endInput), endInput.validationMessage);
            }
        } else if (startDate && endDate && endDate < startDate) {
            isValid = false;
            endInput.setCustomValidity('Selesai ditampilkan tidak boleh lebih awal dari mulai ditampilkan.');
            if (!config.silent) {
                addGroupError(getFormGroup(endInput), endInput.validationMessage);
            }
        }

        return isValid;
    }

    getRequiredFields().forEach(function (field) {
        field.addEventListener('input', function () {
            clearFieldErrorOnChange(field);
        });
        field.addEventListener('change', function () {
            clearFieldErrorOnChange(field);
        });
    });

    [startInput, endInput].forEach(function (input) {
        setupDateTimePicker(input);
    });

    let lastStartComparableValue = getComparableDateTimeValue(startInput ? startInput.value : '');

    validateDateTimeRange({ silent: true });

    if (startInput) {
        const handleStartDateTimeChange = function () {
            const currentComparableValue = getComparableDateTimeValue(startInput.value);
            if (currentComparableValue !== lastStartComparableValue) {
                clearEndDateTimeValue();
            }
            validateDateTimeRange({ silent: true });
            lastStartComparableValue = getComparableDateTimeValue(startInput.value);
        };

        startInput.addEventListener('input', handleStartDateTimeChange);
        startInput.addEventListener('change', handleStartDateTimeChange);
        startInput.addEventListener('blur', function () {
            validateDateTimeRange({ silent: false });
        });
    }

    if (endInput) {
        endInput.addEventListener('input', function () {
            validateDateTimeRange({ silent: true });
        });
        endInput.addEventListener('change', function () {
            validateDateTimeRange({ silent: true });
        });
        endInput.addEventListener('blur', function () {
            validateDateTimeRange({ silent: false });
        });
    }

    form.addEventListener('submit', function (event) {
        const requiredValid = validateRequiredFields({ silent: false });
        const dateRangeValid = validateDateTimeRange({ silent: false });

        if (!requiredValid || !dateRangeValid) {
            event.preventDefault();
            const firstError = form.querySelector('.has-error input, .has-error textarea, .has-error select');
            if (firstError) {
                firstError.focus();
            }
        }
    });
}

function initMasterShowEntriesControl() {
    const forms = document.querySelectorAll('[data-master-entries-form="true"]');

    forms.forEach(function (form) {
        const selects = form.querySelectorAll('.js-show-entries-select, .js-master-filter-select');
        const search = form.querySelector('[data-master-search]');
        const searchClear = form.querySelector('[data-master-search-clear]');
        const pageInput = form.querySelector('input[name="page"]');
        let lastSearch = normalizeSearchText(search?.value);
        let searchTimer = null;
        let searchRequest = null;
        let composing = false;

        function submitForm() {
            if (pageInput) {
                pageInput.value = '1';
            }

            if (typeof form.requestSubmit === 'function') {
                form.requestSubmit();
            } else {
                form.submit();
            }
        }

        function getListRegion(root, targetForm) {
            const panel = targetForm.closest('.table-panel');
            const scope = panel || root;

            return {
                info: targetForm.closest('.master-list-controls')?.querySelector('.master-entries-info') || null,
                pagination: scope.querySelector('.master-pagination-bar'),
                result: scope.querySelector('.table-scroll--list') || scope.querySelector('.notif-list-card'),
            };
        }

        function getSearchUrl() {
            const url = new URL(form.action || window.location.href, window.location.href);
            url.search = '';

            new FormData(form).forEach(function (value, key) {
                url.searchParams.append(key, value);
            });

            return url;
        }

        async function updateSearchResult() {
            const value = normalizeSearchText(search?.value);
            if (!search || value === lastSearch) {
                return;
            }

            if (pageInput) {
                pageInput.value = '1';
            }

            searchRequest?.abort();
            const request = new AbortController();
            searchRequest = request;

            const currentRegion = getListRegion(document, form);
            if (!currentRegion.result) {
                submitForm();
                return;
            }

            const url = getSearchUrl();
            const start = search.selectionStart ?? search.value.length;
            const end = search.selectionEnd ?? start;
            currentRegion.result.setAttribute('aria-busy', 'true');

            try {
                const response = await fetch(url, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    signal: request.signal,
                });

                if (!response.ok) {
                    throw new Error(`Pencarian gagal dimuat (${response.status}).`);
                }

                const remoteDoc = new DOMParser().parseFromString(await response.text(), 'text/html');
                const remoteForm = remoteDoc.querySelector('[data-master-entries-form="true"]');
                if (!remoteForm) {
                    throw new Error('Form pencarian tidak ditemukan pada respons.');
                }

                const remoteRegion = getListRegion(remoteDoc, remoteForm);
                if (!remoteRegion.result) {
                    throw new Error('Hasil pencarian tidak ditemukan pada respons.');
                }

                const nextResult = document.importNode(remoteRegion.result, true);
                currentRegion.result.replaceWith(nextResult);

                if (currentRegion.pagination && remoteRegion.pagination) {
                    currentRegion.pagination.replaceWith(document.importNode(remoteRegion.pagination, true));
                } else if (currentRegion.pagination) {
                    currentRegion.pagination.remove();
                } else if (remoteRegion.pagination) {
                    nextResult.insertAdjacentElement('afterend', document.importNode(remoteRegion.pagination, true));
                }

                if (currentRegion.info && remoteRegion.info) {
                    currentRegion.info.innerHTML = remoteRegion.info.innerHTML;
                }

                lastSearch = value;
                window.history.replaceState(window.history.state, '', url);
                initSortableListTables(nextResult);
                if (document.activeElement === search) {
                    search.setSelectionRange(start, end);
                }
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error(error);
                }
            } finally {
                if (searchRequest === request) {
                    searchRequest = null;
                    getListRegion(document, form).result?.removeAttribute('aria-busy');
                }
            }
        }

        function scheduleSearch() {
            window.clearTimeout(searchTimer);
            searchRequest?.abort();
            if (composing) {
                return;
            }

            searchTimer = window.setTimeout(updateSearchResult, 350);
        }

        selects.forEach(function (select) {
            select.addEventListener('change', function () {
                if (!select.value) {
                    return;
                }

                submitForm();
            });
        });

        search?.addEventListener('compositionstart', function () {
            composing = true;
        });

        search?.addEventListener('compositionend', function () {
            composing = false;
            scheduleSearch();
        });

        search?.addEventListener('input', function () {
            const value = normalizeSearchText(search.value);
            if (searchClear) {
                searchClear.hidden = !value;
            }
            scheduleSearch();
        });

        search?.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter') {
                return;
            }

            event.preventDefault();
            window.clearTimeout(searchTimer);
            updateSearchResult();
        });

        searchClear?.addEventListener('click', function () {
            window.clearTimeout(searchTimer);
            search.value = '';
            searchClear.hidden = true;
            search.focus();
            updateSearchResult();
        });
    });
}
