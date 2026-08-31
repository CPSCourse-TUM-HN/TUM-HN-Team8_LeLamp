from __future__ import annotations

from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "3D/AILamp_Adapters"
TARGET_DIR = ROOT / "simulation/assets/ailamp_adapters"


def _numbers(parts: list[str]) -> tuple[float, float, float]:
    return float(parts[-3]), float(parts[-2]), float(parts[-1])


def _read_ascii_stl(path: Path) -> list[tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...]]]:
    triangles = []
    normal: tuple[float, float, float] | None = None
    vertices: list[tuple[float, float, float]] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if not parts:
            continue
        if parts[:2] == ["facet", "normal"]:
            normal = _numbers(parts)
            vertices = []
        elif parts[0] == "vertex":
            vertices.append(_numbers(parts))
        elif parts[0] == "endfacet":
            if normal is None or len(vertices) != 3:
                raise ValueError(f"invalid ASCII STL facet in {path}")
            triangles.append((normal, tuple(vertices)))
            normal = None
            vertices = []

    if not triangles:
        raise ValueError(f"no triangles in {path}")
    return triangles


def _write_binary_stl(
    path: Path,
    name: str,
    triangles: list[tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...]]],
) -> None:
    header = f"AILamp MuJoCo binary STL from {name}".encode("ascii")[:80].ljust(80, b"\0")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for normal, vertices in triangles:
            handle.write(struct.pack("<3f", *normal))
            for vertex in vertices:
                handle.write(struct.pack("<3f", *vertex))
            handle.write(struct.pack("<H", 0))


def sync_adapter_meshes(source_dir: Path = SOURCE_DIR, target_dir: Path = TARGET_DIR) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    expected_targets = {target_dir / source.name for source in source_dir.glob("AILamp_*.stl")}
    for stale_path in target_dir.glob("AILamp_*.stl"):
        if stale_path not in expected_targets:
            stale_path.unlink()

    written = []
    for source in sorted(source_dir.glob("AILamp_*.stl")):
        triangles = _read_ascii_stl(source)
        target = target_dir / source.name
        _write_binary_stl(target, source.stem, triangles)
        written.append(target)
    return written


if __name__ == "__main__":
    for output_path in sync_adapter_meshes():
        print(output_path.relative_to(ROOT))
