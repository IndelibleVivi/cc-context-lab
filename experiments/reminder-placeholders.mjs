// Offline source-level checks of already inspected, pure upstream functions.
// No upstream imports, filesystem apply driver, CC installation or model calls.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { stripTypeScriptTypes } from 'node:module';
import { runInNewContext } from 'node:vm';

const checkout = process.argv[2];
if (!checkout) {
  console.error('Usage: node experiments/reminder-placeholders.mjs <tweakcc-fixed-checkout>');
  process.exit(2);
}
const read = file => readFile(resolve(checkout, 'src', file), 'utf8');
const [sync, utils, patches] = await Promise.all([
  read('systemReminderSync.ts'), read('utils.ts'), read('patches/systemReminderOverrides.ts'),
]);
// Deliberately tied to the inspected revision; this is not a general TS loader.
function between(source, start, end) {
  const a = source.indexOf(start);
  const b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, `Source shape changed: ${start}`);
  return source.slice(a, b);
}
const names = ['AGENT_LISTING_INJECTION', 'MCP_INSTRUCTIONS_INJECTION', 'LOCAL_CMD_CAVEAT_INJECTION', 'BUDGET_USD_INJECTION'];
const source = [
  between(utils, 'export const escapeNonAscii', 'export function getCurrentClaudeCodeTheme'),
  sync.slice(sync.indexOf('export const substitutePlaceholders')),
  between(patches, 'const findAndReplace', '// A reminder-registry entry'),
  between(patches, 'const matchingBrace', 'const CLAUDEMD_INJECTION'),
  ...names.map(name => between(patches, `const ${name}:`, '\nconst ')),
].join('\n').replace(/^export /gm, '');
const api = runInNewContext(
  stripTypeScriptTypes(source) + `\n;({substitutePlaceholders,${names.join(',')}})`,
  { showDiff() {}, console },
);
const prepare = (injection, body) => {
  const result = api.substitutePlaceholders(body, injection.placeholders);
  assert.equal(result.errors.length, 0);
  return result.result;
};
const render = (injection, pristine, body, expression, data = {}) => {
  const patched = injection.apply(pristine, prepare(injection, body), false);
  assert.equal(typeof patched, 'string');
  return runInNewContext(patched + '\n;' + expression, {
    arr: x => x, msg: x => x, wrap: x => x, data,
  });
};

const agentSource = 'function render(q){switch(q.type){case"agent_listing_delta":{return arr([msg({content:`Available agent types for the Agent tool: ${q.addedLines.join("\\n")}`,isMeta:!0})]);}}}';
const agentText = render(api.AGENT_LISTING_INJECTION, agentSource, '{{ removed }}',
  'render(data)[0].content', { type: 'agent_listing_delta', addedLines: [], removedTypes: ['retired-agent'] });
assert.equal(agentText, '- retired-agent');
console.log('P01 PASS: removed agent placeholder expands through generic variable rebinding');

const mcpSource = 'function render(q){switch(q.type){case"mcp_instructions_delta":{return arr([msg({content:`# MCP Server Instructions ${q.addedBlocks.join("\\n")}`,isMeta:!0})]);}}}';
const mcpText = render(api.MCP_INSTRUCTIONS_INJECTION, mcpSource, '{{removed_names}}',
  'render(data)[0].content', { type: 'mcp_instructions_delta', addedBlocks: [], removedNames: ['retired-server'] });
assert.equal(mcpText, 'retired-server');
console.log('P02 PASS: removed MCP server placeholder expands');

const caveatSource = 'let tag="local-command-caveat";function render(){return msg({content:`<${tag}>synthetic source</${tag}>`,isMeta:!0})}';
assert.equal(render(api.LOCAL_CMD_CAVEAT_INJECTION, caveatSource, 'tag={{tag_name}}', 'render().content'),
  '<local-command-caveat>tag=local-command-caveat</local-command-caveat>');
console.log('P03 PASS: tag_name placeholder uses the discovered tag variable');

const budgetSource = 'const registry={budget_usd:(e)=>[msg({content:wrap(`USD budget: $${e.used}/$${e.total}; $${e.remaining} remaining`),isMeta:!0})]};';
assert.equal(render(api.BUDGET_USD_INJECTION, budgetSource,
  'USD budget: ${{used}}/${{total}}; ${{remaining}} remaining',
  'registry.budget_usd(data)[0].content', { used: 5, total: 10, remaining: 5 }),
  'USD budget: $5/$10; $5 remaining');
console.log('P04 PASS: dollar prefix plus placeholder renders one currency sign');

const literal = '中文 `quote` \\ ${untrusted}';
assert.equal(render(api.LOCAL_CMD_CAVEAT_INJECTION, caveatSource, literal, 'render().content'),
  `<local-command-caveat>${literal}</local-command-caveat>`);
const rejected = api.substitutePlaceholders('{{missing}}', {});
assert.equal(rejected.result, '');
assert.equal(rejected.errors.length, 1);
console.log('P05 PASS: literal Unicode/backticks/backslash/interpolation preserved; unknown placeholder rejected');
console.log('Synthetic bundle shapes only; this does not prove any installed CC build can be patched.');
