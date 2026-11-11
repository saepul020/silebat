const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const context = vm.createContext({ document: { addEventListener() {} }, console });
for (const name of ['chart_summary', 'chart_data', 'dashboard', 'dashboard_display']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js', name + '.js'), 'utf8'), context);
}

test('Totals sum filtered values across visible datasets, including stacks and zero values', () => {
    const chart = {
        data: { datasets: [{ data: [2, 3, 0] }, { data: [4, 1, 0] }, { data: [100] }] },
        isDatasetVisible: index => index !== 2,
    };
    assert.equal(context.getChartTotal(chart), 10);
    chart.data.datasets[0].data = [2];
    chart.data.datasets[1].data = [4];
    assert.equal(context.getChartTotal(chart), 6);
    chart.data.datasets = [];
    assert.equal(context.getChartTotalText(chart), 'Total: 0');
});

test('Pie legend visibility excludes hidden slices and decimal totals use Indonesian formatting', () => {
    const chart = {
        data: { datasets: [{ data: [1000.25, 25, 0.5] }] },
        getDataVisibility: index => index !== 1,
    };
    assert.equal(context.getChartTotalText(chart), 'Total: 1.000,75');
    chart.getDataVisibility = () => false;
    assert.equal(context.getChartTotal(chart), 0);
});

test('Object points follow the numeric axis and invalid values do not corrupt the total', () => {
    const chart = { options: { indexAxis: 'y' }, data: { datasets: [{ data: [{ x: 2, y: 'Kategori' }, null, NaN, Infinity, '3.5'] }] } };
    assert.equal(context.getChartTotal(chart), 5.5);
    chart.options.indexAxis = 'x';
    chart.data.datasets[0].data = [{ x: 'Jan', y: 4 }];
    assert.equal(context.getChartTotal(chart), 4);
});

test('Bar datasets keep the baseline square, including condition stacks and TV charts', () => {
    const source = { categories: [{ id: 1, label: 'A' }], teams: [{ id: 1, label: 'Tim' }], rows: [] };
    const packs = [
        context.buildSingleSeriesChartData(source, 2026, 'layananId', 'Total'),
        context.buildMonthlyGroupedChartData(source, 2026, 'all_months', 'timId', 'teams', ''),
        context.buildMonthlySingleSeriesChartData(source, 2026, 'all_months'),
        context.buildBahanChartData({ items: [{ id: 1, stock: 3 }] }),
        context.buildPenunjangChartData({ items: [{ id: 1, baik: 3, rusak: 2 }] }),
        { datasets: [context.buildTvBarDataset('TV', [2], 'blue')] },
    ];
    for (const pack of packs) {
        for (const dataset of pack.datasets) {
            assert.equal(dataset.borderSkipped, 'start');
            assert.ok(dataset.borderRadius > 0);
        }
    }
});

test('Balai types distinguish abbreviations and full names without matching unrelated institutions', () => {
    for (const [label, type] of [
        [' BWS Bali ', 'BWS'], ['bbws Citarum', 'BBWS'],
        ['Balai Wilayah Sungai Papua', 'BWS'], ['Balai Besar Wilayah Sungai Solo', 'BBWS'],
        [['Balai Besar', 'Wilayah Sungai Solo'], 'BBWS'],
        ['BBWSX', ''], ['BWSX', ''], ['Direktorat SDA', ''], ['', ''],
    ]) {
        assert.equal(context.getBalaiType(label), type, String(label));
    }
});

test('Internal SDA nihil counts follow filtered year and all years while preserving zero categories', () => {
    const source = {
        key: 'instansi-internal',
        categories: [
            'BWS Bali', 'Balai Wilayah Sungai Papua', 'BBWS Citarum',
            'Balai Besar Wilayah Sungai Solo', 'Direktorat SDA', 'BWSX',
        ].map((label, id) => ({ id, label })),
        rows: [{ year: 2025, instansiId: 0, total: 2 }, { year: 2026, instansiId: 2, total: 3 }],
    };
    for (const id of ['grafik-instansi-internal', 'tv-instansi-internal']) {
        const chart = { canvas: { id }, isDatasetVisible: () => false };
        for (const [year, bws, bbws] of [[2026, 2, 1], [2025, 1, 2], ['all', 1, 1], [2024, 2, 2]]) {
            chart.data = context.buildSingleSeriesChartData(source, year, 'instansiId', 'Total');
            assert.deepEqual(Array.from(context.getChartNihilLines(chart)), [
                `BWS Nihil : ${bws} Instansi`, `BBWS Nihil : ${bbws} Instansi`,
            ]);
        }
    }
    assert.deepEqual(Array.from(context.getChartNihilLines({ canvas: { id: 'grafik-instansi-gabungan' }, data: source })), []);
    assert.deepEqual(Array.from(context.getChartNihilLines({ canvas: { id: 'grafik-instansi-internal' }, data: { labels: [], datasets: [] } })), [
        'BWS Nihil : 0 Instansi', 'BBWS Nihil : 0 Instansi',
    ]);
});
