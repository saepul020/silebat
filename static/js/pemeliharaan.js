document.addEventListener('DOMContentLoaded', function () {
    initPemeliharaanForm();
    initPemeliharaanSubmit();
    initPemeliharaanSendModal();
    initPemeliharaanPhotoModal();
});

const MAINT_MONTH_SHORT_ID = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
const MAINT_MONTH_LONG_ID = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
const MAINT_DAY_SHORT_ID = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];

function parseMaintDate(value) {
    const rawValue = String(value || '').trim();
    if (!rawValue) {
        return null;
    }

    const isoMatch = rawValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (isoMatch) {
        return createMaintDate(Number(isoMatch[1]), Number(isoMatch[2]) - 1, Number(isoMatch[3]));
    }

    const numericMatch = rawValue.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
    if (numericMatch) {
        return createMaintDate(Number(numericMatch[3]), Number(numericMatch[2]) - 1, Number(numericMatch[1]));
    }

    const textMatch = rawValue.match(/^(\d{1,2})\s+([A-Za-zÀ-ÿ.]+)\s+(\d{4})$/);
    if (textMatch) {
        const monthKey = textMatch[2].toLowerCase().replace('.', '');
        const monthMap = {
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
        if (Object.prototype.hasOwnProperty.call(monthMap, monthKey)) {
            return createMaintDate(Number(textMatch[3]), monthMap[monthKey], Number(textMatch[1]));
        }
    }

    return null;
}

function createMaintDate(year, month, day) {
    const date = new Date(year, month, day, 12, 0, 0, 0);
    if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) {
        return null;
    }
    return date;
}

function formatMaintDate(date) {
    return [
        String(date.getDate()).padStart(2, '0'),
        MAINT_MONTH_SHORT_ID[date.getMonth()],
        date.getFullYear(),
    ].join(' ');
}

function maintDateKey(date) {
    return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function initPemeliharaanDatePickers(scope) {
    const controls = (scope || document).querySelectorAll('[data-maint-date-picker="true"]:not([data-date-picker-ready="true"])');

    controls.forEach(function (input) {
        const initialDate = parseMaintDate(input.value);
        if (initialDate) {
            input.value = formatMaintDate(initialDate);
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'date-picker-control pemeliharaan-date-picker';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'date-picker-toggle';
        toggleButton.setAttribute('aria-label', 'Pilih tanggal');
        toggleButton.innerHTML = '<i class="bi bi-calendar3"></i>';
        wrapper.appendChild(toggleButton);

        const popup = document.createElement('div');
        popup.className = 'date-picker-popup';
        popup.hidden = true;
        popup.innerHTML = `
            <div class="date-picker-header">
                <button type="button" class="date-picker-nav" data-maint-date-prev aria-label="Bulan sebelumnya">&lsaquo;</button>
                <div class="date-picker-title" data-maint-date-title></div>
                <button type="button" class="date-picker-nav" data-maint-date-next aria-label="Bulan berikutnya">&rsaquo;</button>
            </div>
            <div class="date-picker-weekdays" data-maint-date-weekdays></div>
            <div class="date-picker-grid" data-maint-date-grid></div>
            <div class="date-picker-footer">
                <button type="button" class="date-picker-footer-btn" data-maint-date-today>Hari ini</button>
                <button type="button" class="date-picker-footer-btn" data-maint-date-clear>Kosongkan</button>
            </div>
        `;
        wrapper.appendChild(popup);

        const title = popup.querySelector('[data-maint-date-title]');
        const weekdays = popup.querySelector('[data-maint-date-weekdays]');
        const grid = popup.querySelector('[data-maint-date-grid]');
        const prevButton = popup.querySelector('[data-maint-date-prev]');
        const nextButton = popup.querySelector('[data-maint-date-next]');
        const todayButton = popup.querySelector('[data-maint-date-today]');
        const clearButton = popup.querySelector('[data-maint-date-clear]');
        const minSource = input.dataset.maintMinSource
            ? document.getElementById(input.dataset.maintMinSource)
            : null;
        const baseDate = initialDate || new Date();
        const state = { year: baseDate.getFullYear(), month: baseDate.getMonth() };

        function getMinimumDate() {
            return parseMaintDate(minSource ? minSource.value : input.dataset.maintMinDate);
        }

        weekdays.innerHTML = MAINT_DAY_SHORT_ID.map(function (dayName) {
            return `<span class="date-picker-weekday">${dayName}</span>`;
        }).join('');

        function setInputDate(date) {
            input.value = formatMaintDate(date);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function renderCalendar() {
            grid.innerHTML = '';
            title.textContent = `${MAINT_MONTH_LONG_ID[state.month]} ${state.year}`;

            const selectedDate = parseMaintDate(input.value);
            const today = new Date();
            const todayKey = maintDateKey(today);
            const firstDay = new Date(state.year, state.month, 1, 12, 0, 0, 0);
            const startOffset = firstDay.getDay();
            const daysInMonth = new Date(state.year, state.month + 1, 0, 12, 0, 0, 0).getDate();
            const minimumDate = getMinimumDate();
            todayButton.disabled = Boolean(
                minimumDate && createMaintDate(
                    today.getFullYear(),
                    today.getMonth(),
                    today.getDate()
                ).getTime() < minimumDate.getTime()
            );

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

                const candidate = createMaintDate(state.year, state.month, dayNumber);
                if (!candidate) {
                    continue;
                }

                dayButton.textContent = String(dayNumber);
                if (selectedDate && maintDateKey(candidate) === maintDateKey(selectedDate)) {
                    dayButton.classList.add('is-selected');
                }
                if (maintDateKey(candidate) === todayKey) {
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
                    setInputDate(candidate);
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
            if (input.disabled) {
                return;
            }
            const selectedDate = parseMaintDate(input.value)
                || getMinimumDate() || new Date();
            state.year = selectedDate.getFullYear();
            state.month = selectedDate.getMonth();
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

        function syncMinSource() {
            if (!minSource) {
                return;
            }

            const minimumDate = getMinimumDate();
            const panel = input.closest('[data-action-panel]');
            const locked = !minimumDate || Boolean(panel?.hidden);
            input.disabled = locked;
            toggleButton.disabled = locked;
            input.setAttribute('aria-disabled', String(locked));
            toggleButton.setAttribute('aria-disabled', String(locked));

            if (locked) {
                if (!panel) input.value = '';
                closePopup();
                return;
            }

            const selectedDate = parseMaintDate(input.value);
            if (selectedDate && selectedDate.getTime() < minimumDate.getTime()) {
                input.value = '';
            }
            if (!selectedDate) {
                state.year = minimumDate.getFullYear();
                state.month = minimumDate.getMonth();
            }
            renderCalendar();
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
            setInputDate(new Date());
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
        if (minSource) {
            input.addEventListener('maint:date-sync', syncMinSource);
            minSource.addEventListener('input', syncMinSource);
            minSource.addEventListener('change', syncMinSource);
            syncMinSource();
        }
    });
}

function initPemeliharaanDigits(scope) {
    const inputs = (scope || document).querySelectorAll('[data-maint-digits="true"]');
    inputs.forEach(function (input) {
        function keepDigits() {
            input.value = String(input.value || '').replace(/\D+/g, '');
        }
        input.addEventListener('input', keepDigits);
        keepDigits();
    });
}

function initPemeliharaanPhotoModal() {
    const modal = document.querySelector('[data-maint-photo-modal]');
    const links = document.querySelectorAll('[data-maint-photo]');

    if (!modal || !links.length) {
        return;
    }

    const image = modal.querySelector('[data-photo-image]');
    const caption = modal.querySelector('[data-photo-caption]');
    const counter = modal.querySelector('[data-photo-counter]');
    const prevButton = modal.querySelector('[data-photo-prev]');
    const nextButton = modal.querySelector('[data-photo-next]');
    const closeButtons = modal.querySelectorAll('[data-photo-close]');
    const groups = {};
    let activeGroup = [];
    let activeIndex = 0;

    links.forEach(function (link) {
        const groupName = link.getAttribute('data-photo-group') || 'default';
        if (!groups[groupName]) {
            groups[groupName] = [];
        }
        groups[groupName].push(link);
    });

    function renderPhoto() {
        const link = activeGroup[activeIndex];
        if (!link || !image) {
            return;
        }

        const total = activeGroup.length;
        image.src = link.getAttribute('data-photo-src') || link.href;
        image.alt = link.getAttribute('data-photo-alt') || 'Dokumentasi pemeliharaan';
        if (caption) {
            caption.textContent = link.getAttribute('data-photo-caption') || image.alt;
        }
        if (counter) {
            counter.textContent = total > 1 ? `${activeIndex + 1} / ${total}` : '1 / 1';
        }
        [prevButton, nextButton].forEach(function (button) {
            if (!button) {
                return;
            }
            button.hidden = total <= 1;
            button.disabled = total <= 1;
        });
    }

    function openModal(groupName, index) {
        activeGroup = groups[groupName] || [];
        activeIndex = index;
        renderPhoto();
        modal.hidden = false;
        modal.classList.add('is-open');
        document.body.classList.add('is-scroll-locked');
    }

    function closeModal() {
        modal.classList.remove('is-open');
        modal.hidden = true;
        document.body.classList.remove('is-scroll-locked');
        if (image) {
            image.src = '';
        }
    }

    function showPhoto(nextIndex) {
        if (!activeGroup.length) {
            return;
        }
        activeIndex = (nextIndex + activeGroup.length) % activeGroup.length;
        renderPhoto();
    }

    links.forEach(function (link) {
        link.addEventListener('click', function (event) {
            const groupName = link.getAttribute('data-photo-group') || 'default';
            const group = groups[groupName] || [];
            const index = group.indexOf(link);
            event.preventDefault();
            openModal(groupName, Math.max(index, 0));
        });
    });

    prevButton?.addEventListener('click', function () {
        showPhoto(activeIndex - 1);
    });

    nextButton?.addEventListener('click', function () {
        showPhoto(activeIndex + 1);
    });

    closeButtons.forEach(function (button) {
        button.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (event) {
        if (modal.hidden) {
            return;
        }
        if (event.key === 'Escape') {
            closeModal();
            return;
        }
        if (event.key === 'ArrowLeft') {
            showPhoto(activeIndex - 1);
            return;
        }
        if (event.key === 'ArrowRight') {
            showPhoto(activeIndex + 1);
        }
    });
}

function initPemeliharaanSendModal() {
    const modal = document.getElementById('maintSendModal');
    const form = document.getElementById('maintSendForm');
    const numberNode = modal?.querySelector('[data-maint-send-number]');
    const targetNode = modal?.querySelector('[data-maint-send-target]');
    const buttons = document.querySelectorAll('[data-maint-send-button]');
    const incomplete = document.getElementById('maint-incomplete-modal');
    const incompleteNote = incomplete?.querySelector('[data-maint-incomplete-note]');
    const missingTitle = incomplete?.querySelector('[data-maint-missing-title]');
    const missingList = incomplete?.querySelector('[data-maint-missing-list]');
    const incompleteButtons = document.querySelectorAll('[data-maint-incomplete]');
    const closeButtons = document.querySelectorAll('[data-maint-send-close], [data-maint-incomplete-close]');
    let activeButton = null;

    if (!modal || !form || (!buttons.length && !incompleteButtons.length)) {
        return;
    }

    function openModal(button) {
        activeButton = button;
        form.action = button.getAttribute('data-send-url') || '';
        if (numberNode) {
            numberNode.textContent = button.getAttribute('data-send-number') || '-';
        }
        if (targetNode) {
            targetNode.textContent = button.getAttribute('data-send-target') || 'akan dikirim ke Kepala Lab untuk proses verifikasi';
        }
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
        modal.querySelector('.delete-modal-close')?.focus();
    }

    function closeModal() {
        modal.classList.remove('show');
        incomplete?.classList.remove('show');
        document.body.classList.remove('is-scroll-locked');
        activeButton?.focus();
    }

    incompleteButtons.forEach(function (button) {
        function openIncomplete() {
            if (!incomplete) return;
            activeButton = button;
            if (incompleteNote) {
                const label = button.dataset.incompleteLabel || 'Pengajuan Pemeliharaan';
                incompleteNote.textContent = `Silakan lengkapi Data ${label} terlebih dahulu.`;
            }
            if (missingList) {
                const fields = button.querySelector('[data-maint-missing]');
                missingList.replaceChildren();
                if (fields) missingList.appendChild(fields.content.cloneNode(true));
                missingList.hidden = !missingList.querySelector('li');
                if (missingTitle) missingTitle.hidden = missingList.hidden;
            }
            incomplete.classList.add('show');
            document.body.classList.add('is-scroll-locked');
            incomplete.querySelector('.delete-modal-close')?.focus();
        }
        button.addEventListener('click', openIncomplete);
        button.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openIncomplete();
            }
        });
    });

    buttons.forEach(function (button) {
        button.addEventListener('click', function () {
            openModal(button);
        });
    });

    closeButtons.forEach(function (button) {
        button.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && (modal.classList.contains('show') || incomplete?.classList.contains('show'))) {
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
        const parsed = parseMaintDate(value);
        return parsed ? formatMaintDate(parsed) : value || '-';
    }

    function syncTanggalMulai() {
        form.querySelectorAll('[data-maint-start-date]').forEach(function (input) {
            input.value = getTanggalMulaiLabel();
        });
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
                            <option value="Perbaikan Langsung" ${action === 'Perbaikan Langsung' ? 'selected' : ''}>Perbaikan Langsung</option>
                            <option value="Perbaikan Lanjutan" ${action === 'Perbaikan Lanjutan' ? 'selected' : ''}>Perbaikan Lanjutan</option>
                        </select>
                    </div>
                </div>
                <div class="pemeliharaan-action-panel" data-action-panel="Perbaikan Langsung" ${action === 'Perbaikan Langsung' ? '' : 'hidden'}>
                    <div class="form-row master-form-row master-form-row--1">
                        <div class="form-group form-group-full">
                            <label for="id_uraian_perbaikan_${index}">Uraian Perbaikan</label>
                            <textarea name="uraian_perbaikan_${index}" id="id_uraian_perbaikan_${index}" class="form-control" rows="4" placeholder="Masukkan uraian perbaikan" autocomplete="off">${escapeHtml(uraianPerbaikan)}</textarea>
                        </div>
                    </div>
                    <div class="form-row master-form-row master-form-row--2">
                        <div class="form-group">
                            <label>Tanggal Perbaikan Mulai</label>
                            <input type="text" class="form-control is-readonly-field" value="${escapeHtml(getTanggalMulaiLabel())}" readonly aria-readonly="true" data-maint-start-date>
                        </div>
                        <div class="form-group">
                            <label for="id_tanggal_selesai_perbaikan_${index}">Tanggal Perbaikan Selesai</label>
                            <input type="text" name="tanggal_selesai_perbaikan_${index}" id="id_tanggal_selesai_perbaikan_${index}" class="form-control date-input pemeliharaan-date-input" value="${escapeHtml(tanggalSelesai)}" placeholder="Masukan tanggal sesuai format" autocomplete="off" data-maint-date-picker="true" data-maint-min-source="id_tanggal_pemeriksaan">
                        </div>
                    </div>
                    ${uploadBlock(index, 'dokumentasi_perbaikan', 'Dokumentasi Perbaikan')}
                </div>
                <div class="pemeliharaan-action-panel" data-action-panel="Perbaikan Lanjutan" ${action === 'Perbaikan Lanjutan' ? '' : 'hidden'}>
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

    function clearFieldErrors(field) {
        if (!field.matches?.('input, select, textarea') || field.disabled
            || ['file', 'checkbox', 'hidden'].includes(field.type)) {
            return;
        }
        const group = field.closest('.form-group');
        const errors = Array.from(group?.querySelectorAll('.input-error-text') || []);
        if (!errors.length) return;

        const value = String(field.value || '').trim();
        if (!value && (field.required || errors.some(node => /wajib/i.test(node.textContent)))) return;
        if (value && field.matches('[data-maint-date-picker]')) {
            const date = parseMaintDate(value);
            const source = document.getElementById(field.dataset.maintMinSource || '');
            const minimum = parseMaintDate(source ? source.value : field.dataset.maintMinDate);
            if (!date || (source && !minimum) || (minimum && date < minimum)) return;
        }
        if (field.validity && !field.validity.valid) return;
        errors.forEach(node => node.remove());
        group.classList.remove('has-error');
        field.removeAttribute('aria-invalid');
    }

    ['input', 'change'].forEach(function (eventName) {
        form.addEventListener(eventName, function (event) {
            clearFieldErrors(event.target);
            form.querySelectorAll('[data-maint-min-source]').forEach(function (field) {
                if (field.dataset.maintMinSource === event.target.id) clearFieldErrors(field);
            });
        });
    });

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
            const action = form.dataset.repairMode === 'true' ? 'Perbaikan Langsung' : actionField?.value;
            const isActive = action === panel.getAttribute('data-action-panel');
            panel.hidden = !isActive;
            setPanelDisabled(panel, !isActive);
            panel.querySelectorAll('[data-maint-min-source]').forEach(function (input) {
                input.dispatchEvent(new Event('maint:date-sync'));
            });
        });
    }

    function bindRepairRows(scope) {
        const root = scope || form;
        root.querySelectorAll('[data-repair-row]').forEach(function (row) {
            const actionField = row.querySelector('[data-action-field]');
            if (actionField && actionField.dataset.repairReady !== 'true') {
                actionField.dataset.repairReady = 'true';
                actionField.addEventListener('change', function () {
                    syncRepairRow(row);
                });
            }
            syncRepairRow(row);
        });
        initPemeliharaanGallery(root);
        initPemeliharaanDatePickers(root);
        bindSelectPlaceholderState(root);
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
        const existing = new Map(Array.from(repairList.querySelectorAll('[data-repair-row]'))
            .map(row => [row.dataset.index, row]));
        const fragment = document.createDocumentFragment();
        rows.forEach(function (row) {
            const current = existing.get(row.index);
            if (current) {
                fragment.appendChild(current);
            } else {
                const template = document.createElement('template');
                template.innerHTML = repairRow(row.index, row.component, values);
                fragment.appendChild(template.content);
            }
        });
        repairList.replaceChildren(fragment);
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
    }

    function renderComponents() {
        const components = componentsMap[String(alatSelect?.value || '')] || [];
        if (!list) {
            return;
        }
        list.innerHTML = components.map(function (component, index) {
            return componentRow(index, component);
        }).join('');
        repairList?.replaceChildren();
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
                alatSelect.dispatchEvent(new Event('change', { bubbles: true }));
            });
            return;
        }

        lastAlatValue = nextValue;
        renderComponents();
    });

    tanggalInput?.addEventListener('input', syncTanggalMulai);
    tanggalInput?.addEventListener('change', syncTanggalMulai);
    bindComponentRows(form);
    bindRepairRows(form);
    initPemeliharaanGallery(form);
    initPemeliharaanDatePickers(form);
    syncTanggalMulai();
    initPemeliharaanDigits(form);
}

function initPemeliharaanSubmit() {
    const form = document.querySelector('[data-pemeliharaan-form="true"]');
    if (!form || !window.fetch || !window.FormData) return;
    let pending = false;

    function showStatus(message) {
        let status = form.querySelector('[data-maint-save-error]');
        if (!status) {
            status = document.createElement('p');
            status.className = 'input-error-text';
            status.dataset.maintSaveError = 'true';
            status.setAttribute('role', 'alert');
            form.prepend(status);
        }
        status.textContent = message;
    }

    function showErrors(errors) {
        form.querySelectorAll('.input-error-text:not([data-gallery-error])').forEach(node => node.remove());
        form.querySelectorAll('.has-error').forEach(node => node.classList.remove('has-error'));
        form.querySelectorAll('[aria-invalid]').forEach(node => node.removeAttribute('aria-invalid'));
        const globalErrors = [];
        Object.entries(errors).forEach(function ([name, messages]) {
            const field = form.elements.namedItem(name);
            const group = field?.closest?.('.form-group, .upload-card');
            if (!group) {
                globalErrors.push(...messages);
                return;
            }
            group.classList.add('has-error');
            field.setAttribute('aria-invalid', 'true');
            let anchor = group.querySelector('.landing-gallery-picker') || field.closest('.date-picker-control') || field;
            messages.forEach(function (message) {
                const error = document.createElement('p');
                error.className = 'input-error-text';
                error.textContent = '*' + String(message).replace(/^\*/, '');
                anchor.insertAdjacentElement('afterend', error);
                anchor = error;
            });
        });
        if (globalErrors.length) showStatus(globalErrors.join(' '));
        form.querySelector('.input-error-text:not([hidden])')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    form.addEventListener('submit', async function (event) {
        if (event.defaultPrevented) return;
        event.preventDefault();
        if (pending) return;
        const data = new FormData(form);
        if (event.submitter?.name) data.append(event.submitter.name, event.submitter.value);
        const buttons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]'))
            .map(button => ({ button, disabled: button.disabled }));
        pending = true;
        form.setAttribute('aria-busy', 'true');
        buttons.forEach(({ button }) => { button.disabled = true; });
        form.querySelector('[data-maint-save-error]')?.remove();
        try {
            const response = await fetch(form.action || window.location.href, {
                method: 'POST', body: data, credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
            });
            if (response.redirected || !response.headers.get('content-type')?.includes('application/json')) {
                throw new Error('Unexpected save response');
            }
            const result = await response.json();
            if (response.status === 422 && result.errors) {
                showErrors(result.errors);
            } else if (response.ok && result.redirect_url) {
                form.dispatchEvent(new Event('unsaved:submitted'));
                window.location.assign(result.redirect_url);
            } else {
                throw new Error('Save failed');
            }
        } catch {
            showStatus('Penyimpanan belum dapat dipastikan. Dokumentasi tetap tersedia. Periksa koneksi dan halaman detail sebelum mencoba kembali.');
        } finally {
            pending = false;
            form.removeAttribute('aria-busy');
            buttons.forEach(({ button, disabled }) => { button.disabled = disabled; });
        }
    });
}

function initPemeliharaanGallery(scope) {
    const controls = (scope || document).querySelectorAll('[data-maint-gallery]:not([data-gallery-ready="true"])');

    controls.forEach(function (control) {
        control.dataset.galleryReady = 'true';

        const input = control.querySelector('[data-gallery-input]');
        const preview = control.querySelector('[data-gallery-new]');
        const removeInputs = Array.from(control.querySelectorAll('[data-gallery-remove]'));
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

        function activeExistingCount() {
            return removeInputs.filter(function (item) { return !item.checked; }).length;
        }

        function selectedCount() {
            return activeExistingCount() + selectedFiles.length;
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
            const count = selectedCount();
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
            if (selectedCount() + files.length > maxFiles) {
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
            if (selectedCount() >= maxFiles) {
                event.preventDefault();
            }
        });
        removeInputs.forEach(function (checkbox) {
            checkbox.addEventListener('change', function () {
                clearError();
                updateState();
            });
        });

        renderSelection();
    });
}
