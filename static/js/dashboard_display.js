/* ========================================
   DASHBOARD TV DISPLAY JS
   Chart dan slideshow public display.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    const layout = typeof initTvLayout === 'function' ? initTvLayout() : null;
    initTvClock();
    initTvCharts();
    const slideshow = initTvSlides(layout);
    initTvActiveTable(slideshow, layout);
});

const TV_MONTH_LABELS = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'Mei',
    6: 'Jun',
    7: 'Jul',
    8: 'Agu',
    9: 'Sep',
    10: 'Okt',
    11: 'Nov',
    12: 'Des',
};

const tvZeroDashPlugin = {
    id: 'tvZeroDashPlugin',
    afterDatasetsDraw(chart) {
        const datasets = chart?.data?.datasets || [];
        const yScale = chart?.scales?.y;
        if (!datasets.length || !yScale) {
            return;
        }

        const ctx = chart.ctx;
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = 'rgba(16, 62, 111, 0.58)';
        const fontSize = Number(yScale.options.ticks.font.size) || 7;
        ctx.font = '700 ' + fontSize + 'px "Montserrat", Arial, sans-serif';

        datasets.forEach(function (dataset, datasetIndex) {
            const meta = chart.getDatasetMeta(datasetIndex);
            if (!meta || meta.hidden) {
                return;
            }

            meta.data.forEach(function (element, dataIndex) {
                const rawValue = Array.isArray(dataset.data) ? Number(dataset.data[dataIndex] || 0) : 0;
                if (rawValue !== 0 || !element) {
                    return;
                }
                const x = typeof element.x === 'number' ? element.x : 0;
                const y = yScale.getPixelForValue(0) - fontSize * 0.7;
                ctx.fillText('-', x, y);
            });
        });
        ctx.restore();
    },
};


function initTvActiveTable(slideshow, layout) {
    const wrapper = document.querySelector('[data-tv-active-url]');
    const body = document.querySelector('[data-tv-active-body]');
    const equipment = new Map(Array.from(document.querySelectorAll('[data-tv-equipment]'), node => [node.dataset.tvEquipment, node]));
    const inventory = document.querySelector('[data-tv-inventory]');
    if (!wrapper || !body) {
        return;
    }

    const url = wrapper.getAttribute('data-tv-active-url');
    if (!url) {
        return;
    }

    let isLoading = false;
    let tableHtml = body.innerHTML;

    async function loadActiveData() {
        if (isLoading) {
            return;
        }
        isLoading = true;

        try {
            const response = await fetch(url, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            if (typeof payload.html === 'string' && tableHtml !== payload.html) {
                tableHtml = payload.html;
                body.innerHTML = payload.html;
                layout?.refresh();
            }
            const updates = [];
            if (Array.isArray(payload.equipmentSlides)) {
                payload.equipmentSlides.forEach(function (slide) {
                    const node = equipment.get(String(slide.nomor));
                    if (node && typeof slide.html === 'string') {
                        updates.push({ node: node, html: slide.html });
                    }
                });
            }
            if (inventory && typeof payload.inventoryHtml === 'string') {
                updates.push({ node: inventory, html: payload.inventoryHtml });
            }
            slideshow?.updateContents(updates, payload.documentationSlides);
        } catch (error) {
            console.error('Gagal memuat data kegiatan aktif display TV.', error);
        } finally {
            isLoading = false;
        }
    }

    window.setInterval(loadActiveData, 10000);
}

function initTvClock() {
    const dateNode = document.querySelector('[data-tv-date]');
    const clockNode = document.querySelector('[data-tv-clock]');
    if (!dateNode || !clockNode) {
        return;
    }

    function renderClock() {
        const now = new Date();
        dateNode.textContent = now.toLocaleDateString('id-ID', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric',
        });
        clockNode.textContent = now.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        }).replace(/\./g, ':') + ' WIB';
    }

    renderClock();
    window.setInterval(renderClock, 1000);
}

function initTvSlides(layout) {
    let slides = Array.from(document.querySelectorAll('[data-tv-slide]'));
    if (!slides.length) {
        return null;
    }
    const stage = slides[0].parentElement;
    const tvMode = document.documentElement.classList.contains('tv-screen');
    const groups = slides.map(function (slide) {
        const grid = slide.querySelector('.tv-equipment');
        return grid ? { slide: slide, grid: grid, html: grid.innerHTML, extra: [] } : null;
    }).filter(Boolean);
    const dotsContainer = document.querySelector('[data-tv-dots]');
    let dots = [];
    const title = document.querySelector('[data-tv-slide-title]');
    const documentationAnchor = stage.querySelector('[data-tv-documentation-anchor]');
    const documentationHtml = new Map();
    let activeIndex = 0;

    function renderGroup(group) {
        group.extra.forEach(slide => slide.remove());
        group.extra = [];
        group.grid.innerHTML = group.html;
        if (!tvMode) {
            return;
        }
        const cards = Array.from(group.grid.children).filter(card =>
            card.classList.contains('tv-equipment__card') && !card.classList.contains('tv-equipment__card--empty')
        );
        const pageSize = Math.max(1, parseInt(getComputedStyle(group.grid).getPropertyValue('--tv-columns'), 10) || cards.length);
        group.grid.replaceChildren(...cards.slice(0, pageSize));
        if (!cards.length) {
            const message = document.createElement('p');
            message.className = 'tv-equipment__empty';
            message.textContent = 'Belum ada peralatan yang dipilih.';
            group.grid.append(message);
        }
        let previous = group.slide;
        for (let index = pageSize; index < cards.length; index += pageSize) {
            const slide = group.slide.cloneNode(false);
            slide.classList.remove('is-active');
            slide.setAttribute('data-tv-generated', '');
            const grid = group.grid.cloneNode(false);
            grid.removeAttribute('data-tv-equipment');
            grid.removeAttribute('data-tv-inventory');
            grid.replaceChildren(...cards.slice(index, index + pageSize));
            slide.append(grid);
            previous.after(slide);
            previous = slide;
            group.extra.push(slide);
        }
    }

    function updateDocumentation(items) {
        if (!documentationAnchor || !Array.isArray(items)) return false;
        const existing = new Map(Array.from(stage.querySelectorAll('[data-tv-documentation-slide]'), node => [node.dataset.tvDocumentationSlide, node]));
        let changed = false;
        // Build in reverse so every documentation slide stays directly before the anchor.
        let next = documentationAnchor;
        items.slice().reverse().forEach(item => {
            if (!Number.isSafeInteger(item.id) || item.id < 1 || typeof item.html !== 'string') return;
            const key = String(item.id);
            let slide = existing.get(key);
            if (!slide) {
                slide = document.createElement('article');
                slide.className = 'tv-chart-slide';
                slide.setAttribute('data-tv-slide', '');
                slide.dataset.tvDocumentationSlide = key;
                slide.setAttribute('data-title', 'Dokumentasi Kegiatan Laboratorium');
                const grid = document.createElement('div');
                grid.className = 'tv-documentation';
                grid.setAttribute('data-tv-documentation', '');
                slide.appendChild(grid);
                changed = true;
            }
            const grid = slide.querySelector('[data-tv-documentation]');
            const oldHtml = documentationHtml.has(key) ? documentationHtml.get(key) : grid.innerHTML;
            if (oldHtml !== item.html) {
                grid.innerHTML = item.html;
                changed = true;
            }
            documentationHtml.set(key, item.html);
            if (slide.nextElementSibling !== next) {
                next.before(slide);
                changed = true;
            }
            existing.delete(key);
            next = slide;
        });
        existing.forEach((slide, key) => {
            slide.remove();
            documentationHtml.delete(key);
            changed = true;
        });
        return changed;
    }

    function syncSlides(current, fallback) {
        slides = Array.from(stage.querySelectorAll('[data-tv-slide]')).filter(slide => !slide.hidden);
        if (dots.length !== slides.length) {
            dots = slides.map(function () {
                const dot = document.createElement('span');
                dot.setAttribute('data-tv-dot', '');
                return dot;
            });
            dotsContainer?.replaceChildren(...dots);
        }
        const index = slides.indexOf(current);
        const fallbackIndex = slides.indexOf(fallback);
        showSlide(index >= 0 ? index : Math.max(0, fallbackIndex));
    }

    function showSlide(nextIndex) {
        activeIndex = nextIndex % slides.length;
        slides.forEach(function (slide, index) {
            slide.classList.toggle('is-active', index === activeIndex);
        });
        dots.forEach(function (dot, index) {
            dot.classList.toggle('is-active', index === activeIndex);
        });
        if (dotsContainer && dots[activeIndex]) {
            const dot = dots[activeIndex];
            dotsContainer.scrollLeft = dot.offsetLeft - (dotsContainer.clientWidth - dot.offsetWidth) / 2;
        }
        if (title) {
            title.textContent = slides[activeIndex].getAttribute('data-title') || 'Grafik Dashboard';
        }
        const activeCanvas = slides[activeIndex].querySelector('canvas');
        const activeChart = (window.tvChartInstances || []).find(chart => chart.canvas === activeCanvas);
        const totalNode = document.querySelector('[data-tv-total]');
        if (activeChart) {
            syncChartTotal(activeChart);
        } else if (totalNode) {
            totalNode.hidden = true;
            showChartNihil(totalNode, []);
        }
        layout?.refresh();
        if (window.tvChartInstances) {
            window.tvChartInstances.forEach(function (chart) {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }
    }

    groups.forEach(renderGroup);
    syncSlides();
    window.setInterval(function () {
        showSlide(activeIndex + 1);
    }, 8500);
    return {
        updateContents(updates, documentationSlides) {
            const current = slides[activeIndex];
            const activeGroup = groups.find(group => group.slide === current || group.extra.includes(current));
            let changed = false;
            updates.forEach(function (update) {
                const group = groups.find(item => item.grid === update.node);
                if (group && group.html !== update.html) {
                    group.html = update.html;
                    renderGroup(group);
                    changed = true;
                }
            });
            changed = updateDocumentation(documentationSlides) || changed;
            if (changed) {
                syncSlides(current, activeGroup?.slide);
                layout?.refresh();
            }
        },
    };
}

function initTvCharts() {
    if (typeof Chart === 'undefined') {
        return;
    }

    registerChartSummary();
    Chart.defaults.font.family = '"Montserrat", Arial, sans-serif';
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-soft').trim() || '#103e6f';
    Chart.register(tvZeroDashPlugin, tvLabelPlugin);
    window.tvChartInstances = [
        createTvApprovedChart(),
        createTvCategoryChart('tvLayananChart', 'data-layanan', 'layananId', 'Total Peminjaman'),
        createTvPengukuranChart(),
        createTvGroupedChart('tvTimChart', 'data-tim', 'timId', 'teams'),
        createTvCategoryChart('tvSurveiChart', 'data-survei', 'surveiId', 'Total Peminjaman'),
        ...Array.from(document.querySelectorAll('[data-instansi-chart]'), function (canvas) {
            return createTvCategoryChart(canvas.id, 'data-' + canvas.dataset.instansiChart, 'instansiId', 'Total Peminjaman');
        }),
    ].filter(Boolean);
}

function readTvData(scriptId) {
    const script = document.getElementById(scriptId);
    if (!script) {
        return null;
    }

    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Gagal membaca data display dashboard.', error);
        return null;
    }
}

function getTvYear(source) {
    return Number(source?.defaultYear || new Date().getFullYear());
}

function buildTvMonthKeys(year) {
    const keys = [];
    for (let month = 1; month <= 12; month += 1) {
        keys.push(String(year) + '-' + String(month).padStart(2, '0'));
    }
    return keys;
}

function formatTvMonth(monthKey) {
    const parts = String(monthKey).split('-');
    return TV_MONTH_LABELS[Number(parts[1])] || '-';
}

function createTvBaseOptions(maxValue) {
    const hasValue = Number(maxValue || 0) > 0;
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 850,
            easing: 'easeOutQuart',
        },
        interaction: {
            mode: 'index',
            intersect: false,
        },
        layout: {
            padding: {
                top: 4,
                right: 6,
                bottom: 0,
                left: 0,
            },
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    boxWidth: 7,
                    padding: 7,
                    color: '#103e6f',
                    font: {
                        size: 7,
                        weight: '700',
                    },
                },
            },
            tooltip: {
                enabled: false,
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                    drawBorder: false,
                },
                ticks: {
                    autoSkip: false,
                    maxRotation: 0,
                    minRotation: 0,
                    color: '#48677d',
                    font: {
                        size: 8,
                        weight: '700',
                    },
                },
            },
            y: {
                beginAtZero: true,
                suggestedMax: hasValue ? undefined : 1,
                ticks: {
                    precision: 0,
                    stepSize: 1,
                    color: '#48677d',
                    font: {
                        size: 7,
                        weight: '700',
                    },
                },
                grid: {
                    color: 'rgba(16, 62, 111, 0.12)',
                    drawBorder: false,
                },
            },
        },
    };
}

function wrapTvLabel(label, width, measure) {
    const text = String(label ?? '').replace(/\s+/g, ' ').trim();
    if (measure(text) <= width) {
        return text;
    }
    function prefix(value, suffix = '') {
        const chars = Array.from(value);
        let low = 0;
        let high = chars.length;
        while (low < high) {
            const middle = Math.ceil((low + high) / 2);
            if (measure(chars.slice(0, middle).join('') + suffix) <= width) {
                low = middle;
            } else {
                high = middle - 1;
            }
        }
        return chars.slice(0, low).join('');
    }
    let first = prefix(text);
    const space = first.lastIndexOf(' ');
    if (space > 0) {
        first = first.slice(0, space);
    }
    const rest = text.slice(first.length).trim();
    const last = measure(rest) <= width ? rest : prefix(rest, '\u2026').trimEnd() + '\u2026';
    return first ? [first, last] : last;
}

function getTvTickProfile(labels, width, measure = label => label.length * 4.8, height = 480, scale = 1) {
    const slot = Math.max(1, (Number(width) - 48) / Math.max(1, labels.length));
    // Reserve perpendicular space for two lines and a gap between neighbours.
    const baseSize = Math.min(8, (slot - 2) / 2.4);
    const fontSize = Math.max(1, Math.min(baseSize * scale, (slot - 2 * scale) / 2.4));
    const lineWidth = Math.max(fontSize * 4, Math.min(120, Math.max(30, slot * 2.5), Math.max(30, height * 0.28)) * scale);
    const scaledMeasure = label => measure(label) * fontSize / 8;
    const wrapped = labels.map(label => wrapTvLabel(label, lineWidth, scaledMeasure));
    const lines = wrapped.flatMap(label => [].concat(label));
    const longest = Math.max(0, ...lines.map(scaledMeasure));
    const lineCount = Math.max(1, ...wrapped.map(label => [].concat(label).length));
    const crowded = longest + 6 * scale > slot;
    const angle = Math.asin(Math.min(1, (fontSize * 1.2 * lineCount + 2 * scale) / slot)) * 180 / Math.PI;
    return {
        rotation: crowded ? Math.min(90, Math.max(45, Math.ceil(angle / 5) * 5)) : 0,
        fontSize: fontSize,
        lineWidth: lineWidth,
        labels: wrapped,
    };
}

// Shared by every Live TV chart and recomputed before layout, including resize.
const tvLabelPlugin = {
    id: 'tvLabelPlugin',
    beforeLayout(chart) {
        const ticks = chart.options.scales?.x?.ticks;
        if (!ticks) {
            return;
        }
        const page = chart.canvas?.closest('.tv-page');
        const scale = page ? Math.sqrt(parseFloat(getComputedStyle(page).fontSize) / 8) : 1;
        chart.ctx.save();
        chart.ctx.font = '700 8px "Montserrat", Arial, sans-serif';
        const profile = getTvTickProfile(chart.data.labels || [], chart.width, label => chart.ctx.measureText(label).width, chart.height, scale);
        chart.ctx.restore();
        const labels = new Map((chart.data.labels || []).map((label, index) => [String(label), profile.labels[index]]));
        ticks.minRotation = profile.rotation;
        ticks.maxRotation = profile.rotation;
        ticks.font.size = profile.fontSize;
        ticks.font.lineHeight = 1.2;
        ticks.padding = 2 * scale;
        ticks.callback = function (value) {
            const label = this.getLabelForValue(value);
            return labels.get(String(label)) ?? label;
        };
        const yTicks = chart.options.scales.y.ticks;
        yTicks.font.size = 7 * scale;
        yTicks.padding = 2 * scale;
        const legend = chart.options.plugins.legend.labels;
        legend.font.size = 7 * scale;
        legend.boxWidth = 7 * scale;
        legend.boxHeight = 7 * scale;
        legend.padding = 7 * scale;
    },
};

function createTvChart(canvasId, labels, datasets, maxValue, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return null;
    }

    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets,
        },
        options: options || createTvBaseOptions(maxValue),
    });
}

function buildTvBarDataset(label, data, backgroundColor, borderColor) {
    return {
        label: label,
        data: data,
        backgroundColor: backgroundColor,
        borderColor: borderColor || backgroundColor,
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: 'start',
        categoryPercentage: 0.94,
        barPercentage: 0.96,
    };
}

function getTvPinjamColors(dataset) {
    return {
        backgroundColor: dataset?.backgroundColor || 'rgba(16, 62, 111, 0.82)',
        borderColor: dataset?.borderColor || 'rgba(16, 62, 111, 1)',
    };
}

function createTvApprovedChart() {
    const source = readTvData('data-pinjam');
    if (!source) {
        return null;
    }

    const year = getTvYear(source);
    const monthKeys = buildTvMonthKeys(year);
    const totals = new Map();
    const rows = Array.isArray(source.rows) ? source.rows : [];
    rows.forEach(function (row) {
        if (Number(row.year) !== year) {
            return;
        }
        totals.set(String(row.year) + '-' + String(row.month).padStart(2, '0'), Number(row.total || 0));
    });

    const data = monthKeys.map(function (monthKey) {
        return Number(totals.get(monthKey) || 0);
    });
    const maxValue = Math.max.apply(null, data.concat([0]));
    const dataset = source.dataset || {};
    const colors = getTvPinjamColors(dataset);
    const options = createTvBaseOptions(maxValue);
    options.plugins.legend.display = false;

    return createTvChart(
        'tvApprovedChart',
        monthKeys.map(formatTvMonth),
        [buildTvBarDataset(dataset.label || 'Total Peminjaman', data, colors.backgroundColor, colors.borderColor)],
        maxValue,
        options,
    );
}


function createTvPengukuranChart() {
    const source = readTvData('data-ukur');
    if (!source) {
        return null;
    }

    const year = getTvYear(source);
    const categories = Array.isArray(source.categories) ? source.categories : [];
    const rows = Array.isArray(source.yearRows) ? source.yearRows : Array.isArray(source.rows) ? source.rows : [];
    const totals = new Map();

    rows.forEach(function (row) {
        if (Number(row.year) !== year) {
            return;
        }
        const key = row.pengukuranKey;
        totals.set(key, Number(totals.get(key) || 0) + Number(row.total || 0));
    });

    const labels = categories.map(function (category) {
        return category.label;
    });
    const data = categories.map(function (category) {
        return Number(totals.get(category.id) || 0);
    });
    const colors = getTvPinjamColors(readTvData('data-pinjam')?.dataset);
    const maxValue = Math.max.apply(null, data.concat([0]));
    const options = createTvBaseOptions(maxValue);
    options.plugins.legend.display = false;

    return createTvChart(
        'tvPengukuranChart',
        labels,
        [buildTvBarDataset('Akumulasi Tahun Berjalan', data, colors.backgroundColor, colors.borderColor)],
        maxValue,
        options,
    );
}

function createTvGroupedChart(canvasId, scriptId, categoryKey, categoryConfigKey) {
    const source = readTvData(scriptId);
    if (!source) {
        return null;
    }

    const year = getTvYear(source);
    const monthKeys = buildTvMonthKeys(year);
    const categories = Array.isArray(source?.[categoryConfigKey]) ? source[categoryConfigKey] : [];
    const rows = Array.isArray(source.rows) ? source.rows : [];
    const lookup = new Map();

    rows.forEach(function (row) {
        if (Number(row.year) !== year) {
            return;
        }
        const monthKey = String(row.year) + '-' + String(row.month).padStart(2, '0');
        const lookupKey = monthKey + '::' + row[categoryKey];
        const currentTotal = Number(lookup.get(lookupKey) || 0);
        lookup.set(lookupKey, currentTotal + Number(row.total || 0));
    });

    const datasets = categories.map(function (category) {
        const data = monthKeys.map(function (monthKey) {
            return Number(lookup.get(monthKey + '::' + category.id) || 0);
        });
        return buildTvBarDataset(
            category.label,
            data,
            category.backgroundColor || 'rgba(16, 62, 111, 0.82)',
            category.borderColor || category.backgroundColor || 'rgba(16, 62, 111, 1)',
        );
    });
    const maxValue = datasets.reduce(function (highest, dataset) {
        return Math.max(highest, Math.max.apply(null, dataset.data.concat([0])));
    }, 0);

    const options = createTvBaseOptions(maxValue);
    return createTvChart(canvasId, monthKeys.map(formatTvMonth), datasets, maxValue, options);
}

function createTvCategoryChart(canvasId, scriptId, idKey, datasetLabel) {
    const source = readTvData(scriptId);
    if (!source) {
        return null;
    }

    const year = getTvYear(source);
    let categories = Array.isArray(source.categories) ? source.categories : [];
    const rows = Array.isArray(source.rows) ? source.rows : [];
    const totals = new Map();

    rows.forEach(function (row) {
        if (Number(row.year) !== year) {
            return;
        }
        const key = row[idKey];
        totals.set(key, Number(totals.get(key) || 0) + Number(row.total || 0));
    });

    if (idKey === 'instansiId') {
        categories = sortInstansiCategories(categories, totals, source.key);
    }

    const labels = categories.map(function (category) {
        return category.label;
    });
    const data = categories.map(function (category) {
        return Number(totals.get(category.id) || 0);
    });
    const colors = categories.map(function (category) {
        return category.backgroundColor || 'rgba(16, 62, 111, 0.82)';
    });
    const maxValue = Math.max.apply(null, data.concat([0]));
    const options = createTvBaseOptions(maxValue);
    options.plugins.legend.display = false;

    return createTvChart(
        canvasId,
        labels,
        [buildTvBarDataset(datasetLabel, data, colors, colors)],
        maxValue,
        options,
    );
}
