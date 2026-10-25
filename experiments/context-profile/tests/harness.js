// Minimal offline harness: a synthetic `on`/`next` chain with the event
// semantics the candidate relies on (see the public Mods types). It is NOT the
// official plugin test kit and does not pretend to be a real CC event stream.
//
// Each event has a `core` answer standing for the engine beneath all plugins.
// Hooks run in registration order; `next(e)` runs the rest of the chain then
// the core answer. A hook may answer without calling `next` to replace it.

export function makeChain(coreAnswers) {
  const registry = new Map(); // eventName -> [hook]
  const on = (name, a, b) => {
    const hook = typeof a === "function" ? a : b;
    const matcher = typeof a === "function" ? null : a;
    if (!registry.has(name)) registry.set(name, []);
    registry.get(name).push({ matcher, hook });
    return { catch: () => {} };
  };
  const matches = (matcher, ev) =>
    !matcher || Object.entries(matcher).every(([k, v]) => ev[k] === v);

  const dispatch = async (name, ev) => {
    const hooks = (registry.get(name) || []).filter((h) => matches(h.matcher, ev));
    const core = coreAnswers[name] || ((e) => e);
    const run = async (i, e) => {
      if (i >= hooks.length) return core(e);
      const next = (n = e) => run(i + 1, n);
      return hooks[i].hook(null, e, next);
    };
    return run(0, ev);
  };
  return { on, dispatch };
}
