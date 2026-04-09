from __future__ import annotations

import builtins
import logging
from pathlib import Path

import pytest

from voicetype.api_key import ensure_groq_api_key


def test_api_key_reads_existing_env_file(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text('GROQ_API_KEY="abc"\n', encoding="utf-8")
    key = ensure_groq_api_key(env_path=p, logger=logging.getLogger("t"))
    assert key == "abc"


def test_api_key_returns_empty_when_tkinter_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter" or name.startswith("tkinter."):
            raise ModuleNotFoundError(name)
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    p = tmp_path / ".env"
    key = ensure_groq_api_key(env_path=p, logger=logging.getLogger("t"))
    assert key == ""


def test_api_key_prompts_and_writes_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    tkinter_mod = types.ModuleType("tkinter")
    simpledialog_mod = types.ModuleType("tkinter.simpledialog")

    class FakeTk:
        def withdraw(self) -> None:
            return None

        def destroy(self) -> None:
            return None

    def askstring(_title: str, _prompt: str, show: str | None = None) -> str:
        return "gsk_test"

    tkinter_mod.Tk = FakeTk  # type: ignore[attr-defined]
    tkinter_mod.simpledialog = simpledialog_mod  # type: ignore[attr-defined]
    simpledialog_mod.askstring = askstring  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "tkinter", tkinter_mod)
    monkeypatch.setitem(sys.modules, "tkinter.simpledialog", simpledialog_mod)

    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))

    p = tmp_path / ".env"
    key = ensure_groq_api_key(env_path=p, logger=logging.getLogger("t"))
    assert key == "gsk_test"
    assert 'GROQ_API_KEY="gsk_test"' in p.read_text(encoding="utf-8")


def test_api_key_returns_empty_when_env_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    tkinter_mod = types.ModuleType("tkinter")
    simpledialog_mod = types.ModuleType("tkinter.simpledialog")

    class FakeTk:
        def withdraw(self) -> None:
            return None

        def destroy(self) -> None:
            return None

    simpledialog_mod.askstring = lambda *_a, **_k: "gsk_test"  # type: ignore[attr-defined]
    tkinter_mod.Tk = FakeTk  # type: ignore[attr-defined]
    tkinter_mod.simpledialog = simpledialog_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tkinter", tkinter_mod)
    monkeypatch.setitem(sys.modules, "tkinter.simpledialog", simpledialog_mod)

    p = tmp_path / ".env"

    def boom(*_a, **_k):
        raise OSError("x")

    monkeypatch.setattr(Path, "write_text", boom, raising=True)
    assert ensure_groq_api_key(env_path=p, logger=logging.getLogger("t")) == ""


def test_api_key_returns_empty_when_user_cancels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    tkinter_mod = types.ModuleType("tkinter")
    simpledialog_mod = types.ModuleType("tkinter.simpledialog")

    class FakeTk:
        def withdraw(self) -> None:
            return None

        def destroy(self) -> None:
            return None

    simpledialog_mod.askstring = lambda *_a, **_k: ""  # type: ignore[attr-defined]
    tkinter_mod.Tk = FakeTk  # type: ignore[attr-defined]
    tkinter_mod.simpledialog = simpledialog_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tkinter", tkinter_mod)
    monkeypatch.setitem(sys.modules, "tkinter.simpledialog", simpledialog_mod)

    p = tmp_path / ".env"
    assert ensure_groq_api_key(env_path=p, logger=logging.getLogger("t")) == ""


def test_api_key_destroy_exception_is_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    tkinter_mod = types.ModuleType("tkinter")
    simpledialog_mod = types.ModuleType("tkinter.simpledialog")

    class FakeTk:
        def withdraw(self) -> None:
            return None

        def destroy(self) -> None:
            raise RuntimeError("x")

    simpledialog_mod.askstring = lambda *_a, **_k: "gsk_test"  # type: ignore[attr-defined]
    tkinter_mod.Tk = FakeTk  # type: ignore[attr-defined]
    tkinter_mod.simpledialog = simpledialog_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tkinter", tkinter_mod)
    monkeypatch.setitem(sys.modules, "tkinter.simpledialog", simpledialog_mod)

    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))

    p = tmp_path / ".env"
    key = ensure_groq_api_key(env_path=p, logger=logging.getLogger("t"))
    assert key == "gsk_test"
