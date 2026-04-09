#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p dist_release

APP="dist/TalkieType.app"
ZIP="dist_release/TalkieType-macos.zip"

rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
