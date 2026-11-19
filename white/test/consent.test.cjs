const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const script = fs.readFileSync(path.join(__dirname, '../src/assets/analytics.js'), 'utf8');

function setup(initial = {}) {
  const values = new Map(Object.entries(initial));
  const scripts = [], nodes = [], listeners = {};
  const storage = {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
  };
  function element(tag) {
    const children = {};
    return {
      tagName: tag.toUpperCase(), style: {}, setAttribute() {},
      querySelector(selector) { return children[selector] || (children[selector] = {}); },
      remove() { this.removed = true; },
    };
  }
  const document = {
    referrer: '',
    createElement: element,
    head: { appendChild(node) { if (node.tagName === 'SCRIPT') scripts.push(node); } },
    body: { appendChild(node) { nodes.push(node); } },
    querySelector() { return null; },
    addEventListener(name, cb) { listeners[name] = cb; },
  };
  const location = { hostname: 'smart-soultion.com', origin: 'https://smart-soultion.com', pathname: '/', reload() {} };
  const window = { addEventListener(name, cb) { listeners[name] = cb; } };
  vm.runInNewContext(script, { document, window, location, localStorage: storage, URL, Date });
  return { values, scripts, nodes, window, listeners };
}

test('one branded notice, no tracking before acceptance', () => {
  const state = setup();
  const panel = state.nodes.find(node => node.className === 'ss-consent');
  assert.ok(panel);
  assert.match(panel.innerHTML, /Яндекс Метрика и Google Analytics/);
  assert.match(panel.innerHTML, /class="yes"[^>]*>Принять/);
  assert.doesNotMatch(panel.innerHTML, /class="no"/);
  assert.equal(state.scripts.length, 1); // first-party privacy mask only
  state.scripts[0].onload();
  assert.equal(state.scripts.length, 1);
  panel.querySelector('.yes').onclick();
  assert.equal(state.values.get('ss-analytics-consent-v2'), 'yes');
  assert.equal(state.values.get('ss-google-analytics-consent-v1'), 'yes');
  assert.ok(state.scripts.some(node => node.src.includes('mc.yandex.ru')));
  assert.ok(state.scripts.some(node => node.src.includes('googletagmanager.com')));
});

test('previous Yandex consent never grants Google automatically', () => {
  const state = setup({ 'ss-analytics-consent-v2': 'yes' });
  assert.ok(state.nodes.find(node => node.className === 'ss-consent'));
  state.scripts[0].onload();
  assert.ok(state.scripts.some(node => node.src.includes('mc.yandex.ru')));
  assert.ok(!state.scripts.some(node => node.src.includes('googletagmanager.com')));
  assert.equal(state.values.has('ss-google-analytics-consent-v1'), false);
});

test('stored refusals stay respected without another notice', () => {
  const state = setup({ 'ss-analytics-consent-v2': 'no', 'ss-google-analytics-consent-v1': 'no' });
  assert.ok(!state.nodes.find(node => node.className === 'ss-consent'));
  state.scripts[0].onload();
  assert.equal(state.scripts.length, 1);
});

test('accepting before privacy mask is ready waits for it', () => {
  const state = setup();
  state.nodes.find(node => node.className === 'ss-consent').querySelector('.yes').onclick();
  assert.equal(state.scripts.length, 1);
  state.scripts[0].onload();
  assert.equal(state.scripts.length, 3);
});

test('already granted choices wait for privacy masking', () => {
  const state = setup({ 'ss-analytics-consent-v2': 'yes', 'ss-google-analytics-consent-v1': 'yes' });
  assert.ok(!state.nodes.find(node => node.className === 'ss-consent'));
  assert.equal(state.scripts.length, 1);
  state.scripts[0].onload();
  assert.equal(state.scripts.length, 3);
});
