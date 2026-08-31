"""Render the AILamp base assembly (shell + cover + boot + clips) to a PNG.

Used as a sandbox-friendly substitute for the MuJoCo viewer-based sim-check
render.  Loads the freshly generated STL files with trimesh and rasterises an
isometric view with matplotlib.
"""

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
OUTPUT = ROOT / "outputs/ailamp_current_base_render.png"
OUTPUT_LAYOUT = ROOT / "outputs/ailamp_current_base_layout.png"


PARTS = [
    # (filename, color, alpha, label, translate)
    ("AILamp_LampBase_Electronics_Shell.stl", "#3a7bd5", 0.85, "Shell", (0.0, 0.0, 0.0)),
    (
        "AILamp_LampBase_Electronics_Cover.stl",
        "#cfd8e3",
        0.92,
        "Cover",
        (0.0, 0.0, 48.0),
    ),
    (
        "AILamp_Base_Arm_Link_Boot.stl",
        "#f59f2a",
        0.95,
        "Arm-link Boot",
        (0.0, 0.0, 70.0),
    ),
]


def _load_mesh(name: str, translate: tuple[float, float, float]) -> trimesh.Trimesh:
    mesh = trimesh.load(ADAPTERS / name, force="mesh")
    mesh.apply_translation(translate)
    return mesh


def main() -> Path:
    fig = plt.figure(figsize=(11.0, 9.0), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    all_bounds: list[np.ndarray] = []
    for filename, color, alpha, label, translate in PARTS:
        mesh = _load_mesh(filename, translate)
        all_bounds.append(mesh.bounds)
        faces = mesh.vertices[mesh.faces]
        collection = Poly3DCollection(
            faces,
            facecolor=color,
            edgecolor="black",
            linewidth=0.06,
            alpha=alpha,
        )
        ax.add_collection3d(collection)
        bbox = mesh.bounds
        cx = (bbox[0, 0] + bbox[1, 0]) / 2.0
        cy = bbox[1, 1] + 6.0
        cz = bbox[1, 2] + 4.0
        ax.text(cx, cy, cz, label, color="black", fontsize=8)

    combined = np.vstack(all_bounds)
    min_pt = combined.min(axis=0)
    max_pt = combined.max(axis=0)
    span = (max_pt - min_pt).max()
    center = (min_pt + max_pt) / 2.0
    half = span * 0.6
    ax.set_xlim(center[0] - half, center[0] + half)
    ax.set_ylim(center[1] - half, center[1] + half)
    ax.set_zlim(center[2] - half, center[2] + half)
    ax.set_box_aspect((1.0, 1.0, 1.0))

    ax.set_xlabel("X (mm)", fontsize=8)
    ax.set_ylabel("Y (mm)", fontsize=8)
    ax.set_zlabel("Z (mm)", fontsize=8)
    ax.set_title(
        "AILamp 3D adapters — Jetson Nano hidden-electronics base assembly\n"
        "(replaces the original LampBase shell and cover)",
        fontsize=11,
    )
    ax.view_init(elev=24, azim=-60)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT)
    plt.close(fig)
    _render_internal_layout()
    return OUTPUT


def _render_internal_layout() -> Path:
    """2-D top-down schematic of the new shell's internal zoning."""
    fig, ax = plt.subplots(figsize=(8.0, 9.5), dpi=150)

    # Shell outer rounded rectangle outline (matches generator constants).
    outer_w, outer_d = 190.0, 230.0
    radius = 18.0
    cy = 15.0
    wall = 4.0

    def rounded_rect(width: float, depth: float, r: float, cy_offset: float, **kwargs):
        from matplotlib.patches import FancyBboxPatch

        return FancyBboxPatch(
            (-width / 2.0, cy_offset - depth / 2.0),
            width,
            depth,
            boxstyle=f"round,pad=0,rounding_size={r}",
            **kwargs,
        )

    ax.add_patch(
        rounded_rect(
            outer_w, outer_d, radius, cy, fill=True, facecolor="#e3edf8", edgecolor="#22507a"
        )
    )
    ax.add_patch(
        rounded_rect(
            outer_w - 2 * wall,
            outer_d - 2 * wall,
            radius - wall,
            cy,
            fill=True,
            facecolor="#ffffff",
            edgecolor="#22507a",
            linestyle="--",
        )
    )

    # Jetson zone.
    ax.add_patch(
        plt.Rectangle((-50, -82), 100, 80, fill=True, facecolor="#cfe7d2", edgecolor="#2e7a44")
    )
    ax.text(0.0, -42.0, "Jetson Nano\n100 x 80 mm", ha="center", va="center", fontsize=9)

    # Servo driver.
    ax.add_patch(
        plt.Rectangle((-74, 51), 65, 30, fill=True, facecolor="#fde7c8", edgecolor="#a05f10")
    )
    ax.text(-42.0, 66.0, "ST3215\ndriver", ha="center", va="center", fontsize=8)

    # Pico zone.
    ax.add_patch(
        plt.Rectangle((22, 55), 51, 22, fill=True, facecolor="#f0d4ed", edgecolor="#7a2d80")
    )
    ax.text(48.0, 66.0, "Pico WH", ha="center", va="center", fontsize=8)

    # Cable spine.
    ax.add_patch(plt.Rectangle((-6, -24), 12, 72, fill=True, facecolor="#dadada", edgecolor="#555"))
    ax.text(0.0, 14.0, "cable\nspine", ha="center", va="center", fontsize=7, color="#222")

    # Arm-mount footprint (cover collar position).
    ax.add_patch(
        plt.Rectangle((-46, -49), 92, 98, fill=False, edgecolor="#c64545", linewidth=1.5, linestyle="dotted")
    )
    ax.text(0.0, 50.0, "arm-mount collar (above)", ha="center", va="bottom", fontsize=8, color="#c64545")

    # Case-screw bosses.
    for x, y in [(-82.0, -88.0), (-82.0, 118.0), (82.0, -88.0), (82.0, 118.0)]:
        ax.plot(x, y, "o", color="#22507a", markersize=6)
    ax.text(82.0, 118.0 + 6.0, "case screw boss\n(4x)", ha="center", va="bottom", fontsize=7, color="#22507a")

    ax.set_xlim(-115, 115)
    ax.set_ylim(-115, 145)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title(
        "AILamp shell — internal zoning (top-down)\n"
        "190 x 230 x 48 mm rounded shell, 4 mm walls, replaces original LampBase",
        fontsize=10,
    )
    fig.tight_layout()
    OUTPUT_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_LAYOUT)
    plt.close(fig)
    return OUTPUT_LAYOUT


if __name__ == "__main__":
    print(main())
    print(OUTPUT_LAYOUT)
