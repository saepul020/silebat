const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function chartContext() {
    const context = vm.createContext({
        document: { addEventListener() {}, getElementById() { return {}; } },
        window: { innerWidth: 1920, innerHeight: 1080, matchMedia() { return { matches: false }; } },
        console,
    });
    for (const file of ['chart_data', 'dashboard', 'dashboard_display']) {
        vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js', file + '.js'), 'utf8'), context);
    }
    return context;
}

function chartSource(key) {
    return {
        key,
        defaultYear: 2026,
        categories: [
            ['other', 'Direktorat SDA'], ['bbws', 'BBWS Citarum'], ['bws', 'BWS Bali'],
            ['long', 'Balai Besar Wilayah Sungai Solo'], ['zero', 'Unit Tanpa Transaksi'],
            ['lainnya', 'Instansi Tujuan Lainnya'],
        ].map(([id, label], index) => ({ id, label, backgroundColor: 'color-' + index })),
        rows: [
            ['other', 2026, 20], ['bbws', 2026, 2], ['bws', 2026, 5], ['long', 2026, 1],
            ['lainnya', 2026, 8], ['other', 2025, 1], ['bbws', 2025, 10],
        ].map(([instansiId, year, total]) => ({ instansiId, year, total })),
    };
}

function dashboardData(context, source, year) {
    return context.buildSingleSeriesChartData(source, year, 'instansiId', 'Total', 'scrollable');
}

test('Internal SDA prioritizes BBWS/BWS, then sorts each group by the selected year', () => {
    const context = chartContext();
    const source = chartSource('instansi-internal');
    assert.deepEqual(Array.from(dashboardData(context, source, 2026).labels), [
        'BWS Bali', 'BBWS Citarum', 'Balai Besar Wilayah Sungai Solo',
        'Direktorat SDA', 'Instansi Tujuan Lainnya', 'Unit Tanpa Transaksi',
    ]);
    assert.equal(dashboardData(context, source, 2025).labels[0], 'BBWS Citarum');
    assert.equal(dashboardData(context, source, 'all').labels[0], 'BBWS Citarum');
});

test('Gabungan sorts all categories including manual entries by the selected totals', () => {
    const context = chartContext();
    const source = chartSource('instansi-gabungan');
    assert.deepEqual(Array.from(dashboardData(context, source, 2026).labels), [
        'Direktorat SDA', 'Instansi Tujuan Lainnya', 'BWS Bali', 'BBWS Citarum',
        'Balai Besar Wilayah Sungai Solo', 'Unit Tanpa Transaksi',
    ]);
    assert.equal(dashboardData(context, source, 2025).labels[0], 'BBWS Citarum');
    assert.equal(dashboardData(context, source, 'all').labels[0], 'Direktorat SDA');
});

test('TV and dashboard keep labels, totals, and colors aligned for the same year', () => {
    const context = chartContext();
    for (const key of ['instansi-internal', 'instansi-gabungan']) {
        const source = chartSource(key);
        const original = JSON.stringify(source);
        context.readTvData = () => source;
        context.createTvChart = (_id, labels, datasets) => ({ labels, datasets });
        for (const year of [2026, 2025]) {
            source.defaultYear = year;
            const dashboard = dashboardData(context, source, year);
            const tv = context.createTvCategoryChart('canvas', 'script', 'instansiId', 'Total', 10, 50);
            assert.deepEqual(Array.from(tv.labels), Array.from(dashboard.labels));
            assert.deepEqual(Array.from(tv.datasets[0].data), Array.from(dashboard.datasets[0].data));
            assert.deepEqual(Array.from(tv.datasets[0].backgroundColor), Array.from(dashboard.datasets[0].backgroundColor));
            dashboard.labels.forEach((label, index) => {
                assert.equal(dashboard.datasets[0].backgroundColor[index], source.categories.find(c => c.label === label).backgroundColor);
            });
        }
        source.defaultYear = 2026;
        assert.equal(JSON.stringify(source), original);
    }
});

test('Ties and zero totals have deterministic ordering without dropping categories', () => {
    const context = chartContext();
    const source = chartSource('instansi-internal');
    source.rows = [];
    const result = dashboardData(context, source, 2026);
    assert.equal(result.labels.length, source.categories.length);
    assert.ok(Array.from(result.datasets[0].data).every(value => value === 0));
    assert.deepEqual(Array.from(result.labels).slice(0, 3), [
        'Balai Besar Wilayah Sungai Solo', 'BBWS Citarum', 'BWS Bali',
    ]);
    assert.deepEqual(Array.from(context.sortInstansiCategories(
        [{ id: 1, label: 'Unit Z' }, { id: 2, label: 'Unit A' }],
        new Map([[1, 2], [2, 2]]), 'instansi-gabungan',
    )).map(category => category.label), ['Unit A', 'Unit Z']);
});

test('Balai matching accepts full names and ignores unrelated name fragments', () => {
    const context = chartContext();
    const categories = [
        { id: 1, label: 'BBWSX' }, { id: 2, label: ' bws Bali ' },
        { id: 3, label: 'Balai Wilayah Sungai Papua' },
    ];
    assert.deepEqual(Array.from(context.sortInstansiCategories(
        categories, new Map([[1, 100], [2, 1], [3, 2]]), 'instansi-internal',
    )).map(category => category.id), [3, 2, 1]);
});

test('Empty data is safe and non-institution charts retain their category order', () => {
    const context = chartContext();
    assert.deepEqual(Array.from(dashboardData(context, { categories: [], rows: [] }, 2026).labels), []);
    const source = chartSource('instansi-internal');
    const result = context.buildSingleSeriesChartData(source, 2026, 'layananId', 'Total', 'scrollable');
    assert.deepEqual(Array.from(result.labels), source.categories.map(category => category.label));
});
