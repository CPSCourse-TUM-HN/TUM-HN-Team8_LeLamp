from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Optional

from ailamp.paths import resolve_project_path
from ailamp.services.motor import RecordingStore
from ailamp.simulation.sim_vision import classify_virtual_target_from_joints


LELAMP_ACTUATOR_ORDER = ["2", "1", "3", "4", "5"]
CSV_TO_ACTUATOR = {
    "base_pitch.pos": "2",
    "base_yaw.pos": "1",
    "elbow_pitch.pos": "3",
    "wrist_roll.pos": "4",
    "wrist_pitch.pos": "5",
}

FREEJOINT_QPOS = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
FREEJOINT_QVEL = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

ACTUATOR_CTRL_RANGES = {
    "2": (-1.0842575396713956, 2.0573351139183975),
    "1": (-5.021033992714066, 1.2621513144655205),
    "3": (-2.820024081304335, 0.3215685722854582),
    "4": (-3.7865399953934267, 2.4966453117861596),
    "5": (-0.8533371981959901, 2.288255455393803),
}


class RecordingControlMapper:
    def __init__(self, ctrl_ranges: dict[str, tuple[float, float]] | None = None):
        self.ctrl_ranges = ctrl_ranges or ACTUATOR_CTRL_RANGES

    def csv_degrees_to_control(self, csv_name: str, value_degrees: float) -> float:
        actuator_name = CSV_TO_ACTUATOR[csv_name]
        value = math.radians(value_degrees)
        low, high = self.ctrl_ranges[actuator_name]
        return min(max(value, low), high)

    def row_to_controls(self, row: dict[str, float]) -> dict[str, float]:
        return {
            actuator_name: self.csv_degrees_to_control(csv_name, row[csv_name])
            for csv_name, actuator_name in CSV_TO_ACTUATOR.items()
        }


@dataclass(frozen=True)
class ModelInfo:
    model_path: Path
    nq: int
    nv: int
    nu: int
    joints: list[str]
    actuators: list[str]


class MujocoRunner:
    def __init__(self, model_path: str | Path, lock_freejoint: bool = True):
        self.model_path = resolve_project_path(model_path)
        self.lock_freejoint = lock_freejoint
        self.model = None
        self.data = None
        self.control_mapper = RecordingControlMapper()

    def load(self) -> None:
        import mujoco  # type: ignore

        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)
        self._lock_root_freejoint()
        self._set_joint_qpos_if_exists("target_slide_x", 0.0)
        self._set_joint_qpos_if_exists("target_slide_y", -1.5)
        mujoco.mj_forward(self.model, self.data)

    def _lock_root_freejoint(self) -> None:
        if self.lock_freejoint and self.model is not None and self.data is not None and self.model.nq >= 7:
            self.data.qpos[0:7] = FREEJOINT_QPOS
            self.data.qvel[0:6] = FREEJOINT_QVEL

    def info(self) -> ModelInfo:
        if self.model is None:
            self.load()
        joints = [self.model.joint(i).name for i in range(self.model.njnt)]
        actuators = [self.model.actuator(i).name for i in range(self.model.nu)]
        return ModelInfo(self.model_path, self.model.nq, self.model.nv, self.model.nu, joints, actuators)

    def set_target_position(self, x_m: float, depth_m: float) -> None:
        self._set_joint_qpos("target_slide_x", x_m)
        self._set_joint_qpos("target_slide_y", -abs(depth_m))
        if self.model is not None and self.data is not None:
            import mujoco  # type: ignore

            mujoco.mj_forward(self.model, self.data)

    def target_joint_positions(self) -> dict[str, float]:
        return {
            "target_slide_x": self._get_joint_qpos("target_slide_x"),
            "target_slide_y": self._get_joint_qpos("target_slide_y"),
        }

    def target_vision_event(self):
        return classify_virtual_target_from_joints(self.target_joint_positions())

    def _get_joint_qpos(self, joint_name: str) -> float:
        if self.model is None or self.data is None:
            self.load()
        import mujoco  # type: ignore

        joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        if joint_id < 0:
            raise KeyError(joint_name)
        qpos_address = self.model.jnt_qposadr[joint_id]
        return float(self.data.qpos[qpos_address])

    def _set_joint_qpos(self, joint_name: str, value: float) -> None:
        if self.model is None or self.data is None:
            self.load()
        if not self._set_joint_qpos_if_exists(joint_name, value):
            raise KeyError(joint_name)

    def _set_joint_qpos_if_exists(self, joint_name: str, value: float) -> bool:
        if self.model is None or self.data is None:
            return False
        import mujoco  # type: ignore

        joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        if joint_id < 0:
            return False
        qpos_address = self.model.jnt_qposadr[joint_id]
        self.data.qpos[qpos_address] = value
        return True

    def replay_recording(self, recording_name: str, recordings_dir: str | Path, max_frames: Optional[int] = None) -> int:
        if self.model is None or self.data is None:
            self.load()
        import mujoco  # type: ignore

        store = RecordingStore(resolve_project_path(recordings_dir))
        rows = store.load(recording_name)
        frame_count = 0
        for row in rows[:max_frames]:
            controls = self.control_mapper.row_to_controls(row)
            for actuator_name, control_value in controls.items():
                actuator_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
                if actuator_id >= 0:
                    self.data.ctrl[actuator_id] = control_value
            mujoco.mj_step(self.model, self.data)
            self._lock_root_freejoint()
            mujoco.mj_forward(self.model, self.data)
            frame_count += 1
        return frame_count

    def render(
        self,
        output_path: str | Path,
        width: int = 1280,
        height: int = 720,
        camera_name: str | None = "ailamp_sim_camera",
    ) -> Path:
        if self.model is None or self.data is None:
            self.load()
        import mujoco  # type: ignore

        self.model.vis.global_.offwidth = max(self.model.vis.global_.offwidth, width)
        self.model.vis.global_.offheight = max(self.model.vis.global_.offheight, height)
        renderer = mujoco.Renderer(self.model, width=width, height=height)
        camera = camera_name if self._camera_exists(camera_name) else None
        if camera is None:
            renderer.update_scene(self.data)
        else:
            renderer.update_scene(self.data, camera=camera)
        image = renderer.render()

        from PIL import Image  # type: ignore

        output = resolve_project_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(image).save(output)
        renderer.close()
        return output

    def _camera_exists(self, camera_name: str | None) -> bool:
        if camera_name is None or self.model is None:
            return False
        import mujoco  # type: ignore

        camera_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, camera_name)
        return camera_id >= 0
