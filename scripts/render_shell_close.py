"""Close-up renders of the AILamp shell alone (no arm/head obscuring it)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = ROOT / "3D/AILamp_Adapters"
OUT_DIR = ROOT / "outputs"


PARTS = [
    ("AILamp_LampBase_Electronics_Shell.stl", "#2e73c7", 0.95, (0.0, 0.0, 0.0)),
    ("AILamp_LampBase_Electronics_Cover.stl", "#d6dde4", 0.92, (0.0, 0.0, 48.0)),
]


def _load_mesh(name: str, translate: tuple[float, float, float]) -> trimesh.Trimesh:
    mesh = trimesh.load(ADAPTERS / name, force="mesh")
    mesh.apply_translation(translate)
    return mesh


def _add_meshes(ax, meshes, edge_alpha: float = 0.12):
    all_bounds = []
    for mesh, color, alpha in meshes:
        faces = mesh.vertices[mesh.faces]
        ax.add_collection3d(
            Poly3DCollection(
                faces, facecolor=color, edgecolor=(0, 0, 0, edge_alpha), linewidth=0.05, alpha=alpha
            )
        )
        all_bounds.append(mesh.bounds)
    combined = np.vstack(all_bounds)
    min_pt = combined.min(axis=0)
    max_pt = combined.max(axis=0)
    center = (min_pt + max_pt) / 2.0
    span = (max_pt - min_pt).max() * 0.6
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)
    ax.set_box_aspect((1, 1, 1))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Shell + cover, perspective.
    shell_mesh = _load_mesh(*PARTS[0][:1], translate=PARTS[0][3])
    cover_mesh = _load_mesh(*PARTS[1][:1], translate=PARTS[1][3])
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    _add_meshes(
        ax,
        [(shell_mesh, PARTS[0][1], PARTS[0][2]), (cover_mesh, PARTS[1][1], PARTS[1][2])],
    )
    ax.view_init(elev=18, azim=-55)
    ax.set_title("Optimized base — shell + cover (perspective)")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ailamp_optimized_base_perspective.png")
    plt.close(fig)

    # Shell only (no cover) — see the clean inner cavity + side-wall vents.
    shell_mesh = _load_mesh(*PARTS[0][:1], translate=PARTS[0][3])
    fig = plt.figure(figsize=(11, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    _add_meshes(ax, [(shell_mesh, PARTS[0][1], 0.95)])
    ax.view_init(elev=12, azim=-65)
    ax.set_title("Optimized shell — side view showing ventilation slots")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ailamp_optimized_shell_cavity.png")
    plt.close(fig)

    # Extra: side-elevation view focused on the vent pattern.
    fig = plt.figure(figsize=(11, 7), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    _add_meshes(ax, [(shell_mesh, PARTS[0][1], 0.95)])
    ax.view_init(elev=4, azim=-88)
    ax.set_title("Optimized shell — vent pattern (front elevation)")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ailamp_optimized_shell_vents.png")
    plt.close(fig)

    # Cover only — see the case-screw holes + tapered collar.
    cover_mesh = _load_mesh(*PARTS[1][:1], translate=(0, 0, 0))
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    _add_meshes(ax, [(cover_mesh, PARTS[1][1], 0.95)])
    ax.view_init(elev=58, azim=-65)
    ax.set_title("Optimized cover — tapered collar + case-screw holes")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ailamp_optimized_cover_topdown.png")
    plt.close(fig)

    # Front cross-section illusion: side view with cover hovering above shell.
    shell_mesh = _load_mesh(*PARTS[0][:1], translate=PARTS[0][3])
    cover_mesh = _load_mesh(*PARTS[1][:1], translate=(0.0, 0.0, 80.0))
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    _add_meshes(
        ax,
        [(shell_mesh, PARTS[0][1], 0.95), (cover_mesh, PARTS[1][1], 0.85)],
    )
    ax.view_init(elev=10, azim=-90)
    ax.set_title("Optimized base — exploded side view")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ailamp_optimized_base_exploded.png")
    plt.close(fig)

    for p in (
        "ailamp_optimized_base_perspective.png",
        "ailamp_optimized_shell_cavity.png",
        "ailamp_optimized_cover_topdown.png",
        "ailamp_optimized_base_exploded.png",
    ):
        print(OUT_DIR / p)


if __name__ == "__main__":
    main()
