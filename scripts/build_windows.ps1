$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -Path (Resolve-Path "..")

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
  python -m venv .venv
}

.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt

.\\.venv\\Scripts\\python.exe -m PyInstaller --noconsole --name TalkieType --clean --noconfirm --collect-all pystray --collect-all PIL voicetype\\__main__.py
