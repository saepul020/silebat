const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const context = vm.createContext({ document: { addEventListener() {} } });
for (const name of ['chart_data', 'chart_summary', 'dashboard']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js', name + '.js'), 'utf8'), context);
}

test('Export copies preserve callbacks and isolate nested changes from the live chart', () => {
    const callback = value => 'Value: ' + value;
    const original = {
        data: { labels: ['A'], datasets: [{ data: [4], hidden: false }] },
        options: { scales: { x: { ticks: { callback, font: { size: 8 } } } } },
    };
    const copy = context.copyChartExport(original);
    copy.data.labels.push('B');
    copy.data.datasets[0].data[0] = 99;
    copy.data.datasets[0].hidden = true;
    copy.options.scales.x.ticks.font.size = 14;
    assert.deepEqual(original.data.labels, ['A']);
    assert.deepEqual(original.data.datasets[0], { data: [4], hidden: false });
    assert.equal(original.options.scales.x.ticks.font.size, 8);
    assert.equal(copy.options.scales.x.ticks.callback, callback);
});

test('Export wrapping preserves complete long titles within the measured line width', () => {
    const drawing = { measureText(text) { return { width: text.length * 10 }; } };
    for (const title of [
        'Instansi Tujuan Kegiatan - Gabungan Eksternal SDA, Internal BAT, dan Lainnya',
        'JudulPanjangTanpaSpasiYangHarusTetapUtuh',
    ]) {
        const lines = Array.from(context.wrapExportText(drawing, title, 200));
        assert.ok(lines.length > 1);
        assert.ok(lines.every(line => drawing.measureText(line).width <= 200));
        assert.equal(lines.join('').replace(/\s/g, ''), title.replace(/\s/g, ''));
    }
});

test('JPG output gives totals a background and centers separate nihil badges below the plot', () => {
    const calls = [];
    const boxes = [];
    let plot;
    const drawing = {
        measureText(text) { return { width: text.length * 8 }; },
        fillText(text, x, y) { calls.push({ text, x, y }); },
        createLinearGradient() { return { addColorStop() {} }; },
    };
    for (const name of ['scale', 'beginPath', 'roundRect', 'rect', 'fill', 'stroke', 'fillRect']) {
        drawing[name] = () => {};
    }
    drawing.roundRect = (x, y, w, h) => boxes.push({ x, y, w, h });
    const chart = {
        data: { labels: ['A', 'B'], datasets: [{ data: [2, 3] }, { data: [100, 200] }] },
        isDatasetVisible: index => index === 0,
    };
    const source = { closest() { return {
        querySelectorAll() { return [{ id: 'tahun', selectedOptions: [{ textContent: '2026' }] }]; },
        querySelector() { return null; },
    }; } };
    context.document.createElement = () => ({ getContext() { return drawing; } });
    context.Chart = { getChart() { return chart; } };
    context.renderChartExport = (_chart, _ctx, x, y, w, h) => { plot = { x, y, w, h }; };
    context.buildDashboardChartExportCanvas(source, 'Grafik Pengujian');
    const total = calls.find(call => call.text === 'Total: 5');
    const filter = calls.find(call => call.text === 'Tahun: 2026');
    assert.ok(total && filter);
    assert.equal(total.y, filter.y);
    assert.ok(total.x > filter.x);
    assert.ok(boxes.some(b => total.x > b.x && total.x < b.x + b.w && total.y > b.y && total.y < b.y + b.h && b.h === 34));
    assert.equal(chart.data.datasets[1].data[0], 100);

    // Internal SDA reserves two distinct footer badges outside the plot, below its labels.
    calls.length = 0;
    boxes.length = 0;
    chart.canvas = { id: 'grafik-instansi-internal' };
    chart.data = { labels: ['BWS Bali', 'BBWS Citarum', 'Balai Besar Wilayah Sungai Solo'], datasets: [{ data: [0, 3, 0] }] };
    context.buildDashboardChartExportCanvas(source, 'Instansi Tujuan Kegiatan - Internal SDA');
    const summary = ['Total: 3', 'BWS Nihil : 1 Instansi', 'BBWS Nihil : 1 Instansi'].map(text => calls.find(call => call.text === text));
    assert.ok(summary.every(Boolean));
    assert.equal(summary[0].y, calls.find(call => call.text === 'Tahun: 2026').y);
    const badges = boxes.filter(b => b.h === 36);
    assert.equal(badges.length, 2);
    assert.ok(summary[1].y > plot.y + plot.h);
    assert.equal(summary[1].y, summary[2].y);
    assert.ok(summary[2].x > summary[1].x);
    assert.equal((badges[0].x + badges[1].x + badges[1].w) / 2, 800);
    badges.forEach((b, i) => {
        assert.equal(summary[i + 1].x, b.x + b.w / 2);
        assert.ok(summary[i + 1].y > b.y && summary[i + 1].y < b.y + b.h);
    });
});
