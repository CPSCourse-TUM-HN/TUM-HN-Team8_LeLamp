from pathlib import Path

from ailamp.paths import project_root, resolve_project_path


def test_project_root_can_use_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("AILAMP_PROJECT_ROOT", str(tmp_path))

    assert project_root() == tmp_path.resolve()
    assert resolve_project_path("config/hardware.toml") == tmp_path.resolve() / "config/hardware.toml"
