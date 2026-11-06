const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const context = vm.createContext({ document: { addEventListener() {} } });
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js/dashboard.js'), 'utf8'), context);

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
