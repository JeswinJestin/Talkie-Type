from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path

import pytest

import voicetype.storage as storage
from voicetype.storage import TranscriptRecord, TranscriptStore, daily_transcript_path, transcripts_dir


@pytest.fixture()
def logger() -> logging.Logger:
    logger = logging.getLogger("voicetype-tests")
    logger.setLevel(logging.DEBUG)
    return logger


def test_storage_appends_jsonl_with_expected_schema(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    record = TranscriptRecord(ts=1680001234567, text="hello world")
    store.append(record)

    p = daily_transcript_path(date.today(), tmp_path)
    assert p.exists()
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj == {"ts": 1680001234567, "text": "hello world"}


def test_storage_loads_existing_day_file_on_start(tmp_path: Path, logger: logging.Logger) -> None:
    p = daily_transcript_path(date.today(), tmp_path)
    transcripts_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    p.write_text('{"ts":2,"text":"b"}\n\n{"ts":1,"text":"a"}\n', encoding="utf-8")
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    recs = store.records_today()
    assert recs[0].ts == 2
    assert recs[1].ts == 1


def test_storage_rewrite_today_overwrites_file_atomically(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    store.append(TranscriptRecord(ts=1, text="a"))
    store.rewrite_today([TranscriptRecord(ts=1, text="A"), TranscriptRecord(ts=2, text="B")])
    p = daily_transcript_path(date.today(), tmp_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"ts": 1, "text": "A"}
    assert json.loads(lines[1]) == {"ts": 2, "text": "B"}


def test_storage_atomicity_leaves_original_intact_on_replace_failure(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    p = daily_transcript_path(date.today(), tmp_path)
    transcripts_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    p.write_text('{"ts":1,"text":"a"}\n', encoding="utf-8")

    pending = p.with_suffix(p.suffix + ".pending")

    def boom(_src: str, _dst: str) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError):
        store.append(TranscriptRecord(ts=2, text="b"))

    assert p.read_text(encoding="utf-8") == '{"ts":1,"text":"a"}\n'
    assert pending.exists()


def test_storage_calls_fsync_before_ack(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)

    called = {"fsync": 0}

    def fsync(fd: int) -> None:
        called["fsync"] += 1

    monkeypatch.setattr(os, "fsync", fsync)
    store.append(TranscriptRecord(ts=3, text="c"))
    assert called["fsync"] >= 1


def test_storage_integration_1000_sequential_appends(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    for i in range(1000):
        store.append(TranscriptRecord(ts=1_700_000_000_000 + i, text=f"t{i}"))

    p = daily_transcript_path(date.today(), tmp_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1000
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["ts"] == 1_700_000_000_000
    assert parsed[-1]["ts"] == 1_700_000_000_999


def test_retention_purges_old_files(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=1, logger=logger)
    base = transcripts_dir(tmp_path)
    base.mkdir(parents=True, exist_ok=True)
    old = base / "2000-01-01.jsonl"
    old.write_text('{"ts":1,"text":"x"}\n', encoding="utf-8")
    pending = base / "2000-01-01.jsonl.pending"
    pending.write_text("x", encoding="utf-8")
    os.utime(pending, (946684800, 946684800))
    store.purge_old_files()
    assert not old.exists()
    assert not pending.exists()


def test_parse_day_from_filename_invalid_returns_none(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    assert store._parse_day_from_filename("not-a-date.jsonl") is None  # type: ignore[attr-defined]
    assert store._parse_day_from_filename("2020-13-01.jsonl") is None  # type: ignore[attr-defined]
    assert store._parse_day_from_filename("2020-01-01.txt") is None  # type: ignore[attr-defined]


def test_load_today_invalid_json_is_ignored(tmp_path: Path, logger: logging.Logger) -> None:
    p = daily_transcript_path(date.today(), tmp_path)
    transcripts_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    p.write_text('{"ts":1,"text":"a"}\n{bad\n', encoding="utf-8")
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    assert store.records_today() == []


def test_purge_handles_stat_and_unlink_errors(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=1, logger=logger)
    base = transcripts_dir(tmp_path)
    base.mkdir(parents=True, exist_ok=True)
    pending = base / "2000-01-01.jsonl.pending"
    pending.write_text("x", encoding="utf-8")
    os.utime(pending, (946684800, 946684800))

    orig_stat = Path.stat

    def stat(self: Path, *args, **kwargs):
        if self == pending:
            raise OSError("stat failed")
        return orig_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat, raising=True)

    orig_unlink = Path.unlink

    def unlink(self: Path, *args, **kwargs):
        raise OSError("unlink failed")

    monkeypatch.setattr(Path, "unlink", unlink, raising=True)
    store.purge_old_files()

    monkeypatch.setattr(Path, "unlink", orig_unlink, raising=True)
    store.purge_old_files()


def test_user_data_dir_falls_back_when_appdata_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    p = storage.user_data_dir()
    assert p.name in {".talkietype", ".voicetype", "TalkieType", "VoiceType"}


def test_user_data_dir_uses_appdata_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    p = storage.user_data_dir()
    assert p in {tmp_path / "TalkieType", tmp_path / "VoiceType"}


def test_subscribers_are_called_and_exceptions_are_swallowed(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    seen: list[int] = []

    def ok(r: TranscriptRecord) -> None:
        seen.append(r.ts)

    def boom(_r: TranscriptRecord) -> None:
        raise RuntimeError("x")

    store.subscribe(ok)
    store.subscribe(boom)
    store.append(TranscriptRecord(ts=10, text="x"))
    assert seen == [10]


def test_rollover_resets_today_cache(tmp_path: Path, logger: logging.Logger) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    store.append(TranscriptRecord(ts=1, text="a"))
    assert store.records_today()
    p = daily_transcript_path(date.today(), tmp_path)
    p.unlink(missing_ok=True)
    store._today = date(2000, 1, 1)  # type: ignore[assignment]
    assert store.records_today() == []


def test_fsync_dir_best_effort(tmp_path: Path, logger: logging.Logger, monkeypatch: pytest.MonkeyPatch) -> None:
    store = TranscriptStore(base_dir=tmp_path, retention_days=90, logger=logger)
    called = {"open": 0, "fsync": 0, "close": 0}

    def fake_open(_p: str, _flags: int) -> int:
        called["open"] += 1
        return 123

    def fake_fsync(_fd: int) -> None:
        called["fsync"] += 1

    def fake_close(_fd: int) -> None:
        called["close"] += 1

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fsync", fake_fsync)
    monkeypatch.setattr(os, "close", fake_close)
    store._fsync_dir(tmp_path)  # type: ignore[attr-defined]
    assert called["open"] == 1
    assert called["fsync"] == 1
    assert called["close"] == 1
