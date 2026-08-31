"""Render the AILamp shell back wall so the I/O window is clearly visible."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "3D/AILamp_Adapters/AILamp_LampBase_Electronics_Shell.stl"
OUT = ROOT / "outputs/ailamp_shell_io_window.png"


def main() -> Path:
    mesh = trimesh.load(SHELL, force="mesh")
    fig = plt.figure(figsize=(11, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    faces = mesh.vertices[mesh.faces]
    ax.add_collection3d(
        Poly3DCollection(faces, facecolor="#2e73c7", edgecolor=(0, 0, 0, 0.18), linewidth=0.05, alpha=0.95)
    )
    bbox = mesh.bounds
    center = (bbox[0] + bbox[1]) / 2.0
    span = (bbox[1] - bbox[0]).max() * 0.55
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    ax.set_title("Shell — back wall I/O window (Jetson port panel)")
    ax.view_init(elev=8, azim=90)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    plt.close(fig)
    return OUT


if __name__ == "__main__":
    print(main())
