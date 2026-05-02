/* ========================================
   DASHBOARD JS
   JS halaman dashboard.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initDashboardCharts();
    initChartDownloadActions();
});

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
        ctx.font = '600 ' + getChartFontSize(11, 10, 9) + 'px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

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
    initInstansiTujuanChart();
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
                    duration: 280,
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


function getGroupedBarSizing() {
    return {
        categoryPercentage: isMobileViewport() ? 0.9 : 0.92,
        barPercentage: isMobileViewport() ? 0.94 : 0.96,
        maxBarThickness: isSmallMobileViewport() ? 24 : (isMobileViewport() ? 28 : 48),
    };
}

function getSingleBarSizing(isScrollableChart) {
    if (isScrollableChart) {
        return {
            categoryPercentage: isSmallMobileViewport() ? 1.0 : (isMobileViewport() ? 0.99 : 0.94),
            barPercentage: isSmallMobileViewport() ? 0.99 : (isMobileViewport() ? 0.98 : 0.94),
            maxBarThickness: isSmallMobileViewport() ? 34 : (isMobileViewport() ? 38 : 52),
        };
    }

    return {
        categoryPercentage: 0.92,
        barPercentage: 0.94,
        maxBarThickness: isSmallMobileViewport() ? 28 : (isMobileViewport() ? 32 : 52),
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

    const barSizing = getGroupedBarSizing();
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
            categoryPercentage: barSizing.categoryPercentage,
            barPercentage: barSizing.barPercentage,
            maxBarThickness: barSizing.maxBarThickness,
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

    const barSizing = getSingleBarSizing(false);
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
                categoryPercentage: barSizing.categoryPercentage,
                barPercentage: barSizing.barPercentage,
                maxBarThickness: barSizing.maxBarThickness,
            },
        ],
        maxValue: maxValue,
    };
}



function buildSingleSeriesChartData(source, selectedYear, idKey, datasetLabel, chartType) {
    const rows = Array.isArray(source?.rows) ? source.rows : [];
    const categories = Array.isArray(source?.categories) ? source.categories : [];
    const totals = new Map();

    rows.forEach(function (row) {
        if (selectedYear !== 'all' && Number(row.year) !== Number(selectedYear)) {
            return;
        }

        const currentTotal = Number(totals.get(row[idKey]) || 0);
        totals.set(row[idKey], currentTotal + Number(row.total || 0));
    });

    const isScrollableChart = chartType === 'scrollable';
    const barSizing = getSingleBarSizing(isScrollableChart);
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
                categoryPercentage: barSizing.categoryPercentage,
                barPercentage: barSizing.barPercentage,
                maxBarThickness: barSizing.maxBarThickness,
            },
        ],
        maxValue: maxValue,
    };
}

function upsertBarChart(currentChart, canvas, labels, datasets, options) {
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
    currentChart.update();
    return currentChart;
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
    const canvas = document.getElementById('timKegiatanChart');
    const source = readDashboardChartData('tim-chart-data');
    const yearFilter = document.getElementById('timChartYearFilter');
    const monthFilter = document.getElementById('timChartMonthFilter');

    if (!canvas || !source || !yearFilter || !monthFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
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

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    monthFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
}

function initLayananKegiatanChart() {
    const canvas = document.getElementById('layananKegiatanChart');
    const source = readDashboardChartData('layanan-chart-data');
    const yearFilter = document.getElementById('layananChartYearFilter');

    if (!canvas || !source || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'layananId',
            'Total Peminjaman',
            'standard',
        );
        const options = createSingleSeriesChartOptions(chartData.maxValue, 18, isMobileViewport() ? 55 : 42);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
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
    const canvas = document.getElementById('pengukuranLapanganChart');
    const source = readDashboardChartData('pengukuran-chart-data');
    const yearFilter = document.getElementById('pengukuranChartYearFilter');
    const monthFilter = document.getElementById('pengukuranChartMonthFilter');

    if (!canvas || !source || !yearFilter || !monthFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
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

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    monthFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
}


function initApprovedPeminjamanChart() {
    const canvas = document.getElementById('approvedPeminjamanChart');
    const source = readDashboardChartData('approved-peminjaman-chart-data');
    const yearFilter = document.getElementById('approvedPeminjamanChartYearFilter');
    const monthFilter = document.getElementById('approvedPeminjamanChartMonthFilter');

    if (!canvas || !source || !yearFilter || !monthFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
        const chartData = buildMonthlySingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            normalizeDashboardMonthFilter(monthFilter.value),
        );
        const options = createBaseBarOptions(chartData.maxValue);
        options.plugins.legend.display = false;
        options.plugins.tooltip.callbacks = {
            label: function (context) {
                const numericValue = Number(context.raw || 0);
                return 'Total Peminjaman: ' + (numericValue === 0 ? '-' : numericValue);
            },
        };

        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    monthFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
}


function initSurveiKegiatanChart() {
    const canvas = document.getElementById('surveiKegiatanChart');
    const source = readDashboardChartData('survei-chart-data');
    const holder = document.querySelector('[data-chart-holder="survei"]');
    const yearFilter = document.getElementById('surveiChartYearFilter');

    if (!canvas || !source || !holder || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'surveiId',
            'Total Peminjaman',
            'scrollable',
        );
        updateScrollableChartWidth(holder, chartData.labels.length, isSmallMobileViewport() ? 54 : (isMobileViewport() ? 62 : 132));
        const options = createSingleSeriesChartOptions(chartData.maxValue, isMobileViewport() ? 13 : 18, isMobileViewport() ? 52 : 42);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
}

function initInstansiTujuanChart() {
    const canvas = document.getElementById('instansiTujuanKegiatanChart');
    const source = readDashboardChartData('instansi-chart-data');
    const holder = document.querySelector('[data-chart-holder="instansi"]');
    const yearFilter = document.getElementById('instansiChartYearFilter');

    if (!canvas || !source || !holder || !yearFilter) {
        return;
    }

    let chartInstance = null;

    function renderChart() {
        const chartData = buildSingleSeriesChartData(
            source,
            normalizeDashboardYearFilter(yearFilter.value),
            'instansiId',
            'Total Peminjaman',
            'scrollable',
        );
        updateScrollableChartWidth(holder, chartData.labels.length, isSmallMobileViewport() ? 56 : (isMobileViewport() ? 66 : 136));
        const options = createSingleSeriesChartOptions(chartData.maxValue, isMobileViewport() ? 12 : 18, isMobileViewport() ? 58 : 46);
        chartInstance = upsertBarChart(chartInstance, canvas, chartData.labels, chartData.datasets, options);
    }

    yearFilter.addEventListener('change', renderChart);
    window.addEventListener('resize', debounce(renderChart, 180));
    renderChart();
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
        button.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();

            const chartId = button.dataset.chartTarget;
            const title = button.dataset.chartTitle || 'Dashboard Chart';

            downloadDashboardChart(chartId, title);
            closeChartDownloadMenus();
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

function downloadDashboardChart(chartId, title) {
    const canvas = document.getElementById(chartId);
    if (!canvas) {
        return;
    }

    if (typeof Chart !== 'undefined') {
        const chartInstance = Chart.getChart(canvas);
        if (chartInstance && typeof chartInstance.update === 'function') {
            chartInstance.update('none');
        }
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

function buildDashboardChartExportCanvas(sourceCanvas, title) {
    const sourceWidth = sourceCanvas.width || sourceCanvas.clientWidth || 1200;
    const sourceHeight = sourceCanvas.height || sourceCanvas.clientHeight || 600;
    const exportScale = 2;
    const titleHeight = 92;
    const paddingX = 48;
    const paddingBottom = 38;
    const exportCanvas = document.createElement('canvas');
    const exportContext = exportCanvas.getContext('2d');
    const exportWidth = Math.max(1200, sourceWidth + (paddingX * 2));
    const exportHeight = Math.max(720, sourceHeight + titleHeight + paddingBottom);

    exportCanvas.width = exportWidth * exportScale;
    exportCanvas.height = exportHeight * exportScale;

    if (!exportContext) {
        return sourceCanvas;
    }

    exportContext.scale(exportScale, exportScale);

    const rootStyle = getComputedStyle(document.documentElement);
    const backgroundColor = rootStyle.getPropertyValue('--color-white').trim() || '#ffffff';
    const titleColor = rootStyle.getPropertyValue('--color-primary-navy').trim() || '#103e6f';
    const borderColor = rootStyle.getPropertyValue('--color-soft-gray').trim() || '#f0f4f6';

    exportContext.fillStyle = backgroundColor;
    exportContext.fillRect(0, 0, exportWidth, exportHeight);

    exportContext.fillStyle = titleColor;
    exportContext.font = '700 32px Arial, sans-serif';
    exportContext.textAlign = 'center';
    exportContext.textBaseline = 'middle';
    exportContext.fillText(title || 'Dashboard Chart', exportWidth / 2, 42, exportWidth - (paddingX * 2));

    exportContext.strokeStyle = borderColor;
    exportContext.lineWidth = 1;
    exportContext.beginPath();
    exportContext.moveTo(paddingX, 78);
    exportContext.lineTo(exportWidth - paddingX, 78);
    exportContext.stroke();

    const availableWidth = exportWidth - (paddingX * 2);
    const availableHeight = exportHeight - titleHeight - paddingBottom;
    const drawRatio = Math.min(availableWidth / sourceWidth, availableHeight / sourceHeight);
    const drawWidth = sourceWidth * drawRatio;
    const drawHeight = sourceHeight * drawRatio;
    const drawX = (exportWidth - drawWidth) / 2;
    const drawY = titleHeight;

    exportContext.drawImage(sourceCanvas, drawX, drawY, drawWidth, drawHeight);

    return exportCanvas;
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
