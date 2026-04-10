from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _venv_python() -> str:
    root = _repo_root()
    if os.name == "nt":
        p = root / ".venv" / "Scripts" / "python.exe"
        if p.exists():
            return str(p)
    p = root / ".venv" / "bin" / "python"
    if p.exists():
        return str(p)
    return sys.executable


def _config_path(python: str) -> Path:
    out = subprocess.check_output([python, "-c", "from voicetype.config import config_path; print(config_path())"], text=True).strip()
    return Path(out)


def _user_data_dir(python: str) -> Path:
    out = subprocess.check_output([python, "-c", "from voicetype.storage import user_data_dir; print(user_data_dir())"], text=True).strip()
    return Path(out)


def _log_file(python: str) -> Path:
    out = subprocess.check_output([python, "-c", "from voicetype.logging_setup import log_file_path; print(log_file_path())"], text=True).strip()
    return Path(out)


def _write_config(cfg_path: Path, *, recording_path: Path) -> None:
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}

    raw["hands_free_enabled"] = True
    raw["toggle_hotkey"] = "ctrl+shift+windows+u"
    raw["hold_hotkey"] = "ctrl+alt+u"
    raw["recording_output_path"] = str(recording_path)

    cfg_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def _send_hotkey() -> None:
    import keyboard

    combos = ["ctrl+shift+windows+u", "ctrl+shift+left windows+u"]
    last = None
    for combo in combos:
        try:
            keyboard.send(combo)
            return
        except Exception as e:
            last = e
    raise RuntimeError(f"Unable to send hotkey: {last}")


def main() -> int:
    python = _venv_python()
    doctor = subprocess.run([python, "scripts/doctor.py", "--strict"], cwd=str(_repo_root()), capture_output=True, text=True)
    if doctor.returncode != 0:
        sys.stdout.write(doctor.stdout)
        sys.stderr.write(doctor.stderr)
        raise SystemExit("Doctor check failed; fix microphone_stream before running smoke hotkey test.")

    cfg_path = _config_path(python)
    base = _user_data_dir(python)
    recording_path = base / "recordings" / "smoke.wav"
    recording_path.parent.mkdir(parents=True, exist_ok=True)
    if recording_path.exists():
        try:
            recording_path.unlink()
        except Exception:
            pass

    _write_config(cfg_path, recording_path=recording_path)

    log_path = _log_file(python)
    if log_path.exists():
        try:
            log_path.unlink()
        except Exception:
            pass

    proc = subprocess.Popen([python, "-m", "voicetype", "--background"], cwd=str(_repo_root()))
    try:
        time.sleep(2.0)

        t0 = time.time()
        _send_hotkey()

        deadline = t0 + 6.0
        sizes: list[int] = []
        while time.time() < deadline:
            if recording_path.exists():
                try:
                    sizes.append(recording_path.stat().st_size)
                except Exception:
                    pass
            time.sleep(0.5)

        if not sizes:
            raise SystemExit(f"Recording file was not created: {recording_path}")

        grew = any(b > a for a, b in zip(sizes, sizes[1:]))
        if not grew:
            raise SystemExit(f"Recording file did not grow over time: sizes={sizes}")

        _send_hotkey()
        time.sleep(1.0)

        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="ignore")
            if "ERROR" in text or "Traceback" in text:
                raise SystemExit("Errors found in log file after hotkey recording.")

    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=5.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    print(f"OK: created {recording_path} and size grew (samples={sizes[:5]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
