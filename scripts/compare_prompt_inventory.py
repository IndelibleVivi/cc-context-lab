#!/usr/bin/env python3
"""Reproduce the lobotomized named-prompt inventory against a pristine baseline.

Read-only. No network, no install, no model call. It reads a local overrides
directory (a checkout or `git archive` of skrabe/lobotomized-claude-code's
`system-prompts-lcc/`) and a pristine prompts JSON (tweakcc's extractor output
for one CC version), then classifies every `.md`:

  exact       body (header removed and stripped) == joined pristine pieces
  norm_only   identical only after whitespace + ${placeholder}-name normalization
  changed     differs beyond that normalization (real override OR pristine drift)
  suppressed  empty body (the author's suppress marker)
  unmatched   filename id absent from this baseline's pristine ids

`exact` is not "byte-identical raw file": `body_of` strips the header and trims,
so it means the model-facing body equals the joined pristine pieces. It is not
evidence about the file's history.

Usage:
  python3 scripts/compare_prompt_inventory.py \
      --overrides <dir> --pristine <prompts-X.Y.Z.json> [--json] [--selftest]

`--selftest` runs a small synthetic check of the five categories (no external
inputs needed). Exit 0 on success, 2 on bad input or failed self-test.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter

FRONTMATTER = re.compile(r"<!--(.*?)-->", re.S)
PLACEHOLDER = re.compile(r"\$\{[^}]*\}")


def load_pristine(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out: dict[str, str] = {}
    for prompt in doc.get("prompts", []):
        pieces = prompt.get("pieces")
        if isinstance(pieces, str):
            try:
                pieces = json.loads(pieces)
            except json.JSONDecodeError:
                pieces = [pieces]
        out[prompt["id"]] = "".join(pieces) if pieces else ""
    return out


def body_of(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = FRONTMATTER.match(text)
    return (text[m.end():] if m else text).strip()


def norm(text: str) -> str:
    # Whitespace + ${placeholder-name} only. No currency/escape stripping: a
    # literal `$` is real text and must survive normalization.
    text = PLACEHOLDER.sub("${V}", text)
    return re.sub(r"\s+", " ", text).strip()


def classify(overrides_dir: str, pristine: dict[str, str]) -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {
        "exact": [], "norm_only": [], "changed": [], "suppressed": [], "unmatched": [],
    }
    for name in sorted(os.listdir(overrides_dir)):
        if not name.endswith(".md"):
            continue
        pid = name[:-3]
        body = body_of(os.path.join(overrides_dir, name))
        if pid not in pristine:
            cats["unmatched"].append(pid)
        elif body == "":
            cats["suppressed"].append(pid)
        elif body == pristine[pid]:
            cats["exact"].append(pid)
        elif norm(body) == norm(pristine[pid]):
            cats["norm_only"].append(pid)
        else:
            cats["changed"].append(pid)
    return cats


def selftest() -> int:
    """Synthetic five-category check plus a currency-preservation check."""
    # Exercise normalization itself: exact equality below would bypass it.
    if norm(r"cost is \$10") == norm("cost is 10"):
        print("SELFTEST FAIL normalization erased literal currency", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as d:
        def write(name, body):
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write("<!--\nname: x\n-->\n" + body)

        write("a-exact.md", "shared text ${V1}\n")
        write("b-norm.md", "shared   text ${DIFFERENT_NAME}\n")   # same after norm
        write("c-changed.md", "totally different body\n")
        write("d-empty.md", "")                                    # suppressed
        write("e-unmatched.md", "orphan\n")
        write("f-currency.md", "cost is ${{used}} of $10\n")       # $-prefixed

        pristine = {
            "a-exact": "shared text ${V1}",
            "b-norm": "shared text ${V1}",
            "c-changed": "engine default body",
            "d-empty": "engine body",
            "f-currency": "cost is ${{used}} of $10",
        }
        cats = classify(d, pristine)
        expected = {
            "exact": ["a-exact", "f-currency"],
            "norm_only": ["b-norm"],
            "changed": ["c-changed"],
            "suppressed": ["d-empty"],
            "unmatched": ["e-unmatched"],
        }
        for k, v in expected.items():
            if cats[k] != v:
                print(f"SELFTEST FAIL {k}: got {cats[k]} want {v}", file=sys.stderr)
                return 2
    print("selftest: 5 categories + currency preservation OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overrides", help="path to system-prompts-lcc/")
    ap.add_argument("--pristine", help="path to prompts-X.Y.Z.json")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--selftest", action="store_true", help="run synthetic self-test only")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.overrides or not args.pristine:
        print("need --overrides and --pristine (or --selftest)", file=sys.stderr)
        return 2
    if not os.path.isdir(args.overrides) or not os.path.isfile(args.pristine):
        print("missing --overrides dir or --pristine file", file=sys.stderr)
        return 2

    pristine = load_pristine(args.pristine)
    cats = classify(args.overrides, pristine)

    if args.json:
        print(json.dumps({
            "overrides": args.overrides,
            "pristine": args.pristine,
            "pristine_ids": len(pristine),
            "counts": {k: len(v) for k, v in cats.items()},
            "matchable": sum(len(v) for k, v in cats.items() if k != "unmatched"),
            "by_prefix": {k: dict(Counter(p.split("-")[0] for p in v))
                          for k, v in cats.items()},
            "unmatched_ids": cats["unmatched"],
        }, indent=1, ensure_ascii=False))
        return 0

    total = sum(len(v) for v in cats.values())
    print(f"overrides: {args.overrides}")
    print(f"pristine:  {args.pristine}  ({len(pristine)} prompt ids)")
    print(f"total .md: {total}")
    for k in ("exact", "norm_only", "changed", "suppressed", "unmatched"):
        print(f"  {k:10s} {len(cats[k]):5d}")
    print(f"  matchable  {total - len(cats['unmatched']):5d}  (non-unmatched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
