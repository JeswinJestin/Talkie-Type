from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest

import voicetype.recorder as recorder_mod


class _FakeStream:
    last: "_FakeStream | None" = None

    def __init__(self, *, samplerate: int, channels: int, dtype: str, callback, device=None):
        self.samplerate = int(samplerate)
        self.channels = int(channels)
        self.dtype = dtype
        self.callback = callback
        self.device = device
        self.started = False
        _FakeStream.last = self

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def close(self) -> None:
        return None

    def emit_seconds(self, seconds: float) -> None:
        assert self.started
        total_frames = int(self.samplerate * seconds)
        chunk = 1024
        t = 0
        while t < total_frames:
            frames = min(chunk, total_frames - t)
            x = np.zeros((frames, self.channels), dtype=np.float32)
            for i in range(frames):
                x[i, 0] = float(math.sin(2 * math.pi * 220.0 * ((t + i) / self.samplerate)))
            self.callback(x, frames, None, None)
            t += frames


@pytest.mark.parametrize("seconds", [1.0, 5.0, 30.0])
def test_recorder_writes_valid_wav_for_durations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    class _Default:
        device = (0, 0)

    def query_hostapis():
        return []

    def query_devices(*args, **kwargs):
        if args and isinstance(args[0], int):
            return {"default_samplerate": 16000.0}
        return {"default_samplerate": 16000.0, "max_input_channels": 1}

    monkeypatch.setattr(recorder_mod.sd, "default", _Default())
    monkeypatch.setattr(recorder_mod.sd, "query_hostapis", query_hostapis)
    monkeypatch.setattr(recorder_mod.sd, "query_devices", query_devices)
    monkeypatch.setattr(recorder_mod.sd, "InputStream", lambda **kw: _FakeStream(**kw))

    rec = recorder_mod.MicrophoneRecorder(sample_rate_hz=16000, channels=1, vad_rms_threshold=0.001, logger=recorder_mod.logging.getLogger("t"))  # type: ignore[attr-defined]
    rec.start()
    assert _FakeStream.last is not None
    _FakeStream.last.emit_seconds(seconds)

    out = tmp_path / "out.wav"
    stats = rec.stop_to_wav(out)
    assert out.exists()
    assert stats.frames > 0
    assert stats.sample_rate_hz in {16000, 44100, 48000}
    assert stats.duration_s > 0.9 * seconds

    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == stats.sample_rate_hz
        assert wf.getnframes() == stats.frames
