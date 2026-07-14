/* ========================================
   MASTER DETAIL JS
   Grafik riwayat transaksi detail alat.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initAssetHistoryChart();
});

const ASSET_MONTH_LABELS = {
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

function readAssetChartData() {
    const script = document.getElementById('asset-chart-data');
    if (!script) {
        return null;
    }

    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Gagal membaca data grafik riwayat alat.', error);
        return null;
    }
}

function toNumber(value) {
    const numericValue = Number(value || 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
}

function buildAssetRows(source, filterValue) {
    const allValue = source.allValue || 'all';
    if (String(filterValue) === allValue) {
        const yearTotals = new Map();
        (source.yearRows || []).forEach(function (row) {
            const year = Number(row.year);
            if (year) {
                yearTotals.set(year, toNumber(row.total));
            }
        });

        const years = (source.availableYears || [])
            .map(Number)
            .filter(Boolean)
            .sort(function (left, right) { return left - right; });

        return {
            labels: years.map(String),
            values: years.map(function (year) { return yearTotals.get(year) || 0; }),
            title: source.chartTitle || 'Total Riwayat per Tahun',
        };
    }

    const selectedYear = Number(filterValue || source.currentYear);
    const monthTotals = new Map();
    (source.rows || []).forEach(function (row) {
        if (Number(row.year) === selectedYear) {
            monthTotals.set(Number(row.month), toNumber(row.total));
        }
    });

    const monthLabels = source.monthLabels || ASSET_MONTH_LABELS;
    const months = Array.from({ length: 12 }, function (_, index) { return index + 1; });

    return {
        labels: months.map(function (month) {
            return monthLabels[month] || ASSET_MONTH_LABELS[month] || String(month);
        }),
        values: months.map(function (month) { return monthTotals.get(month) || 0; }),
        title: source.chartTitle || ('Riwayat Tahun ' + selectedYear),
    };
}

function buildAssetChartOptions(maxValue, chartTitle) {
    const isEmpty = toNumber(maxValue) <= 0;

    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 800,
            easing: 'easeOutQuart',
        },
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: chartTitle,
                color: '#103e6f',
                font: {
                    size: 14,
                    weight: '700',
                },
            },
            tooltip: {
                callbacks: {
                    label: function (context) {
                        const value = toNumber(context.parsed.y);
                        const label = context.chart.$assetTooltipLabel || 'Jumlah';
                        return label + ': ' + value;
                    },
                },
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#4b647c',
                    maxRotation: 0,
                    autoSkip: false,
                },
            },
            y: {
                beginAtZero: true,
                suggestedMax: isEmpty ? 1 : undefined,
                ticks: {
                    precision: 0,
                    stepSize: 1,
                    color: '#4b647c',
                },
                grid: {
                    color: 'rgba(16, 62, 111, 0.12)',
                },
            },
        },
    };
}

function syncAssetFilterUrl(filterValue, source) {
    if (!window.history || !window.history.replaceState || !source.filterParam) {
        return;
    }

    const url = new URL(window.location.href);
    const currentYear = String(source.currentYear || '');
    const value = String(filterValue || '');
    if (!value || value === currentYear) {
        url.searchParams.delete(source.filterParam);
    } else {
        url.searchParams.set(source.filterParam, value);
    }
    window.history.replaceState({}, '', url.toString());
}

function syncAssetPlotWidth(rows, source, chartWrap, chartPlot) {
    if (!source || !source.scrollMobile || !chartWrap || !chartPlot) {
        return;
    }

    const labelCount = Array.isArray(rows.labels) ? rows.labels.length : 0;
    const baseWidth = chartWrap.clientWidth || chartPlot.clientWidth || 0;
    const targetWidth = Math.max(baseWidth, (labelCount * 44) + 96);
    chartPlot.style.setProperty('--asset-chart-width', Math.ceil(targetWidth) + 'px');
}

function fillAssetYearFilter(yearFilter, source) {
    if (!yearFilter) {
        return;
    }

    const allOption = document.createElement('option');
    allOption.value = source.allValue || 'all';
    allOption.textContent = 'All';
    const options = [allOption];

    (source.availableYears || []).forEach(function (year) {
        const option = document.createElement('option');
        option.value = String(year);
        option.textContent = String(year);
        options.push(option);
    });

    yearFilter.replaceChildren.apply(yearFilter, options);
    yearFilter.value = String(source.selectedYear || source.currentYear || '');
    if (!yearFilter.value) {
        yearFilter.value = String(source.currentYear || source.allValue || 'all');
    }
    yearFilter.setAttribute('aria-label', 'Filter tahun ' + String(source.title || '').toLowerCase());
}

function initAssetHistoryChart() {
    if (typeof Chart === 'undefined') {
        return;
    }

    const pack = readAssetChartData();
    const sources = pack && Array.isArray(pack.items) ? pack.items : [];
    const canvas = document.querySelector('[data-asset-chart-canvas]');
    const card = document.querySelector('[data-asset-chart-card]');
    const title = document.querySelector('[data-asset-chart-title]');
    const chartWrap = document.querySelector('[data-asset-chart-wrap]');
    const chartPlot = document.querySelector('[data-asset-chart-plot]');
    const yearFilter = document.querySelector('[data-asset-year-filter]');
    const emptyState = document.querySelector('[data-asset-chart-empty]');
    const switchButtons = Array.from(document.querySelectorAll('[data-asset-chart-switch]'));

    if (!canvas || !sources.length) {
        return;
    }

    let activeSource = sources[0];
    fillAssetYearFilter(yearFilter, activeSource);
    const initialRows = buildAssetRows(activeSource, yearFilter ? yearFilter.value : activeSource.selectedYear);
    const initialMax = Math.max.apply(null, initialRows.values.concat([0]));
    syncAssetPlotWidth(initialRows, activeSource, chartWrap, chartPlot);

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: initialRows.labels,
            datasets: [{
                label: activeSource.datasetLabel || 'Jumlah Riwayat',
                data: initialRows.values,
                backgroundColor: activeSource.backgroundColor || 'rgba(16, 62, 111, 0.82)',
                borderColor: activeSource.borderColor || 'rgba(16, 62, 111, 1)',
                borderWidth: 1,
                borderRadius: 8,
                maxBarThickness: 58,
                categoryPercentage: 0.78,
                barPercentage: 0.78,
            }],
        },
        options: buildAssetChartOptions(initialMax, initialRows.title),
    });

    function updateChart(filterValue, syncUrl) {
        const nextRows = buildAssetRows(activeSource, filterValue);
        const nextTotal = nextRows.values.reduce(function (sum, value) {
            return sum + toNumber(value);
        }, 0);
        const nextMax = Math.max.apply(null, nextRows.values.concat([0]));
        const dataset = chart.data.datasets[0];

        activeSource.selectedYear = filterValue;
        syncAssetPlotWidth(nextRows, activeSource, chartWrap, chartPlot);
        chart.resize();
        chart.$assetTooltipLabel = activeSource.tooltipLabel || 'Jumlah';
        chart.data.labels = nextRows.labels;
        dataset.label = activeSource.datasetLabel || 'Jumlah Riwayat';
        dataset.data = nextRows.values;
        dataset.backgroundColor = activeSource.backgroundColor || 'rgba(16, 62, 111, 0.82)';
        dataset.borderColor = activeSource.borderColor || 'rgba(16, 62, 111, 1)';
        chart.options.plugins.title.text = nextRows.title;
        chart.options.scales.y.suggestedMax = nextMax <= 0 ? 1 : undefined;
        chart.update();

        if (title) {
            title.textContent = activeSource.title;
        }
        if (card) {
            card.setAttribute('aria-label', activeSource.title);
        }
        canvas.setAttribute('aria-label', 'Grafik ' + String(activeSource.title || '').toLowerCase());
        if (emptyState) {
            emptyState.textContent = activeSource.emptyText || 'Belum ada data untuk filter ini.';
            emptyState.classList.toggle('is-hidden', nextTotal > 0);
        }
        if (syncUrl) {
            syncAssetFilterUrl(filterValue, activeSource);
        }
    }

    updateChart(yearFilter ? yearFilter.value : activeSource.selectedYear, false);

    if (yearFilter) {
        yearFilter.addEventListener('change', function () {
            updateChart(yearFilter.value, true);
        });
    }

    switchButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const nextSource = sources.find(function (source) {
                return source.key === button.dataset.assetChartSwitch;
            });
            if (!nextSource || nextSource === activeSource) {
                return;
            }

            activeSource = nextSource;
            switchButtons.forEach(function (item) {
                const isActive = item === button;
                item.classList.toggle('asset-chart-switch__button--active', isActive);
                item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
            fillAssetYearFilter(yearFilter, activeSource);
            if (chartWrap) {
                chartWrap.scrollLeft = 0;
            }
            updateChart(yearFilter ? yearFilter.value : activeSource.selectedYear, false);
        });
    });
}
