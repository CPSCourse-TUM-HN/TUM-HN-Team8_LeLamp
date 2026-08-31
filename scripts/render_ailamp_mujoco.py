"""Render the AILamp simulation rest pose without an OpenGL context.

Loads ``simulation/ailamp_scene.xml`` with MuJoCo to compute the world-space
position and orientation of every mesh geom, then rasterises that scene with
trimesh + matplotlib.  This avoids needing OSMesa or EGL libraries which are
not available in the sandbox.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[1]
SCENE_XML = ROOT / "simulation/ailamp_scene.xml"
OUTPUT = ROOT / "outputs/ailamp_mujoco_render.png"
OUTPUT_TOP = ROOT / "outputs/ailamp_mujoco_topdown.png"


def _color_for_geom(name: str) -> tuple[float, float, float, float]:
    lowered = name.lower()
    if "shell" in lowered:
        return (0.18, 0.45, 0.78, 0.96)
    if "cover" in lowered:
        return (0.84, 0.87, 0.90, 0.96)
    if "boot" in lowered:
        return (0.96, 0.62, 0.18, 0.96)
    if "clip" in lowered:
        return (0.18, 0.18, 0.18, 0.95)
    if "diffuser" in lowered:
        return (1.00, 0.94, 0.78, 0.85)
    if "head" in lowered or "lamphead" in lowered:
        return (0.97, 0.81, 0.28, 0.95)
    if "wrist" in lowered or "elbow" in lowered or "pitch" in lowered or "lamparm" in lowered:
        return (0.74, 0.78, 0.84, 0.96)
    if "金属" in name or "motor" in lowered or "pcb" in lowered:
        return (0.28, 0.28, 0.32, 0.95)
    if "person" in lowered or "target" in lowered:
        return (0.90, 0.18, 0.16, 0.55)
    return (0.55, 0.59, 0.65, 0.90)


def _quat_to_matrix(quat: np.ndarray) -> np.ndarray:
    matrix = np.eye(4)
    mat3 = np.zeros(9)
    mujoco.mju_quat2Mat(mat3, quat)
    matrix[:3, :3] = mat3.reshape(3, 3)
    return matrix


def _world_pose(data: mujoco.MjData, geom_id: int) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, :3] = data.geom_xmat[geom_id].reshape(3, 3)
    matrix[:3, 3] = data.geom_xpos[geom_id]
    return matrix


def _collect_geom_meshes(
    model: mujoco.MjModel, data: mujoco.MjData
) -> list[tuple[str, np.ndarray, np.ndarray, np.ndarray, tuple[float, float, float, float]]]:
    """Returns a list of (name, vertices_world, faces, normals, color) entries."""
    results: list[
        tuple[str, np.ndarray, np.ndarray, np.ndarray, tuple[float, float, float, float]]
    ] = []
    for geom_id in range(model.ngeom):
        if model.geom_type[geom_id] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        # MuJoCo class for collision geoms uses group 3; skip those to declutter the render.
        if model.geom_group[geom_id] == 3:
            continue
        mesh_id = model.geom_dataid[geom_id]
        vert_start = model.mesh_vertadr[mesh_id]
        vert_count = model.mesh_vertnum[mesh_id]
        face_start = model.mesh_faceadr[mesh_id]
        face_count = model.mesh_facenum[mesh_id]
        verts = model.mesh_vert[vert_start : vert_start + vert_count].reshape(-1, 3)
        faces = model.mesh_face[face_start : face_start + face_count].reshape(-1, 3)
        pose = _world_pose(data, geom_id)
        # Apply geom-local transform first (already part of geom_xpos/xmat after mj_forward).
        homog = np.ones((verts.shape[0], 4))
        homog[:, :3] = verts
        world_verts = (pose @ homog.T).T[:, :3]
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or f"geom_{geom_id}"
        # Look up the underlying mesh name as a fallback for colouring (geom names can be empty).
        if name.startswith("geom_") or name is None:
            mesh_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh_id) or ""
            name = name or mesh_name
        else:
            mesh_name = name
        color = _color_for_geom(mesh_name)
        results.append((name, world_verts, faces, None, color))
    return results


def render_view(camera_elev: float, camera_azim: float, output: Path, title: str) -> Path:
    model = mujoco.MjModel.from_xml_path(str(SCENE_XML))
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    parts = _collect_geom_meshes(model, data)

    fig = plt.figure(figsize=(12.0, 9.0), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    all_pts: list[np.ndarray] = []
    for name, verts, faces, _normals, color in parts:
        triangles = verts[faces]
        collection = Poly3DCollection(
            triangles,
            facecolor=color,
            edgecolor=(0.0, 0.0, 0.0, 0.18),
            linewidth=0.05,
        )
        ax.add_collection3d(collection)
        all_pts.append(verts)

    combined = np.vstack(all_pts)
    min_pt = combined.min(axis=0)
    max_pt = combined.max(axis=0)
    center = (min_pt + max_pt) / 2.0
    span = (max_pt - min_pt).max() * 0.6
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title(title, fontsize=11)
    ax.view_init(elev=camera_elev, azim=camera_azim)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    print(
        render_view(
            camera_elev=14.0,
            camera_azim=-55.0,
            output=OUTPUT,
            title="AILamp MuJoCo scene — rest pose (perspective)",
        )
    )
    print(
        render_view(
            camera_elev=88.0,
            camera_azim=-90.0,
            output=OUTPUT_TOP,
            title="AILamp MuJoCo scene — rest pose (top-down)",
        )
    )
    front = OUTPUT.parent / "ailamp_mujoco_front.png"
    print(
        render_view(
            camera_elev=8.0,
            camera_azim=-90.0,
            output=front,
            title="AILamp MuJoCo scene — rest pose (front)",
        )
    )


if __name__ == "__main__":
    main()
