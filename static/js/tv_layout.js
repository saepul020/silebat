/* Responsive TV type, wrapped fields, and the visible signage viewport. */
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
        const lines = Array.from(node.querySelectorAll('.tv-wrap__line'));
        if (lines.length) return Math.max(0, ...lines.map(textWidth));
        const range = document.createRange();
        range.selectNodeContents(node);
        return range.getBoundingClientRect().width;
    }

    function innerWidth(node) {
        const style = getComputedStyle(node);
        return node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    }

    function fitText(selector, property, container = page, widthOf = innerWidth) {
        container.style.removeProperty(property);
        const nodes = Array.from(container.querySelectorAll(selector));
        let ratio = 1;
        nodes.forEach(node => {
            if (node.clientWidth > 0) {
                ratio = Math.min(ratio, Math.max(1, widthOf(node) - 2) / Math.max(1, textWidth(node)));
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
            // Titles and brands share a scale; metadata fits separately below them.
            let ratio = Infinity;
            let metaRatio = Infinity;
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
                    metaRatio = Math.min(metaRatio, Math.max(1, list.clientWidth - 2) / Math.max(1, labelWidth + valueWidth + gap));
                }
            });
            if (!Number.isFinite(ratio) || !Number.isFinite(metaRatio)) return;
            // Fill the available width while keeping short headings proportional to metadata.
            ratio = Math.min(ratio, metaRatio * sizes[2] * 1.6 / sizes[0]);
            groups.slice(0, 2).forEach(([, property], index) => {
                setValue(grid, property, `${Math.floor(sizes[index] * ratio * 10) / 10}px`);
            });
            metaRatio = Math.min(metaRatio, sizes[0] * ratio * 0.65 / sizes[2], sizes[1] * ratio * 0.9 / sizes[2]);
            setValue(grid, '--tv-meta-size', `${Math.floor(sizes[2] * metaRatio * 10) / 10}px`);
            if (tvMode) {
                // The TV frame is fixed: wrapped text must fit its remaining height too.
                for (let attempt = 0; attempt < 3; attempt += 1) {
                    let heightRatio = 1;
                    bodies.forEach(body => {
                        const style = getComputedStyle(body);
                        const available = body.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
                        const needed = Array.from(body.children).reduce((sum, node) => {
                            const childStyle = getComputedStyle(node);
                            return sum + node.getBoundingClientRect().height
                                + parseFloat(childStyle.marginTop) + parseFloat(childStyle.marginBottom);
                        }, 0);
                        heightRatio = Math.min(heightRatio, Math.max(0.1, available - 2) / Math.max(1, needed));
                    });
                    if (heightRatio >= 1) break;
                    const current = groups.map(([selector]) => parseFloat(getComputedStyle(bodies[0].querySelector(selector)).fontSize));
                    groups.forEach(([, property], index) => {
                        setValue(grid, property, `${Math.max(0.1, Math.floor(current[index] * heightRatio * 10) / 10)}px`);
                    });
                }
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
        // TV fields wrap at the column width instead of shrinking the whole table.
        const tableCells = tvMode
            ? '.tv-table th:not(.cell-status)'
            : '.tv-table th:not(.cell-status), .tv-table td:not([colspan]):not(.cell-status)';
        fitText(tableCells, '--tv-table-size');
        if (tvMode) {
            page.querySelectorAll('.cell-status .tv-table__text').forEach(node => {
                if (node.querySelector('.tv-wrap__line')) node.textContent = node.title;
            });
        } else {
            fitText('.tv-table .cell-status .status-badge', '--tv-status-size', page, badge => {
                const style = getComputedStyle(badge);
                return innerWidth(badge.parentElement) - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
            });
        }
        fitText('[data-tv-slide-title]', '--tv-title-size');
        fitEquipment();
        fitStage();
        (window.tvChartInstances || []).forEach(chart => chart.resize());
    }

    function fitStage() {
        // Normal mode grows with the content. TV uses the remaining viewport track,
        // so inactive equipment slides cannot push a chart/footer below the screen.
        if (tvMode) return;
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
