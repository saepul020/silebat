/* ========================================
   MASTER DETAIL JS
   Grafik riwayat peminjaman detail barang.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initAssetLoanChart();
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

function readAssetLoanData() {
    const script = document.getElementById('asset-loan-chart-data');
    if (!script) {
        return null;
    }

    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Gagal membaca data grafik peminjaman alat.', error);
        return null;
    }
}

function toNumber(value) {
    const numericValue = Number(value || 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
}

function buildLoanRows(source, filterValue) {
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
            title: source.chartTitle || 'Total Peminjaman per Tahun',
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
        labels: months.map(function (month) { return monthLabels[month] || ASSET_MONTH_LABELS[month] || String(month); }),
        values: months.map(function (month) { return monthTotals.get(month) || 0; }),
        title: source.chartTitle || ('Peminjaman Tahun ' + selectedYear),
    };
}

function buildAssetLoanOptions(maxValue, chartTitle) {
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
                        return 'Jumlah peminjaman: ' + value;
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

function syncLoanFilterUrl(filterValue, source) {
    if (!window.history || !window.history.replaceState) {
        return;
    }

    const url = new URL(window.location.href);
    const currentYear = String(source.currentYear || '');
    const value = String(filterValue || '');
    if (!value || value === currentYear) {
        url.searchParams.delete('tahun_pinjam');
    } else {
        url.searchParams.set('tahun_pinjam', value);
    }
    window.history.replaceState({}, '', url.toString());
}

function syncLoanPlotWidth(rows, source, chartWrap, chartPlot) {
    if (!source || !source.scrollMobile || !chartWrap || !chartPlot) {
        return;
    }

    const labelCount = Array.isArray(rows.labels) ? rows.labels.length : 0;
    const baseWidth = chartWrap.clientWidth || chartPlot.clientWidth || 0;
    const targetWidth = Math.max(baseWidth, (labelCount * 44) + 96);
    chartPlot.style.setProperty('--loan-chart-width', Math.ceil(targetWidth) + 'px');
}

function initAssetLoanChart() {
    if (typeof Chart === 'undefined') {
        return;
    }

    const canvas = document.querySelector('[data-loan-chart-canvas]');
    const chartWrap = document.querySelector('[data-loan-chart-wrap]');
    const chartPlot = document.querySelector('[data-loan-chart-plot]');
    const yearFilter = document.querySelector('[data-loan-year-filter]');
    const emptyState = document.querySelector('[data-loan-chart-empty]');
    const source = readAssetLoanData();

    if (!canvas || !source) {
        return;
    }

    const initialValue = yearFilter ? yearFilter.value : source.selectedYear;
    const initialRows = buildLoanRows(source, initialValue);
    const initialMax = Math.max.apply(null, initialRows.values.concat([0]));
    syncLoanPlotWidth(initialRows, source, chartWrap, chartPlot);

    const loanDataset = {
        label: source.datasetLabel || 'Jumlah Peminjaman',
        data: initialRows.values,
        backgroundColor: 'rgba(16, 62, 111, 0.82)',
        borderColor: 'rgba(16, 62, 111, 1)',
        borderWidth: 1,
        borderRadius: 8,
        maxBarThickness: 58,
    };

    if (source.scrollMobile) {
        loanDataset.categoryPercentage = 0.78;
        loanDataset.barPercentage = 0.78;
    }

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: initialRows.labels,
            datasets: [loanDataset],
        },
        options: buildAssetLoanOptions(initialMax, initialRows.title),
    });

    function updateChart(filterValue, syncUrl) {
        const nextRows = buildLoanRows(source, filterValue);
        const nextTotal = nextRows.values.reduce(function (sum, value) { return sum + toNumber(value); }, 0);
        const nextMax = Math.max.apply(null, nextRows.values.concat([0]));

        syncLoanPlotWidth(nextRows, source, chartWrap, chartPlot);
        chart.resize();
        chart.data.labels = nextRows.labels;
        chart.data.datasets[0].data = nextRows.values;
        chart.options.plugins.title.text = nextRows.title;
        chart.options.scales.y.suggestedMax = nextMax <= 0 ? 1 : undefined;
        chart.update();

        if (emptyState) {
            emptyState.classList.toggle('is-hidden', nextTotal > 0);
        }
        if (syncUrl) {
            syncLoanFilterUrl(filterValue, source);
        }
    }

    updateChart(initialValue, false);

    if (yearFilter) {
        yearFilter.addEventListener('change', function () {
            updateChart(yearFilter.value, true);
        });
    }
}
