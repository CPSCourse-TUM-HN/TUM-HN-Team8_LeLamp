from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    env_root = os.environ.get("AILAMP_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "config/hardware.toml").exists():
        return package_root

    cwd = Path.cwd().resolve()
    if (cwd / "config/hardware.toml").exists():
        return cwd

    return package_root


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate
