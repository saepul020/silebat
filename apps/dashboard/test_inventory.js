const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const context = vm.createContext({
    document: { addEventListener() {} },
    window: { matchMedia() { return { matches: false }; } },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js/dashboard.js'), 'utf8'), context);
const plain = value => JSON.parse(JSON.stringify(value));
const source = {
    backgroundColor: '#103e6f',
    items: [
        { id: 1, label: 'Nama Sama', stock: 4, baik: 4, rusak: 2, unit: 'Botol' },
        { id: 2, label: 'Nilai Besar', stock: 100, baik: 100, rusak: 40, unit: 'Liter' },
        { id: 3, label: 'Nama Sama', stock: 0, baik: 0, rusak: 0, unit: 'Unit' },
    ],
};

test('Bahan selection uses IDs and keeps labels, units, stock and scale aligned', () => {
    const data = plain(context.buildBahanChartData(source, new Set(['3', '1'])));
    assert.deepEqual(data.labels, ['Nama Sama', 'Nama Sama']);
    assert.deepEqual(data.units, ['Botol', 'Unit']);
    assert.deepEqual(data.datasets[0].data, [4, 0]);
    assert.equal(data.maxValue, 4);
    assert.equal(data.datasets[0].backgroundColor, source.backgroundColor);
});

test('Penunjang selection keeps both condition stacks and their combined maximum', () => {
    const data = plain(context.buildPenunjangChartData(source, new Set(['1'])));
    assert.deepEqual(data.labels, ['Nama Sama']);
    assert.deepEqual(data.units, ['Botol']);
    assert.deepEqual(data.datasets.map(d => d.data), [[2], [4]]);
    assert.equal(data.maxValue, 6);
    assert.ok(data.datasets.every(d => d.stack === 'condition'));
});

test('Clearing selection empties both charts, while selected zero stock remains data', () => {
    for (const build of [context.buildBahanChartData, context.buildPenunjangChartData]) {
        const empty = plain(build(source, new Set()));
        assert.deepEqual(empty.labels, []);
        assert.ok(empty.datasets.every(d => d.data.length === 0));
        assert.equal(empty.hasData, false);
        assert.equal(empty.maxValue, 0);
        const zero = plain(build(source, new Set(['3'])));
        assert.equal(zero.hasData, true);
        assert.equal(zero.labels.length, 1);
    }
});

test('Repeated filtering never changes the source and no filter keeps all items', () => {
    const original = JSON.stringify(source);
    for (const build of [context.buildBahanChartData, context.buildPenunjangChartData]) {
        build(source, new Set(['1']));
        build(source, new Set(['missing']));
        assert.equal(build(source).labels.length, 3);
        assert.equal(build(source, new Set(['missing'])).hasData, false);
        assert.equal(build({ items: [] }).hasData, false);
    }
    assert.deepEqual(plain(context.getInventoryItems(null)), []);
    assert.equal(JSON.stringify(source), original);
});
