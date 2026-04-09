from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


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


def _check_python() -> CheckResult:
    ver = sys.version.split()[0]
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 10)
    return CheckResult("python", ok, f"{ver} ({sys.executable})")


def _check_import(mod: str) -> CheckResult:
    try:
        __import__(mod)
        return CheckResult(f"import:{mod}", True, "ok")
    except Exception as e:
        return CheckResult(f"import:{mod}", False, f"{type(e).__name__}: {e}")


def _check_env_key() -> CheckResult:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return CheckResult("GROQ_API_KEY", True, "present (env)")
    return CheckResult("GROQ_API_KEY", False, "missing (set in Settings or .env)")


def _check_keyring() -> CheckResult:
    try:
        import keyring

        backend = keyring.get_keyring()
        return CheckResult("keyring", True, f"{type(backend).__name__}")
    except Exception as e:
        return CheckResult("keyring", False, f"{type(e).__name__}: {e}")


def _check_audio_device() -> CheckResult:
    try:
        import sounddevice as sd

        device = sd.query_devices(kind="input")
        name = device.get("name") if isinstance(device, dict) else str(device)
        return CheckResult("microphone", True, f"default input: {name}")
    except Exception as e:
        return CheckResult("microphone", False, f"{type(e).__name__}: {e}")


def _check_audio_open() -> CheckResult:
    try:
        import sounddevice as sd

        def cb(indata, frames, time_info, status):
            return None

        rates: list[int] = []
        try:
            info = sd.query_devices(kind="input")
            default_rate = info.get("default_samplerate") if isinstance(info, dict) else None
            if default_rate:
                rates.append(int(float(default_rate)))
        except Exception:
            pass
        rates.extend([48000, 44100, 16000])

        seen: set[int] = set()
        attempts: list[int] = []
        for r in rates:
            if r <= 0 or r in seen:
                continue
            seen.add(r)
            attempts.append(r)

        last: Exception | None = None
        for rate in attempts:
            try:
                stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32", callback=cb)
                stream.start()
                time.sleep(0.05)
                stream.stop()
                stream.close()
                return CheckResult("microphone_stream", True, f"opened at {rate} Hz")
            except Exception as e:
                last = e
                try:
                    stream.close()  # type: ignore[name-defined]
                except Exception:
                    pass

        if last is not None:
            return CheckResult("microphone_stream", False, f"{type(last).__name__}: {last}")
        return CheckResult("microphone_stream", False, "unable to open input stream")
    except Exception as e:
        return CheckResult("microphone_stream", False, f"{type(e).__name__}: {e}")


def _check_storage_paths() -> CheckResult:
    try:
        from voicetype.storage import transcripts_dir, user_data_dir

        base = user_data_dir()
        tdir = transcripts_dir(base)
        base.mkdir(parents=True, exist_ok=True)
        tdir.mkdir(parents=True, exist_ok=True)
        return CheckResult("storage", True, f"base={base} transcripts={tdir}")
    except Exception as e:
        return CheckResult("storage", False, f"{type(e).__name__}: {e}")


def _check_pyinstaller() -> CheckResult:
    try:
        import PyInstaller  # type: ignore[import-not-found]

        return CheckResult("pyinstaller", True, getattr(PyInstaller, "__version__", "installed"))
    except Exception as e:
        return CheckResult("pyinstaller", False, f"{type(e).__name__}: {e}")


def _print(results: list[CheckResult]) -> None:
    width = max(len(r.name) for r in results)
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"{r.name.ljust(width)}  {status}  {r.detail}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any failure")
    parser.add_argument("--require-key", action="store_true", help="Fail if GROQ_API_KEY is not configured")
    args = parser.parse_args()

    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print("Talkie Type doctor")
    print(f"platform: {platform.platform()}")
    print(f"python:   {sys.version.split()[0]} ({sys.executable})")
    vp = _venv_python()
    if vp:
        print(f"venv:     {vp}")
    else:
        print("venv:     not found (.venv)")
    print("")

    checks = [
        _check_python(),
        _check_import("voicetype"),
        _check_import("groq"),
        _check_import("sounddevice"),
        _check_import("keyboard"),
        _check_import("pystray"),
        _check_import("PIL"),
        _check_import("pyautogui"),
        _check_keyring(),
        _check_storage_paths(),
        _check_audio_device(),
        _check_audio_open(),
        _check_env_key(),
        _check_pyinstaller(),
    ]

    _print(checks)

    failures: list[CheckResult] = []
    for c in checks:
        if c.ok:
            continue
        if c.name == "GROQ_API_KEY" and not args.require_key:
            continue
        failures.append(c)
    if failures:
        print("")
        print("Hints:")
        for f in failures:
            if f.name == "GROQ_API_KEY":
                print("- Open the app -> Settings -> paste your Groq key (stored encrypted locally).")
            if f.name == "microphone":
                if os.name == "nt":
                    print("- Windows Settings -> Privacy & security -> Microphone -> allow access.")
                else:
                    print("- Check system mic permissions and ensure a default input device exists.")
            if f.name == "microphone_stream":
                if os.name == "nt":
                    print("- Close apps that may be using the mic (Teams/Zoom/Discord/browser).")
                    print("- Sound settings -> Input -> pick the correct microphone as default.")
                    print("- Microphone Properties -> Advanced -> disable Exclusive Mode and retry.")
                else:
                    print("- Close other apps using the mic and retry.")
                    print("- Verify system audio permissions and PortAudio/ALSA/Pulse setup.")
            if f.name.startswith("import:"):
                print("- Install dependencies: pip install -r requirements.txt -r requirements-dev.txt")
        if args.strict:
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
