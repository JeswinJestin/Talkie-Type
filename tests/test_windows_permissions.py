from __future__ import annotations

import os

import pytest

import voicetype.windows_permissions as wp


def test_open_microphone_settings_noop_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp.os, "name", "posix", raising=False)
    called = {"n": 0}
    monkeypatch.setattr(wp.os, "startfile", lambda *_a, **_k: called.__setitem__("n", called["n"] + 1), raising=False)
    wp.open_microphone_privacy_settings()
    assert called["n"] == 0


def test_open_microphone_settings_uses_ms_settings_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp.os, "name", "nt", raising=False)
    captured: list[str] = []
    monkeypatch.setattr(wp.os, "startfile", lambda arg: captured.append(arg), raising=False)
    wp.open_microphone_privacy_settings()
    assert captured == ["ms-settings:privacy-microphone"]
