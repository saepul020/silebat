/* Explicit signage mode. Normal display typography until content needs fitting. */
function getTvViewport(viewport, fallback) {
    const positive = value => Number.isFinite(Number(value)) && Number(value) > 0;
    const offset = value => Number.isFinite(Number(value)) ? Math.max(0, Number(value)) : 0;
    return {
        width: positive(viewport?.width) ? Number(viewport.width) : positive(fallback.innerWidth) ? fallback.innerWidth : 1,
        height: positive(viewport?.height) ? Number(viewport.height) : positive(fallback.innerHeight) ? fallback.innerHeight : 1,
        left: offset(viewport?.offsetLeft),
        top: offset(viewport?.offsetTop),
    };
}

function initTvLayout() {
    const root = document.documentElement;
    const page = document.querySelector('.tv-page');
    if (!root.classList.contains('tv-screen') || !page) {
        return null;
    }

    const table = page.querySelector('.tv-active-table');
    const tbody = page.querySelector('[data-tv-active-body]');
    const badge = table?.querySelector('.tv-live-badge');
    let rowPages = [];
    let rowIndex = 0;
    let pending = false;
    let dirty = true;
    let viewportKey = '';
    let fontSize = 16;

    function setValue(node, name, value) {
        if (node.style.getPropertyValue(name) !== value) {
            node.style.setProperty(name, value);
        }
    }

    function showRows() {
        if (!tbody || !rowPages.length) {
            return;
        }
        rowIndex %= rowPages.length;
        const visible = new Set(rowPages[rowIndex]);
        Array.from(tbody.children).forEach(row => { row.hidden = !visible.has(row); });
        if (badge) {
            badge.textContent = rowPages.length > 1 ? `Realtime · ${rowIndex + 1}/${rowPages.length}` : 'Realtime';
        }
    }

    function paginateRows(height, share = 0.3) {
        if (!table || !tbody) {
            return;
        }
        table.style.removeProperty('--tv-table-height');
        const rows = Array.from(tbody.children);
        rows.forEach(row => { row.hidden = false; });
        const fixed = table.getBoundingClientRect().height - tbody.getBoundingClientRect().height;
        const available = Math.max(1, height * share - fixed);
        rowPages = [];
        let group = [];
        let used = 0;
        let largest = 0;
        rows.forEach(row => {
            const size = row.getBoundingClientRect().height;
            if (group.length && used + size > available) {
                rowPages.push(group);
                largest = Math.max(largest, used);
                group = [];
                used = 0;
            }
            group.push(row);
            used += size;
        });
        if (group.length) {
            rowPages.push(group);
            largest = Math.max(largest, used);
        }
        setValue(table, '--tv-table-height', `${Math.ceil(fixed + largest)}px`);
        showRows();
    }

    function contentFits() {
        const photosFit = Array.from(page.querySelectorAll('.tv-equipment__card')).every(card => {
            const photo = card.querySelector('.tv-equipment__photo');
            if (!photo) {
                return true;
            }
            return photo.getBoundingClientRect().bottom <= card.getBoundingClientRect().bottom + 1;
        });
        const nodes = page.querySelectorAll('.tv-equipment__body, .tv-summary__body, .tv-head h1, .tv-head p');
        return photosFit && Array.from(nodes).every(node =>
            node.scrollWidth <= node.clientWidth + 1 && node.scrollHeight <= node.clientHeight + 1
        );
    }

    function measure() {
        pending = false;
        const size = getTvViewport(window.visualViewport, window);
        const key = `${size.width}:${size.height}`;
        const changed = key !== viewportKey;
        viewportKey = key;
        setValue(root, '--tv-width', `${size.width}px`);
        setValue(root, '--tv-height', `${size.height}px`);
        setValue(root, '--tv-left', `${size.left}px`);
        setValue(root, '--tv-top', `${size.top}px`);
        const base = 16;
        if (changed || dirty) {
            fontSize = base;
        }
        setValue(root, '--tv-font-size', `${fontSize}px`);
        if (changed || dirty) {
            paginateRows(size.height);
        }
        let tableShare = 0.3;
        let fits = contentFits();
        while (!fits && tableShare > 0.18) {
            tableShare = Math.max(0.18, tableShare - 0.04);
            paginateRows(size.height, tableShare);
            fits = contentFits();
        }
        for (let attempt = 0; !fits && attempt < 6 && fontSize > base * 0.75; attempt += 1) {
            fontSize = Math.max(base * 0.75, fontSize * 0.95);
            setValue(root, '--tv-font-size', `${fontSize}px`);
            paginateRows(size.height, tableShare);
            fits = contentFits();
        }
        dirty = false;
        root.dataset.tvFit = fits ? 'ready' : 'compact';
        (window.tvChartInstances || []).forEach(chart => chart.resize());
    }

    function schedule(reset) {
        dirty = dirty || reset === true;
        if (!pending) {
            pending = true;
            window.requestAnimationFrame(measure);
        }
    }

    window.addEventListener('resize', () => schedule(true));
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', () => schedule(true));
        window.visualViewport.addEventListener('scroll', () => schedule());
    }
    if (typeof ResizeObserver !== 'undefined') {
        const observer = new ResizeObserver(() => schedule());
        observer.observe(page);
    }
    page.addEventListener('load', () => schedule(true), true);
    if (document.fonts?.ready) {
        document.fonts.ready.then(() => schedule(true));
    }
    schedule(true);
    return {
        refresh() { schedule(true); },
        nextTablePage() {
            if (rowPages.length > 1) {
                rowIndex += 1;
                showRows();
            }
        },
    };
}
