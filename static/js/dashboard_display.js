/* ========================================
   DASHBOARD TV DISPLAY JS
   Chart dan slideshow public display.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initTvClock();
    initTvCharts();
    initTvSlides();
    initTvActiveTable();
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


function initTvActiveTable() {
    const wrapper = document.querySelector('[data-tv-active-url]');
    const body = document.querySelector('[data-tv-active-body]');
    if (!wrapper || !body) {
        return;
    }

    const url = wrapper.getAttribute('data-tv-active-url');
    if (!url) {
        return;
    }

    let isLoading = false;

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
            if (typeof payload.html === 'string') {
                body.innerHTML = payload.html;
            }
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

function initTvSlides() {
    const slides = Array.from(document.querySelectorAll('[data-tv-slide]'));
    const dots = Array.from(document.querySelectorAll('[data-tv-dot]'));
    const title = document.querySelector('[data-tv-slide-title]');
    if (slides.length <= 1) {
        return;
    }

    let activeIndex = 0;

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

    showSlide(0);
    window.setInterval(function () {
        showSlide(activeIndex + 1);
    }, 8500);
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
        createTvCategoryChart('tvLayananChart', 'layanan-chart-data', 'layananId', 'Total Peminjaman', 12, 45),
        createTvPengukuranChart(),
        createTvGroupedChart('tvTimChart', 'tim-chart-data', 'timId', 'teams'),
        createTvCategoryChart('tvSurveiChart', 'survei-chart-data', 'surveiId', 'Total Peminjaman', 10, 50),
        createTvCategoryChart('tvInstansiChart', 'instansi-chart-data', 'instansiId', 'Total Peminjaman', 10, 50),
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

function buildTvBarDataset(label, data, backgroundColor, borderColor, isGrouped) {
    return {
        label: label,
        data: data,
        backgroundColor: backgroundColor,
        borderColor: borderColor || backgroundColor,
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
        categoryPercentage: isGrouped ? 0.82 : 0.74,
        barPercentage: isGrouped ? 0.86 : 0.78,
        maxBarThickness: isGrouped ? 30 : 40,
    };
}

function createTvApprovedChart() {
    const source = readTvData('approved-peminjaman-chart-data');
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
        [buildTvBarDataset(dataset.label || 'Total Peminjaman', data, dataset.backgroundColor || 'rgba(16, 62, 111, 0.82)', dataset.borderColor || 'rgba(16, 62, 111, 1)', false)],
        maxValue,
        options,
    );
}


function createTvPengukuranChart() {
    const source = readTvData('pengukuran-chart-data');
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
        [buildTvBarDataset('Akumulasi Tahun Berjalan', data, colors, colors, false)],
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
            true,
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
    const categories = Array.isArray(source.categories) ? source.categories : [];
    const rows = Array.isArray(source.rows) ? source.rows : [];
    const totals = new Map();

    rows.forEach(function (row) {
        if (Number(row.year) !== year) {
            return;
        }
        const key = row[idKey];
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
    const options = createTvBaseOptions(maxValue, wrapWidth, rotation);
    options.plugins.legend.display = false;

    return createTvChart(
        canvasId,
        labels,
        [buildTvBarDataset(datasetLabel, data, colors, colors, false)],
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
        limited[lastIndex] = limited[lastIndex].slice(0, Math.max(1, maxCharsPerLine - 1)).replace(/[\s.]+$/g, '') + '…';
        return limited;
    }

    return lines;
}
