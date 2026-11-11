/* Shared single-line fitting; signage also follows the visual viewport. */
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
    if (!page) {
        return null;
    }
    const tvMode = root.classList.contains('tv-screen');
    let pending = false;

    function setValue(node, name, value) {
        if (node.style.getPropertyValue(name) !== value) {
            node.style.setProperty(name, value);
        }
    }

    function textWidth(node) {
        const range = document.createRange();
        range.selectNodeContents(node);
        return range.getBoundingClientRect().width;
    }

    function innerWidth(node) {
        const style = getComputedStyle(node);
        return node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    }

    function fitText(selector, property, container = page) {
        container.style.removeProperty(property);
        const nodes = Array.from(container.querySelectorAll(selector));
        let ratio = 1;
        nodes.forEach(node => {
            if (node.clientWidth > 0) {
                ratio = Math.min(ratio, Math.max(1, innerWidth(node) - 2) / Math.max(1, textWidth(node)));
            }
        });
        if (nodes.length && ratio < 1) {
            const size = parseFloat(getComputedStyle(nodes[0]).fontSize);
            setValue(container, property, `${Math.floor(size * ratio * 10) / 10}px`);
        }
    }

    function fitEquipment() {
        page.querySelectorAll('.tv-equipment').forEach(grid => {
            const groups = [
                ['.tv-equipment__name', '--tv-name-size'],
                ['.tv-equipment__brand', '--tv-brand-size'],
                ['.tv-equipment__meta', '--tv-meta-size'],
            ];
            groups.forEach(([, property]) => grid.style.removeProperty(property));
            const bodies = Array.from(grid.querySelectorAll('.tv-equipment__card:not(.tv-equipment__card--empty) .tv-equipment__body'));
            if (!bodies.length) {
                fitText('.tv-summary .tv-equipment__name', '--tv-name-size', grid);
                return;
            }
            const sizes = groups.map(([selector]) => parseFloat(getComputedStyle(bodies[0].querySelector(selector)).fontSize));
            // A shared multiplier preserves the title/brand/metadata hierarchy.
            // Start uncapped so short fields can grow into the available width.
            let ratio = Infinity;
            bodies.forEach(body => {
                body.querySelectorAll('.tv-equipment__name, .tv-equipment__brand').forEach(node => {
                    if (node.clientWidth > 0 && node.textContent.trim()) {
                        ratio = Math.min(ratio, Math.max(1, innerWidth(node) - 2) / Math.max(1, textWidth(node)));
                    }
                });
                const list = body.querySelector('.tv-equipment__meta');
                if (list?.clientWidth > 0) {
                    const labelWidth = Math.max(0, ...Array.from(list.querySelectorAll('dt'), node => node.scrollWidth));
                    const valueWidth = Math.max(0, ...Array.from(list.querySelectorAll('dd'), textWidth));
                    const gap = parseFloat(getComputedStyle(list).columnGap) || 0;
                    ratio = Math.min(ratio, Math.max(1, list.clientWidth - 2) / Math.max(1, labelWidth + valueWidth + gap));
                }
            });
            if (Number.isFinite(ratio)) {
                groups.forEach(([, property], index) => {
                    setValue(grid, property, `${Math.floor(sizes[index] * ratio * 10) / 10}px`);
                });
            }
        });
    }

    function measure() {
        pending = false;
        if (tvMode) {
            const size = getTvViewport(window.visualViewport, window);
            setValue(root, '--tv-width', `${size.width}px`);
            setValue(root, '--tv-height', `${size.height}px`);
            setValue(root, '--tv-left', `${size.left}px`);
            setValue(root, '--tv-top', `${size.top}px`);
        }
        fitText('.tv-head h1', '--tv-heading-size');
        fitText('.tv-head p', '--tv-subtitle-size');
        fitText('.tv-table th, .tv-table td:not([colspan])', '--tv-table-size');
        fitText('[data-tv-slide-title]', '--tv-title-size');
        fitEquipment();

        // Preserve full cards below all active rows. Dense pages can scroll vertically.
        const grids = Array.from(page.querySelectorAll('.tv-equipment'));
        const stageMin = parseFloat(getComputedStyle(page).getPropertyValue('--tv-stage-min')) || 180;
        const contentHeight = Math.max(stageMin, ...grids.map(grid => {
            const cardHeight = Math.max(0, ...Array.from(grid.children).map(card => {
                const photo = card.querySelector('.tv-equipment__photo');
                const body = card.querySelector('.tv-equipment__body, .tv-summary__body');
                let height = 0;
                if (body) {
                    const style = getComputedStyle(body);
                    const range = document.createRange();
                    range.selectNodeContents(body);
                    height = body.classList.contains('tv-summary__body')
                        ? Array.from(body.children).reduce((sum, node) => sum + node.offsetHeight, 0)
                            + (parseFloat(style.gap) || 0) * Math.max(0, body.children.length - 1) + 3
                        : range.getBoundingClientRect().height;
                    height += parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
                }
                return (photo?.offsetHeight || 0) + height + 4;
            }));
            const rows = Math.ceil(grid.children.length / (parseInt(getComputedStyle(grid).getPropertyValue('--tv-columns'), 10) || 6));
            const gap = parseFloat(getComputedStyle(grid).rowGap) || 0;
            return rows * cardHeight + Math.max(0, rows - 1) * gap + 4;
        }));
        const chart = page.querySelector('.tv-chart-card');
        const header = page.querySelector('.tv-chart-head');
        if (chart && header) {
            const style = getComputedStyle(chart);
            const height = contentHeight + header.offsetHeight + parseFloat(getComputedStyle(header).marginBottom)
                + (chart.querySelector('.chart-nihil')?.offsetHeight || 0)
                + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) + 2;
            setValue(page, '--tv-chart-min', `${Math.ceil(height)}px`);
        }
        (window.tvChartInstances || []).forEach(chart => chart.resize());
    }

    function schedule() {
        if (!pending) {
            pending = true;
            window.requestAnimationFrame(measure);
        }
    }

    window.addEventListener('resize', schedule);
    if (tvMode && window.visualViewport) {
        window.visualViewport.addEventListener('resize', schedule);
        window.visualViewport.addEventListener('scroll', schedule);
    }
    if (typeof ResizeObserver !== 'undefined') {
        const observer = new ResizeObserver(schedule);
        observer.observe(page);
    }
    page.addEventListener('load', schedule, true);
    document.fonts?.ready.then(schedule);
    schedule();
    return { refresh: schedule };
}
