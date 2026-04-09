from __future__ import annotations

import types

import pytest

import voicetype.hotkeys as hotkeys


def test_parse_combo_normalizes() -> None:
    assert hotkeys.parse_combo("Ctrl+Space") == {"ctrl", "space"}
    assert hotkeys.parse_combo("control+  space") == {"ctrl", "space"}
    assert hotkeys.parse_combo("CTRL+SHIFT+R") == {"ctrl", "shift", "r"}


def test_toggle_hotkey_listener_registers_and_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    fake_kb = types.SimpleNamespace()

    def add_hotkey(hk, fn, **kwargs):
        calls.append(("add_hotkey", hk))
        return "handle"

    def remove_hotkey(handle):
        calls.append(("remove_hotkey", handle))

    fake_kb.add_hotkey = add_hotkey
    fake_kb.remove_hotkey = remove_hotkey
    monkeypatch.setattr(hotkeys, "keyboard", fake_kb)

    toggled = {"n": 0}

    def on_toggle():
        toggled["n"] += 1

    t = hotkeys.ToggleHotkeyListener(hotkey="ctrl+shift+r", logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None), on_toggle=on_toggle)  # type: ignore[arg-type]
    t.start()
    t.update_hotkey("f6")
    t.stop()

    assert ("add_hotkey", "ctrl+shift+r") in calls
    assert ("remove_hotkey", "handle") in calls
    assert ("add_hotkey", "f6") in calls


def test_hold_hotkey_listener_hold_mode_transitions(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            calls.append("unhook")

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())

    started = {"n": 0}
    stopped = {"n": 0}
    toggled = {"n": 0}

    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=False),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: started.__setitem__("n", started["n"] + 1),
        on_stop=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        on_toggle=lambda: toggled.__setitem__("n", toggled["n"] + 1),
    )

    listener.start()

    ev = types.SimpleNamespace(event_type="down", name="ctrl")
    listener._handle_event(ev)  # type: ignore[attr-defined]
    ev = types.SimpleNamespace(event_type="down", name="space")
    listener._handle_event(ev)  # type: ignore[attr-defined]
    ev = types.SimpleNamespace(event_type="up", name="space")
    listener._handle_event(ev)  # type: ignore[attr-defined]

    listener.stop()

    assert started["n"] == 1
    assert stopped["n"] == 1
    assert toggled["n"] == 0


@pytest.mark.parametrize("seconds,repeat_hz", [(1, 30), (5, 30), (30, 30)])
def test_hold_hotkey_listener_hold_mode_ignores_repeated_keydown(monkeypatch: pytest.MonkeyPatch, seconds: int, repeat_hz: int) -> None:
    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            return None

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())

    started = {"n": 0}
    stopped = {"n": 0}

    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=False),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: started.__setitem__("n", started["n"] + 1),
        on_stop=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        on_toggle=lambda: None,
    )

    listener._handle_event(types.SimpleNamespace(event_type="down", name="ctrl"))  # type: ignore[attr-defined]
    listener._handle_event(types.SimpleNamespace(event_type="down", name="space"))  # type: ignore[attr-defined]
    assert started["n"] == 1
    assert stopped["n"] == 0

    repeats = int(seconds * repeat_hz)
    for _ in range(repeats):
        listener._handle_event(types.SimpleNamespace(event_type="down", name="space"))  # type: ignore[attr-defined]
    assert started["n"] == 1
    assert stopped["n"] == 0

    listener._handle_event(types.SimpleNamespace(event_type="up", name="space"))  # type: ignore[attr-defined]
    assert stopped["n"] == 1


def test_hold_hotkey_listener_hands_free_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            return None

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())

    toggled = {"n": 0}

    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=True),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: None,
        on_stop=lambda: None,
        on_toggle=lambda: toggled.__setitem__("n", toggled["n"] + 1),
    )

    ev = types.SimpleNamespace(event_type="down", name="ctrl")
    listener._handle_event(ev)  # type: ignore[attr-defined]
    ev = types.SimpleNamespace(event_type="down", name="space")
    listener._handle_event(ev)  # type: ignore[attr-defined]
    ev = types.SimpleNamespace(event_type="up", name="space")
    listener._handle_event(ev)  # type: ignore[attr-defined]

    ev = types.SimpleNamespace(event_type="down", name="space")
    listener._handle_event(ev)  # type: ignore[attr-defined]
    assert toggled["n"] == 2


def test_hold_hotkey_listener_update_config_resets_state(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            return None

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())

    started = {"n": 0}
    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=False),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: started.__setitem__("n", started["n"] + 1),
        on_stop=lambda: None,
        on_toggle=lambda: None,
    )

    listener._handle_event(types.SimpleNamespace(event_type="down", name="ctrl"))  # type: ignore[attr-defined]
    listener._handle_event(types.SimpleNamespace(event_type="down", name="space"))  # type: ignore[attr-defined]
    assert started["n"] == 1

    listener.update_config(hotkeys.HotkeyConfig(hold_combo="ctrl+shift+r", hands_free_enabled=False))
    listener._handle_event(types.SimpleNamespace(event_type="down", name="r"))  # type: ignore[attr-defined]
    assert started["n"] == 1


def test_hold_hotkey_listener_stop_is_best_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            raise RuntimeError("x")

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())
    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=False),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: None,
        on_stop=lambda: None,
        on_toggle=lambda: None,
    )
    listener.start()
    listener.stop()
    listener.stop()


def test_hold_hotkey_listener_callback_exceptions_are_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKeyboard:
        KEY_DOWN = "down"
        KEY_UP = "up"

        def hook(self, _fn):
            return "hook"

        def unhook(self, _handle):
            return None

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())
    listener = hotkeys.HoldHotkeyListener(
        cfg=hotkeys.HotkeyConfig(hold_combo="ctrl+space", hands_free_enabled=True),
        logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None),
        on_start=lambda: (_ for _ in ()).throw(RuntimeError("x")),
        on_stop=lambda: (_ for _ in ()).throw(RuntimeError("x")),
        on_toggle=lambda: (_ for _ in ()).throw(RuntimeError("x")),
    )
    listener._handle_event(types.SimpleNamespace(event_type="down", name="ctrl"))  # type: ignore[attr-defined]
    listener._handle_event(types.SimpleNamespace(event_type="down", name="space"))  # type: ignore[attr-defined]
    listener._handle_event(types.SimpleNamespace(event_type="up", name="space"))  # type: ignore[attr-defined]


def test_toggle_hotkey_listener_start_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeKeyboard:
        def add_hotkey(self, *_a, **_k):
            raise RuntimeError("x")

        def remove_hotkey(self, *_a, **_k):
            return None

    monkeypatch.setattr(hotkeys, "keyboard", FakeKeyboard())
    t = hotkeys.ToggleHotkeyListener(hotkey="f6", logger=types.SimpleNamespace(debug=lambda *a, **k: None, exception=lambda *a, **k: None), on_toggle=lambda: None)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        t.start()
