#!/usr/bin/env python3
"""Compare public branch tips with the revisions read by this research repo."""

import json
from pathlib import Path
import subprocess
import sys


def main() -> int:
    catalog = Path(__file__).resolve().parents[1] / "references" / "upstreams.json"
    repositories = json.loads(catalog.read_text(encoding="utf-8"))["repositories"]
    changed = False
    failed = False
    for entry in repositories:
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--exit-code", entry["url"],
                 f"refs/heads/{entry['branch']}"],
                check=True,
                text=True,
                capture_output=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            failed = True
            detail = "timeout" if isinstance(error, subprocess.TimeoutExpired) else error.stderr.strip()
            print(f"UNAVAILABLE {entry['repo']}: {detail}", file=sys.stderr)
            continue
        current = result.stdout.split()[0]
        differs = current != entry["revision"]
        changed |= differs
        label = "CHANGED" if differs else "UNCHANGED"
        print(f"{label} {entry['repo']} {entry['revision'][:12]} -> {current[:12]}")
    return 2 if failed else 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
