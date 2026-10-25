// State-boundary regressions for the real study.js functions. DOM layout,
// canonical projection semantics and browser interaction have separate owners.
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'workbench/study.js'), 'utf8');
const fixtureSource = fs.readFileSync(path.join(root,
  'experiments/companion-input/fixtures/common_scenario.json'), 'utf8');
const plain = value => JSON.parse(JSON.stringify(value));

function harness() {
  const fixture = JSON.parse(fixtureSource);
  const scenario = {
    id: fixture.scenario_id, fixture,
    policies: fixture.policies, placements: fixture.placements,
    observations: {P1_fixed_interval: {PL_main_defer: {
      same: {sources: [], opportunities: []},
      fresh: {sources: [], opportunities: []},
    }}},
  };
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      value: '', checked: false, disabled: false, textContent: '', attributes: {},
      setAttribute(key, value) { this.attributes[key] = value; },
    });
    return nodes.get(id);
  }
  const tabs = [];
  const context = vm.createContext({
    $: node,
    scenarios: () => [scenario],
    findById: (items, id) => items.find(item => item.id === id) || null,
    isObj: value => Boolean(value) && typeof value === 'object' && !Array.isArray(value),
    changeState: {caps: {}, intent: null},
    activateTab: (...args) => tabs.push(args),
  });
  vm.runInContext(source, context, {filename: 'workbench/study.js'});
  // Do not simulate the DOM renderer: these checks own import/export state,
  // and assert that invalid input never reaches the render boundary.
  let renderCount = 0;
  context.renderStudy = () => { renderCount += 1; };
  const plan = {
    schema: 'cc-context-study/1',
    title: '自定义研究：旧天气与新回忆',
    question: '旧天气退出 current 后，history 是否仍有它？',
    preserve: ['保留原话、附件与 reply target', '纠正不复活；内部结果不算外部交付'],
    fixture: plain(fixture),
    baseline: {policy_id: 'P1_fixed_interval', placement_id: 'PL_main_defer', history_mode: 'same'},
    candidate: {policy_id: 'P1_fixed_interval', placement_id: 'PL_main_defer', history_mode: 'fresh'},
  };
  context.restoreStudy(plan);

  function snapshot() {
    return {
      state: plain(context.studyState),
      fields: Object.fromEntries([...nodes].map(([id, field]) => [id, plain(field)])),
      attachment: plain(context.studyAttachment),
      renderCount,
    };
  }
  return {context, node, plan, scenario, snapshot, tabs};
}

test('invalid imports leave the active study and form untouched', async t => {
  const cases = [
    ['prototype history', plan => { plan.baseline.history_mode = '__proto__'; }],
    ['array policy', plan => { plan.baseline.policy_id = ['P1_fixed_interval']; }],
    ['unknown candidate placement', plan => { plan.candidate.placement_id = 'missing-placement'; }],
    ['different fixture snapshot', plan => { plan.fixture.title = 'a different source snapshot'; }],
  ];
  for (const [label, corrupt] of cases) await t.test(label, () => {
    const h = harness();
    h.context.studyState.sourceId = 'amb_weather_1';
    h.context.studyState.query = 'weather';
    h.context.studyState.changedOnly = true;
    h.node('study-source-search').value = 'weather';
    h.node('study-changed-only').checked = true;
    const before = h.snapshot();
    const invalid = plain(h.plan);
    corrupt(invalid);
    assert.throws(() => h.context.restoreStudy(invalid));
    assert.deepEqual(h.snapshot(), before);
  });
});

test('custom title, question, preserve conditions and fixture survive JSON roundtrip', () => {
  const h = harness();
  const saved = plain(h.context.studyPlan());
  assert.deepEqual(saved, h.plan);
  h.node('study-title').value = 'temporary draft';
  h.node('study-question').value = 'another question';
  h.node('study-preserve').value = 'another condition';
  h.context.studyState.candidate.history_mode = 'same';
  h.context.restoreStudy(JSON.parse(JSON.stringify(saved)));
  assert.deepEqual(plain(h.context.studyPlan()), saved);
});

test('empty question blocks saving and handoff without discarding the draft', () => {
  const h = harness();
  h.node('study-title').value = '未完成的研究草稿';
  h.node('study-question').value = '   ';
  h.context.updateStudyActions();
  for (const id of ['study-plan-download', 'study-report-download', 'study-to-brief']) {
    assert.equal(h.node(id).disabled, true);
  }
  const before = h.snapshot();
  assert.throws(() => h.context.studyPlan(), /研究问题/);
  assert.throws(() => h.context.attachStudy(), /研究问题/);
  assert.deepEqual(h.snapshot(), before);
  assert.deepEqual(h.tabs, []);

  h.node('study-question').value = '补齐后的问题';
  h.context.updateStudyActions();
  for (const id of ['study-plan-download', 'study-report-download', 'study-to-brief']) {
    assert.equal(h.node(id).disabled, false);
  }
  assert.equal(h.context.studyPlan().title, '未完成的研究草稿');
});

test('attached plan and report remain fixed when the active study is edited', () => {
  const h = harness();
  h.context.attachStudy();
  const attachment = plain(h.context.studyAttachment);
  assert.deepEqual(attachment.plan, h.plan);
  assert.ok(attachment.markdown.includes(h.plan.title));
  assert.ok(attachment.markdown.includes(h.plan.question));
  assert.ok(attachment.markdown.includes(h.plan.preserve[0]));
  assert.deepEqual(h.tabs, [['change', true]]);

  h.node('study-title').value = 'new draft title';
  h.node('study-question').value = 'new draft question';
  h.node('study-preserve').value = 'new draft condition';
  h.context.studyState.candidate.history_mode = 'same';
  // The source snapshot is nested; the attachment must own a deep copy too.
  h.scenario.fixture.timeline[0].id = 'edited-source-after-attachment';
  assert.notDeepEqual(plain(h.context.studyPlan()), attachment.plan);
  assert.deepEqual(plain(h.context.studyAttachment), attachment);
});
