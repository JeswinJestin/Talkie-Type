#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

python -m PyInstaller --noconsole --name TalkieType --clean --noconfirm voicetype/__main__.py
