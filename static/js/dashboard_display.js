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

const TV_COMPACT_WIDTH = 1280;
const TV_COMPACT_HEIGHT = 800;

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
        ctx.font = '700 9px "Montserrat", Arial, sans-serif';

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
                const y = yScale.getPixelForValue(0) - 5;
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
            slideshow?.updateContents(updates);
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

    function syncSlides(current, fallback) {
        slides = Array.from(stage.querySelectorAll('[data-tv-slide]'));
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
        if (title) {
            title.textContent = slides[activeIndex].getAttribute('data-title') || 'Grafik Dashboard';
        }
        if (window.tvChartInstances) {
            window.tvChartInstances.forEach(function (chart) {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }
    }

    if (tvMode) {
        groups.forEach(renderGroup);
    }
    syncSlides();
    window.setInterval(function () {
        showSlide(activeIndex + 1);
        layout?.nextTablePage();
    }, 8500);
    return {
        updateContents(updates) {
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

    Chart.defaults.font.family = '"Montserrat", Arial, sans-serif';
    Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-soft').trim() || '#103e6f';
    Chart.register(tvZeroDashPlugin);
    window.tvChartInstances = [
        createTvApprovedChart(),
        createTvCategoryChart('tvLayananChart', 'data-layanan', 'layananId', 'Total Peminjaman', 12, 45),
        createTvPengukuranChart(),
        createTvGroupedChart('tvTimChart', 'data-tim', 'timId', 'teams'),
        createTvCategoryChart('tvSurveiChart', 'data-survei', 'surveiId', 'Total Peminjaman', 10, 50),
        ...Array.from(document.querySelectorAll('[data-instansi-chart]'), function (canvas) {
            return createTvCategoryChart(canvas.id, 'data-' + canvas.dataset.instansiChart, 'instansiId', 'Total Peminjaman', 10, 50);
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

function createTvBaseOptions(maxValue, wrapWidth, rotation) {
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
                        size: 9,
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
                    maxRotation: rotation,
                    minRotation: rotation,
                    color: '#48677d',
                    font: {
                        size: 9,
                        weight: '700',
                    },
                    callback: function (value) {
                        return wrapTvLabel(this.getLabelForValue(value), wrapWidth, 2);
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
                        size: 9,
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

function getTvInstansiTickProfile(width, height) {
    const viewportWidth = Math.max(Number(width || window.innerWidth || 0), 1);
    const viewportHeight = Math.max(Number(height || window.innerHeight || 0), 1);
    const compact = viewportWidth <= TV_COMPACT_WIDTH || viewportHeight <= TV_COMPACT_HEIGHT;

    if (!compact) {
        return {
            maxLines: 2,
            rotation: 50,
            wrapWidth: 10,
            fontSize: 9,
        };
    }

    return {
        maxLines: 1,
        rotation: 90,
        wrapWidth: viewportWidth <= 1024 ? 11 : 13,
        fontSize: viewportWidth <= 1024 ? 7 : 8,
    };
}

function applyTvInstansiAxis(options, size) {
    const ticks = options?.scales?.x?.ticks;
    if (!ticks) {
        return;
    }

    const profile = getTvInstansiTickProfile(size?.width, size?.height);
    ticks.autoSkip = false;
    delete ticks.maxTicksLimit;
    ticks.maxRotation = profile.rotation;
    ticks.minRotation = profile.rotation;
    ticks.align = 'center';
    ticks.font.size = profile.fontSize;
    ticks.callback = function (value) {
        return wrapTvLabel(this.getLabelForValue(value), profile.wrapWidth, profile.maxLines);
    };
}

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
        options: options || createTvBaseOptions(maxValue, 12, 0),
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
        borderSkipped: false,
        categoryPercentage: 0.94,
        barPercentage: 0.96,
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
    const options = createTvBaseOptions(maxValue, 8, 0);
    options.plugins.legend.display = false;

    return createTvChart(
        'tvApprovedChart',
        monthKeys.map(formatTvMonth),
        [buildTvBarDataset(dataset.label || 'Total Peminjaman', data, dataset.backgroundColor || 'rgba(16, 62, 111, 0.82)', dataset.borderColor || 'rgba(16, 62, 111, 1)')],
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
    const colors = categories.map(function (category) {
        return category.backgroundColor || 'rgba(16, 62, 111, 0.82)';
    });
    const maxValue = Math.max.apply(null, data.concat([0]));
    const options = createTvBaseOptions(maxValue, 10, 0);
    options.plugins.legend.display = false;

    return createTvChart(
        'tvPengukuranChart',
        labels,
        [buildTvBarDataset('Akumulasi Tahun Berjalan', data, colors, colors)],
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

    const options = createTvBaseOptions(maxValue, 8, 0);
    return createTvChart(canvasId, monthKeys.map(formatTvMonth), datasets, maxValue, options);
}

function createTvCategoryChart(canvasId, scriptId, idKey, datasetLabel, wrapWidth, rotation) {
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
    const options = createTvBaseOptions(maxValue, wrapWidth, rotation);
    options.plugins.legend.display = false;
    if (idKey === 'instansiId') {
        applyTvInstansiAxis(options, {
            width: window.innerWidth,
            height: window.innerHeight,
        });
        options.onResize = function (chart, size) {
            applyTvInstansiAxis(chart.config.options, {
                width: size?.width || window.innerWidth,
                height: window.innerHeight,
            });
        };
    }

    return createTvChart(
        canvasId,
        labels,
        [buildTvBarDataset(datasetLabel, data, colors, colors)],
        maxValue,
        options,
    );
}

function wrapTvLabel(label, maxCharsPerLine, maxLines) {
    if (typeof label !== 'string' || !label.trim()) {
        return label;
    }

    const normalized = label.replace(/\s+/g, ' ').trim();
    if (normalized.length <= maxCharsPerLine) {
        return normalized;
    }

    const words = normalized.split(' ');
    const lines = [];
    let currentLine = '';

    words.forEach(function (word) {
        if (!word) {
            return;
        }

        const nextLine = currentLine ? currentLine + ' ' + word : word;
        if (nextLine.length <= maxCharsPerLine) {
            currentLine = nextLine;
            return;
        }

        if (currentLine) {
            lines.push(currentLine);
        }
        currentLine = word.length > maxCharsPerLine ? word.slice(0, maxCharsPerLine) : word;
    });

    if (currentLine) {
        lines.push(currentLine);
    }

    if (lines.length > maxLines) {
        const limited = lines.slice(0, maxLines);
        const lastIndex = limited.length - 1;
        limited[lastIndex] = limited[lastIndex].slice(0, Math.max(1, maxCharsPerLine - 3)).replace(/[\s.]+$/g, '') + '...';
        return limited;
    }

    return lines;
}
