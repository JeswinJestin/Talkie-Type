from __future__ import annotations

from voicetype.state_machine import ToggleStateMachine


def test_toggle_state_machine_basic_flow() -> None:
    sm = ToggleStateMachine()
    assert sm.state() == "idle"

    d1 = sm.toggle()
    assert d1.action == "start"
    assert sm.state() == "recording"

    d2 = sm.toggle()
    assert d2.action == "stop"
    assert sm.state() == "processing"

    d3 = sm.toggle()
    assert d3.action == "ignore"
    assert sm.state() == "processing"

    sm.mark_idle()
    assert sm.state() == "idle"

    sm.mark_recording()
    assert sm.state() == "recording"

    sm.mark_processing()
    assert sm.state() == "processing"
