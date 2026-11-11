# While Claude Works

A tiny offline page for Claude Code's 187 built-in waiting words, plus a six-frame star made from text glyphs. It is display-only: it does not read a Claude Code session, logs, or task state, and its motion does not mean a model is working.

Open [index.html](index.html) to use it offline. The words, styles, and script are embedded in that one file, with no CDN, font download, package, or other dependency. The [line-separated vocabulary](spinner-verbs-2.1.322.txt) is available for direct copy and reuse.

## Provenance and limits

- Vocabulary: the 187 built-in waiting words from Claude Code **2.1.322**, checked on 2026-11-11 against the official [@anthropic-ai/claude-code-darwin-arm64 package](https://registry.npmjs.org/@anthropic-ai/claude-code-darwin-arm64/2.1.322).
- The [official spinnerVerbs documentation](https://code.claude.com/docs/en/settings-reference#spinnerverbs) describes the vocabulary setting. The animation is independently authored here.
- The vocabulary is attributed third-party source material and is not relicensed by this project's SUL or documentation terms.
- The page and its reusable CSS/JS recreation are project-authored functional work under [SUL-1.0](../../LICENSE).
- The animation uses `· ✢ ✳ ✶ ✻ ✽` with hard frame changes over 1.2 seconds and rests on `✻`. This is an independent web recreation; it makes no claim about exact native timing, implementation, or behavior.
- The page makes no network calls, invokes no real model, and shows no fake progress. The word changes only on mount or an explicit reroll.

## Files

| File | Purpose |
| --- | --- |
| [verbs.json](verbs.json) | The sole hand-maintained vocabulary: 187 strings |
| [spinner.css](spinner.css) | Reusable styles, scoped around `.cc-spinner-glyph` |
| [spinner.js](spinner.js) | Classic browser JS; auto-initializes `[data-cc-spinner]` |
| [template.html](template.html) | Source template for the standalone page |
| [index.html](index.html) | Generated self-contained page; do not edit by hand |
| [spinner-verbs-2.1.322.txt](spinner-verbs-2.1.322.txt) | Generated one-word-per-line list; do not edit by hand |

## Integration

Include the styles, data and script together. This short example has two words; for the complete 187-word snapshot, embed the full `verbs.json` array:

```html
<link rel="stylesheet" href="./spinner.css">
<script src="./spinner.js" defer></script>
<script type="application/json" id="cc-spinner-data">["Accomplishing", "Actioning"]</script>

<div data-cc-spinner class="cc-spinner">
  <span class="cc-spinner-glyph" data-spinner-glyph aria-hidden="true"></span>
  <span data-spinner-word aria-live="polite"></span>
  <button class="cc-spinner__button" type="button" data-spinner-next>New word</button>
  <button class="cc-spinner__button" type="button" data-spinner-pause aria-pressed="false" data-label-pause="Pause animation" data-label-resume="Resume animation">Pause animation</button>
  <button class="cc-spinner__button" type="button" data-spinner-download>Download TXT</button>
</div>
```

After including `spinner.css` and `spinner.js`, each `[data-cc-spinner]` root mounts independently; its controls and word updates stay scoped to that root. Only `[data-spinner-next]` rerolls after mount, and the word does not change on a timer. The pause button toggles the root's `data-paused` state without changing the current word.

- `[data-spinner-glyph]`: the glyph node. The script adds `.cc-spinner-glyph` and `aria-hidden`.
- `[data-spinner-word]`: the word text node.
- `[data-spinner-next]`: optional; click or activate with Enter to reroll.
- `[data-spinner-pause]`: optional; maintains `aria-pressed` and the root state. Add `data-label-pause` / `data-label-resume` for localized button labels.
- `[data-spinner-download]`: optional; exports the supplied vocabulary as lines (187 when using the complete snapshot), locally.

Controls may be omitted; a compact embed needs only the glyph and word. A page should contain one `#cc-spinner-data` element. For programmatic mounting, call `CCSpinner.mount(root)`; the script has already initialized unmounted roots, and repeated calls do not duplicate listeners.

`prefers-reduced-motion: reduce` fixes the glyph at `✻`. Pause does the same, and resume restores the 1.2-second frame sequence.

## Use just the star

The decorative glyph needs only CSS, without JS or vocabulary. Pair it with readable status text if it communicates actual work state.

```html
<link rel="stylesheet" href="./spinner.css">
<span class="cc-spinner cc-spinner-glyph" aria-hidden="true"></span>
```

## Build

From the repository root:

```sh
python3 scripts/build_spinner.py
```

The builder reads `verbs.json`, `spinner.css`, `spinner.js`, `template.html`, and the repository `LICENSE` to generate `index.html` and the TXT. Both generated files are tracked. If you change canonical source, rebuild and inspect the output rather than editing generated files.

`scripts/build_spinner.py` also exports `load_spinner_assets(root: Path) -> dict[str, str]` with `css`, `js`, and `data_json` keys for other offline pages, including the Workbench.

## Standalone download

`index.html` does not depend on the sibling CSS, JS, or JSON files; it can be moved as one file. The generated HTML includes the complete SUL-1.0 text and provenance. When copying the CSS/JS separately, carry [LICENSE](../../LICENSE). The TXT is also independent. If you use the frontend CSS/JS from a local checkout, preserve the `extras/spinner/` layout so the relative paths resolve.

## Verification

```sh
python3 scripts/test_spinner.py
node --test scripts/test_spinner_ui.cjs
node --check extras/spinner/spinner.js
```

The tests cover the data, generated artifacts, safe offline embedding, download line count, control isolation, pause behavior, the reduced-motion fallback, and tolerance for missing optional controls. The integrating owner remains responsible for final rendered layout and experience checks.
