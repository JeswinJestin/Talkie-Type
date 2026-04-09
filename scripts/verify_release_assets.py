from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request


def _capture(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _infer_repo() -> str:
    url = _capture(["git", "remote", "get-url", "origin"])
    m = re.search(r"[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit("Unable to infer GitHub repo from origin remote.")
    return f"{m.group('owner')}/{m.group('repo')}"


def _request_json(url: str, token: str) -> object:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--require", action="append", default=[])
    args = parser.parse_args()

    repo = args.repo or os.environ.get("GITHUB_REPOSITORY") or _infer_repo()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not token:
        raise SystemExit("Missing GITHUB_TOKEN or GH_TOKEN.")

    data = _request_json(f"https://api.github.com/repos/{repo}/releases/tags/{args.tag}", token)
    if not isinstance(data, dict):
        raise SystemExit("Unexpected GitHub API response.")
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise SystemExit("Release has no assets list.")

    names = {a.get("name") for a in assets if isinstance(a, dict)}
    required = set(args.require)
    missing = sorted([n for n in required if n not in names])
    if missing:
        raise SystemExit(f"Missing release assets: {missing}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
