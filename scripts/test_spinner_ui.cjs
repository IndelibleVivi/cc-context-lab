'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..');
const SCRIPT = fs.readFileSync(path.join(ROOT, 'extras/spinner/spinner.js'), 'utf8');
const WORDS = JSON.parse(fs.readFileSync(path.join(ROOT, 'extras/spinner/verbs.json'), 'utf8'));

class ClassList {
  constructor() { this.values = new Set(); }
  add(value) { this.values.add(value); }
  contains(value) { return this.values.has(value); }
}

class Element {
  constructor(tag = 'div', attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = { ...attrs };
    this.listeners = {};
    this.children = [];
    this.parentNode = null;
    this.classList = new ClassList();
    this.hidden = false;
    this.href = '';
    this.download = '';
    this._text = '';
  }
  getAttribute(name) { return Object.hasOwn(this.attrs, name) ? this.attrs[name] : null; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  addEventListener(type, listener) {
    (this.listeners[type] ||= []).push(listener);
  }
  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }
  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index >= 0) this.children.splice(index, 1);
    child.parentNode = null;
  }
  click() { this.clicked = (this.clicked || 0) + 1; }
  get textContent() { return this._text; }
  set textContent(value) { this._text = String(value); }
  querySelector(selector) {
    const attr = selector.slice(1, -1);
    return this.children.find((child) => Object.hasOwn(child.attrs, attr)) || null;
  }
}

function uiRoot(attrs = {}, children = []) {
  const root = new Element('div', { 'data-cc-spinner': '', ...attrs });
  children.forEach((child) => root.appendChild(child));
  return root;
}

function mountedHarness({ words = WORDS, roots = null, readyState = 'complete' } = {}) {
  const documentListeners = {};
  const body = new Element('body');
  const data = new Element('script', { id: 'cc-spinner-data' });
  data.textContent = JSON.stringify(words);
  const activeRoots = roots || [
    uiRoot({}, [
      new Element('span', { 'data-spinner-glyph': '' }),
      new Element('span', { 'data-spinner-word': '' }),
      new Element('button', { 'data-spinner-next': '' }),
      new Element('button', {
        'data-spinner-pause': '',
        'data-label-pause': 'Pause animation',
        'data-label-resume': 'Resume animation',
      }),
      new Element('button', { 'data-spinner-download': '' }),
    ]),
    uiRoot({}, [
      new Element('span', { 'data-spinner-glyph': '' }),
      new Element('span', { 'data-spinner-word': '' }),
      new Element('button', { 'data-spinner-next': '' }),
      new Element('button', {
        'data-spinner-pause': '',
        'data-label-pause': 'Pause animation',
        'data-label-resume': 'Resume animation',
      }),
    ]),
  ];
  activeRoots.forEach((root) => body.appendChild(root));
  const created = [];
  const blobs = [];
  const urls = [];
  const document = {
    readyState,
    body,
    addEventListener(type, listener) {
      (documentListeners[type] ||= []).push(listener);
    },
    getElementById(id) { return id === 'cc-spinner-data' ? data : null; },
    querySelectorAll(selector) {
      assert.equal(selector, '[data-cc-spinner]');
      return activeRoots;
    },
    createElement(tag) {
      const node = new Element(tag);
      created.push(node);
      return node;
    },
  };
  let randomIndex = 0;
  const randomValues = [0, 0.9999, 0.5];
  const sequence = function () {
    return randomValues[Math.min(randomIndex++, randomValues.length - 1)];
  };
  let timers = 0;
  const context = {
    document,
    Math: Object.assign(Object.create(Math), { random: sequence }),
    Blob: class {
      constructor(parts, options) {
        this.parts = parts;
        this.options = options;
        blobs.push(this);
      }
    },
    URL: {
      createObjectURL(blob) {
        urls.push({ blob, url: 'blob:test-' + urls.length });
        return urls.at(-1).url;
      },
      revokeObjectURL(url) { urls.push({ revoked: url }); },
    },
    setTimeout(callback) { timers += 1; callback(); },
  };
  context.globalThis = context;
  vm.runInNewContext(SCRIPT, context, { filename: 'spinner.js' });
  return {
    context, roots: activeRoots, documentListeners, created, blobs, urls,
    calls: () => randomIndex, timers: () => timers,
  };
}

function part(root, name) {
  return root.querySelector(`[${name}]`);
}

test('mount draws once per root, stays stable, and isolates explicit rerolls', () => {
  const h = mountedHarness();
  const [a, b] = h.roots;
  assert.equal(part(a, 'data-spinner-glyph').classList.contains('cc-spinner-glyph'), true);
  assert.equal(part(a, 'data-spinner-glyph').getAttribute('aria-hidden'), 'true');
  assert.equal(part(a, 'data-spinner-word').textContent, WORDS[0]);
  assert.equal(part(b, 'data-spinner-word').textContent, WORDS.at(-1));
  assert.equal(h.calls(), 2);
  assert.equal(h.timers(), 0);

  part(a, 'data-spinner-next').listeners.click[0]();
  assert.equal(part(a, 'data-spinner-word').textContent, WORDS[Math.floor(WORDS.length * 0.5)]);
  assert.equal(part(b, 'data-spinner-word').textContent, WORDS.at(-1));
});

test('pause is root-scoped and exposes its pressed state without changing the word', () => {
  const h = mountedHarness();
  const [a, b] = h.roots;
  const aPause = part(a, 'data-spinner-pause');
  const bPause = part(b, 'data-spinner-pause');
  const aWord = part(a, 'data-spinner-word').textContent;
  const bWord = part(b, 'data-spinner-word').textContent;
  aPause.listeners.click[0]();
  assert.equal(a.getAttribute('data-paused'), 'true');
  assert.equal(aPause.getAttribute('aria-pressed'), 'true');
  assert.equal(aPause.textContent, 'Resume animation');
  assert.equal(part(a, 'data-spinner-word').textContent, aWord);
  assert.equal(b.getAttribute('data-paused'), 'false');
  assert.equal(bPause.getAttribute('aria-pressed'), 'false');
  assert.equal(part(b, 'data-spinner-word').textContent, bWord);
  aPause.listeners.click[0]();
  assert.equal(a.getAttribute('data-paused'), 'false');
  assert.equal(aPause.getAttribute('aria-pressed'), 'false');
  assert.equal(aPause.textContent, 'Pause animation');
});

test('omitting pause labels leaves a compact pause control usable and untouched', () => {
  const pause = new Element('button', { 'data-spinner-pause': '' });
  pause.textContent = '||';
  const root = uiRoot({}, [
    new Element('span', { 'data-spinner-word': '' }),
    pause,
  ]);
  mountedHarness({ roots: [root] });
  pause.listeners.click[0]();
  assert.equal(root.getAttribute('data-paused'), 'true');
  assert.equal(pause.getAttribute('aria-pressed'), 'true');
  assert.equal(pause.textContent, '||');
});

test('download uses the embedded words and exactly 187 line-separated entries', () => {
  const h = mountedHarness();
  part(h.roots[0], 'data-spinner-download').listeners.click[0]();
  assert.equal(h.blobs.length, 1);
  assert.equal(h.blobs[0].options.type, 'text/plain;charset=utf-8');
  assert.equal(h.blobs[0].parts[0], WORDS.join('\n') + '\n');
  assert.equal(h.blobs[0].parts[0].split('\n').length - 1, 187);
  assert.equal(h.created.length, 1);
  assert.equal(h.created[0].tagName, 'A');
  assert.equal(h.created[0].download, 'claude-code-spinner-verbs-2.1.322.txt');
  assert.equal(h.created[0].clicked, 1);
  assert.equal(h.created[0].parentNode, null);
  assert.deepEqual(h.urls[0], { blob: h.blobs[0], url: 'blob:test-0' });
  assert.deepEqual(h.urls[1], { revoked: 'blob:test-0' });
});

test('compact roots tolerate every optional control missing', () => {
  const compact = uiRoot({}, [
    new Element('span', { 'data-spinner-glyph': '' }),
    new Element('span', { 'data-spinner-word': '' }),
  ]);
  const h = mountedHarness({ roots: [compact] });
  assert.equal(part(compact, 'data-spinner-word').textContent, WORDS[0]);
  assert.equal(compact.getAttribute('data-paused'), 'false');
  assert.equal(h.timers(), 0);
});

test('mount helper is idempotent and preserves global Math.random', () => {
  const root = uiRoot({}, [
    new Element('span', { 'data-spinner-glyph': '' }),
    new Element('span', { 'data-spinner-word': '' }),
    new Element('button', { 'data-spinner-next': '' }),
  ]);
  const h = mountedHarness({ roots: [root] });
  const random = h.context.Math.random;
  h.context.CCSpinner.mount(root);
  assert.equal(h.context.Math.random, random);
  assert.equal(part(root, 'data-spinner-next').listeners.click.length, 1);
  assert.equal(h.calls(), 1);
});

test('malformed JSON falls back to a visible glyph instead of throwing', () => {
  const root = uiRoot({}, [
    new Element('span', { 'data-spinner-glyph': '' }),
    new Element('span', { 'data-spinner-word': '' }),
  ]);
  const h = mountedHarness({ words: '</script><script>', roots: [root] });
  assert.equal(part(root, 'data-spinner-word').textContent, '✻');
  assert.equal(h.calls(), 0);
});

test('deferred script waits for DOMContentLoaded before mounting', () => {
  const root = uiRoot({}, [new Element('span', { 'data-spinner-word': '' })]);
  const h = mountedHarness({ roots: [root], readyState: 'loading' });
  assert.equal(part(root, 'data-spinner-word').textContent, '');
  assert.equal(h.documentListeners.DOMContentLoaded.length, 1);
  h.documentListeners.DOMContentLoaded[0]();
  assert.equal(part(root, 'data-spinner-word').textContent, WORDS[0]);
});
