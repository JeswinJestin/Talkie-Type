from __future__ import annotations

import argparse
import subprocess
import sys


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _capture(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        _run([sys.executable, "-m", "pytest", "-q"])

    status = _capture(["git", "status", "--porcelain"])
    if status:
        raise SystemExit("Working tree is not clean. Commit or stash changes before shipping.")

    if args.tag:
        tag = args.tag
    else:
        from voicetype import __version__

        tag = f"v{__version__}"

    existing = _capture(["git", "tag", "--list", tag])
    if existing:
        raise SystemExit(f"Tag already exists: {tag}")

    _run(["git", "tag", tag])
    _run(["git", "push", "origin", tag])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
