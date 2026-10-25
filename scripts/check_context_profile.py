#!/usr/bin/env python3
"""Run the official validator/test kit on a clean local candidate copy.

No installation, account access, model session, upstream fetch or pin update.
The caller supplies a trusted Claude executable. Raw outputs remain in the
chosen local output directory. Exit 0: these offline checks passed; 1: candidate
failed; 2: command unavailable/unsupported, timeout, or unrecognized output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UNSUPPORTED = re.compile(r"unknown (?:command|option)|unrecognized (?:command|option)", re.I)


def invoke(executable: str, args: list[str], cwd: Path, env: dict, timeout: float) -> dict:
    try:
        result = subprocess.run([executable, *args], cwd=cwd, env=env,
                                capture_output=True, text=True, timeout=timeout)
        return {"arguments": args, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"arguments": args, "exit_code": None, "error": "timeout"}
    except OSError as error:
        return {"arguments": args, "exit_code": None,
                "error": f"cannot_execute: {error.strerror}"}


def command_status(result: dict) -> str:
    if result.get("error"):
        return "unavailable"
    if UNSUPPORTED.search(result["stdout"] + result["stderr"]):
        return "unsupported"
    if "hooks modules are turned off" in result["stdout"] + result["stderr"]:
        return "unavailable"
    return "passed" if result["exit_code"] == 0 else "failed"


def run_check(executable: str, source: Path, output: Path, timeout: float) -> tuple[dict, Path, int]:
    output.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=output)).resolve()
    config = run_dir / "config"
    config.mkdir()
    candidate = run_dir / "candidate"
    generated_root = source / ".claude-plugin"

    def ignore(directory, names):
        excluded = {n for n in names if n in {".git", "node_modules", "__pycache__"} or n.endswith(".pyc")}
        if Path(directory) == generated_root:
            excluded.add("types")  # never reuse generated types from an older build
        return excluded

    shutil.copytree(source, candidate, ignore=ignore)
    env = {"PATH": os.environ.get("PATH", os.defpath), "LANG": "en_US.UTF-8",
           "CLAUDE_CONFIG_DIR": str(config), "DISABLE_AUTOUPDATER": "1",
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
    report = {"schema": "cc-context-lab.offline-check/1", "executable": executable,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "offline_status": "unavailable", "steps": {},
              "target_types": {"status": "not_generated"},
              "request_behavior": "not_tested", "model_behavior": "not_tested"}
    exit_code = 2

    def finish():
        types_dir = candidate / ".claude-plugin/types"
        files = sorted(str(p.relative_to(candidate)) for p in types_dir.rglob("*.d.ts")) if types_dir.exists() else []
        if files:
            report["target_types"] = {"status": "generated_not_reviewed", "files": files}
        path = run_dir / "report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return report, path, exit_code

    version = invoke(executable, ["--version"], run_dir, env, timeout)
    version["status"] = command_status(version)
    report["steps"]["version"] = version
    if version["status"] != "passed":
        report["offline_status"] = "unavailable" if version["status"] == "failed" else version["status"]
        return finish()
    match = re.fullmatch(r"(\d+\.\d+\.\d+(?:-[\w.-]+)?) \(Claude Code\)\s*", version["stdout"])
    if not match:
        version["status"] = report["offline_status"] = "unrecognized_output"
        return finish()
    report["version"] = match.group(1)

    validation = invoke(executable, ["plugin", "validate", str(candidate), "--strict", "--json"], run_dir, env, timeout)
    validation["status"] = command_status(validation)
    report["steps"]["validate"] = validation
    if validation["status"] in {"unsupported", "unavailable"}:
        report["offline_status"] = validation["status"]
        return finish()
    try:
        data = json.loads(validation["stdout"])
        success = data["success"]
        if not isinstance(success, bool):
            raise ValueError("success is not boolean")
    except (ValueError, KeyError, TypeError):
        validation["status"] = report["offline_status"] = "unrecognized_output"
        return finish()
    if not success or validation["exit_code"] != 0:
        validation["status"] = report["offline_status"] = "failed"
        exit_code = 1
        return finish()

    testing = invoke(executable, ["plugin", "test", str(candidate)], run_dir, env, timeout)
    testing["status"] = command_status(testing)
    report["steps"]["test"] = testing
    if testing["status"] != "passed":
        report["offline_status"] = testing["status"]
        exit_code = 1 if testing["status"] == "failed" else 2
        return finish()
    text = testing["stdout"] + testing["stderr"]
    passed = re.search(r"^\s*(\d+) pass\s*$", text, re.M)
    failed = re.search(r"^\s*(\d+) fail\s*$", text, re.M)
    ran = re.search(r"Ran (\d+) tests? across (\d+) files?\.", text)
    if not (passed and failed and ran):
        testing["status"] = report["offline_status"] = "unrecognized_output"
        return finish()
    counts = {"passed": int(passed[1]), "failed": int(failed[1]), "total": int(ran[1]), "files": int(ran[2])}
    testing["counts"] = counts
    if counts["failed"] or not counts["passed"] or counts["total"] != counts["passed"] or not counts["files"]:
        testing["status"] = report["offline_status"] = "failed"
        exit_code = 1
        return finish()
    report["offline_status"] = "passed"
    exit_code = 0
    return finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude", required=True, help="trusted executable path, or command on PATH")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/context-profile-checks")
    parser.add_argument("--plugin", type=Path, default=ROOT / "experiments/context-profile")
    parser.add_argument("--timeout", type=float, default=60, help="seconds per offline command")
    args = parser.parse_args()
    executable = shutil.which(args.claude)
    if not executable:
        print(json.dumps({"offline_status": "unavailable", "reason": "executable_not_found"}))
        return 2
    source = args.plugin.resolve()
    if not (source / ".claude-plugin/plugin.json").is_file() or args.timeout <= 0:
        parser.error("provide a plugin directory with a manifest and a positive timeout")
    output = args.output.resolve()
    if output == source or source in output.parents:
        parser.error("output must be outside the plugin source to avoid recursive copies")
    report, path, code = run_check(str(Path(executable).resolve()), source, output, args.timeout)
    print(json.dumps({"offline_status": report["offline_status"], "version": report.get("version"),
                      "target_types": report["target_types"]["status"], "report": str(path)}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
