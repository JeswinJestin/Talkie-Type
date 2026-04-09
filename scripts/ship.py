from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _capture(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _venv_python() -> str | None:
    root = _repo_root()
    candidates = []
    if os.name == "nt":
        candidates.append(root / ".venv" / "Scripts" / "python.exe")
    candidates.append(root / ".venv" / "bin" / "python")
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _ensure_pytest(python: str) -> None:
    try:
        subprocess.run([python, "-c", "import pytest"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except Exception:
        pass

    root = _repo_root()
    req = root / "requirements-dev.txt"
    if req.exists():
        _run([python, "-m", "pip", "install", "-r", str(req)])
        return
    raise SystemExit("pytest is not installed. Install dev dependencies (requirements-dev.txt) and retry.")

def _ensure_deps(python: str) -> None:
    root = _repo_root()
    req = root / "requirements.txt"
    dev = root / "requirements-dev.txt"
    if req.exists():
        _run([python, "-m", "pip", "install", "-r", str(req)])
    if dev.exists():
        _run([python, "-m", "pip", "install", "-r", str(dev)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--ensure-deps", action="store_true")
    args = parser.parse_args()

    python = _venv_python() or sys.executable
    if args.ensure_deps:
        _ensure_deps(python)
    if not args.skip_tests:
        _ensure_pytest(python)
        _run([python, "-m", "pytest", "-q"])

    status = _capture(["git", "status", "--porcelain"])
    if status:
        raise SystemExit("Working tree is not clean. Commit or stash changes before shipping.")

    if args.tag:
        tag = args.tag
    else:
        out = subprocess.check_output([python, "-c", "import voicetype; print(voicetype.__version__)"], text=True).strip()

        tag = f"v{out}"

    existing = _capture(["git", "tag", "--list", tag])
    if existing:
        raise SystemExit(f"Tag already exists: {tag}")

    _run(["git", "tag", tag])
    _run(["git", "push", "origin", tag])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
