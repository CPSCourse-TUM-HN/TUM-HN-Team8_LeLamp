#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

cleanup_build_artifacts() {
  rm -rf build dist ailamp_runtime/ailamp.egg-info
}
trap cleanup_build_artifacts EXIT

python3 -m pytest -q
uv lock --check
PYTHONPATH=ailamp_runtime python3 -m ailamp.cli hardware-check
uv build --wheel

if [[ -x ../mujoco_mcp/.venv/bin/python ]]; then
  PYTHONPATH=ailamp_runtime ../mujoco_mcp/.venv/bin/python -m ailamp.cli sim-viewer --render outputs/verify_model.png
  PYTHONPATH=ailamp_runtime ../mujoco_mcp/.venv/bin/python -m ailamp.cli sim-demo --render
fi

git diff --check
