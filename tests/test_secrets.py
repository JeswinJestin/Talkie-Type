from __future__ import annotations

import json
import logging
import os
import sys
import types
from pathlib import Path

import pytest

from voicetype.secrets import delete_groq_api_key, get_groq_api_key, set_groq_api_key


@pytest.fixture()
def logger() -> logging.Logger:
    l = logging.getLogger("secrets-tests")
    l.setLevel(logging.DEBUG)
    return l


def test_api_key_encrypted_roundtrip(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    keyring_mod = types.SimpleNamespace(get_password=get_password, set_password=set_password)
    monkeypatch.setitem(sys.modules, "keyring", keyring_mod)

    set_groq_api_key(api_key="gsk_secret", logger=logger, base_dir=tmp_path)
    raw = (tmp_path / "secrets.json").read_text(encoding="utf-8")
    assert "gsk_secret" not in raw

    parsed = json.loads(raw)
    assert parsed["v"] == 1
    assert isinstance(parsed["groq_api_key"], str)

    got = get_groq_api_key(logger=logger, base_dir=tmp_path)
    assert got == "gsk_secret"


def test_get_returns_empty_when_missing(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    keyring_mod = types.SimpleNamespace(get_password=lambda *_a, **_k: None, set_password=lambda *_a, **_k: None)
    monkeypatch.setitem(sys.modules, "keyring", keyring_mod)
    assert get_groq_api_key(logger=logger, base_dir=tmp_path) == ""


def test_master_key_regenerates_when_invalid(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    keyring_mod = types.SimpleNamespace(get_password=get_password, set_password=set_password)
    monkeypatch.setitem(sys.modules, "keyring", keyring_mod)

    store[("Talkie Type", "master_key_v1")] = "not-valid-base64"
    set_groq_api_key(api_key="gsk_secret", logger=logger, base_dir=tmp_path)
    assert get_groq_api_key(logger=logger, base_dir=tmp_path) == "gsk_secret"


def test_get_returns_empty_on_invalid_json(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))
    p = tmp_path / "secrets.json"
    p.write_text("{bad", encoding="utf-8")
    assert get_groq_api_key(logger=logger, base_dir=tmp_path) == ""


def test_delete_removes_file(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))
    set_groq_api_key(api_key="gsk_secret", logger=logger, base_dir=tmp_path)
    assert (tmp_path / "secrets.json").exists()
    delete_groq_api_key(logger=logger, base_dir=tmp_path)
    assert not (tmp_path / "secrets.json").exists()


def test_master_key_reuse_when_valid(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}
    calls = {"set": 0}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        calls["set"] += 1
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))

    set_groq_api_key(api_key="first", logger=logger, base_dir=tmp_path)
    first_master = store[("Talkie Type", "master_key_v1")]
    set_groq_api_key(api_key="second", logger=logger, base_dir=tmp_path)
    assert store[("Talkie Type", "master_key_v1")] == first_master
    assert calls["set"] == 1


def test_get_returns_empty_when_token_missing(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=lambda *_a, **_k: None, set_password=lambda *_a, **_k: None))
    (tmp_path / "secrets.json").write_text('{"v":1}\n', encoding="utf-8")
    assert get_groq_api_key(logger=logger, base_dir=tmp_path) == ""


def test_delete_handles_fsync_errors(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str) -> str | None:
        return store.get((service, username))

    def set_password(service: str, username: str, password: str) -> None:
        store[(service, username)] = password

    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=get_password, set_password=set_password))
    set_groq_api_key(api_key="gsk_secret", logger=logger, base_dir=tmp_path)

    monkeypatch.setattr(os, "open", lambda *_a, **_k: 123, raising=True)
    monkeypatch.setattr(os, "fsync", lambda *_a, **_k: (_ for _ in ()).throw(OSError("x")), raising=True)
    monkeypatch.setattr(os, "close", lambda *_a, **_k: (_ for _ in ()).throw(OSError("x")), raising=True)
    delete_groq_api_key(logger=logger, base_dir=tmp_path)
