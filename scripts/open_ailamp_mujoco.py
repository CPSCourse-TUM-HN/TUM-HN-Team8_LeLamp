from __future__ import annotations

import argparse
from pathlib import Path
import site
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "ailamp_runtime"
MUJOCO_VENV_SITE = ROOT.parent / "mujoco_mcp/.venv/lib/python3.11/site-packages"
for import_path in (RUNTIME_PATH, MUJOCO_VENV_SITE):
    if import_path.exists():
        site.addsitedir(str(import_path))
        if str(import_path) not in sys.path:
            sys.path.insert(0, str(import_path))

from ailamp.config import load_hardware_config
from ailamp.paths import resolve_project_path
from ailamp.simulation.mujoco_runner import MujocoRunner
from ailamp.services.motor import RecordingStore


def _set_joint_qpos(model, data, joint_name: str, value: float) -> None:
    import mujoco  # type: ignore

    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise KeyError(joint_name)
    data.qpos[model.jnt_qposadr[joint_id]] = value


def _set_actuator_ctrl(model, data, actuator_name: str, value: float) -> None:
    import mujoco  # type: ignore

    actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
    if actuator_id < 0:
        raise KeyError(actuator_name)
    data.ctrl[actuator_id] = value


def launch_viewer(config_path: str, recording: str) -> None:
    import mujoco  # type: ignore
    import mujoco.viewer  # type: ignore

    config = load_hardware_config(config_path)
    runner = MujocoRunner(config.simulation.model_path, lock_freejoint=config.simulation.lock_freejoint)
    runner.load()

    rows = RecordingStore(resolve_project_path(config.simulation.recordings_dir)).load(recording)
    controls = runner.control_mapper.row_to_controls(rows[0])
    for actuator_name, value in controls.items():
        _set_joint_qpos(runner.model, runner.data, actuator_name, value)
        _set_actuator_ctrl(runner.model, runner.data, actuator_name, value)
    runner._lock_root_freejoint()
    runner.set_target_position(1.2, 3.8)
    mujoco.mj_forward(runner.model, runner.data)

    mujoco.viewer.launch(runner.model, runner.data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config/hardware.toml"))
    parser.add_argument("--recording", default="wake_up")
    args = parser.parse_args()
    launch_viewer(args.config, args.recording)


if __name__ == "__main__":
    main()
