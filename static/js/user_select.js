document.addEventListener('DOMContentLoaded', function () {
    const root = document.querySelector('.app-content, [data-select-adaptive]');
    if (!root) return;
    let nextId = 0;
    const adaptive = root.hasAttribute('data-select-adaptive');
    let active = null;
    let frame = 0;

    function reposition() {
        if (frame || !active) return;
        frame = requestAnimationFrame(function () {
            frame = 0;
            active?.position();
        });
    }
    window.addEventListener('resize', reposition);
    document.addEventListener('scroll', reposition, true);
    window.visualViewport?.addEventListener('resize', reposition);
    window.visualViewport?.addEventListener('scroll', reposition);

    function floatPanel(wrapper, panel) {
        if (adaptive && wrapper.closest('.table-scroll') && typeof panel.showPopover === 'function') {
            panel.popover = 'manual';
            panel.classList.add('user-select__panel--floating');
        }
    }

    function showPanel(panel) {
        panel.hidden = false;
        if (panel.popover && !panel.matches(':popover-open')) panel.showPopover();
    }

    function hidePanel(panel) {
        if (panel.popover && panel.matches(':popover-open')) panel.hidePopover();
        panel.hidden = true;
    }

    function place(wrapper, toggle, panel, options, close) {
        const viewport = window.visualViewport;
        const top = (viewport?.offsetTop || 0) + 12;
        const bottom = (viewport?.offsetTop || 0) + (viewport?.height || window.innerHeight) - 12;
        const left = (viewport?.offsetLeft || 0) + 12;
        const right = (viewport?.offsetLeft || 0) + (viewport?.width || window.innerWidth) - 12;
        const rect = toggle.getBoundingClientRect();
        if (rect.bottom < top || rect.top > bottom) { close(); return; }
        panel.style.maxWidth = Math.max(0, right - left) + 'px';
        if (panel.popover) panel.style.width = rect.width + 'px';
        const desired = Math.min(420, panel.getBoundingClientRect().height - options.clientHeight + options.scrollHeight);
        const below = Math.max(0, bottom - rect.bottom - 6);
        const above = Math.max(0, rect.top - top - 6);
        const up = below < desired && above > below;
        panel.classList.toggle('user-select__panel--up', up);
        panel.style.maxHeight = Math.min(420, up ? above : below) + 'px';
        const width = panel.getBoundingClientRect().width;
        const anchor = panel.popover ? 0 : wrapper.getBoundingClientRect().left;
        panel.style.left = (Math.max(left, Math.min(rect.left, right - width)) - anchor) + 'px';
        if (panel.popover) {
            panel.style.top = (up ? rect.top - 6 - panel.getBoundingClientRect().height : rect.bottom + 6) + 'px';
        }
    }

    // Opt-in for existing multiple-choice menus; selection stays with their owner.
    function enhanceMenu(wrapper) {
        if (!adaptive || wrapper.dataset.selectReady) return;
        const toggle = wrapper.querySelector('[data-select-toggle]');
        const panel = wrapper.querySelector('[data-select-panel]');
        const options = wrapper.querySelector('[data-select-options]');
        if (!toggle || !panel || !options) return;
        wrapper.dataset.selectReady = 'true';
        floatPanel(wrapper, panel);
        if (!panel.id) panel.id = 'user-select-' + (++nextId);
        toggle.setAttribute('aria-controls', panel.id);
        function close(focus = false) {
            wrapper.open = false;
            hidePanel(panel);
            wrapper.classList.remove('user-select--open');
            toggle.setAttribute('aria-expanded', 'false');
            if (active?.wrapper === wrapper) active = null;
            if (focus) toggle.focus();
        }
        function position() {
            if (wrapper.open) place(wrapper, toggle, panel, options, close);
        }
        function sync() {
            if (!wrapper.open) { close(); return; }
            if (active?.wrapper !== wrapper) active?.close();
            active = { wrapper, close, position };
            showPanel(panel);
            wrapper.classList.add('user-select--open');
            toggle.setAttribute('aria-expanded', 'true');
            position();
        }
        wrapper.addEventListener('toggle', sync);
        wrapper.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && wrapper.open) {
                event.preventDefault();
                close(true);
            }
        });
        wrapper.addEventListener('focusout', function (event) {
            if (!wrapper.contains(event.relatedTarget)) close();
        });
        sync();
    }

    function enhance(select) {
        if (select.multiple || select.closest('.user-select')) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'user-select';
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'user-select__toggle';
        toggle.setAttribute('role', 'combobox');
        toggle.setAttribute('aria-haspopup', 'listbox');
        toggle.setAttribute('aria-expanded', 'false');
        const panel = document.createElement('div');
        panel.className = 'user-select__panel';
        panel.id = 'user-select-' + (++nextId);
        const options = adaptive ? document.createElement('div') : panel;
        options.setAttribute('role', 'listbox');
        if (adaptive) options.id = panel.id + '-options';
        let search;
        let empty;
        if (adaptive) {
            panel.classList.add('user-select__panel--adaptive');
            options.className = 'user-select__options';
            panel.append(options);
        }

        function syncSearch() {
            if (!adaptive) return;
            // View filters use GET forms or stand alone; only data entry uses POST.
            const count = Array.from(select.options).filter(option => option.value !== '' && !option.hidden
                && !option.disabled && !option.closest('optgroup:disabled')).length;
            const enabled = select.form?.method === 'post' && count > 10;
            panel.classList.toggle('user-select__panel--search', enabled);
            if (!enabled) {
                if (search) {
                    if (document.activeElement === search) toggle.focus({ preventScroll: true });
                    search.remove();
                    search = undefined;
                    empty.remove();
                    empty = undefined;
                }
                return;
            }
            if (search) return;
            search = document.createElement('input');
            search.type = 'search';
            search.className = 'user-select__search';
            search.placeholder = 'Cari pilihan...';
            search.autocomplete = 'off';
            search.setAttribute('data-unsaved-ignore-field', '');
            search.setAttribute('aria-label', 'Cari pilihan');
            search.setAttribute('aria-controls', options.id);
            panel.prepend(search);
            empty = document.createElement('p');
            empty.className = 'user-select__empty';
            empty.textContent = 'Pilihan tidak ditemukan.';
            empty.setAttribute('role', 'status');
            empty.hidden = true;
            panel.append(empty);
            search.addEventListener('input', function (event) {
                event.stopPropagation();
                filter();
            });
            search.addEventListener('change', function (event) { event.stopPropagation(); });
        }
        panel.hidden = true;
        toggle.setAttribute('aria-controls', options.id);
        select.before(wrapper);
        wrapper.append(select, toggle, panel);
        floatPanel(wrapper, panel);
        select.classList.add('user-select__native');
        select.setAttribute('aria-hidden', 'true');
        select.tabIndex = -1;

        function close(focus = false) {
            hidePanel(panel);
            wrapper.classList.remove('user-select--open');
            toggle.setAttribute('aria-expanded', 'false');
            if (search) {
                search.value = '';
                empty.hidden = true;
            }
            if (active?.wrapper === wrapper) active = null;
            if (focus && !toggle.disabled) toggle.focus();
        }

        function position() {
            if (!adaptive || panel.hidden) return;
            place(wrapper, toggle, panel, options, close);
        }

        function filter() {
            if (!adaptive) return;
            const keyword = (search?.value || '').trim().toLocaleLowerCase('id');
            let count = 0;
            options.querySelectorAll('button').forEach(function (button) {
                button.hidden = !button.textContent.toLocaleLowerCase('id').includes(keyword);
                if (!button.hidden) count++;
            });
            if (empty) empty.hidden = !keyword || count > 0;
            position();
        }

        function available() {
            return Array.from(options.querySelectorAll('button:not(:disabled):not([hidden])'));
        }

        function sync() {
            syncSearch();
            const label = select.labels?.[0];
            if (label && !label.id) label.id = panel.id + '-label';
            if (label) {
                toggle.setAttribute('aria-labelledby', label.id);
                options.setAttribute('aria-labelledby', label.id);
                search?.setAttribute('aria-label', 'Cari ' + label.textContent.trim());
            } else {
                const name = select.getAttribute('aria-label') || select.title || 'Pilih opsi';
                toggle.setAttribute('aria-label', name);
                options.setAttribute('aria-label', name);
                search?.setAttribute('aria-label', 'Cari ' + name);
            }
            toggle.disabled = select.matches(':disabled');
            toggle.setAttribute('aria-disabled', String(toggle.disabled));
            toggle.setAttribute('aria-required', String(select.required));
            toggle.setAttribute('aria-invalid', String(select.getAttribute('aria-invalid') === 'true' || Boolean(select.closest('.has-error'))));
            toggle.textContent = select.selectedOptions[0]?.textContent || 'Pilih opsi';
            if (select.hasAttribute('data-select-fit')) {
                toggle.dataset.fitLabel = Array.from(select.options, option => option.textContent.trim()).join('\n');
            }
            toggle.classList.toggle('user-select__toggle--placeholder', !select.value);
            options.replaceChildren();
            Array.from(select.options).forEach(function (option) {
                if (option.hidden) return;
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'user-select__option';
                button.classList.toggle('user-select__option--placeholder', option.value === '');
                button.setAttribute('role', 'option');
                button.setAttribute('aria-selected', String(option.selected));
                button.textContent = option.textContent;
                button.disabled = toggle.disabled || option.disabled || Boolean(option.closest('optgroup:disabled'));
                button.tabIndex = -1;
                button.addEventListener('click', function () {
                    if (select.matches(':disabled')) return;
                    select.value = option.value;
                    close(true);
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                });
                options.append(button);
            });
            if (toggle.disabled) close();
            filter();
        }

        function open() {
            if (select.matches(':disabled')) return;
            if (active?.wrapper !== wrapper) active?.close();
            active = { wrapper, close, position };
            showPanel(panel);
            if (adaptive) {
                wrapper.classList.add('user-select--open');
                if (search) search.value = '';
                filter();
            }
            toggle.setAttribute('aria-expanded', 'true');
            const selected = options.querySelector('[aria-selected="true"]:not(:disabled)');
            (search || selected || available()[0])?.focus({ preventScroll: adaptive });
        }

        toggle.addEventListener('click', function () { panel.hidden ? open() : close(); });
        wrapper.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                close(true);
            } else if (event.key === 'Enter' && event.target === search) {
                event.preventDefault();
                available()[0]?.click();
            } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
                if (event.target === search && ['Home', 'End'].includes(event.key)) return;
                event.preventDefault();
                if (panel.hidden) { open(); return; }
                const buttons = available();
                if (!buttons.length) return;
                const index = buttons.indexOf(document.activeElement);
                const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
                    : index < 0 ? (event.key === 'ArrowUp' ? buttons.length - 1 : 0)
                    : (index + (event.key === 'ArrowUp' ? -1 : 1) + buttons.length) % buttons.length;
                buttons[next].focus();
            } else if (event.target !== search && event.key.length === 1 && event.key !== ' ' && !event.ctrlKey && !event.metaKey && !event.altKey) {
                if (search) {
                    event.preventDefault();
                    if (panel.hidden) open();
                    search.focus({ preventScroll: true });
                    search.value += event.key;
                    filter();
                } else {
                    const match = available().find(option => option.textContent.trim().toLocaleLowerCase('id').startsWith(event.key.toLocaleLowerCase('id')));
                    if (match) { event.preventDefault(); open(); match.focus(); }
                }
            }
        });
        wrapper.addEventListener('focusout', function (event) {
            if (!wrapper.contains(event.relatedTarget)) close();
        });
        select.addEventListener('change', sync);
        select.addEventListener('focus', function () { toggle.focus(); });
        select.addEventListener('invalid', function (event) { event.preventDefault(); toggle.focus(); });
        select.form?.addEventListener('reset', function () { setTimeout(sync, 0); });
        new MutationObserver(sync).observe(select, {
            attributes: true, attributeFilter: ['disabled', 'selected', 'required', 'aria-invalid', 'label', 'hidden'],
            subtree: true, childList: true, characterData: true,
        });
        sync();
    }

    root.querySelectorAll('select').forEach(enhance);
    root.querySelectorAll('[data-select-menu]').forEach(enhanceMenu);
    new MutationObserver(function (records) {
        records.forEach(record => record.addedNodes.forEach(function (node) {
            if (node.nodeType !== 1) return;
            if (node.matches('select')) enhance(node);
            node.querySelectorAll('select').forEach(enhance);
            if (node.matches('[data-select-menu]')) enhanceMenu(node);
            node.querySelectorAll('[data-select-menu]').forEach(enhanceMenu);
        }));
    }).observe(root, { childList: true, subtree: true });
    document.addEventListener('click', function (event) {
        const label = event.target.closest('label');
        const control = label?.control;
        const dropdown = control?.closest('.user-select');
        if (dropdown && root.contains(dropdown) && !dropdown.contains(event.target)) {
            event.preventDefault();
            dropdown.querySelector('.user-select__toggle').focus();
        }
        if (active && !active.wrapper.contains(event.target)) active.close();
    });
});
