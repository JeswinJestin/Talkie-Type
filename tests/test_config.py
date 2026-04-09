from __future__ import annotations

import os
from pathlib import Path

from voicetype.config import AppConfig, config_path, load_config, save_config


def test_config_roundtrip_creates_and_persists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    cfg = load_config()
    assert cfg.toggle_hotkey

    updated = AppConfig.from_dict({**cfg.to_dict(), "toggle_hotkey": "f6", "retention_days": 7})
    save_config(updated)
    reloaded = load_config()
    assert reloaded.toggle_hotkey == "f6"
    assert reloaded.retention_days == 7
    assert config_path().exists()


def test_config_handles_invalid_json_and_non_dict(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not json", encoding="utf-8")
    cfg = load_config()
    assert isinstance(cfg, AppConfig)

    p.write_text('["not a dict"]', encoding="utf-8")
    cfg2 = load_config()
    assert isinstance(cfg2, AppConfig)


def test_config_path_falls_back_when_appdata_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    p = config_path()
    assert p.name == "config.json"
