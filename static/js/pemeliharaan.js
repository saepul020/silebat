document.addEventListener('DOMContentLoaded', function () {
    initPemeliharaanForm();
    initPemeliharaanSendModal();
});

function initPemeliharaanSendModal() {
    const modal = document.getElementById('maintSendModal');
    const form = document.getElementById('maintSendForm');
    const numberNode = modal?.querySelector('[data-maint-send-number]');
    const buttons = document.querySelectorAll('[data-maint-send-button]');
    const closeButtons = modal?.querySelectorAll('[data-maint-send-close]') || [];

    if (!modal || !form || !buttons.length) {
        return;
    }

    function openModal(button) {
        form.action = button.getAttribute('data-send-url') || '';
        if (numberNode) {
            numberNode.textContent = button.getAttribute('data-send-number') || '-';
        }
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
    }

    function closeModal() {
        modal.classList.remove('show');
        document.body.classList.remove('is-scroll-locked');
    }

    buttons.forEach(function (button) {
        button.addEventListener('click', function () {
            openModal(button);
        });
    });

    closeButtons.forEach(function (button) {
        button.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });
}

function initPemeliharaanForm() {
    const form = document.querySelector('[data-pemeliharaan-form="true"]');
    if (!form) {
        return;
    }

    const alatSelect = form.querySelector('#id_pilih_alat');
    const checkFieldset = form.querySelector('[data-check-fieldset]');
    const list = form.querySelector('[data-komponen-list]');
    const repairFieldset = form.querySelector('[data-repair-fieldset]');
    const repairList = form.querySelector('[data-repair-list]');
    const empty = form.querySelector('[data-pemeliharaan-empty]');
    const repairEmpty = form.querySelector('[data-repair-empty]');
    const dataNode = document.getElementById('pemeliharaan-components-data');
    const tanggalInput = form.querySelector('#id_tanggal_pemeriksaan');
    let componentsMap = {};
    let lastAlatValue = String(alatSelect?.value || '');
    let pendingAlatValue = '';

    try {
        componentsMap = JSON.parse(dataNode?.textContent || '{}');
    } catch (error) {
        console.error('Data komponen pemeliharaan tidak valid.', error);
    }

    function escapeHtml(value) {
        return String(value || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function getTanggalMulaiLabel() {
        const value = String(tanggalInput?.value || '').trim();
        return value ? value.replace('T', ' ') : '-';
    }

    function uploadBlock(index, name, label) {
        const inputId = 'id_' + name + '_' + index;
        return `
            <div class="master-upload-stack landing-upload-stack">
                <div class="upload-card landing-gallery-upload" data-maint-gallery data-gallery-max="3" data-gallery-label="${escapeHtml(label)}">
                    <div class="upload-card__head">
                        <label for="${inputId}">${escapeHtml(label)}</label>
                        <span class="landing-gallery-limit">Maksimal 3 foto, masing-masing 7 MB</span>
                    </div>
                    <div class="landing-gallery-picker">
                        <input type="file" name="${name}_${index}" id="${inputId}" class="landing-gallery-input" accept=".jpg,.jpeg,.png" multiple data-gallery-input>
                        <label for="${inputId}" class="landing-gallery-trigger" data-gallery-trigger>
                            <span class="landing-gallery-trigger__icon"><i class="bi bi-images"></i></span>
                            <span data-gallery-status>0/3 foto dipilih &middot; Tambah foto</span>
                        </label>
                    </div>
                    <p class="input-error-text" data-gallery-error hidden></p>
                    <div class="landing-gallery-strip" data-gallery-strip>
                        <div class="landing-gallery-new" data-gallery-new></div>
                        <div class="landing-gallery-empty" data-gallery-empty>
                            <i class="bi bi-images"></i>
                            <span>Belum ada foto dipilih</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function componentRow(index, component) {
        const safeComponent = escapeHtml(component);
        return `
            <section class="pemeliharaan-komponen" data-komponen-row data-index="${index}">
                <div class="pemeliharaan-komponen__head">
                    <h2>${safeComponent}</h2>
                    <span>Komponen Pemeriksaan</span>
                </div>
                <input type="hidden" name="komponen_${index}" value="${safeComponent}">
                <div class="form-row master-form-row master-form-row--1">
                    <div class="form-group">
                        <label for="id_kondisi_${index}">Kondisi Pemeliharaan</label>
                        <select name="kondisi_${index}" id="id_kondisi_${index}" class="form-control" data-kondisi-field data-preserve-placeholder="true" autocomplete="off" required>
                            <option value="">Pilih kondisi pemeliharaan</option>
                            <option value="Baik">Baik</option>
                            <option value="Perlu Perbaikan">Perlu Perbaikan</option>
                        </select>
                    </div>
                </div>
            </section>
        `;
    }

    function getRepairValues() {
        const values = {};
        repairList?.querySelectorAll('[data-repair-row]').forEach(function (row) {
            const index = row.getAttribute('data-index');
            values[index] = {};
            row.querySelectorAll('input:not([type="file"]), select, textarea').forEach(function (field) {
                values[index][field.name] = field.value;
            });
        });
        return values;
    }

    function repairRow(index, component, values) {
        const safeComponent = escapeHtml(component);
        const data = values?.[index] || {};
        const action = data['tindakan_' + index] || '';
        const uraianPerbaikan = data['uraian_perbaikan_' + index] || '';
        const tanggalSelesai = data['tanggal_selesai_perbaikan_' + index] || '';
        const uraianKerusakan = data['uraian_kerusakan_' + index] || '';

        return `
            <section class="pemeliharaan-komponen pemeliharaan-komponen--repair" data-repair-row data-index="${index}">
                <div class="pemeliharaan-komponen__head">
                    <h2>${safeComponent}</h2>
                    <span>Komponen Perbaikan</span>
                </div>
                <div class="form-row master-form-row master-form-row--1">
                    <div class="form-group">
                        <label for="id_tindakan_${index}">Tindakan Perbaikan</label>
                        <select name="tindakan_${index}" id="id_tindakan_${index}" class="form-control" data-action-field data-preserve-placeholder="true" autocomplete="off">
                            <option value="">Pilih tindakan perbaikan</option>
                            <option value="Perbaikan Mandiri" ${action === 'Perbaikan Mandiri' ? 'selected' : ''}>Perbaikan Mandiri</option>
                            <option value="Perbaikan Eksternal" ${action === 'Perbaikan Eksternal' ? 'selected' : ''}>Perbaikan Eksternal</option>
                        </select>
                    </div>
                </div>
                <div class="pemeliharaan-action-panel" data-action-panel="Perbaikan Mandiri" ${action === 'Perbaikan Mandiri' ? '' : 'hidden'}>
                    <div class="form-row master-form-row master-form-row--1">
                        <div class="form-group form-group-full">
                            <label for="id_uraian_perbaikan_${index}">Uraian Perbaikan</label>
                            <textarea name="uraian_perbaikan_${index}" id="id_uraian_perbaikan_${index}" class="form-control" rows="4" placeholder="Masukkan uraian perbaikan" autocomplete="off">${escapeHtml(uraianPerbaikan)}</textarea>
                        </div>
                    </div>
                    <div class="form-row master-form-row master-form-row--2">
                        <div class="form-group">
                            <label>Tanggal Perbaikan Mulai</label>
                            <input type="text" class="form-control is-readonly-field" value="${escapeHtml(getTanggalMulaiLabel())}" readonly aria-readonly="true">
                        </div>
                        <div class="form-group">
                            <label for="id_tanggal_selesai_perbaikan_${index}">Tanggal Perbaikan Selesai</label>
                            <input type="datetime-local" name="tanggal_selesai_perbaikan_${index}" id="id_tanggal_selesai_perbaikan_${index}" class="form-control" value="${escapeHtml(tanggalSelesai)}" autocomplete="off">
                        </div>
                    </div>
                    ${uploadBlock(index, 'dokumentasi_perbaikan', 'Dokumentasi Perbaikan')}
                </div>
                <div class="pemeliharaan-action-panel" data-action-panel="Perbaikan Eksternal" ${action === 'Perbaikan Eksternal' ? '' : 'hidden'}>
                    <div class="form-row master-form-row master-form-row--1">
                        <div class="form-group form-group-full">
                            <label for="id_uraian_kerusakan_${index}">Uraian Kerusakan</label>
                            <textarea name="uraian_kerusakan_${index}" id="id_uraian_kerusakan_${index}" class="form-control" rows="4" placeholder="Masukkan uraian kerusakan" autocomplete="off">${escapeHtml(uraianKerusakan)}</textarea>
                        </div>
                    </div>
                    ${uploadBlock(index, 'dokumentasi_kerusakan', 'Dokumentasi Kerusakan')}
                </div>
            </section>
        `;
    }

    function clearAreaErrors(target) {
        const area = target.closest?.('[data-komponen-row], [data-repair-row], .upload-card');
        area?.querySelectorAll('.pemeliharaan-komponen__errors, .input-error-text:not([data-gallery-error])').forEach(function (node) {
            node.remove();
        });
        area?.classList.remove('has-error');
    }

    function bindErrorClear(scope) {
        const root = scope || form;
        root.querySelectorAll('input, select, textarea').forEach(function (field) {
            if (field.dataset.errorClearReady === 'true') {
                return;
            }
            field.dataset.errorClearReady = 'true';
            field.addEventListener('input', function () {
                clearAreaErrors(field);
            });
            field.addEventListener('change', function () {
                clearAreaErrors(field);
            });
        });
    }

    function bindSelectPlaceholderState(scope) {
        const root = scope || form;
        root.querySelectorAll('select[data-preserve-placeholder="true"]').forEach(function (select) {
            function syncState() {
                select.classList.toggle('is-placeholder-state', !select.value);
            }

            syncState();
            if (select.dataset.placeholderReady === 'true') {
                return;
            }
            select.dataset.placeholderReady = 'true';
            select.addEventListener('change', syncState);
        });
    }

    function setPanelDisabled(panel, disabled) {
        panel.querySelectorAll('input, select, textarea, button').forEach(function (field) {
            field.disabled = disabled;
        });
    }

    function syncRepairRow(row) {
        const actionField = row.querySelector('[data-action-field]');
        row.querySelectorAll('[data-action-panel]').forEach(function (panel) {
            const isActive = actionField?.value === panel.getAttribute('data-action-panel');
            panel.hidden = !isActive;
            setPanelDisabled(panel, !isActive);
        });
    }

    function bindRepairRows(scope) {
        const root = scope || form;
        root.querySelectorAll('[data-repair-row]').forEach(function (row) {
            const actionField = row.querySelector('[data-action-field]');
            if (actionField?.dataset.repairReady !== 'true') {
                actionField.dataset.repairReady = 'true';
                actionField.addEventListener('change', function () {
                    syncRepairRow(row);
                });
            }
            syncRepairRow(row);
        });
        initPemeliharaanGallery(root);
        bindSelectPlaceholderState(root);
        bindErrorClear(root);
    }

    function getRepairNeededRows() {
        const rows = [];
        list?.querySelectorAll('[data-komponen-row]').forEach(function (row) {
            const conditionField = row.querySelector('[data-kondisi-field]');
            if (conditionField?.value !== 'Perlu Perbaikan') {
                return;
            }
            const index = row.getAttribute('data-index');
            const component = row.querySelector('input[type="hidden"]')?.value || row.querySelector('h2')?.textContent || '';
            rows.push({ index, component });
        });
        return rows;
    }

    function renderRepairRows() {
        if (!repairFieldset || !repairList) {
            return;
        }

        const values = getRepairValues();
        const rows = getRepairNeededRows();
        repairFieldset.hidden = rows.length === 0;
        if (repairEmpty) {
            repairEmpty.hidden = rows.length > 0;
        }
        repairList.innerHTML = rows.map(function (row) {
            return repairRow(row.index, row.component, values);
        }).join('');
        bindRepairRows(repairList);
    }

    function bindComponentRows(scope) {
        const root = scope || form;
        root.querySelectorAll('[data-komponen-row]').forEach(function (row) {
            const conditionField = row.querySelector('[data-kondisi-field]');
            if (conditionField?.dataset.conditionReady === 'true') {
                return;
            }
            conditionField.dataset.conditionReady = 'true';
            conditionField.addEventListener('change', function () {
                renderRepairRows();
            });
        });
        bindSelectPlaceholderState(root);
        bindErrorClear(root);
    }

    function renderComponents() {
        const components = componentsMap[String(alatSelect?.value || '')] || [];
        if (!list) {
            return;
        }
        list.innerHTML = components.map(function (component, index) {
            return componentRow(index, component);
        }).join('');
        if (checkFieldset) {
            checkFieldset.hidden = !alatSelect?.value;
        }
        if (empty) {
            empty.hidden = components.length > 0;
        }
        bindComponentRows(list);
        renderRepairRows();
    }

    function hasEnteredData() {
        if (form.querySelector('#id_dokumentasi_pemeriksaan')?.files?.length) {
            return true;
        }
        const conditionChanged = Array.from(form.querySelectorAll('[data-kondisi-field]')).some(function (field) {
            return field.value && field.value !== 'Baik';
        });
        if (conditionChanged) {
            return true;
        }
        const repairHasValue = Array.from(repairList?.querySelectorAll('input, select, textarea') || []).some(function (field) {
            if (field.type === 'file') {
                return field.files.length > 0;
            }
            return !field.readOnly && String(field.value || '').trim() !== '';
        });
        return repairHasValue;
    }

    function openAlatChangeModal(onConfirm) {
        const modal = document.getElementById('alatChangeModal');
        const confirmButton = document.getElementById('alatChangeModalConfirm');
        const closeTargets = [
            document.getElementById('alatChangeModalBackdrop'),
            document.getElementById('alatChangeModalClose'),
            document.getElementById('alatChangeModalCancel'),
        ].filter(Boolean);

        if (!modal || !confirmButton) {
            onConfirm();
            return;
        }

        function closeModal() {
            modal.classList.remove('show');
            document.body.classList.remove('is-scroll-locked');
            confirmButton.removeEventListener('click', confirmChange);
            closeTargets.forEach(function (target) {
                target.removeEventListener('click', closeModal);
            });
        }

        function confirmChange() {
            closeModal();
            onConfirm();
        }

        confirmButton.addEventListener('click', confirmChange);
        closeTargets.forEach(function (target) {
            target.addEventListener('click', closeModal);
        });
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
    }

    alatSelect?.addEventListener('change', function () {
        const nextValue = String(alatSelect.value || '');
        if (nextValue === lastAlatValue) {
            return;
        }

        pendingAlatValue = nextValue;
        if (hasEnteredData()) {
            alatSelect.value = lastAlatValue;
            openAlatChangeModal(function () {
                alatSelect.value = pendingAlatValue;
                lastAlatValue = pendingAlatValue;
                renderComponents();
            });
            return;
        }

        lastAlatValue = nextValue;
        renderComponents();
    });

    bindComponentRows(form);
    bindRepairRows(form);
    initPemeliharaanGallery(form);
}

function initPemeliharaanGallery(scope) {
    const controls = (scope || document).querySelectorAll('[data-maint-gallery]:not([data-gallery-ready="true"])');

    controls.forEach(function (control) {
        control.dataset.galleryReady = 'true';

        const input = control.querySelector('[data-gallery-input]');
        const preview = control.querySelector('[data-gallery-new]');
        const empty = control.querySelector('[data-gallery-empty]');
        const trigger = control.querySelector('[data-gallery-trigger]');
        const status = control.querySelector('[data-gallery-status]');
        const error = control.querySelector('[data-gallery-error]');
        const maxFiles = Number(control.getAttribute('data-gallery-max') || 3);
        const label = String(control.getAttribute('data-gallery-label') || 'Foto');
        const maxSize = 7 * 1024 * 1024;
        const allowed = ['jpg', 'jpeg', 'png'];
        let selectedFiles = [];
        let previewUrls = [];

        if (!input || !preview || !empty || !trigger || !status || !error) {
            return;
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
            control.querySelectorAll('.input-error-text:not([data-gallery-error])').forEach(function (node) {
                node.remove();
            });
        }

        function syncInput() {
            const transfer = new DataTransfer();
            selectedFiles.forEach(function (file) {
                transfer.items.add(file);
            });
            input.files = transfer.files;
        }

        function updateState() {
            const count = selectedFiles.length;
            const isFull = count >= maxFiles;
            status.textContent = count + '/' + maxFiles + ' foto dipilih' + (isFull ? ' \u00b7 Batas maksimal tercapai' : ' \u00b7 Tambah foto');
            control.classList.toggle('is-full', isFull);
            trigger.classList.toggle('is-full', isFull);
            trigger.setAttribute('aria-disabled', String(isFull));
            input.setAttribute('aria-disabled', String(isFull));
            input.tabIndex = isFull ? -1 : 0;
            empty.hidden = count > 0;
        }

        function validateFiles(files) {
            if (selectedFiles.length + files.length > maxFiles) {
                return label + ' maksimal ' + maxFiles + ' foto.';
            }
            for (const file of files) {
                const extension = String(file.name || '').split('.').pop().toLowerCase();
                if (!allowed.includes(extension)) {
                    return label + ' hanya boleh berupa file JPG, JPEG, atau PNG.';
                }
                if (file.size > maxSize) {
                    return 'Ukuran setiap ' + label + ' maksimal 7 MB.';
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
                const name = document.createElement('span');
                previewUrls.push(url);
                item.className = 'landing-gallery-thumb';
                image.src = url;
                image.alt = 'Preview ' + label + ' ' + (index + 1);
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
                name.className = 'landing-gallery-name';
                name.textContent = file.name;
                item.append(image, remove, name);
                preview.appendChild(item);
            });
            updateState();
        }

        input.addEventListener('change', function () {
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
        });
        input.addEventListener('click', function (event) {
            if (selectedFiles.length >= maxFiles) {
                event.preventDefault();
            }
        });

        renderSelection();
    });
}
