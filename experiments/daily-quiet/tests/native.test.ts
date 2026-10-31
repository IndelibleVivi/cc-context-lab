// Offline native test kit; all inputs are synthetic. No model or live hooks.
import { test, expect } from 'claude-code/testing';

test('engine nudge is omitted, hook and task payloads stay', async ($, on) => {
  on('prompt.attachment', ($, e) => ({ text: e.text }));
  expect((await $.prompt.attachment({ type: 'silent_turn_reminder', origin: { kind: 'engine' }, text: 'synthetic nudge' } as any)).text).toBe(null);
  expect((await $.prompt.attachment({ type: 'silent_turn_reminder', origin: { kind: 'hook', event: 'Stop' }, text: 'synthetic hook' } as any)).text).toBe('synthetic hook');
  expect((await $.prompt.attachment({ type: 'task_notification', origin: { kind: 'engine' }, text: 'synthetic task result' } as any)).text).toBe('synthetic task result');
});
test('unknown descriptions and provider tools pass through', async ($, on) => {
  on('tool.describe', ($, e) => ({ description: e.description, isDeferred: true }));
  const value = await $.tool.describe({ tool: 'Read', provider: { plugin: 'engine', tier: 'core' }, description: 'synthetic new native fact' } as any);
  expect(value.description).toBe('synthetic new native fact');
  expect(value.isDeferred).toBe(true);
});
test('own initial context and instructionFiles survive email projection', async ($, on) => {
  on('prompt.context', ($, e) => ({ blocks: e.blocks, instructionFiles: e.instructionFiles } as any));
  const value = await $.prompt.context({ blocks: [{ name: 'claudeMd', text: 'synthetic own core' }, { name: 'userEmail', text: 'synthetic@example.invalid' }], instructionFiles: [{ path: 'synthetic.md', kind: 'project', content: 'synthetic own core' }] } as any);
  expect(value.blocks.map((b: any) => b.name)).toEqual(['claudeMd']);
  expect((value as any).instructionFiles).toEqual([{ path: 'synthetic.md', kind: 'project', content: 'synthetic own core' }]);
});
