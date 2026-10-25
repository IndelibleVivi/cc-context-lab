// Offline candidate tests. Synthetic events only; no CC process, no model call.
// Run: node --test experiments/context-profile/tests/register.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { makeChain } from "./harness.js";
import {
  register, sectionOverrides, toolDescriptionOverrides,
  ownCoreSection, placeSessionSection,
} from "../hooks/register.js";

// Synthetic section override: the candidate does NOT claim any real engine
// section name (`env_info_simple`, `memory`, ... are documented names but not
// proof a given section may be rewritten). Tests inject this own selector.
const REPLACEMENT =
  "Lab synthetic guidance: state what was checked, inferred and left unverified.";
const SECTION_SELECTOR = "lab:synthetic-guidance";

const withSynthetic = (core) => {
  const chain = makeChain(core);
  sectionOverrides.set(SECTION_SELECTOR, REPLACEMENT);
  try { register(chain.on); }
  finally { sectionOverrides.delete(SECTION_SELECTOR); }
  return chain;
};

const freshChain = (core) => {
  const chain = makeChain(core);
  register(chain.on);
  return chain;
};

test("default production shape selects zero engine sections", async () => {
  const chain = freshChain({ "prompt.section": (e) => ({ text: e.text }) });
  for (const name of ["env_info_simple", "memory"]) {
    const body = `engine default text for ${name}`;
    const r = await chain.dispatch("prompt.section", { name, text: body });
    assert.equal(r.text, body, `${name} must not be rewritten by the default shape`);
  }
});

test("prompt.section: explicitly selected name is replaced", async () => {
  const chain = withSynthetic({ "prompt.section": (e) => ({ text: e.text }) });
  const r = await chain.dispatch("prompt.section", {
    name: SECTION_SELECTOR, text: "previous synthetic body",
  });
  assert.equal(r.text, REPLACEMENT);
});

test("prompt.section: engine-omitted (text:null) selected section stays null", async () => {
  const chain = withSynthetic({ "prompt.section": (e) => ({ text: e.text }) });
  const r = await chain.dispatch("prompt.section", { name: SECTION_SELECTOR, text: null });
  assert.equal(r.text, null);
});

test("prompt.section: unselected section carrying the replacement string is preserved", async () => {
  // A CLAUDE.md / @file reference that happens to contain the exact replacement
  // text. It is a different section id and must pass through byte-for-byte.
  const chain = withSynthetic({ "prompt.section": (e) => ({ text: e.text }) });
  const external = `Project notes:\n${REPLACEMENT}\n(quoted from a file, do not rewrite)`;
  const r = await chain.dispatch("prompt.section", { name: "memory", text: external });
  assert.equal(r.text, external);
});

test("prompt.section: prototype names are treated as unknown, not overrides", async () => {
  const chain = withSynthetic({ "prompt.section": (e) => ({ text: e.text }) });
  for (const name of ["toString", "constructor", "hasOwnProperty", "__proto__"]) {
    const body = `engine text for ${name}`;
    const r = await chain.dispatch("prompt.section", { name, text: body });
    assert.equal(r.text, body, `${name} must not be picked up as an override`);
  }
});

test("prompt.compose: own core is a session section at the shared/session boundary", async () => {
  const engineSections = [
    { id: "intro", text: "engine shared intro", scope: "shared" },
    { id: "tools", text: "engine shared tools", scope: "shared" },
    { id: "memory", text: "engine session memory", scope: "session" },
  ];
  const chain = freshChain({ "prompt.compose": () => ({ sections: engineSections }) });
  const { sections } = await chain.dispatch("prompt.compose", { model: "synthetic" });

  const lastShared = sections.map((s) => s.scope).lastIndexOf("shared");
  const firstSession = sections.map((s) => s.scope).indexOf("session");
  assert.ok(firstSession > lastShared, "every shared section must precede every session one");

  const own = sections.find((s) => s.id === "lab:core");
  assert.equal(own.scope, "session", "private core must not be shared/cached across orgs");
  const engine = sections.filter((s) => s.id !== "lab:core");
  assert.deepEqual(engine, engineSections, "engine sections keep relative order and shape");
});

test("prompt.compose: repeated renders do not duplicate lab:core", async () => {
  const engineSections = [
    { id: "intro", text: "engine intro", scope: "shared" },
    { id: "memory", text: "engine memory", scope: "session" },
  ];
  const chain = freshChain({ "prompt.compose": () => ({ sections: engineSections }) });
  const first = (await chain.dispatch("prompt.compose", { model: "m" })).sections;
  const chain2 = freshChain({ "prompt.compose": () => ({ sections: first }) });
  const second = (await chain2.dispatch("prompt.compose", { model: "m" })).sections;
  assert.equal(second.filter((s) => s.id === "lab:core").length, 1);
});

test("placeSessionSection: de-duplicates and moves to the shared/session boundary", () => {
  // Core already present in the SECOND session slot: it must be removed from
  // there and re-inserted at the boundary, leaving the other session in place.
  const sections = [
    { id: "intro", text: "s1", scope: "shared" },
    { id: "memory", text: "s2", scope: "session" },
    { id: "lab:core", text: "stale", scope: "session" },
    { id: "env", text: "s3", scope: "session" },
  ];
  const out = placeSessionSection(sections, ownCoreSection());
  assert.equal(out.filter((s) => s.id === "lab:core").length, 1);
  assert.equal(out.find((s) => s.id === "lab:core").text, ownCoreSection().text);
  // lab:core sits immediately before the first remaining session section.
  assert.deepEqual(out.map((s) => s.id), ["intro", "lab:core", "memory", "env"]);
});

// --- prompt.attachment: candidate registers NO handler ----------------------
// These tests exercise the chain with no candidate hook, so they only document
// the baseline "no rewriting" behavior, not a candidate capability.

test("prompt.attachment baseline: engine-origin payload with live task state is preserved", async () => {
  const chain = freshChain({ "prompt.attachment": (e) => ({ text: e.text }) });
  const payload = "Tasks:\n#1. [pending] ship the fix\n#2. [in_progress] run tests";
  const engine = await chain.dispatch("prompt.attachment", {
    type: "todo_reminder", text: payload, origin: { kind: "engine" },
  });
  assert.equal(engine.text, payload);
});

test("prompt.attachment baseline: settings-hook origin is preserved", async () => {
  const chain = freshChain({ "prompt.attachment": (e) => ({ text: e.text }) });
  const own = "own SessionStart additionalContext: unfinished work order #42";
  const hook = await chain.dispatch("prompt.attachment", {
    type: "todo_reminder", text: own, origin: { kind: "hook", event: "SessionStart" },
  });
  assert.equal(hook.text, own);
});

test("prompt.attachment baseline: plugin origin (prompt.submit) is preserved", async () => {
  const chain = freshChain({ "prompt.attachment": (e) => ({ text: e.text }) });
  const own = "plugin chain context attached at prompt.submit";
  const plugin = await chain.dispatch("prompt.attachment", {
    type: "todo_reminder", text: own, origin: { kind: "plugin", event: "prompt.submit" },
  });
  assert.equal(plugin.text, own);
});

test("tool.describe: core receives the event with only description changed", async () => {
  const received = [];
  const chain = freshChain({
    "tool.describe": (e) => {
      received.push(e);
      return { description: e.description, isDeferred: e.isDeferred };
    },
  });
  const input = {
    tool: "Bash",
    description: "engine bash description",
    isDeferred: true,
    provider: { plugin: "engine", tier: "core" },
  };
  await chain.dispatch("tool.describe", input);

  assert.equal(received.length, 1, "core must be reached once");
  const seen = received[0];
  assert.equal(seen.description, toolDescriptionOverrides.get("Bash"));
  assert.equal(seen.tool, "Bash");
  assert.equal(seen.isDeferred, true);
  assert.deepEqual(seen.provider, { plugin: "engine", tier: "core" });
  assert.equal(input.description, "engine bash description", "input object not mutated");
});

test("tool.describe: isDeferred=true and omission are left as the engine answered", async () => {
  const deferred = freshChain({
    "tool.describe": (e) => ({ description: e.description, isDeferred: true }),
  });
  const r1 = await deferred.dispatch("tool.describe", {
    tool: "Bash", description: "d", isDeferred: true,
    provider: { plugin: "engine", tier: "core" },
  });
  assert.equal(r1.isDeferred, true);

  const omitted = freshChain({ "tool.describe": (e) => ({ description: e.description }) });
  const r2 = await omitted.dispatch("tool.describe", {
    tool: "Bash", description: "d", provider: { plugin: "engine", tier: "core" },
  });
  assert.equal("isDeferred" in r2, false, "omission must stay an omission");
});

test("tool.describe: same-named tool from a foreign provider is preserved", async () => {
  const received = [];
  const chain = freshChain({
    "tool.describe": (e) => { received.push(e); return { description: e.description }; },
  });
  const foreign = { plugin: "acme", tier: "user" };
  const out = await chain.dispatch("tool.describe", {
    tool: "Bash", description: "acme's own Bash", provider: foreign,
  });
  assert.equal(out.description, "acme's own Bash");
  assert.deepEqual(received[0].provider, foreign);
});
