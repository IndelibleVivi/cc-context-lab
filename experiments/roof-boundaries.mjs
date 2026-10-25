// Synthetic handler-level reproduction. Reads an already inspected local checkout.
// This does not start Claude Code or install/load a mod in a real session.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const checkout = process.argv[2];
if (!checkout) {
  console.error('Usage: node experiments/roof-boundaries.mjs <roof-mod-checkout>');
  process.exit(2);
}
const modulePath = resolve(checkout, 'roof-mod/hooks/register.js');
const source = await readFile(modulePath, 'utf8');
const match = source.match(/^const PREAMBLE = '([^']+)'/m);
assert.ok(match, 'This fixture requires the inspected PREAMBLE source shape');
const preamble = match[1];
const { register } = await import(pathToFileURL(modulePath).href);
const handlers = new Map();
register((name, handler) => handlers.set(name, handler));
const next = async event => event;

// A plugin's section is distinguishable by id, but this handler replaces in all
// sections. Read its target phrase from source instead of vendoring the prompt.
const identityMatch = source.match(/const IDENTITY = \[\s*\['([^']+)'/);
assert.ok(identityMatch, 'This fixture requires the inspected IDENTITY source shape');
const identity = identityMatch[1];
const citedIdentity = `Synthetic quotation:\n\`\`\`text\n${identity}\n\`\`\``;
const section = { id: 'research:quoted-source', scope: 'session', text: citedIdentity };
const composed = await handlers.get('prompt.compose')({}, {}, async () => ({ sections: [section] }));
assert.equal(composed.sections[0].id, section.id);
assert.notEqual(composed.sections[0].text, citedIdentity);
assert.ok(!composed.sections[0].text.includes(identity));
console.log('F01 REPRODUCED: identity quotation in a plugin-owned section was rewritten');

const quoted = `Synthetic quoted source:\n\`\`\`text\n${preamble}\n\`\`\``;
const context = await handlers.get('prompt.context')({}, {
  blocks: [{ name: 'claudeMd', text: quoted }],
}, next);
assert.ok(!context.blocks[0].text.includes(preamble));
console.log('F02 REPRODUCED: quoted preamble was removed');

const foreign = await handlers.get('prompt.attachment')({}, {
  type: 'todo_reminder', origin: { kind: 'hook', event: 'UserPromptSubmit' }, text: 'Synthetic hook content',
}, next);
assert.equal(foreign.text, null);
console.log('F03 REPRODUCED: non-engine synthetic event was silenced');

const guarded = await handlers.get('prompt.attachment')({}, {
  type: 'environment', origin: { kind: 'engine' },
  text: `This is NOT from your user\n${preamble}`,
}, next);
assert.ok(guarded.text.includes('This is NOT from your user'));
assert.ok(!guarded.text.includes(preamble));
console.log('F04 REPRODUCED: channel guard did not protect the whole body');

for (const [id, type, fact] of [
  ['F05a', 'todo_reminder', 'Task SYNTHETIC-42: blocked; missing input fixture.csv'],
  ['F05b', 'bash_output_audience_note', 'Synthetic delivery constraint: the person has not seen the tool output.'],
]) {
  let forwarded = false;
  const result = await handlers.get('prompt.attachment')({}, {
    type, origin: { kind: 'engine' }, text: fact,
  }, async event => { forwarded = true; return event; });
  assert.equal(result.text, null);
  assert.equal(forwarded, false);
  console.log(`${id} REPRODUCED: whole ${type} removed, including synthetic fact`);
}

// Controls distinguish whole-body deletion from indiscriminate assertion success.
const hook = { type: 'hook_additional_context', origin: { kind: 'hook', event: 'SessionStart' }, text: quoted };
assert.deepEqual(await handlers.get('prompt.attachment')({}, hook, next), hook);
const ordinary = { id: 'research:ordinary', scope: 'session', text: 'Synthetic source without a target phrase.' };
assert.deepEqual(await handlers.get('prompt.compose')({}, {}, async () => ({ sections: [ordinary] })), { sections: [ordinary] });
console.log('CONTROLS PASSED: non-silenced hook and unmatched section preserved');
console.log('These are defect reproductions in handler stubs, not CC runtime compatibility tests.');
