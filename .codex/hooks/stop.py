#!/usr/bin/env python3
"""Codex Stop hook: 턴 종료 시 ruff와 pytest를 돌리고, 실패하면 한 번 더 작업하게 한다 (ADR-014)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (명령, 통과로 보는 exit code). pytest 5 = 수집된 테스트 없음.
CHECKS = [
    (["ruff", "check", "."], {0}),
    ([sys.executable, "-m", "pytest", "-q"], {0, 5}),
]

MAX_OUTPUT_CHARS = 1500


def run_checks(root: Path, checks) -> list[str]:
    failures = []
    for cmd, ok_codes in checks:
        label = "$ " + " ".join(cmd)
        try:
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        except FileNotFoundError:
            failures.append(f"{label}\n명령을 찾을 수 없음")
            continue
        if r.returncode not in ok_codes:
            output = (r.stdout + r.stderr).strip()[-MAX_OUTPUT_CHARS:]
            failures.append(f"{label} (exit {r.returncode})\n{output}")
    return failures


def decide(payload: dict, root: Path, checks) -> dict | None:
    # 이미 hook이 계속 진행시킨 턴이면 무한 루프를 막기 위해 통과시킨다.
    if payload.get("stop_hook_active"):
        return None
    failures = run_checks(root, checks)
    if not failures:
        return None
    reason = "Stop hook 검사 실패. 아래 오류를 고친 뒤 끝내라.\n\n" + "\n\n".join(failures)
    return {"decision": "block", "reason": reason}


def main() -> int:
    result = decide(json.load(sys.stdin), ROOT, CHECKS)
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
