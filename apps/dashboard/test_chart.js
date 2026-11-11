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

test('Chart labels share compact type and keep short month labels horizontal', () => {
    const context = chartContext();
    const labels = ['BBWS Citarum', 'Balai Besar Wilayah Sungai Bengawan Solo'];
    for (const width of [390, 960, 1280, 1920, 3840]) {
        const profile = context.getTvTickProfile(labels, width);
        assert.ok(profile.rotation === 0 || profile.rotation >= 45);
        assert.ok(profile.fontSize >= 5 && profile.fontSize <= 8);
    }
    const months = context.buildTvMonthKeys(2026).map(context.formatTvMonth);
    assert.equal(context.getTvTickProfile(months, 960).rotation, 0);
    assert.equal(context.getTvTickProfile(months, 960).fontSize, 8);
    assert.equal(context.getTvTickProfile([], 960).rotation, 0);
});

test('Dense institution charts reserve space for both label lines', () => {
    const context = chartContext();
    for (const width of [390, 640, 960, 1280, 1920, 3840]) {
        const labels = Array(55).fill('Balai Besar Wilayah Sungai Bengawan Solo');
        const profile = context.getTvTickProfile(labels, width);
        const slot = (width - 48) / labels.length;
        assert.ok(slot * Math.sin(profile.rotation * Math.PI / 180) + 0.01 >= profile.fontSize * 2.4 + 2);
        assert.ok(profile.labels.every(label => [].concat(label).length <= 2));
    }
});

test('The shared axis plugin recalculates after resizing or changing labels', () => {
    const context = chartContext();
    const plugin = vm.runInContext('tvLabelPlugin', context);
    const chart = {
        width: 1920,
        data: { labels: Array(12).fill('Balai Besar Wilayah Sungai') },
        options: context.createTvBaseOptions(1),
        ctx: { save() {}, restore() {}, measureText(label) { return { width: label.length * 4.8 }; } },
    };
    plugin.beforeLayout(chart);
    const wide = chart.options.scales.x.ticks.callback.call({ getLabelForValue: () => chart.data.labels[0] }, 0);
    chart.width = 390;
    plugin.beforeLayout(chart);
    const ticks = chart.options.scales.x.ticks;
    assert.ok(ticks.minRotation >= 45);
    assert.equal(ticks.maxRotation, ticks.minRotation);
    assert.equal(ticks.autoSkip, false);
    assert.ok(ticks.font.size <= 8);
    const narrow = ticks.callback.call({ getLabelForValue: () => chart.data.labels[0] }, 0);
    assert.ok(Array.isArray(narrow) && narrow.length === 2);
    assert.notDeepEqual(narrow, wide);
    assert.equal(chart.data.labels[0], 'Balai Besar Wilayah Sungai');
    chart.data.labels = ['Jan', 'Feb'];
    plugin.beforeLayout(chart);
    assert.equal(ticks.maxRotation, 0);
    assert.equal(ticks.font.size, 8);
    assert.equal(ticks.callback.call({ getLabelForValue: () => 'Jan' }, 0), 'Jan');
});

test('TV wrapping uses rendered widths and adds ellipsis only for overflowing second lines', () => {
    const context = chartContext();
    const measure = text => Array.from(text).reduce((sum, char) => sum + (char === 'W' ? 10 : 4), 0);
    assert.equal(context.wrapTvLabel('Jan', 40, measure), 'Jan');
    assert.deepEqual(Array.from(context.wrapTvLabel('BBWS Citarum', 30, measure)), ['BBWS', 'Citarum']);
    const label = 'Balai Besar Wilayah Sungai Bengawan Solo dengan nama instansi sangat panjang';
    const lines = Array.from(context.wrapTvLabel(label, 60, measure));
    assert.equal(lines.length, 2);
    assert.equal(lines[0], 'Balai Besar');
    assert.ok(lines[1].endsWith('\u2026'));
    assert.ok(lines.every(line => measure(line) <= 60));
    assert.ok(label.startsWith(lines[0]));
});

test('Long words, whitespace and Unicode stay within two measured lines', () => {
    const context = chartContext();
    const measure = text => Array.from(text).length * 5;
    for (const label of ['PengukuranElektromagnetikTanpaSpasi', 'WWWWiiiiWWWWiiiiWWWW', '\u{1F30A}'.repeat(30)]) {
        const lines = Array.from(context.wrapTvLabel(label, 30, measure));
        assert.equal(lines.length, 2);
        assert.ok(lines[1].endsWith('\u2026'));
        assert.ok(lines.every(line => measure(line) <= 30));
        assert.ok(lines.every(line => !/[\uD800-\uDBFF]$/.test(line)));
    }
    assert.equal(context.wrapTvLabel('  Internal   SDA  ', 100, measure), 'Internal SDA');
    assert.equal(context.wrapTvLabel('', 100, measure), '');
});

test('360p chart type and label width shrink together while preserving two-line wrapping', () => {
    const context = chartContext();
    const labels = Array(55).fill('Balai Besar Wilayah Sungai Bengawan Solo dengan nama sangat panjang');
    const baseline = context.getTvTickProfile(labels, 640, undefined, 180);
    const compact = context.getTvTickProfile(labels, 640, undefined, 180, Math.sqrt(0.5));
    assert.ok(compact.fontSize < baseline.fontSize);
    assert.ok(compact.lineWidth < baseline.lineWidth);
    assert.ok(compact.labels.every(label => Array.isArray(label) && label.length === 2 && label[1].endsWith('\u2026')));
});

test('Canvas axes and legend follow the shared page type scale after resizing', () => {
    const context = chartContext();
    const plugin = vm.runInContext('tvLabelPlugin', context);
    let pageSize = 4;
    context.getComputedStyle = () => ({ fontSize: String(pageSize) });
    const chart = {
        width: 640, height: 180,
        canvas: { closest() { return {}; } },
        data: { labels: ['Jan', 'Feb'] },
        options: context.createTvBaseOptions(1),
        ctx: { save() {}, restore() {}, measureText(label) { return { width: label.length * 4.8 }; } },
    };
    plugin.beforeLayout(chart);
    const small = chart.options.scales.x.ticks.font.size;
    assert.ok(small < 8);
    assert.ok(chart.options.scales.y.ticks.font.size < 7);
    assert.equal(chart.options.plugins.legend.labels.font.size, chart.options.scales.y.ticks.font.size);
    pageSize = 12;
    chart.width = 1920;
    chart.height = 500;
    plugin.beforeLayout(chart);
    assert.ok(chart.options.scales.x.ticks.font.size > small);
    assert.ok(chart.options.plugins.legend.labels.font.size > 7);
});
