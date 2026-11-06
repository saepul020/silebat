document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-koreksi-form]');
    if (!form) return;
    const dateInputs = [...form.querySelectorAll('[data-maint-date-picker="true"]')];
    const dateSources = new Map(dateInputs.map(input => {
        const source = document.createElement('input');
        source.type = 'hidden';
        source.id = `koreksi-date-${input.id}`;
        source.value = input.dataset.koreksiPrevious || '';
        form.append(source);
        return [input, source];
    }));
    initPemeliharaanDatePickers(form);

    function syncDates() {
        // Empty edits use the original date for validation without filling the visible input.
        dateInputs.forEach(input => {
            const source = dateSources.get(input);
            source.value = input.value.trim() || input.dataset.koreksiPrevious || '';
            source.dispatchEvent(new Event('input'));
        });
        dateInputs.forEach(input => {
            input.setCustomValidity('');
            const value = parseMaintDate(dateSources.get(input).value);
            if (input.value.trim() && !parseMaintDate(input.value)) {
                input.setCustomValidity('Masukkan tanggal yang valid.');
                return;
            }
            const sources = (input.dataset.koreksiMinSources || '').split(' ').filter(Boolean);
            const affected = input.value.trim() || sources.some(id => document.getElementById(id).value.trim());
            const bounds = sources.map(id => parseMaintDate(dateSources.get(document.getElementById(id)).value)).filter(Boolean);
            if (affected && value && bounds.some(bound => value < bound)) {
                input.setCustomValidity('Tanggal tidak boleh sebelum tanggal acuannya.');
            }
        });
    }

    form.addEventListener('input', event => {
        if (dateInputs.includes(event.target)) syncDates();
    });
    form.addEventListener('change', event => {
        if (dateInputs.includes(event.target)) syncDates();
    });
    syncDates();

    form.querySelectorAll('select[data-koreksi-other]').forEach(select => {
        const other = document.getElementById(select.dataset.koreksiOther);
        function syncPair() {
            const selected = Boolean(select.value), manual = Boolean(other.value.trim());
            const message = selected && manual ? 'Pilih data dari daftar atau isi lainnya, bukan keduanya.' : '';
            other.disabled = selected && !manual;
            select.disabled = manual && !selected;
            other.setAttribute('aria-disabled', String(other.disabled));
            select.setAttribute('aria-disabled', String(select.disabled));
            select.setCustomValidity(message);
            other.setCustomValidity(message);
            select.classList.toggle('is-placeholder-state', !selected);
        }
        select.addEventListener('change', syncPair);
        other.addEventListener('input', syncPair);
        other.addEventListener('change', syncPair);
        syncPair();
    });
    const items = form.querySelector('[data-alat-list]');
    const total = form.querySelector('[name="alat-TOTAL_FORMS"]');
    const maximum = Number(form.querySelector('[name="alat-MAX_NUM_FORMS"]').value);
    const add = form.querySelector('[data-alat-add]');
    const template = form.querySelector('[data-alat-template]');
    const options = [...template.content.querySelector('select[name$="-barang"]').options]
        .map(option => option.cloneNode(true));

    function syncChoices() {
        const rows = [...items.querySelectorAll('[data-alat-row]')];
        const section = items.closest('[data-alat-section]');
        const previousCount = section.querySelectorAll('[data-previous-alat]').length;
        section.style.setProperty('--koreksi-rows', Math.max(rows.length, previousCount) + 2);
        const selected = new Set(rows
            .filter(row => !row.querySelector('[name$="-DELETE"]').checked)
            .map(row => row.querySelector('select').value || row.querySelector('select').dataset.previousBarang).filter(Boolean));
        rows.forEach((row, index) => {
            const select = row.querySelector('select');
            const value = select.value;
            select.replaceChildren(...options
                .filter(option => !option.value || option.value === value || option.value === select.dataset.previousBarang || !selected.has(option.value))
                .map(option => option.cloneNode(true)));
            select.value = value;
            select.classList.toggle('is-placeholder-state', !value);
            const deleted = row.querySelector('[name$="-DELETE"]').checked;
            row.classList.toggle('koreksi__alat--deleted', deleted);
            const label = row.querySelector(`label[for="${select.id}"]`);
            label.textContent = `Peralatan Survei Lapangan ${index + 1}`;
        });
        add.disabled = Number(total.value) >= maximum;
    }

    add.addEventListener('click', () => {
        const index = Number(total.value);
        if (index >= maximum) return;
        const fragment = template.content.cloneNode(true);
        fragment.querySelectorAll('*').forEach(node => {
            ['name', 'id', 'for', 'aria-describedby'].forEach(attr => {
                if (node.hasAttribute(attr)) {
                    node.setAttribute(attr, node.getAttribute(attr).replaceAll('__prefix__', String(index)));
                }
            });
        });
        items.append(fragment);
        total.value = index + 1;
        syncChoices();
    });
    items.addEventListener('change', event => {
        if (event.target.matches('select, input[name$="-DELETE"]')) syncChoices();
    });
    syncChoices();
});
