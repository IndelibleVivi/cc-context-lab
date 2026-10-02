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

const quoted = `Synthetic quoted source:\n\`\`\`text\n${preamble}\n\`\`\``;
const context = await handlers.get('prompt.context')({}, {
  blocks: [{ name: 'claudeMd', text: quoted }],
}, next);
assert.ok(!context.blocks[0].text.includes(preamble));
console.log('F02 REPRODUCED: quoted preamble was removed');

const foreign = await handlers.get('prompt.attachment')({}, {
  type: 'todo_reminder', origin: { kind: 'hook' }, text: 'Synthetic hook content',
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
console.log('These are defect reproductions in handler stubs, not CC runtime compatibility tests.');
