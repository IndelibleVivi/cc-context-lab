import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DESCRIPTION_RULES, fragmentDigest, quietExtraAttachment, quietContextBlocks, quietToolDescription } from '../hooks/quiet-rules.mjs';
import { register } from '../hooks/register.mjs';

const provider = { plugin: 'engine', tier: 'core' };
const event = description => ({ tool: 'Read', description, provider });
const rule = async (text, unit = 'line', replacement = '') => [['Read', unit, await fragmentDigest(text), replacement]];

test('quiet rules do not bind a CC version or remove native capabilities', () => {
  assert.equal(DESCRIPTION_RULES.length, 13);
  for (const [, unit, digest, replacement] of DESCRIPTION_RULES) {
    assert.ok(['line', 'paragraph'].includes(unit));
    assert.match(digest, /^[a-f0-9]{64}$/);
    assert.equal(typeof replacement, 'string');
  }
});
test('only engine-owned silent-turn nudge is selected', () => {
  assert.deepEqual(quietExtraAttachment({ origin: { kind: 'engine' }, type: 'silent_turn_reminder', text: 'synthetic nudge' }), { text: null });
  for (const kind of ['hook', 'plugin', undefined]) {
    assert.equal(quietExtraAttachment({ origin: { kind }, type: 'silent_turn_reminder', text: 'same quote' }), undefined);
  }
});
test('task results, safety, own context and unknown engine kinds survive', () => {
  for (const type of ['task_notification', 'task_reminder', 'instructions', 'hook_additional_context', 'deferred_tools_delta', 'new_kind']) {
    assert.equal(quietExtraAttachment({ origin: { kind: 'engine' }, type, text: 'synthetic data' }), undefined);
  }
});
test('context removes email block only and retains object/file metadata identity', () => {
  const own = { name: 'claudeMd', text: 'synthetic own core', instructionFiles: ['synthetic-path'] };
  const date = { name: 'currentDate', text: 'synthetic date' };
  const source = [own, { name: 'userEmail', text: 'user@example.invalid' }, date];
  const result = quietContextBlocks(source);
  assert.deepEqual(result, [own, date]);
  assert.equal(result[0], own);
  assert.equal(source.length, 3);
  assert.equal(quietContextBlocks(undefined), undefined);
});
test('an exact reviewed fragment is removed while unknown new facts survive', async () => {
  const prose = 'Synthetic workflow preference.';
  const rules = await rule(prose);
  assert.equal(await quietToolDescription(event('Read data.\n'+prose+'\nNew native limit: 27.'), rules), 'Read data.\n\nNew native limit: 27.');
});
test('changed prose passes unchanged, with no global substring removal', async () => {
  const prose = 'Synthetic workflow preference.';
  assert.equal(await quietToolDescription(event(prose+' Added a new fact.'), await rule(prose)), undefined);
  assert.equal(await quietToolDescription(event('Quoted: '+prose), await rule(prose)), undefined);
});
test('a selected removal cannot normalize an unrelated native example', async () => {
  const prose = 'Synthetic preference.';
  const unknown = '  New native example:\n\n\n    preserved indentation  \n\n';
  const original = '  Leading space.\n'+prose+'\n\n'+unknown+'  ';
  const actual = await quietToolDescription(event(original), await rule(prose));
  assert.equal(actual, original.replace(prose, ''));
});
test('unreviewed version-specific prose remains native', async () => {
  assert.equal(await quietToolDescription(event('A new native description.')), undefined);
  assert.equal(await quietToolDescription({ ...event('known'), tool: 'Unrecognized' }), undefined);
});
test('matching names from MCP, plugin and noncore tiers are untouched', async () => {
  const rules = await rule('synthetic');
  for (const source of [{ plugin: 'mcp:demo', tier: 'user' }, { plugin: 'engine', tier: 'user' }, { plugin: 'other', tier: 'core' }, undefined]) {
    assert.equal(await quietToolDescription({ ...event('synthetic'), provider: source }, rules), undefined);
  }
});
test('paragraph rewrite preserves all other paragraphs and declared facts', async () => {
  const prose = 'Synthetic multi-line preference.\nDo it this way.';
  assert.equal(await quietToolDescription(event('Capability.\n\n'+prose+'\n\nFailure: missing file.'), await rule(prose, 'paragraph', 'Synthetic fact.')), 'Capability.\n\nSynthetic fact.\n\nFailure: missing file.');
});
test('same text in another tool remains untouched', async () => {
  assert.equal(await quietToolDescription({ ...event('synthetic'), tool: 'Bash' }, await rule('synthetic')), undefined);
});
test('standalone mod forwards results and preserves non-description fields', async () => {
  const handlers = new Map();
  register((name, handler) => handlers.set(name, handler));
  const schema = { type: 'object', properties: { path: { type: 'string' } } };
  const native = { description: 'synthetic unknown', isDeferred: true };
  const input = { ...event(native.description), input_schema: schema };
  assert.equal(await handlers.get('tool.describe')({}, input, async e => { assert.equal(e, input); return native; }), native);
  assert.equal(input.input_schema, schema);
  const original = { text: 'synthetic completed result' };
  assert.equal(await handlers.get('prompt.attachment')({}, { type: 'task_notification' }, async () => original), original);
});
test('context middleware keeps instructionFiles and other native result fields', async () => {
  const handlers = new Map(); register((name, handler) => handlers.set(name, handler));
  const files = [{ path: 'synthetic.md', revision: 'synthetic' }];
  const own = { name: 'claudeMd', text: 'synthetic' };
  const result = await handlers.get('prompt.context')({}, {}, async () => ({ blocks: [own, { name: 'userEmail', text: 'synthetic' }], instructionFiles: files, unknown: 42 }));
  assert.deepEqual(result.blocks, [own]); assert.equal(result.instructionFiles, files); assert.equal(result.unknown, 42);
});
