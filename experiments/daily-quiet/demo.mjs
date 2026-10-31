// Emits one completely synthetic case to stdout. No capture, model or runtime I/O.
import { fragmentDigest, quietExtraAttachment, quietToolDescription } from './hooks/quiet-rules.mjs';

const preference = 'Synthetic workflow preference for this demonstration.';
const syntheticRules = [['Read', 'line', await fragmentDigest(preference), '']];
const schema = { type: 'object', properties: { path: { type: 'string' } }, required: ['path'] };
const tool = { name: 'Read', description: 'Synthetic file reader.\n'+preference, input_schema: schema };
const events = [
  { origin: { kind: 'hook' }, type: 'silent_turn_reminder', text: 'OWN_HOOK_CONTEXT' },
  { origin: { kind: 'engine' }, type: 'task_notification', text: 'COMPLETED_TASK_RESULT' },
  { origin: { kind: 'engine' }, type: 'silent_turn_reminder', text: 'SYNTHETIC_NUDGE' },
];
const messages = items => [{ role: 'user', content: items.map(item => ({ type: 'text', text: item.text })) }];
const keep = events.filter(event => quietExtraAttachment(event)?.text !== null);
const capture = (id, body) => ({
  schema: 'harness-context-capture/1', capture_id: id,
  evidence: { kind: 'synthetic_fixture', observed_at: null },
  runtime: { harness: 'synthetic-harness', version: 'synthetic', entrypoint: 'daily-quiet-demo', mode: 'offline', candidate: 'synthetic-fragment-example', session_path: id },
  wire_format: 'anthropic-messages', body,
});
const baseline = { system: [{ type: 'text', text: 'OWN_CORE' }], messages: messages(events), tools: [tool] };
const description = await quietToolDescription({ tool: 'Read', description: tool.description, provider: { plugin: 'engine', tier: 'core' } }, syntheticRules);
const after = { ...baseline, messages: messages(keep), tools: [{ ...tool, description }] };
const changedNative = tool.description+'\nNEW_NATIVE_LIMIT';
const updatedDescription = await quietToolDescription({ tool: 'Read', description: changedNative, provider: { plugin: 'engine', tier: 'core' } }, syntheticRules);
const updated = { ...after, tools: [{ ...tool, description: updatedDescription }] };
const req = (id, text, level = 'request_structure') => ({ id, text, level });
const checks = [];
for (const step of ['after', 'updated']) {
  for (const [id, pointer, expected] of [
    ['core', '/system', baseline.system],
    ['schema', '/tools/0/input_schema', schema],
    ['own_hook', '/messages/0/content/0/text', 'OWN_HOOK_CONTEXT'],
    ['task_result', '/messages/0/content/1/text', 'COMPLETED_TASK_RESULT'],
  ]) checks.push({ id: step+'_'+id, requirement_id: id, step_id: step, pointer, operator: 'equals', expected });
  checks.push({ id: step+'_nudge', requirement_id: 'nudge', step_id: step, pointer: '/messages/0/content/2', operator: 'absent', expected: null });
}
checks.push({ id: 'new_fact', requirement_id: 'new_fact', step_id: 'updated', pointer: '/tools/0/description', operator: 'contains_text', expected: 'NEW_NATIVE_LIMIT' });
checks.push({ id: 'resume_unknown', requirement_id: 'resume', step_id: 'resume', pointer: '/messages', operator: 'exists', expected: null });
checks.push({ id: 'shape_tool_schema', requirement_id: 'partial_structure', step_id: 'shape', pointer: '/tools/0/input_schema', operator: 'equals', expected: schema });
checks.push({ id: 'shape_messages_unknown', requirement_id: 'unknown_history', step_id: 'shape', pointer: '/messages', operator: 'absent', expected: null });
const shape = capture('shape', { system: updated.system, tools: updated.tools });
shape.evidence_scope = { request_body: 'partial', observed_fields: ['system', 'tools'] };
console.log(JSON.stringify({
  schema: 'harness-context-case/1', case_id: 'daily-quiet-synthetic', title: 'Daily quiet / synthetic portability comparison',
  question: 'Can selected presentation prose exit while own context, task facts, schemas and new native facts remain?',
  requirements: [req('core', 'Owned core remains exact.'), req('schema', 'Tool parameters remain exact.'), req('own_hook', 'Hook content remains.'), req('task_result', 'Task completion payload remains.'), req('nudge', 'Selected engine nudge exits.'), req('new_fact', 'New native fact survives an update.'), req('partial_structure', 'Explicit shape fields remain checkable.'), req('unknown_history', 'Missing message coverage must remain unassessed.'), req('resume', 'Real resume coverage is still missing.'), req('behavior', 'Daily conversation feels quieter.', 'model_behavior'), req('delivery', 'External delivery remains correct.', 'external_delivery')],
  study_plan: null,
  steps: [{ id: 'before', label: 'Synthetic baseline', capture: capture('before', baseline) }, { id: 'after', label: 'Synthetic rules', capture: capture('after', after) }, { id: 'updated', label: 'Synthetic native description update', capture: capture('updated', updated) }, { id: 'shape', label: 'Partial system/tools evidence', capture: shape }, { id: 'resume', label: 'Actual lifecycle not captured', capture: null }],
  comparisons: [{ id: 'quiet_change', baseline: 'before', candidate: 'after' }, { id: 'native_change', baseline: 'after', candidate: 'updated' }, { id: 'partial_coverage', baseline: 'updated', candidate: 'shape' }], checks,
}, null, 2));
