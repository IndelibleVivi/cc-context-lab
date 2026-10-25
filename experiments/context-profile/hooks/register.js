// cc-context-lab candidate hooks module — SOURCE CANDIDATE, NOT INSTALLED.
//
// Offline experiment for the first owned context profile. Written against the
// *public* Mods types (anthropics/claude-code@2bfb629dfaff0c8318047a4beb93cf1dc5b58b18,
// header 2.1.277). Node fixtures and the official 2.1.289 offline test kit
// exercise synthetic events. No model/session or installed profile is involved.
//
// Design contract (see ../README.md and docs/profile-design.md):
//  - Rewrite is scope-based: explicit `prompt.section` names, engine provider on
//    `tool.describe`. Never global string replacement.
//  - External source text (file references, CLAUDE.md, hook/plugin context, tool
//    results) and dynamic runtime facts are preserved.
//  - Unselected section / tool is a no-op pass-through. Map lookup does not
//    inherit prototype keys such as `toString`/`constructor`.
//  - tool.describe changes only the description of an engine-tier tool; the
//    result carries only `{ description, isDeferred? }`.
//  - No attachment handler at all: no kind is dropped. The public extract shows
//    an engine task reminder body carries a live task list, so dropping an
//    attachment could drop facts.

// Configure these maps in the authored module, then reload the mod. The default
// selects no engine section; known names alone do not establish rewrite scope.
export const sectionOverrides = new Map();
export const toolDescriptionOverrides = new Map([
  ["Bash", "Executes a shell command and returns its output. Prefer dedicated tools where they exist."],
]);
const kEngineProvider = { plugin: "engine", tier: "core" };

// The official analyzer requires a directly exported register function. Keep
// one registration path for the official loader and the Node tests.
export function register(on) {
  const selectedSections = new Map(sectionOverrides);
  const selectedTools = new Map(toolDescriptionOverrides);

  on("prompt.section", ($, e, next) => {
    if (!selectedSections.has(e.name)) return next(e);
    if (e.text === null) return { text: null };
    return { text: selectedSections.get(e.name) };
  });

  on("tool.describe", ($, e, next) => {
    if (!isEngineProvider(e.provider) || !selectedTools.has(e.tool)) return next(e);
    return next({ ...e, description: selectedTools.get(e.tool) });
  });

  on("prompt.compose", async ($, e, next) => {
    const { sections } = await next(e);
    return { sections: placeSessionSection(sections, ownCoreSection()) };
  });
  // No attachment handler: engine-authored framing can contain live facts.
}

// ---------------------------------------------------------------------------
// Synthetic candidate data and helpers. NOT the final identity.
// ---------------------------------------------------------------------------

function isEngineProvider(provider) {
  return (
    provider != null &&
    provider.plugin === kEngineProvider.plugin &&
    provider.tier === kEngineProvider.tier
  );
}

// A session-scoped section. `shared` text must read the same for everyone (it
// is cached across organizations), so the private core must NOT be `shared`.
export function ownCoreSection() {
  return {
    id: "lab:core",
    scope: "session",
    text: [
      "# Lab core (synthetic)",
      "Follow the written authorization in the current request; do not widen its scope.",
      "State what was checked, inferred and left unverified, and keep quoted source text intact.",
    ].join("\n"),
  };
}

// Place the session section at the shared/session boundary: drop any existing
// section with the same id (de-duplicate), then insert before the first
// remaining session-scoped section, or append after all sections if there is
// none. Engine sections keep their relative order. The engine's contract is
// that every `shared` section precedes every `session` section; the engine
// places the cache boundary itself, but a hook must not answer a list that
// violates the order.
export function placeSessionSection(sections, own) {
  const withoutOwn = sections.filter((s) => s.id !== own.id);
  const firstSession = withoutOwn.findIndex((s) => s.scope === "session");
  if (firstSession === -1) return [...withoutOwn, own];
  return [
    ...withoutOwn.slice(0, firstSession),
    own,
    ...withoutOwn.slice(firstSession),
  ];
}
