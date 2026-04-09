from __future__ import annotations

import types

import voicetype.autostart as autostart


def test_autostart_unsupported_on_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(autostart.os, "name", "posix", raising=False)
    status = autostart.enable_autostart(command="x")
    assert status.enabled is False
    assert autostart.is_autostart_enabled() is False


def test_autostart_registry_run_key_mock(monkeypatch) -> None:
    monkeypatch.setattr(autostart.os, "name", "nt", raising=False)

    calls: list[tuple[str, tuple]] = []

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake = types.SimpleNamespace()
    fake.HKEY_CURRENT_USER = object()
    fake.KEY_SET_VALUE = 1
    fake.KEY_READ = 2
    fake.REG_SZ = 1

    def open_key(_root, _path, *_args):
        calls.append(("OpenKey", (_root, _path)))
        return FakeKey()

    def set_value_ex(_key, name, _reserved, _typ, value):
        calls.append(("SetValueEx", (name, value)))

    def query_value_ex(_key, name):
        if name != "Talkie Type":
            raise FileNotFoundError()
        return ("cmd", 1)

    def delete_value(_key, name):
        calls.append(("DeleteValue", (name,)))

    fake.OpenKey = open_key
    fake.SetValueEx = set_value_ex
    fake.QueryValueEx = query_value_ex
    fake.DeleteValue = delete_value

    monkeypatch.setitem(autostart.sys.modules, "winreg", fake)

    st = autostart.enable_autostart(command="cmd")
    assert st.enabled is True
    assert autostart.is_autostart_enabled() is True

    st2 = autostart.disable_autostart()
    assert st2.enabled is False


def test_autostart_default_command_includes_background(monkeypatch) -> None:
    monkeypatch.setattr(autostart.os, "name", "nt", raising=False)

    captured = {"value": ""}

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake = types.SimpleNamespace()
    fake.HKEY_CURRENT_USER = object()
    fake.KEY_SET_VALUE = 1
    fake.KEY_READ = 2
    fake.REG_SZ = 1

    def open_key(_root, _path, *_args):
        return FakeKey()

    def set_value_ex(_key, name, _reserved, _typ, value):
        if name == "Talkie Type":
            captured["value"] = value

    def query_value_ex(_key, name):
        raise FileNotFoundError()

    fake.OpenKey = open_key
    fake.SetValueEx = set_value_ex
    fake.QueryValueEx = query_value_ex
    fake.DeleteValue = lambda *_a, **_k: None

    monkeypatch.setitem(autostart.sys.modules, "winreg", fake)
    autostart.enable_autostart()
    assert "--background" in captured["value"]


def test_autostart_prefers_pythonw_when_available(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(autostart.os, "name", "nt", raising=False)
    python = tmp_path / "python.exe"
    pythonw = tmp_path / "pythonw.exe"
    python.write_text("", encoding="utf-8")
    pythonw.write_text("", encoding="utf-8")
    monkeypatch.setattr(autostart.sys, "executable", str(python))
    cmd = autostart._default_command()  # type: ignore[attr-defined]
    assert "pythonw.exe" in cmd.lower()


def test_autostart_enable_failure_returns_failed(monkeypatch) -> None:
    monkeypatch.setattr(autostart.os, "name", "nt", raising=False)

    fake = types.SimpleNamespace()
    fake.HKEY_CURRENT_USER = object()
    fake.KEY_SET_VALUE = 1
    fake.REG_SZ = 1

    def open_key(*_a, **_k):
        raise OSError("no access")

    fake.OpenKey = open_key
    fake.SetValueEx = lambda *_a, **_k: None

    monkeypatch.setitem(autostart.sys.modules, "winreg", fake)
    st = autostart.enable_autostart(command="cmd")
    assert st.enabled is False
