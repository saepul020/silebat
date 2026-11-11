const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const context = vm.createContext({
    document: {
        documentElement: { classList: { contains() { return false; } } },
        querySelector() { return null; },
    },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/js/tv_layout.js'), 'utf8'), context);
const size = (viewport, fallback) => JSON.parse(JSON.stringify(context.getTvViewport(viewport, fallback)));

test('Visual viewport dimensions and offsets determine the visible frame', () => {
    assert.deepEqual(size({ width: 872, height: 491, offsetLeft: 44, offsetTop: 24 }, {
        innerWidth: 960, innerHeight: 540,
    }), { width: 872, height: 491, left: 44, top: 24 });
});

test('Browsers without VisualViewport use inner dimensions', () => {
    assert.deepEqual(size(undefined, { innerWidth: 1280, innerHeight: 720 }), {
        width: 1280, height: 720, left: 0, top: 0,
    });
});

test('Invalid metrics cannot create an empty or invalid frame', () => {
    assert.deepEqual(size({ width: 0, height: Infinity, offsetLeft: NaN, offsetTop: -10 }, {
        innerWidth: 960, innerHeight: 540,
    }), { width: 960, height: 540, left: 0, top: 0 });
    assert.deepEqual(size(null, {}), { width: 1, height: 1, left: 0, top: 0 });
});

test('Physical pixel density does not change CSS viewport dimensions', () => {
    const fallback = { innerWidth: 960, innerHeight: 540 };
    assert.deepEqual(size(null, { ...fallback, devicePixelRatio: 4 }), size(null, {
        ...fallback, devicePixelRatio: 1,
    }));
});

test('Pages without the display do not install layout listeners', () => {
    assert.equal(context.initTvLayout(), null);
});
