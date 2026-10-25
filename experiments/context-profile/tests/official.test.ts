import { expect, test } from 'claude-code/testing'

// Real CC loader and event chain, synthetic engine answers. No model or tool runs.
test('default module composes a session core without losing engine sections', async ($, on) => {
  const sections = [
    { id: 'intro', scope: 'shared', text: 'SYNTHETIC SHARED' },
    { id: 'memory', scope: 'session', text: 'QUOTED SOURCE' },
  ]
  on('prompt.compose', () => ({ sections }))
  const result = await $.prompt.compose({
    model: 'synthetic', promptModel: 'synthetic', surfaces: [], tools: ['Bash'],
    outputStyle: null, traits: [],
  })
  expect(result.sections.map(s => s.id).join(',')).toBe('intro,lab:core,memory')
  expect(result.sections[1].scope).toBe('session')
  expect(JSON.stringify(result.sections.filter(s => s.id !== 'lab:core'))).toBe(JSON.stringify(sections))
})

test('tool description changes only for the engine provider and keeps placement', async ($, on) => {
  on('tool.describe', ($, e) => ({ description: e.description, isDeferred: true }))
  const engine = await $.tool.describe({
    tool: 'Bash', description: 'ENGINE BASELINE', isDeferred: true,
    provider: { plugin: 'engine', tier: 'core' },
  })
  expect(engine.description).toBe('Executes a shell command and returns its output. Prefer dedicated tools where they exist.')
  expect(engine.isDeferred).toBe(true)
  const foreign = await $.tool.describe({
    tool: 'Bash', description: 'FOREIGN BASELINE',
    provider: { plugin: 'synthetic-provider', tier: 'user' },
  })
  expect(foreign.description).toBe('FOREIGN BASELINE')
})

test('unselected and unknown sections preserve source text including core quotations', async ($, on) => {
  on('prompt.section', ($, e) => ({ text: e.text }))
  const source = "A quotation: Follow the written authorization in the current request; do not widen its scope."
  for (const name of ['memory', 'future_section', 'constructor']) {
    const result = await $.prompt.section({ name, text: source })
    expect(result.text).toBe(source)
  }
})
