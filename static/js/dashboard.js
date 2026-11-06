/* ========================================
   DASHBOARD JS
   JS halaman dashboard.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initDashboardCharts();
    initChartDownloadActions();
    initDashboardActiveItemModals();
});

function initDashboardActiveItemModals() {
    const openButtons = document.querySelectorAll('[data-item-open]');
    if (!openButtons.length) {
        return;
    }

    let activeModal = null;

    function closeModal(modal) {
        if (!modal) {
            return;
        }
        modal.classList.remove('show');
        if (activeModal === modal) {
            activeModal = null;
        }
        if (!document.querySelector('.item-modal.show')) {
            document.body.classList.remove('is-scroll-locked');
        }
    }

    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            return;
        }
        if (activeModal && activeModal !== modal) {
            closeModal(activeModal);
        }
        modal.classList.add('show');
        document.body.classList.add('is-scroll-locked');
        activeModal = modal;
    }

    openButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            openModal(button.getAttribute('data-item-open'));
        });
    });

    document.querySelectorAll('.item-modal [data-item-close]').forEach(function (button) {
        button.addEventListener('click', function () {
            closeModal(button.closest('.item-modal'));
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && activeModal) {
            closeModal(activeModal);
        }
    });
}

const DASHBOARD_MONTH_LABELS = {
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

const DASHBOARD_MONTH_FILTER_ALL_MONTHS = 'all_months';
const DASHBOARD_MONTH_FILTER_ACCUMULATED = 'accumulated';

const zeroValueDashPlugin = {
    id: 'zeroValueDashPlugin',
    afterDatasetsDraw(chart) {
        const datasets = chart?.data?.datasets || [];
        if (!datasets.length) {
            return;
        }

        const ctx = chart.ctx;
        const yScale = chart.scales?.y;
        if (!ctx || !yScale) {
            return;
        }

        const mobile = isMobileViewport();
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-soft').trim() || 'rgba(16, 62, 111, 0.68)';
        ctx.font = '600 ' + (chart.options.plugins.zeroValueDashPlugin?.fontSize || getChartFontSize(11, 10, 9)) + 'px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

        datasets.forEach(function (dataset, datasetIndex) {
            if (dataset.showZeroDash === false) {
                return;
            }

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
                const y = typeof yScale.getPixelForValue === 'function'
                    ? yScale.getPixelForValue(0) - (mobile ? 4 : 6)
                    : element.y - (mobile ? 4 : 6);

                ctx.fillText('-', x, y);
            });
        });
        ctx.restore();
    },
};

function initDashboardCharts() {
    if (typeof Chart === 'undefined') {
        return;
    }

    Chart.register(zeroValueDashPlugin);
    initTimKegiatanChart();
    initLayananKegiatanChart();
    initPengukuranLapanganChart();
    initApprovedPeminjamanChart();
    initSurveiKegiatanChart();
    initPeralatanSurveiChart();
    document.querySelectorAll('[data-instansi-chart]').forEach(function (section) {
        initInstansiTujuanChart(section.dataset.instansiChart);
    });
    initInventoryCharts();
    initSdmCharts();
}

function readDashboardChartData(scriptId) {
    const script = document.getElementById(scriptId);
    if (!script) {
        return null;
    }

    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Gagal membaca data grafik dashboard.', error);
        return null;
    }
}

function isMobileViewport() {
    return window.matchMedia('(max-width: 768px)').matches;
}

function isSmallMobileViewport() {
    return window.matchMedia('(max-width: 480px)').matches;
}

function getChartFontSize(defaultSize, mobileSize, smallMobileSize) {
    if (isSmallMobileViewport()) {
        return typeof smallMobileSize === 'number' ? smallMobileSize : mobileSize;
    }

    return isMobileViewport() ? mobileSize : defaultSize;
}

function buildDashboardAxisY(maxValue) {
    const isAllZero = Number(maxValue || 0) <= 0;

    return {
        beginAtZero: true,
        suggestedMax: isAllZero ? 1 : undefined,
        ticks: {
            precision: 0,
            stepSize: 1,
            font: {
                size: getChartFontSize(12, 10, 9),
            },
            callback: function (value) {
                return Number(value) === 0 ? '0' : value;
            },
        },
        grid: {
            color: 'rgba(16, 62, 111, 0.14)',
            drawBorder: false,
        },
    };
}

function buildMonthKey(year, month) {
    return String(year) + '-' + String(month).padStart(2, '0');
}

function formatMonthLabel(year, month, withYear) {
    const monthLabel = DASHBOARD_MONTH_LABELS[Number(month)] || '-';
    return withYear ? monthLabel + ' ' + year : monthLabel;
}

function sortMonthKeys(monthKeys) {
    return monthKeys.slice().sort(function (left, right) {
        return left.localeCompare(right);
    });
}

function createBaseBarOptions(maxValue) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 950,
            easing: 'easeOutQuart',
        },
        transitions: {
            active: {
                animation: {
                    duration: 220,
                },
            },
            resize: {
                animation: {
                    duration: 0,
                },
            },
        },
        animations: {
            y: {
                from: function (context) {
                    const yScale = context.chart?.scales?.y;
                    return yScale && typeof yScale.getPixelForValue === 'function'
                        ? yScale.getPixelForValue(0)
                        : context.chart.chartArea?.bottom;
                },
            },
        },
        interaction: {
            mode: 'index',
            intersect: false,
        },
        layout: {
            padding: {
                top: isSmallMobileViewport() ? 2 : (isMobileViewport() ? 4 : 8),
            },
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    boxWidth: isSmallMobileViewport() ? 7 : (isMobileViewport() ? 8 : 10),
                    padding: isSmallMobileViewport() ? 8 : (isMobileViewport() ? 10 : 14),
                    font: {
                        size: getChartFontSize(12, 10, 9),
                    },
                },
            },
            tooltip: {
                titleFont: {
                    size: getChartFontSize(12, 10, 9),
                },
                bodyFont: {
                    size: getChartFontSize(12, 10, 9),
                },
            },
        },
        scales: {
            x: {
                stacked: false,
                grid: {
                    display: false,
                    drawBorder: false,
                },
                ticks: {
                    autoSkip: false,
                    maxRotation: 0,
                    minRotation: 0,
                    font: {
                        size: getChartFontSize(12, 9, 8),
                    },
                },
            },
            y: buildDashboardAxisY(maxValue),
        },
    };
}


function normalizeDashboardYearFilter(value) {
    return value === 'all' ? 'all' : Number(value);
}

function normalizeDashboardMonthFilter(value) {
    if (value === 'all' || value === DASHBOARD_MONTH_FILTER_ALL_MONTHS) {
        return DASHBOARD_MONTH_FILTER_ALL_MONTHS;
    }

    if (value === DASHBOARD_MONTH_FILTER_ACCUMULATED) {
        return DASHBOARD_MONTH_FILTER_ACCUMULATED;
    }

    return Number(value);
}

function isAnnualAccumulationFilter(selectedMonth) {
    return selectedMonth === DASHBOARD_MONTH_FILTER_ACCUMULATED;
}

function getDashboardYearKeys(source, rows, selectedYear) {
    const defaultYear = Number(source?.defaultYear || new Date().getFullYear());

    if (selectedYear !== 'all') {
        return [Number(selectedYear || defaultYear)];
    }

    const sourceYears = Array.isArray(source?.availableYears) && source.availableYears.length
        ? source.availableYears.map(Number)
        : [];
    const rowYears = rows.map(function (row) {
        return Number(row.year);
    }).filter(Boolean);
    const yearKeys = Array.from(new Set(sourceYears.concat(rowYears))).sort(function (left, right) {
        return left - right;
    });

    return yearKeys.length ? yearKeys : [defaultYear];
}

function getDashboardMonthKeys(source, rows, selectedYear, selectedMonth) {
    const defaultYear = Number(source?.defaultYear || new Date().getFullYear());
    const defaultMonth = Number(source?.defaultMonth || (new Date().getMonth() + 1));

    if (selectedYear !== 'all' && selectedMonth !== DASHBOARD_MONTH_FILTER_ALL_MONTHS) {
        return [buildMonthKey(selectedYear, selectedMonth)];
    }

    if (selectedYear !== 'all' && selectedMonth === DASHBOARD_MONTH_FILTER_ALL_MONTHS) {
        return Array.from({ length: 12 }, function (_, index) {
            return buildMonthKey(selectedYear, index + 1);
        });
    }

    if (selectedYear === 'all' && selectedMonth !== DASHBOARD_MONTH_FILTER_ALL_MONTHS) {
        return getDashboardYearKeys(source, rows, 'all').map(function (year) {
            return buildMonthKey(year, selectedMonth);
        });
    }

    const allMonthKeys = rows.map(function (row) {
        return buildMonthKey(row.year, row.month);
    });

    if (!allMonthKeys.length) {
        return [buildMonthKey(defaultYear, defaultMonth)];
    }

    return sortMonthKeys(Array.from(new Set(allMonthKeys)));
}

function formatYearAccumulationLabel(year, singleYear) {
    return singleYear ? 'Akumulasi ' + year : String(year);
}


function getBarSizing() {
    return {
        categoryPercentage: 0.94,
        barPercentage: 0.96,
    };
}


function buildMonthlyGroupedChartData(source, selectedYear, selectedMonth, categoryKey, categoryConfigKey, datasetLabelPrefix) {
    const rows = Array.isArray(source?.rows) ? source.rows : [];
    const categories = Array.isArray(source?.[categoryConfigKey]) ? source[categoryConfigKey] : [];
    const rowLookup = new Map();
    let labels = [];
    let dataKeys = [];

    if (isAnnualAccumulationFilter(selectedMonth)) {
        const yearKeys = getDashboardYearKeys(source, rows, selectedYear);
        const singleYear = yearKeys.length === 1;

        rows.forEach(function (row) {
            const year = Number(row.year);
            if (selectedYear !== 'all' && year !== Number(selectedYear)) {
                return;
            }

            const lookupKey = year + '::' + row[categoryKey];
            const currentTotal = Number(rowLookup.get(lookupKey) || 0);
            rowLookup.set(lookupKey, currentTotal + Number(row.total || 0));
        });

        dataKeys = yearKeys.map(String);
        labels = yearKeys.map(function (year) {
            return formatYearAccumulationLabel(year, singleYear);
        });
    } else {
        rows.forEach(function (row) {
            const monthKey = buildMonthKey(row.year, row.month);
            rowLookup.set(monthKey + '::' + row[categoryKey], Number(row.total || 0));
        });

        dataKeys = getDashboardMonthKeys(source, rows, selectedYear, selectedMonth);
        const showYearOnLabel = selectedYear === 'all' || dataKeys.length === 1;
        labels = dataKeys.map(function (monthKey) {
            const parts = monthKey.split('-');
            return formatMonthLabel(parts[0], parts[1], showYearOnLabel);
        });
    }

    const barSizing = getBarSizing();
    const datasets = categories.map(function (category) {
        return {
            label: datasetLabelPrefix ? datasetLabelPrefix + ' - ' + category.label : category.label,
            data: dataKeys.map(function (dataKey) {
                return Number(rowLookup.get(dataKey + '::' + category.id) || 0);
            }),
            backgroundColor: category.backgroundColor,
            borderColor: category.borderColor || category.backgroundColor,
            borderWidth: 1,
            borderRadius: 8,
            borderSkipped: false,
            ...barSizing,
        };
    });

    const maxValue = datasets.reduce(function (highestValue, dataset) {
        const datasetMax = Math.max.apply(null, dataset.data.concat([0]));
        return Math.max(highestValue, datasetMax);
    }, 0);

    return {
        labels: labels,
        datasets: datasets,
        maxValue: maxValue,
    };
}



function buildMonthlySingleSeriesChartData(source, selectedYear, selectedMonth) {
    const rows = Array.isArray(source?.rows) ? source.rows : [];
    const datasetConfig = source?.dataset || {};
    const totalsByPeriod = new Map();
    let dataKeys = [];
    let labels = [];

    if (isAnnualAccumulationFilter(selectedMonth)) {
        const yearKeys = getDashboardYearKeys(source, rows, selectedYear);
        const singleYear = yearKeys.length === 1;

        rows.forEach(function (row) {
            const year = Number(row.year);
            if (selectedYear !== 'all' && year !== Number(selectedYear)) {
                return;
            }

            const currentTotal = Number(totalsByPeriod.get(String(year)) || 0);
            totalsByPeriod.set(String(year), currentTotal + Number(row.total || 0));
        });

        dataKeys = yearKeys.map(String);
        labels = yearKeys.map(function (year) {
            return formatYearAccumulationLabel(year, singleYear);
        });
    } else {
        rows.forEach(function (row) {
            const monthKey = buildMonthKey(row.year, row.month);
            totalsByPeriod.set(monthKey, Number(row.total || 0));
        });

        dataKeys = getDashboardMonthKeys(source, rows, selectedYear, selectedMonth);
        const showYearOnLabel = selectedYear === 'all' || dataKeys.length === 1;
        labels = dataKeys.map(function (monthKey) {
            const parts = monthKey.split('-');
            return formatMonthLabel(parts[0], parts[1], showYearOnLabel);
        });
    }

    const barSizing = getBarSizing();
    const data = dataKeys.map(function (dataKey) {
        return Number(totalsByPeriod.get(dataKey) || 0);
    });
    const maxValue = Math.max.apply(null, data.concat([0]));

    return {
        labels: labels,
        datasets: [
            {
                label: datasetConfig.label || 'Total',
                data: data,
                backgroundColor: datasetConfig.backgroundColor || 'rgba(16, 62, 111, 0.82)',
                borderColor: datasetConfig.borderColor || datasetConfig.backgroundColor || 'rgba(16, 62, 111, 1)',
                borderWidth: 1,
                borderRadius: 8,
                borderSkipped: false,
                ...barSizing,
            },
        ],
        maxValue: maxValue,
    };
}



function buildSingleSeriesChartData(source, selectedYear, idKey, datasetLabel) {
    const rows = Array.isArray(source?.rows) ? source.rows : [];
    let categories = Array.isArray(source?.categories) ? source.categories : [];
    const totals = new Map();

    rows.forEach(function (row) {
        if (selectedYear !== 'all' && Number(row.year) !== Number(selectedYear)) {
            return;
        }

        const currentTotal = Number(totals.get(row[idKey]) || 0);
        totals.set(row[idKey], currentTotal + Number(row.total || 0));
    });

    if (idKey === 'instansiId') {
        categories = sortInstansiCategories(categories, totals, source.key);
    }

    const barSizing = getBarSizing();
    const data = categories.map(function (category) {
        return Number(totals.get(category.id) || 0);
    });
    const maxValue = Math.max.apply(null, data.concat([0]));

    return {
        labels: categories.map(function (category) {
            return category.label;
        }),
        datasets: [
            {
                label: datasetLabel,
                data: data,
                backgroundColor: categories.map(function (category) {
                    return category.backgroundColor;
                }),
                borderColor: categories.map(function (category) {
                    return category.backgroundColor;
                }),
                borderWidth: 1,
                borderRadius: 8,
                borderSkipped: false,
                ...barSizing,
            },
        ],
        maxValue: maxValue,
    };
}

function normalizeChartUpdateMode(updateMode) {
    return typeof updateMode === 'string' ? updateMode : undefined;
}

function upsertBarChart(currentChart, canvas, labels, datasets, options, updateMode) {
    if (!currentChart) {
        return new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: options,
        });
    }

    currentChart.data.labels = labels;
    currentChart.data.datasets = datasets;
    currentChart.options = options;
    currentChart.update(normalizeChartUpdateMode(updateMode));
    return currentChart;
}

function bindDashboardChartResize(renderChart) {
    window.addEventListener('resize', debounce(function () {
        renderChart('none');
    }, 180));
}

function updateScrollableChartWidth(holder, labelCount, minPixelsPerLabel) {
    if (!holder) {
        return;
    }

    const scrollContainer = holder.parentElement;
    const containerWidth = scrollContainer ? scrollContainer.clientWidth : 0;
    const calculatedWidth = Math.max(containerWidth, Number(labelCount || 0) * Number(minPixelsPerLabel || 96));
    holder.style.minWidth = calculatedWidth + 'px';
}

function createSingleSeriesChartOptions(maxValue, labelWrapWidth, rotation) {
    const options = createBaseBarOptions(maxValue);
    options.plugins.legend.display = false;
    options.plugins.tooltip.callbacks = {
        label: function (context) {
            const numericValue = Number(context.raw || 0);
            return 'Total: ' + (numericValue === 0 ? '-' : numericValue);
        },
    };
    options.scales.x.ticks.maxRotation = rotation;
    options.scales.x.ticks.minRotation = rotation;
    options.scales.x.ticks.align = 'center';
    options.scales.x.ticks.callback = function (value) {
        return wrapChartLabel(this.getLabelForValue(value), labelWrapWidth, 2);
    };
    return options;
}

function initTimKegiatanChart() {
    const canvas = document.getElementById('grafikTim');
    const source = readDashboardChartData('data-tim');
    const yearFilter = document.getElementById('tahunTim');
    const monthFilter = document.getElementById('bulanTim');

    if (!canvas || !source || !yearFilter || !monthFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildMonthlyGroupedChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            normalizeDashboardMonthFilter(monthFilter.value),
            'timId',
            'teams',
            '',
        );

        const options = createBaseBarOptions(chartData.maxValue);
        options.plugins.tooltip.callbacks = {
            label: function (context) {
                const numericValue = Number(context.raw || 0);
                return context.dataset.label + ': ' + (numericValue === 0 ? '-' : numericValue);
            },
        };

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    monthFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function initLayananKegiatanChart() {
    const canvas = document.getElementById('grafikLayanan');
    const source = readDashboardChartData('data-layanan');
    const yearFilter = document.getElementById('tahunLayanan');

    if (!canvas || !source || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'layananId',
            'Total Peminjaman',
        );
        const options = createSingleSeriesChartOptions(chartData.maxValue, 18, isMobileViewport() ? 55 : 42);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}


function getChartPalette(index) {
    const palette = [
        { background: 'rgba(16, 62, 111, 0.82)', border: 'rgba(16, 62, 111, 1)' },
        { background: 'rgba(100, 205, 209, 0.82)', border: 'rgba(100, 205, 209, 1)' },
        { background: 'rgba(73, 126, 184, 0.82)', border: 'rgba(73, 126, 184, 1)' },
        { background: 'rgba(86, 173, 142, 0.82)', border: 'rgba(86, 173, 142, 1)' },
    ];
    return palette[index % palette.length];
}

function buildSdmData(source, selectedYear) {
    const rows = Array.isArray(source?.rows) ? source.rows : [];
    const categories = Array.isArray(source?.categories) ? source.categories : [];
    const totals = new Map();

    categories.forEach(function (category) {
        totals.set(String(category.id), 0);
    });

    rows.forEach(function (row) {
        if (selectedYear !== 'all' && Number(row.year) !== Number(selectedYear)) {
            return;
        }

        const key = String(row.key || '').trim();
        if (!key) {
            return;
        }

        totals.set(key, Number(totals.get(key) || 0) + Number(row.total || 0));
    });

    const labels = categories.map(function (category) {
        return category.label || category.id;
    });
    const data = categories.map(function (category) {
        return Number(totals.get(String(category.id)) || 0);
    });
    const maxValue = Math.max.apply(null, data.concat([0]));

    return {
        labels: labels,
        data: data,
        maxValue: maxValue,
    };
}

function updateChartEmptyState(key, hasData, message) {
    const emptyState = document.querySelector('[data-chart-empty="' + key + '"]');
    if (!emptyState) {
        return;
    }

    if (message) {
        emptyState.textContent = message;
    }
    emptyState.classList.toggle('is-hidden', hasData);
}

function buildSdmBarData(source, selectedYear) {
    const chartData = buildSdmData(source, selectedYear);
    const colors = chartData.labels.map(function (_, index) {
        return getChartPalette(index);
    });

    return {
        labels: chartData.labels,
        datasets: [
            {
                label: 'Total Pelatihan',
                data: chartData.data,
                backgroundColor: colors.map(function (color) { return color.background; }),
                borderColor: colors.map(function (color) { return color.border; }),
                borderWidth: 1,
                borderRadius: 8,
                borderSkipped: false,
                categoryPercentage: isMobileViewport() ? 0.76 : 0.68,
                barPercentage: isMobileViewport() ? 0.82 : 0.76,
                maxBarThickness: isSmallMobileViewport() ? 34 : 54,
            },
        ],
        maxValue: chartData.maxValue,
        hasData: chartData.data.some(function (value) { return Number(value) > 0; }),
    };
}

function buildSdmPieData(source, selectedYear) {
    const chartData = buildSdmData(source, selectedYear);
    const colors = chartData.labels.map(function (_, index) {
        return getChartPalette(index);
    });

    return {
        labels: chartData.labels,
        datasets: [
            {
                data: chartData.data,
                backgroundColor: colors.map(function (color) { return color.background; }),
                borderColor: colors.map(function (color) { return color.border; }),
                borderWidth: 1,
                hoverOffset: 8,
            },
        ],
        hasData: chartData.data.some(function (value) { return Number(value) > 0; }),
    };
}

function createSdmPieOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 850,
            easing: 'easeOutQuart',
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    boxWidth: isSmallMobileViewport() ? 7 : (isMobileViewport() ? 8 : 10),
                    padding: isSmallMobileViewport() ? 8 : (isMobileViewport() ? 10 : 14),
                    font: {
                        size: getChartFontSize(12, 10, 9),
                    },
                },
            },
            tooltip: {
                callbacks: {
                    label: function (context) {
                        const numericValue = Number(context.raw || 0);
                        const dataset = context.dataset?.data || [];
                        const total = dataset.reduce(function (sum, value) {
                            return sum + Number(value || 0);
                        }, 0);
                        const percentage = total > 0 ? ' (' + ((numericValue / total) * 100).toFixed(1).replace('.0', '') + '%)' : '';
                        return context.label + ': ' + (numericValue === 0 ? '-' : numericValue) + percentage;
                    },
                },
                titleFont: {
                    size: getChartFontSize(12, 10, 9),
                },
                bodyFont: {
                    size: getChartFontSize(12, 10, 9),
                },
            },
        },
    };
}

function initSdmTipeChart() {
    const canvas = document.getElementById('sdmTipeChart');
    const source = readDashboardChartData('sdm-tipe-data');
    const yearFilter = document.getElementById('sdmTipeYear');

    if (!canvas || !source || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSdmBarData(source, normalizeDashboardYearFilter(yearFilter.value));
        const options = createBaseBarOptions(chartData.maxValue);
        options.plugins.legend.display = false;
        options.plugins.tooltip.callbacks = {
            label: function (context) {
                const numericValue = Number(context.raw || 0);
                return 'Total: ' + (numericValue === 0 ? '-' : numericValue);
            },
        };
        options.scales.x.ticks.callback = function (value) {
            return wrapChartLabel(this.getLabelForValue(value), isMobileViewport() ? 12 : 18, 2);
        };
        updateChartEmptyState('sdm-tipe', chartData.hasData);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function initSdmJenisChart() {
    const canvas = document.getElementById('sdmJenisChart');
    const source = readDashboardChartData('sdm-jenis-data');
    const yearFilter = document.getElementById('sdmJenisYear');

    if (!canvas || !source || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSdmPieData(source, normalizeDashboardYearFilter(yearFilter.value));
        updateChartEmptyState('sdm-jenis', chartData.hasData);

        if (!chartInstance) {
            chartInstance = new Chart(canvas, {
                type: 'pie',
                data: {
                    labels: chartData.labels,
                    datasets: chartData.datasets,
                },
                options: createSdmPieOptions(),
            });
            return;
        }

        chartInstance.data.labels = chartData.labels;
        chartInstance.data.datasets = chartData.datasets;
        chartInstance.options = createSdmPieOptions();
        chartInstance.update(normalizeChartUpdateMode(updateMode));
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function initSdmCharts() {
    initSdmTipeChart();
    initSdmJenisChart();
}

function wrapChartLabel(label, maxCharsPerLine, maxLines) {
    if (typeof label !== 'string' || !label.trim()) {
        return label;
    }

    const normalizedLabel = label.replace(/\s+/g, ' ').trim();
    if (normalizedLabel.toLowerCase() === 'borehole camera') {
        return ['Borehole', 'Camera'];
    }
    if (normalizedLabel.length <= maxCharsPerLine) {
        return normalizedLabel;
    }

    const words = normalizedLabel.split(' ');
    const lines = [];
    let currentLine = '';

    words.forEach(function (word) {
        if (!word) {
            return;
        }

        if (word.length > maxCharsPerLine) {
            if (currentLine) {
                lines.push(currentLine);
                currentLine = '';
            }

            let remainingWord = word;
            while (remainingWord.length > maxCharsPerLine && lines.length < maxLines - 1) {
                lines.push(remainingWord.slice(0, maxCharsPerLine));
                remainingWord = remainingWord.slice(maxCharsPerLine);
            }
            currentLine = remainingWord;
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
        currentLine = word;
    });

    if (currentLine) {
        lines.push(currentLine);
    }

    if (!lines.length) {
        return normalizedLabel;
    }

    if (lines.length > maxLines) {
        const limitedLines = lines.slice(0, maxLines);
        const lastLineIndex = limitedLines.length - 1;
        let lastLine = limitedLines[lastLineIndex];
        if (lastLine.length >= maxCharsPerLine) {
            lastLine = lastLine.slice(0, Math.max(1, maxCharsPerLine - 1));
        }
        limitedLines[lastLineIndex] = lastLine.replace(/[\s.]+$/g, '') + '…';
        return limitedLines;
    }

    return lines;
}

function initPengukuranLapanganChart() {
    const canvas = document.getElementById('grafikUkur');
    const source = readDashboardChartData('data-ukur');
    const yearFilter = document.getElementById('tahunUkur');
    const monthFilter = document.getElementById('bulanUkur');

    if (!canvas || !source || !yearFilter || !monthFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildMonthlyGroupedChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            normalizeDashboardMonthFilter(monthFilter.value),
            'pengukuranKey',
            'categories',
            '',
        );

        const options = createBaseBarOptions(chartData.maxValue);
        options.plugins.tooltip.callbacks = {
            label: function (context) {
                const numericValue = Number(context.raw || 0);
                return context.dataset.label + ': ' + (numericValue === 0 ? '-' : numericValue);
            },
        };

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    monthFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}


function initApprovedPeminjamanChart() {
    const canvas = document.getElementById('grafikPinjam');
    const source = readDashboardChartData('data-pinjam');
    const yearFilter = document.getElementById('tahunPinjam');

    if (!canvas || !source || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildMonthlySingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            DASHBOARD_MONTH_FILTER_ALL_MONTHS,
        );
        const options = createBaseBarOptions(chartData.maxValue);
        options.plugins.legend.display = false;
        options.plugins.tooltip.callbacks = {
            label: function (context) {
                const numericValue = Number(context.raw || 0);
                return 'Total Peminjaman: ' + (numericValue === 0 ? '-' : numericValue);
            },
        };

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}


function initSurveiKegiatanChart() {
    const canvas = document.getElementById('grafikSurvei');
    const source = readDashboardChartData('data-survei');
    const holder = document.querySelector('[data-chart-holder="survei"]');
    const yearFilter = document.getElementById('tahunSurvei');

    if (!canvas || !source || !holder || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'surveiId',
            'Total Peminjaman',
        );
        updateScrollableChartWidth(holder, chartData.labels.length, isSmallMobileViewport() ? 54 : (isMobileViewport() ? 62 : 132));
        const options = createSingleSeriesChartOptions(chartData.maxValue, isMobileViewport() ? 13 : 18, isMobileViewport() ? 52 : 42);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function initInstansiTujuanChart(key) {
    const canvas = document.getElementById('grafik-' + key);
    const source = readDashboardChartData('data-' + key);
    const holder = document.querySelector('[data-chart-holder="' + key + '"]');
    const yearFilter = document.getElementById('tahun-' + key);

    if (!canvas || !source || !holder || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'instansiId',
            'Total Peminjaman',
        );
        updateScrollableChartWidth(holder, chartData.labels.length, isSmallMobileViewport() ? 56 : (isMobileViewport() ? 66 : 136));
        updateChartEmptyState(key, chartData.datasets[0].data.some(function (total) { return total > 0; }));
        const options = createSingleSeriesChartOptions(chartData.maxValue, isMobileViewport() ? 12 : 18, isMobileViewport() ? 58 : 46);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function initPeralatanSurveiChart() {
    const canvas = document.getElementById('grafikPeralatanSurvei');
    const source = readDashboardChartData('data-peralatan-survei');
    const holder = document.querySelector('[data-chart-holder="peralatan-survei"]');
    const yearFilter = document.getElementById('tahunPeralatanSurvei');

    if (!canvas || !source || !holder || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart(updateMode) {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'barangId',
            'Total Transaksi',
        );
        updateScrollableChartWidth(holder, chartData.labels.length, isSmallMobileViewport() ? 56 : (isMobileViewport() ? 66 : 136));
        updateChartEmptyState('peralatan-survei', chartData.datasets.some(function (dataset) {
            return dataset.data.some(function (value) {
                return Number(value) > 0;
            });
        }));
        const options = createSingleSeriesChartOptions(chartData.maxValue, isMobileViewport() ? 12 : 18, isMobileViewport() ? 58 : 46);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    yearFilter.addEventListener('change', renderChart);
    bindDashboardChartResize(renderChart);
    renderChart();
}

function getInventoryItems(source, selectedIds = null) {
    const items = Array.isArray(source?.items) ? source.items : [];
    return selectedIds === null ? items : items.filter(item => selectedIds.has(String(item.id)));
}

function bindInventoryFilter(key, renderChart) {
    const picker = document.querySelector('[data-chart-picker="' + key + '"]');
    if (!picker) {
        return () => null;
    }
    const inputs = Array.from(picker.querySelectorAll('input[type="checkbox"]'));
    const summary = picker.querySelector('[data-chart-selection]');
    const getSelection = () => new Set(inputs.filter(input => input.checked).map(input => input.value));

    function updateSelection() {
        const count = getSelection().size;
        summary.textContent = count > 0 && count === inputs.length ? 'All' : count + ' item';
    }

    picker.addEventListener('change', function () {
        updateSelection();
        renderChart();
    });
    picker.querySelectorAll('[data-chart-select]').forEach(function (button) {
        button.addEventListener('click', function () {
            inputs.forEach(input => { input.checked = button.dataset.chartSelect === 'all'; });
            updateSelection();
            renderChart();
        });
    });
    picker.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && picker.open) {
            picker.open = false;
            picker.querySelector('summary').focus();
            event.preventDefault();
        }
    });
    document.addEventListener('click', function (event) {
        if (!picker.contains(event.target)) {
            picker.open = false;
        }
    });
    updateSelection();
    return getSelection;
}

function createInventoryChartOptions(maxValue, units, stacked) {
    const options = createBaseBarOptions(maxValue);
    options.scales.x.stacked = stacked;
    options.scales.y.stacked = stacked;
    options.scales.x.ticks.maxRotation = isMobileViewport() ? 52 : 42;
    options.scales.x.ticks.minRotation = isMobileViewport() ? 52 : 42;
    options.scales.x.ticks.align = 'center';
    options.scales.x.ticks.callback = function (value) {
        return wrapChartLabel(this.getLabelForValue(value), isMobileViewport() ? 13 : 18, 2);
    };
    options.plugins.tooltip.callbacks = {
        label: function (context) {
            const numericValue = Number(context.raw || 0);
            const unit = units[context.dataIndex] ? ' ' + units[context.dataIndex] : '';
            return context.dataset.label + ': ' + numericValue + unit;
        },
    };
    return options;
}

function buildBahanChartData(source, selectedIds = null) {
    const items = getInventoryItems(source, selectedIds);
    const data = items.map(function (item) {
        return Number(item.stock || 0);
    });
    const barSizing = getBarSizing();

    return {
        labels: items.map(function (item) { return item.label; }),
        units: items.map(function (item) { return item.unit || ''; }),
        datasets: [
            {
                label: 'Stok',
                data: data,
                backgroundColor: source.backgroundColor,
                borderColor: source.backgroundColor,
                borderWidth: 1,
                borderRadius: 8,
                borderSkipped: false,
                ...barSizing,
            },
        ],
        maxValue: Math.max.apply(null, data.concat([0])),
        hasData: items.length > 0,
    };
}

function buildPenunjangChartData(source, selectedIds = null) {
    const items = getInventoryItems(source, selectedIds);
    const rusak = items.map(function (item) {
        return Number(item.rusak || 0);
    });
    const baik = items.map(function (item) {
        return Number(item.baik || 0);
    });
    const totals = items.map(function (_, index) {
        return rusak[index] + baik[index];
    });
    const barSizing = getBarSizing();
    const commonDataset = {
        stack: 'condition',
        borderWidth: 1,
        borderRadius: 0,
        borderSkipped: false,
        ...barSizing,
        showZeroDash: false,
    };

    return {
        labels: items.map(function (item) { return item.label; }),
        units: items.map(function (item) { return item.unit || ''; }),
        datasets: [
            {
                ...commonDataset,
                label: 'Rusak',
                data: rusak,
                backgroundColor: 'rgba(220, 53, 69, 0.78)',
                borderColor: 'rgba(220, 53, 69, 1)',
            },
            {
                ...commonDataset,
                label: 'Baik',
                data: baik,
                backgroundColor: 'rgba(100, 205, 209, 0.86)',
                borderColor: 'rgba(16, 62, 111, 0.82)',
            },
        ],
        maxValue: Math.max.apply(null, totals.concat([0])),
        hasData: items.length > 0,
    };
}

function initBahanOperasionalChart() {
    const canvas = document.getElementById('grafikBahan');
    const source = readDashboardChartData('data-bahan');
    const holder = document.querySelector('[data-chart-holder="bahan"]');

    if (!canvas || !source || !holder) {
        return;
    }

    let chartInstance = null;
    const getSelection = bindInventoryFilter('bahan', renderChart);

    function renderChart(updateMode) {
        const chartData = buildBahanChartData(source, getSelection());
        updateScrollableChartWidth(holder, chartData.labels.length, isMobileViewport() ? 72 : 118);
        updateChartEmptyState('bahan', chartData.hasData, getInventoryItems(source).length
            ? 'Pilih minimal satu bahan operasional untuk menampilkan grafik.'
            : 'Belum ada data bahan operasional.');
        const options = createInventoryChartOptions(chartData.maxValue, chartData.units, false);
        options.plugins.legend.display = false;
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    bindDashboardChartResize(renderChart);
    renderChart();
}

function initBarangPenunjangChart() {
    const canvas = document.getElementById('grafikPenunjang');
    const source = readDashboardChartData('data-penunjang');
    const holder = document.querySelector('[data-chart-holder="penunjang"]');

    if (!canvas || !source || !holder) {
        return;
    }

    let chartInstance = null;
    const getSelection = bindInventoryFilter('penunjang', renderChart);

    function renderChart(updateMode) {
        const chartData = buildPenunjangChartData(source, getSelection());
        updateScrollableChartWidth(holder, chartData.labels.length, isMobileViewport() ? 72 : 118);
        updateChartEmptyState('penunjang', chartData.hasData, getInventoryItems(source).length
            ? 'Pilih minimal satu barang penunjang untuk menampilkan grafik.'
            : 'Belum ada data barang penunjang lapangan.');
        const options = createInventoryChartOptions(chartData.maxValue, chartData.units, true);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options, updateMode);
    }

    bindDashboardChartResize(renderChart);
    renderChart();
}

function initInventoryCharts() {
    initBahanOperasionalChart();
    initBarangPenunjangChart();
}

function debounce(callback, delay) {
    let timeoutId;
    return function () {
        const args = arguments;
        clearTimeout(timeoutId);
        timeoutId = setTimeout(function () {
            callback.apply(null, args);
        }, delay);
    };
}


function initChartDownloadActions() {
    const menuToggles = document.querySelectorAll('[data-chart-menu-toggle]');
    const downloadButtons = document.querySelectorAll('[data-chart-download]');

    if (!menuToggles.length || !downloadButtons.length) {
        return;
    }

    function closeChartDownloadMenus(exceptMenu) {
        document.querySelectorAll('.chart-download.is-open').forEach(function (menu) {
            if (exceptMenu && menu === exceptMenu) {
                return;
            }

            menu.classList.remove('is-open');
            const toggle = menu.querySelector('[data-chart-menu-toggle]');
            if (toggle) {
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    menuToggles.forEach(function (toggle) {
        toggle.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();

            const menu = toggle.closest('.chart-download');
            if (!menu) {
                return;
            }

            const willOpen = !menu.classList.contains('is-open');
            closeChartDownloadMenus(menu);
            menu.classList.toggle('is-open', willOpen);
            toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        });
    });

    downloadButtons.forEach(function (button) {
        button.addEventListener('click', async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const chartId = button.dataset.chartTarget;
            const title = button.dataset.chartTitle || 'Dashboard Chart';
            const format = button.dataset.chartDownload || 'jpg';

            closeChartDownloadMenus();
            button.disabled = true;
            try {
                if (format === 'xlsx') {
                    await downloadDashboardChartExcel(
                        chartId,
                        title,
                        button.dataset.chartExportUrl
                    );
                } else {
                    downloadDashboardChart(chartId, title);
                }
            } catch (error) {
                window.alert(error.message || 'Download grafik gagal diproses.');
            } finally {
                button.disabled = false;
            }
        });
    });

    document.addEventListener('click', function (event) {
        if (!event.target.closest('.chart-download')) {
            closeChartDownloadMenus();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeChartDownloadMenus();
        }
    });
}

function getDashboardCsrfToken() {
    const cookie = document.cookie
        .split(';')
        .map(function (item) { return item.trim(); })
        .find(function (item) { return item.startsWith('csrftoken='); });
    return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

function normalizeDashboardChartValue(value) {
    if (value && typeof value === 'object') {
        return Number(value.y ?? value.x ?? 0);
    }
    return Number(value || 0);
}

async function downloadDashboardChartExcel(chartId, title, exportUrl) {
    const canvas = document.getElementById(chartId);
    const chartInstance = canvas && typeof Chart !== 'undefined' ? Chart.getChart(canvas) : null;
    if (!chartInstance || !exportUrl) {
        throw new Error('Data grafik tidak tersedia untuk export Excel.');
    }

    chartInstance.update('none');
    const payload = {
        title: title,
        type: chartInstance.config.type || 'bar',
        stacked: Boolean(
            chartInstance.options?.scales?.x?.stacked ||
            chartInstance.options?.scales?.y?.stacked
        ),
        labels: (chartInstance.data.labels || []).map(function (label) {
            return Array.isArray(label) ? label.join(' ') : String(label ?? '-');
        }),
        datasets: (chartInstance.data.datasets || []).map(function (dataset, index) {
            return {
                label: dataset.label || 'Data ' + (index + 1),
                data: (dataset.data || []).map(normalizeDashboardChartValue),
            };
        }),
    };

    const response = await fetch(exportUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getDashboardCsrfToken(),
        },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        let message = 'Export Excel grafik gagal diproses.';
        try {
            const errorData = await response.json();
            message = errorData.error || message;
        } catch (error) {
            // Respons non-JSON tetap menggunakan pesan standar.
        }
        throw new Error(message);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = buildDashboardChartFileName(title, 'xlsx');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);
}

function downloadDashboardChart(chartId, title) {
    const canvas = document.getElementById(chartId);
    if (!canvas) {
        return;
    }

    const exportCanvas = buildDashboardChartExportCanvas(canvas, title);
    const dataUrl = exportCanvas.toDataURL('image/jpeg', 0.98);

    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = buildDashboardChartFileName(title, 'jpg');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function copyChartExport(value) {
    if (Array.isArray(value)) {
        return value.map(copyChartExport);
    }
    if (value && Object.prototype.toString.call(value) === '[object Object]') {
        return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, copyChartExport(item)]));
    }
    return value;
}

function wrapExportText(context, text, maxWidth) {
    const lines = [];
    let line = '';
    String(text).trim().split(/\s+/).forEach(function (word) {
        if (line && context.measureText(line + word).width > maxWidth) {
            lines.push(line);
            line = '';
        }
        for (const character of word) {
            if (context.measureText(line + character).width > maxWidth && line) {
                lines.push(line);
                line = '';
            }
            line += character;
        }
        line += ' ';
    });
    if (line.trim()) {
        lines.push(line.trim());
    }
    return lines.map(item => item.trim());
}

function getChartExportFilters(canvas) {
    const section = canvas.closest('.dashboard-chart');
    if (!section) {
        return 'Semua data';
    }
    const filters = Array.from(section.querySelectorAll('select')).map(function (select) {
        const name = /tahun|year/i.test(select.id) ? 'Tahun' : 'Periode';
        return name + ': ' + (select.selectedOptions[0]?.textContent.trim() || 'All');
    });
    const selection = section.querySelector('[data-chart-selection]');
    if (selection) {
        filters.push('Pilihan: ' + selection.textContent.trim());
    }
    return filters.join('   /   ') || 'Semua data';
}

function renderChartExport(chart, context, x, y, width, height) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const options = copyChartExport(chart.config.options);
    options.responsive = false;
    options.maintainAspectRatio = false;
    options.animation = false;
    options.animations = false;
    options.devicePixelRatio = 2;
    options.events = [];
    options.onResize = null;
    options.font = { family: 'Arial, sans-serif', size: 14 };
    options.layout = { padding: 12 };
    options.plugins = options.plugins || {};
    options.plugins.tooltip = { enabled: false };
    options.plugins.zeroValueDashPlugin = { fontSize: 13 };
    if (options.plugins.legend !== false) {
        const legend = options.plugins.legend = options.plugins.legend || {};
        legend.labels = { ...legend.labels, font: { family: 'Arial, sans-serif', size: 14 }, padding: 18, boxWidth: 12 };
    }
    Object.values(options.scales || {}).forEach(function (scale) {
        scale.ticks = { ...scale.ticks, font: { family: 'Arial, sans-serif', size: 14 }, color: '#48627b' };
    });
    if (chart.config.type === 'bar' && options.scales?.x) {
        const ticks = options.scales.x.ticks;
        const longLabels = chart.data.labels.some(label => String(label).length > 14);
        const dense = chart.data.labels.length > 24;
        ticks.font.size = dense ? 12 : 14;
        ticks.minRotation = ticks.maxRotation = dense ? 65 : longLabels ? 35 : 0;
        ticks.callback = function (value) {
            const label = this.getLabelForValue(value);
            return dense ? label : wrapChartLabel(label, 20, Infinity);
        };
    }
    const data = copyChartExport(chart.data);
    data.datasets.forEach((dataset, index) => { dataset.hidden = !chart.isDatasetVisible(index); });
    let rendered;
    try {
        rendered = new Chart(canvas, { type: chart.config.type, data: data, options: options });
        if (chart.config.type === 'pie' || chart.config.type === 'doughnut') {
            data.labels.forEach((_, index) => {
                if (!chart.getDataVisibility(index)) {
                    rendered.toggleDataVisibility(index);
                }
            });
            rendered.update('none');
        }
        context.drawImage(canvas, x, y, width, height);
    } finally {
        (rendered || Chart.getChart(canvas))?.destroy();
        canvas.width = canvas.height = 0;
    }
}

function buildDashboardChartExportCanvas(sourceCanvas, title) {
    const chart = typeof Chart !== 'undefined' ? Chart.getChart(sourceCanvas) : null;
    const labelCount = chart?.data?.labels?.length || 0;
    const width = Math.min(2400, Math.max(1600, labelCount * 72 + 160));
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) {
        return sourceCanvas;
    }
    // Measure text before sizing the final canvas; canvas sizing resets its context.
    context.font = '700 32px Arial, sans-serif';
    const titles = wrapExportText(context, title || 'Dashboard Laboratorium', width - 160);
    context.font = '14px Arial, sans-serif';
    const filters = wrapExportText(context, getChartExportFilters(sourceCanvas), width - 160);
    const headerHeight = 96 + titles.length * 42 + filters.length * 21;
    const plotY = 40 + headerHeight + 24;
    const height = Math.max(Math.round(width * 9 / 16), plotY + 520 + 76);
    const plotHeight = height - plotY - 76;
    canvas.width = width * 2;
    canvas.height = height * 2;
    context.scale(2, 2);
    context.textBaseline = 'top';

    function box(x, y, w, h, fill, border) {
        context.beginPath();
        if (typeof context.roundRect === 'function') {
            context.roundRect(x, y, w, h, 20);
        } else {
            context.rect(x, y, w, h);
        }
        context.fillStyle = fill;
        context.fill();
        if (border) {
            context.strokeStyle = border;
            context.lineWidth = 1;
            context.stroke();
        }
    }

    context.fillStyle = '#edf3f8';
    context.fillRect(0, 0, width, height);
    const gradient = context.createLinearGradient(40, 40, width - 40, 40 + headerHeight);
    gradient.addColorStop(0, '#103e6f');
    gradient.addColorStop(1, '#1c647c');
    box(40, 40, width - 80, headerHeight, gradient);
    context.fillStyle = '#64cdd1';
    context.fillRect(64, 65, 5, 14);
    context.font = '700 13px Arial, sans-serif';
    context.fillStyle = '#c6eef2';
    context.fillText('SILEBAT  /  DASHBOARD LABORATORIUM', 80, 65);
    context.fillStyle = '#ffffff';
    context.font = '700 32px Arial, sans-serif';
    titles.forEach((line, index) => context.fillText(line, 64, 98 + index * 42));
    context.fillStyle = '#d7eaf2';
    context.font = '14px Arial, sans-serif';
    filters.forEach((line, index) => context.fillText(line, 64, 116 + titles.length * 42 + index * 21));

    box(40, plotY, width - 80, plotHeight, '#ffffff', '#d9e3ef');
    if (chart && labelCount && chart.data.datasets.some((_, index) => chart.isDatasetVisible(index))) {
        renderChartExport(chart, context, 68, plotY + 28, width - 136, plotHeight - 56);
    } else if (!chart) {
        const ratio = Math.min((width - 136) / sourceCanvas.width, (plotHeight - 56) / sourceCanvas.height);
        const w = sourceCanvas.width * ratio;
        const h = sourceCanvas.height * ratio;
        context.drawImage(sourceCanvas, (width - w) / 2, plotY + (plotHeight - h) / 2, w, h);
    } else {
        context.fillStyle = '#48627b';
        context.font = '18px Arial, sans-serif';
        context.textAlign = 'center';
        context.fillText('Belum ada data untuk pilihan ini.', width / 2, plotY + plotHeight / 2);
    }

    context.textAlign = 'left';
    context.fillStyle = '#48627b';
    context.font = '13px Arial, sans-serif';
    context.fillText('Sumber: Dashboard SILEBAT', 44, height - 46);
    context.textAlign = 'right';
    const exportedAt = new Date().toLocaleString('id-ID', {
        timeZone: 'Asia/Jakarta', day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
    });
    context.fillText('Diunduh: ' + exportedAt, width - 44, height - 46);
    return canvas;
}

function buildDashboardChartFileName(title, format) {
    const safeTitle = String(title || 'dashboard-chart')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'dashboard-chart';
    const today = new Date();
    const dateCode = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0'),
    ].join('');

    return safeTitle + '-' + dateCode + '.' + format;
}
