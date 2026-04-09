from __future__ import annotations

from voicetype.time_utils import unix_ms_monotonic


def test_unix_ms_monotonic_is_strictly_increasing() -> None:
    values = [unix_ms_monotonic() for _ in range(500)]
    assert all(b > a for a, b in zip(values, values[1:]))
