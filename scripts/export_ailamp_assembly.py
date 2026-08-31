"""Export the AILamp simulation rest pose as a single assembled mesh.

Reads ``simulation/ailamp_scene.xml`` via MuJoCo, walks every visual mesh
geom, applies its world-space pose, and writes:

- ``outputs/ailamp_full_assembly.stl`` — single binary STL (slicer-friendly)
- ``outputs/ailamp_full_assembly.3mf`` — single 3MF (Bambu Studio / PrusaSlicer)
- ``outputs/ailamp_full_assembly.glb`` — single glTF binary (Blender / web)

This is intended as a "look at the whole lamp" deliverable; do NOT print this
file directly — for printing use the per-part files in
``output/3d_print/AILamp_Current_3D_Print_Files/Required_3MF``.
"""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[1]
SCENE_XML = ROOT / "simulation/ailamp_scene.xml"
OUT_STL = ROOT / "outputs/ailamp_full_assembly.stl"
OUT_3MF = ROOT / "outputs/ailamp_full_assembly.3mf"
OUT_GLB = ROOT / "outputs/ailamp_full_assembly.glb"

# Approximate per-part colours for the glTF preview.
COLOR_RULES: list[tuple[str, tuple[int, int, int, int]]] = [
    ("shell", (46, 115, 199, 255)),
    ("cover", (215, 222, 230, 255)),
    ("boot", (245, 159, 42, 255)),
    ("clip", (45, 45, 45, 255)),
    ("diffuser", (255, 240, 200, 220)),
    ("head", (247, 207, 71, 255)),
    ("lamphead", (247, 207, 71, 255)),
    ("lamparm", (190, 200, 215, 255)),
    ("wrist", (190, 200, 215, 255)),
    ("elbow", (190, 200, 215, 255)),
    ("pitch", (190, 200, 215, 255)),
    ("motor", (70, 70, 75, 255)),
    ("pcb", (40, 90, 50, 255)),
    ("金属", (70, 70, 75, 255)),
    ("person", (200, 40, 40, 120)),
    ("target", (200, 40, 40, 120)),
]
DEFAULT_COLOR = (140, 150, 160, 255)


def _pick_color(name: str) -> tuple[int, int, int, int]:
    lowered = name.lower()
    for key, color in COLOR_RULES:
        if key in lowered or key in name:
            return color
    return DEFAULT_COLOR


def _world_pose(data: mujoco.MjData, geom_id: int) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, :3] = data.geom_xmat[geom_id].reshape(3, 3)
    matrix[:3, 3] = data.geom_xpos[geom_id]
    return matrix


def _collect_meshes() -> list[trimesh.Trimesh]:
    model = mujoco.MjModel.from_xml_path(str(SCENE_XML))
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    meshes: list[trimesh.Trimesh] = []
    for geom_id in range(model.ngeom):
        if model.geom_type[geom_id] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        # Skip collision-only and helper visuals.
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
        homog = np.ones((verts.shape[0], 4))
        homog[:, :3] = verts
        world = (pose @ homog.T).T[:, :3]

        geom_name = (
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
            or mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh_id)
            or f"geom_{geom_id}"
        )
        if "person" in geom_name.lower() or "target" in geom_name.lower():
            # Skip the simulated training target — not part of the physical lamp.
            continue
        color = _pick_color(geom_name)
        tm = trimesh.Trimesh(vertices=world, faces=faces, process=True)
        tm.visual.face_colors = np.tile(color, (len(tm.faces), 1))
        tm.metadata["name"] = geom_name
        meshes.append(tm)
    return meshes


def main() -> None:
    OUT_STL.parent.mkdir(parents=True, exist_ok=True)
    meshes = _collect_meshes()
    print(f"collected {len(meshes)} meshes")
    combined = trimesh.util.concatenate(meshes)
    print(f"merged into {len(combined.vertices)} vertices / {len(combined.faces)} faces")

    combined.export(str(OUT_STL))
    combined.export(str(OUT_3MF))

    # For glTF preserve per-part colour: build a Scene with each mesh as a separate node.
    scene = trimesh.Scene()
    for index, mesh in enumerate(meshes):
        scene.add_geometry(
            mesh,
            node_name=mesh.metadata.get("name", f"part_{index}"),
        )
    scene.export(str(OUT_GLB))

    for path in (OUT_STL, OUT_3MF, OUT_GLB):
        print(path, path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
