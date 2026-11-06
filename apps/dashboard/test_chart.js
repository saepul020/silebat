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
    return context.buildSingleSeriesChartData(source, year, 'instansiId', 'Total');
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
            const tv = context.createTvCategoryChart('canvas', 'script', 'instansiId', 'Total');
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
    const result = context.buildSingleSeriesChartData(source, 2026, 'layananId', 'Total');
    assert.deepEqual(Array.from(result.labels), source.categories.map(category => category.label));
});

test('Long axis labels use smaller type and 22.5 degrees in every viewport', () => {
    const context = chartContext();
    const labels = ['BBWS Citarum', 'Balai Besar Wilayah Sungai Bengawan Solo'];
    for (const width of [390, 960, 1280, 1920, 3840]) {
        const profile = context.getTvTickProfile(labels, width);
        assert.equal(profile.rotation, 22.5);
        assert.ok(profile.fontSize >= 6 && profile.fontSize < 9);
    }
    const months = context.buildTvMonthKeys(2026).map(context.formatTvMonth);
    assert.equal(context.getTvTickProfile(months, 960).rotation, 0);
    assert.equal(context.getTvTickProfile(months, 960).fontSize, 9);
    assert.equal(context.getTvTickProfile([], 960).rotation, 0);
});

test('Wrapping preserves full names and long words instead of truncating them', () => {
    const context = chartContext();
    for (const label of [
        'Balai Besar Wilayah Sungai Bengawan Solo',
        'PengukuranElektromagnetikTanpaSpasi', '  Internal   SDA  ',
    ]) {
        const result = context.wrapTvLabel(label, 10);
        const lines = Array.isArray(result) ? Array.from(result) : [result];
        assert.equal(lines.join('').replace(/\s/g, ''), label.replace(/\s/g, ''));
        assert.ok(lines.every(line => line.length <= 10));
    }
    assert.equal(context.wrapTvLabel('', 10), '');
});

test('The shared axis plugin recalculates after resizing or changing labels', () => {
    const context = chartContext();
    const plugin = vm.runInContext('tvLabelPlugin', context);
    const chart = {
        width: 1920,
        data: { labels: Array(12).fill('Balai Besar Wilayah Sungai') },
        options: context.createTvBaseOptions(1),
    };
    plugin.beforeLayout(chart);
    const wideWrap = [].concat(chart.options.scales.x.ticks.callback.call({ getLabelForValue: () => chart.data.labels[0] }, 0));
    chart.width = 390;
    plugin.beforeLayout(chart);
    const ticks = chart.options.scales.x.ticks;
    assert.equal(ticks.minRotation, 22.5);
    assert.equal(ticks.maxRotation, 22.5);
    assert.equal(ticks.autoSkip, false);
    assert.ok(ticks.font.size < 8);
    assert.ok(ticks.callback.call({ getLabelForValue: () => chart.data.labels[0] }, 0).length > wideWrap.length);
    chart.data.labels = ['Jan', 'Feb'];
    plugin.beforeLayout(chart);
    assert.equal(ticks.maxRotation, 0);
    assert.equal(ticks.font.size, 9);
});
