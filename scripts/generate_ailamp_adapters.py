from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_PRINT_DIR = ROOT / "3D"
PCB_EDGE_CLEARANCE_MM = 1.5
CABLE_EXIT_EXTRA_WIDTH_MM = 2.5
JETSON_BOARD_MM = (100.0, 80.0)
JETSON_ASSEMBLY_HEIGHT_MM = 29.0
PICO_BOARD_MM = (51.0, 21.0)
SERVO_DRIVER_BOARD_MM = (65.0, 30.0)
SERVO_DRIVER_MOUNT_HOLE_MM = (58.0, 23.0)
PICO_USB_RELIEF_MM = (14.0, 10.0)
ZIP_TIE_SLOT_MM = (38.0, 4.0)
LELAMP_BASE_FOOTPRINT_MM = (160.0, 190.0)

# === v6 architecture: motor lives in shell, cover is bottom panel ============
#
# Matches the original LeLamp `LampBase.3mf` + `LampBase - Cover.3mf` topology:
#
#   * Shell is bottom-open, top-closed.  The closed top carries a rectangular
#     base_yaw motor-body pass-through hole and a separate cable slit; the
#     STS3215 body sits inside a cradle hanging from the closed-top underside
#     with its horn protruding upward through the pass-through into the
#     LampArm Base-Elbow's open-bottom socket.
#   * Cover is a 6 mm flat tray (4 mm lip + 2 mm flange) that slips into the
#     shell's open bottom from below and is bolted at the 4 corners.
#
# STS3215 body dimensions per AnnotatedSTS3215.jpg datasheet (#ServoHeight ×
# #ServoWidth × #ServoDepth): 45.22 × 24.72 × 29.0 mm.  Horn (Φ19.2 mm metal
# disc) sits on top of the body, 4 × M2 horn screws are on a Φ14 mm bolt
# circle.  None of those screws engage our cover or shell — they only fasten
# the horn to the inside of the LampArm.  We just have to expose the motor
# body up through the shell top so the LampArm socket can drop over it.

# STS3215 dimensions per AnnotatedSTS3215.jpg datasheet:
#   ServoHeight × ServoWidth × ServoDepth = 45.22 × 24.72 × 29.0 mm
#   Drive horn (output): Φ19.2 × 4.5 mm (from upstream 金属舵盘_驱动__v2.stl)
#   Idle horn (axis alignment): Φ19.2 × 3.3 mm (from 金属舵盘_从动__v2.stl)
MOTOR_BODY_SIZE_MM = (24.72, 45.22, 29.0)
MOTOR_CAVITY_INNER_MM = (24.7, 45.2)       # tight slip-fit on the 24.72×45.22 body
MOTOR_CAVITY_OUTER_MM = (30.7, 51.2)       # 3 mm walls (matches original 30.7×51.2)
MOTOR_CAVITY_HEIGHT_MM = 30.0              # interior cavity height (z=7..37)
MOTOR_CENTER_XY_MM = (0.0, -25.7)
MOTOR_PASS_THROUGH_MM = (24.7, 45.2)
CABLE_SLIT_MM = (24.7, 10.0)
CABLE_SLIT_CENTER_XY_MM = (0.0, 4.9)

# Cradle bottom floor — Interpretation A "vertical motor" assembly per
# original LeLamp LampBase.3mf measured geometry (sliced and verified):
#
#   * Motor body is inserted INTO the cradle FROM BELOW (through the shell's
#     open bottom), with the body's 45.22×24.72 large face DOWN onto the
#     floor and the 29 mm depth running vertical.
#   * Body's 4 mounting tabs land on the 2 floor flanges; 4× M2.5 self-tap
#     screws come up from below and lock the body to the floor.
#   * Drive horn (Φ19.2, top of motor body) protrudes UP into the cradle
#     cavity and exits through the shell-top 24.7×45.2 motor pass-through.
#   * Idle horn (Φ19.2, bottom of motor body — for axis alignment) drops
#     DOWN into the Φ21 idle-horn pocket on the front flange.
#
# Floor sits above the cover-lip insertion zone (z = 0 → COVER_LIP_HEIGHT_MM)
# at z = COVER_LIP_HEIGHT_MM → +MOTOR_FLOOR_THICKNESS_MM (z = 4 → 7).
MOTOR_FLOOR_THICKNESS_MM = 3.0
MOTOR_FLOOR_BOTTOM_Z_MM = 4.0
MOTOR_FLOOR_REAR_FLANGE_MM = (30.7, 21.0)
MOTOR_FLOOR_FRONT_FLANGE_MM = (30.7, 24.7)
MOTOR_FLOOR_FRONT_OFFSET_MM = 28.3
MOTOR_FLOOR_SCREW_PILOT_RADIUS_MM = 1.25
MOTOR_FLOOR_SCREW_SINK_RADIUS_MM = 1.75
MOTOR_FLOOR_SCREW_SINK_HEIGHT_MM = 0.6
MOTOR_FLOOR_REAR_SCREW_Y_OFFSET_MM = -5.2
MOTOR_FLOOR_FRONT_SCREW_Y_OFFSET_MM = -9.1
MOTOR_FLOOR_SCREW_X_OFFSET_MM = 10.3
MOTOR_FLOOR_IDLE_HORN_POCKET_RADIUS_MM = 10.5    # Φ21 idle-horn axis pocket
MOTOR_FLOOR_IDLE_HORN_POCKET_Y_OFFSET_MM = -1.0    # offset from front flange center

# v6.2 — confirmed-from-photo features:
#   * Cradle interior rear-half ceiling — original LampBase has a solid shelf
#     between the cradle wall top and the shell-top motor pass-through that
#     closes the rear of the cradle.  Without it, looking from below into the
#     cradle you see straight up through the shell top; with it, the rear
#     half of the cradle has a solid ceiling at z = cavity_top_z, leaving only
#     the front half open for the drive horn to protrude through.
#   * 4 small alignment posts at the cradle's bottom corners — Φ4 × 2 mm
#     stubs that locate the STS3215 body's 4 mounting tabs on the floor
#     before screws are tightened.
MOTOR_CRADLE_REAR_SHELF_LENGTH_MM = 22.6   # half the cradle inner Y length
MOTOR_CRADLE_REAR_SHELF_THICKNESS_MM = 2.0
MOTOR_CRADLE_CORNER_POST_RADIUS_MM = 2.0   # Φ4
MOTOR_CRADLE_CORNER_POST_HEIGHT_MM = 2.0   # 2 mm protrusion
MOTOR_CRADLE_CORNER_POST_INSET_MM = 3.0    # inset from cradle outer corners

# v7.3-C: shrunk from 190×230 to 155×225 (-35 × -5 mm, ~28% volume savings).
# Z stays 40 mm to match the original LampBase cradle's horn-protrusion height.
INTEGRATED_BASE_OUTER_MM = (155.0, 225.0, 40.0)
INTEGRATED_BASE_TOP_THICKNESS_MM = 2.0
# v7.3-C cradle insert: SMALL CROP — only the cradle structure itself.
#
# Original LampBase shell outer: 160 × 190 × 40 mm with inner cavity 154 × 184
# mm.  Inside that cavity, the original has 8 Pi mount bosses (58×49 pattern,
# for Raspberry Pi — wrong for AILamp's Jetson Nano), 8 Waveshare driver
# mount bosses (designed for original-position driver, in the wrong place now
# that we moved the driver behind the cradle), and 4 corner case-screw
# bosses (also superseded — v7.3-C uses corner case-screw bosses pushed
# further to the actual shell corners).
#
# We crop tightly to ONLY the cradle structure proper (X ± 25, Y -55..+25) so
# all those unused original bosses are discarded.  AILamp adds its own
# Jetson + driver + Pico + 4-corner case-screw bosses via
# _integrated_base_internal_features().
CRADLE_INSERT_X_HALF_MM = 25.0     # JUST the cradle structure
CRADLE_INSERT_Y_MIN_MM = -55.0     # cradle rear extent
CRADLE_INSERT_Y_MAX_MM = 38.0      # extends past the cable slit (capsule at Y=+30.6,
                                   # span +25.6..+35.6) so the cable slit comes through
                                   # while still excluding Pi/Waveshare bosses at Y≥+50
CRADLE_INSERT_Z_OFFSET_MM = 4.0    # shift original z=-4 → new z=0
COVER_FLANGE_THICKNESS_MM = 2.0
COVER_LIP_HEIGHT_MM = 4.0
COVER_TOTAL_THICKNESS_MM = COVER_FLANGE_THICKNESS_MM + COVER_LIP_HEIGHT_MM
COVER_LIP_INSET_MM = 0.5
INTEGRATED_BASE_COVER_MM = (
    INTEGRATED_BASE_OUTER_MM[0] - 2.0,
    INTEGRATED_BASE_OUTER_MM[1] - 2.0,
    COVER_TOTAL_THICKNESS_MM,
)
INTEGRATED_BASE_Y_CENTER_MM = 15.0
INTEGRATED_BASE_WALL_MM = 2.5
INTEGRATED_BASE_CASE_SCREW_POSITIONS_MM = (
    # v7.3-C: pushed to the actual shell corners (was at original-LampBase
    # positions (±73.5, -76/+101) in v7.2.x — those came from the cradle
    # insert and were inset 13 mm from the corners of the smaller original
    # shell).  Now with a 155×225 shell, max corner positions inside the
    # cavity with 5 mm wall clearance + 5 mm boss radius are (±67, -87/+117).
    (-67.0, -87.0),
    (-67.0, 117.0),
    (67.0, -87.0),
    (67.0, 117.0),
)
JETSON_STANDOFF_SPACING_MM = (84.0, 64.0)
JETSON_STANDOFF_HOLE_MM = 3.4
# v7.3-C: Pico WH (51 × 21 mm, rotated 90° → 21 × 51 in our layout) placed
# beside cradle on the right at (+45, 0).  Standard Pico mount-hole pattern
# is 47 × 11.4 mm — rotated to 11.4 × 47 to match the board orientation.
PICO_CENTER_XY_MM = (45.0, 0.0)
PICO_HOLE_PATTERN_MM = (11.4, 47.0)
PICO_STANDOFF_HOLE_MM = 2.1     # phi 2.1 for M2 self-tap
CASE_SCREW_CLEARANCE_MM = 4.0
INTEGRATED_BASE_CORNER_RADIUS_MM = 18.0
INTEGRATED_BASE_COVER_CORNER_RADIUS_MM = 16.0
SMOOTH_CORNER_STEPS = 28
STANDOFF_SEGMENTS = 32


CORE_NAMESPACE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
FIXED_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
ELECTRONICS_SIDE_DECK_WIRING_ALLOWANCE_MM = (26.0, 15.0)
ROUNDED_CORNER_SEGMENTS = 24
COVER_CASE_SCREW_CLEARANCE_RADIUS_MM = 2.4


def _loose_pcb_pocket(board_mm: tuple[float, float]) -> tuple[float, float]:
    return (
        board_mm[0] + 2.0 * PCB_EDGE_CLEARANCE_MM,
        board_mm[1] + 2.0 * PCB_EDGE_CLEARANCE_MM,
    )


def _loose_cable_channel_width(nominal_width_mm: float) -> float:
    return nominal_width_mm + CABLE_EXIT_EXTRA_WIDTH_MM


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    outer_mm: tuple[float, float, float]
    board_pocket_mm: tuple[float, float]
    description: str


def adapter_specs() -> list[AdapterSpec]:
    electronics_pocket = (
        SERVO_DRIVER_BOARD_MM[0]
        + PICO_BOARD_MM[0]
        + 2.0 * PCB_EDGE_CLEARANCE_MM
        + ELECTRONICS_SIDE_DECK_WIRING_ALLOWANCE_MM[0],
        max(SERVO_DRIVER_BOARD_MM[1], PICO_BOARD_MM[1])
        + 2.0 * PCB_EDGE_CLEARANCE_MM
        + ELECTRONICS_SIDE_DECK_WIRING_ALLOWANCE_MM[1],
    )
    return [
        AdapterSpec(
            "AILamp_LampBase_Electronics_Shell",
            INTEGRATED_BASE_OUTER_MM,
            (
                INTEGRATED_BASE_OUTER_MM[0] - 2.0 * INTEGRATED_BASE_WALL_MM,
                INTEGRATED_BASE_OUTER_MM[1] - 2.0 * INTEGRATED_BASE_WALL_MM,
            ),
            "Replacement LampBase shell for Jetson Nano, servo driver, Pico WH, wiring, airflow — bottom-open + top-closed with built-in base_yaw motor cradle (per original LeLamp architecture)",
        ),
        AdapterSpec(
            "AILamp_LampBase_Electronics_Cover",
            INTEGRATED_BASE_COVER_MM,
            MOTOR_PASS_THROUGH_MM,
            "Bottom panel for the LampBase shell — 6 mm flat plate (4 mm lip + 2 mm flange) with 4 corner case-screw bores",
        ),
        AdapterSpec(
            "AILamp_Jetson_Nano_Base_Tray",
            (122.0, 102.0, 12.0),
            _loose_pcb_pocket(JETSON_BOARD_MM),
            "Loose external Jetson Nano tray",
        ),
        AdapterSpec(
            "AILamp_Electronics_Side_Deck",
            (145.0, 48.0, 10.0),
            electronics_pocket,
            "Servo driver and Pico WH side deck",
        ),
        AdapterSpec(
            "AILamp_Cable_Clip_6mm",
            (24.0, 18.0, 8.0),
            (_loose_cable_channel_width(6.0), 8.0),
            "Loose cable clip for USB and signal wires",
        ),
        AdapterSpec(
            "AILamp_Cable_Clip_10mm",
            (30.0, 22.0, 10.0),
            (_loose_cable_channel_width(10.0), 10.0),
            "Loose cable clip for power or servo bundles",
        ),
    ]


class Mesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self._boxes: list[tuple[float, float, float, float, float, float]] = []
        self._cutouts: list[tuple[float, float, float, float, float, float]] = []

    def add_box(
        self,
        cx: float,
        cy: float,
        cz: float,
        sx: float,
        sy: float,
        sz: float,
    ) -> None:
        self._boxes.append(_box_bounds(cx, cy, cz, sx, sy, sz))

    def subtract_box(
        self,
        cx: float,
        cy: float,
        cz: float,
        sx: float,
        sy: float,
        sz: float,
    ) -> None:
        self._cutouts.append(_box_bounds(cx, cy, cz, sx, sy, sz))

    def write_stl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        vertices, triangles = self._surface_mesh()
        lines = [f"solid {self.name}"]
        for a, b, c in triangles:
            va = vertices[a]
            vb = vertices[b]
            vc = vertices[c]
            normal = _triangle_normal(va, vb, vc)
            lines.extend(
                [
                    f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}",
                    "    outer loop",
                    f"      vertex {va[0]:.4f} {va[1]:.4f} {va[2]:.4f}",
                    f"      vertex {vb[0]:.4f} {vb[1]:.4f} {vb[2]:.4f}",
                    f"      vertex {vc[0]:.4f} {vc[1]:.4f} {vc[2]:.4f}",
                    "    endloop",
                    "  endfacet",
                ]
            )
        lines.append(f"endsolid {self.name}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_3mf(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        vertices, triangles = self._surface_mesh()
        vertices = "\n".join(
            f'          <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}" />'
            for x, y, z in vertices
        )
        triangles = "\n".join(
            f'          <triangle v1="{a}" v2="{b}" v3="{c}" />'
            for a, b, c in triangles
        )
        model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="{CORE_NAMESPACE}">
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
{vertices}
        </vertices>
        <triangles>
{triangles}
        </triangles>
      </mesh>
    </object>
  </resources>
  <build>
    <item objectid="1" />
  </build>
</model>
"""
        content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />
</Types>
"""
        rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />
</Relationships>
"""
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_zip_entry(archive, "[Content_Types].xml", content_types)
            _write_zip_entry(archive, "_rels/.rels", rels)
            _write_zip_entry(archive, "3D/3dmodel.model", model)

    def _surface_mesh(self) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        if not self._boxes:
            return [], []

        xs = _sorted_boundaries(self._boxes, self._cutouts, 0, 1)
        ys = _sorted_boundaries(self._boxes, self._cutouts, 2, 3)
        zs = _sorted_boundaries(self._boxes, self._cutouts, 4, 5)
        solid_cells: set[tuple[int, int, int]] = set()

        for ix in range(len(xs) - 1):
            cx = (xs[ix] + xs[ix + 1]) / 2.0
            for iy in range(len(ys) - 1):
                cy = (ys[iy] + ys[iy + 1]) / 2.0
                for iz in range(len(zs) - 1):
                    cz = (zs[iz] + zs[iz + 1]) / 2.0
                    if self._is_solid_point(cx, cy, cz):
                        solid_cells.add((ix, iy, iz))

        vertices: list[tuple[float, float, float]] = []
        vertex_index: dict[tuple[float, float, float], int] = {}
        triangles: list[tuple[int, int, int]] = []

        def vertex_id(vertex: tuple[float, float, float]) -> int:
            key = tuple(round(value, 4) for value in vertex)
            if key not in vertex_index:
                vertex_index[key] = len(vertices)
                vertices.append(key)
            return vertex_index[key]

        def add_quad(quad: tuple[tuple[float, float, float], ...]) -> None:
            a, b, c, d = (vertex_id(vertex) for vertex in quad)
            triangles.append((a, b, c))
            triangles.append((a, c, d))

        directions = (
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
        )
        for ix, iy, iz in sorted(solid_cells):
            x0, x1 = xs[ix], xs[ix + 1]
            y0, y1 = ys[iy], ys[iy + 1]
            z0, z1 = zs[iz], zs[iz + 1]
            for direction in directions:
                neighbor = (
                    ix + direction[0],
                    iy + direction[1],
                    iz + direction[2],
                )
                if neighbor in solid_cells:
                    continue
                add_quad(_face_quad(direction, x0, x1, y0, y1, z0, z1))

        return vertices, triangles

    def _is_solid_point(self, x: float, y: float, z: float) -> bool:
        inside_box = any(_contains(box, x, y, z) for box in self._boxes)
        inside_cutout = any(_contains(cutout, x, y, z) for cutout in self._cutouts)
        return inside_box and not inside_cutout


class TriangleMesh:
    def __init__(
        self,
        name: str,
        vertices: list[tuple[float, float, float]] | None = None,
        triangles: list[tuple[int, int, int]] | None = None,
    ) -> None:
        self.name = name
        self.vertices = list(vertices or [])
        self.triangles = list(triangles or [])

    def extend(
        self,
        vertices: list[tuple[float, float, float]],
        triangles: list[tuple[int, int, int]],
    ) -> None:
        offset = len(self.vertices)
        self.vertices.extend(vertices)
        self.triangles.extend((a + offset, b + offset, c + offset) for a, b, c in triangles)

    def extend_mesh(self, mesh: Mesh) -> None:
        vertices, triangles = mesh._surface_mesh()
        self.extend(vertices, triangles)

    def extend_triangle_mesh(self, mesh: "TriangleMesh") -> None:
        self.extend(mesh.vertices, mesh.triangles)

    def write_stl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"solid {self.name}"]
        for a, b, c in self.triangles:
            va = self.vertices[a]
            vb = self.vertices[b]
            vc = self.vertices[c]
            normal = _triangle_normal(va, vb, vc)
            lines.extend(
                [
                    f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}",
                    "    outer loop",
                    f"      vertex {va[0]:.4f} {va[1]:.4f} {va[2]:.4f}",
                    f"      vertex {vb[0]:.4f} {vb[1]:.4f} {vb[2]:.4f}",
                    f"      vertex {vc[0]:.4f} {vc[1]:.4f} {vc[2]:.4f}",
                    "    endloop",
                    "  endfacet",
                ]
            )
        lines.append(f"endsolid {self.name}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_3mf(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        vertices = "\n".join(
            f'          <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}" />'
            for x, y, z in self.vertices
        )
        triangles = "\n".join(
            f'          <triangle v1="{a}" v2="{b}" v3="{c}" />'
            for a, b, c in self.triangles
        )
        model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="{CORE_NAMESPACE}">
  <resources>
    <object id="1" type="model">
      <mesh>
        <vertices>
{vertices}
        </vertices>
        <triangles>
{triangles}
        </triangles>
      </mesh>
    </object>
  </resources>
  <build>
    <item objectid="1" />
  </build>
</model>
"""
        content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />
</Types>
"""
        rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />
</Relationships>
"""
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_zip_entry(archive, "[Content_Types].xml", content_types)
            _write_zip_entry(archive, "_rels/.rels", rels)
            _write_zip_entry(archive, "3D/3dmodel.model", model)


def _box_bounds(
    cx: float,
    cy: float,
    cz: float,
    sx: float,
    sy: float,
    sz: float,
) -> tuple[float, float, float, float, float, float]:
    return (
        cx - sx / 2.0,
        cx + sx / 2.0,
        cy - sy / 2.0,
        cy + sy / 2.0,
        cz - sz / 2.0,
        cz + sz / 2.0,
    )


def _sorted_boundaries(
    boxes: list[tuple[float, float, float, float, float, float]],
    cutouts: list[tuple[float, float, float, float, float, float]],
    low_index: int,
    high_index: int,
) -> list[float]:
    boundaries = set()
    for bounds in boxes + cutouts:
        boundaries.add(round(bounds[low_index], 4))
        boundaries.add(round(bounds[high_index], 4))
    return sorted(boundaries)


def _contains(
    bounds: tuple[float, float, float, float, float, float],
    x: float,
    y: float,
    z: float,
) -> bool:
    x0, x1, y0, y1, z0, z1 = bounds
    return x0 < x < x1 and y0 < y < y1 and z0 < z < z1


def _face_quad(
    direction: tuple[int, int, int],
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
) -> tuple[tuple[float, float, float], ...]:
    if direction == (-1, 0, 0):
        return ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
    if direction == (1, 0, 0):
        return ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))
    if direction == (0, -1, 0):
        return ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
    if direction == (0, 1, 0):
        return ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
    if direction == (0, 0, -1):
        return ((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))
    return ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))


def _triangle_normal(
    va: tuple[float, float, float],
    vb: tuple[float, float, float],
    vc: tuple[float, float, float],
) -> tuple[float, float, float]:
    ux, uy, uz = vb[0] - va[0], vb[1] - va[1], vb[2] - va[2]
    vx, vy, vz = vc[0] - va[0], vc[1] - va[1], vc[2] - va[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def _arc_points(
    cx: float,
    cy: float,
    radius: float,
    start_deg: float,
    end_deg: float,
    segments: int,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(segments + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * index / segments)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def _rounded_rect_polygon(
    width: float,
    depth: float,
    radius: float,
    segments: int = ROUNDED_CORNER_SEGMENTS,
    cx: float = 0.0,
    cy: float = 0.0,
) -> list[tuple[float, float]]:
    """CCW outline (viewed from +z) of a rounded rectangle centered at (cx, cy)."""
    if radius * 2 > min(width, depth):
        raise ValueError("corner radius too large for given width/depth")
    hw = width / 2.0
    hd = depth / 2.0
    pts: list[tuple[float, float]] = []
    # Each arc returns segments+1 points; drop the last so the next arc's start does not repeat.
    pts.extend(
        _arc_points(cx + hw - radius, cy - hd + radius, radius, 270.0, 360.0, segments)[:-1]
    )
    pts.extend(
        _arc_points(cx + hw - radius, cy + hd - radius, radius, 0.0, 90.0, segments)[:-1]
    )
    pts.extend(
        _arc_points(cx - hw + radius, cy + hd - radius, radius, 90.0, 180.0, segments)[:-1]
    )
    pts.extend(
        _arc_points(cx - hw + radius, cy - hd + radius, radius, 180.0, 270.0, segments)[:-1]
    )
    return pts


def _polygon_centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    count = len(points)
    return (
        sum(p[0] for p in points) / count,
        sum(p[1] for p in points) / count,
    )


def _circle_polygon(
    cx: float, cy: float, radius: float, segments: int = ROUNDED_CORNER_SEGMENTS
) -> list[tuple[float, float]]:
    """CCW circle polygon."""
    return [
        (
            cx + radius * math.cos(2.0 * math.pi * i / segments),
            cy + radius * math.sin(2.0 * math.pi * i / segments),
        )
        for i in range(segments)
    ]


def _triangulate_polygon_with_holes(
    outer: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
) -> list[tuple[int, int, int]]:
    """Earcut-triangulate a 2D polygon with holes.

    Returns triangle indices into the concatenated vertex list
    ``outer + holes[0] + holes[1] + ...``.
    """
    import mapbox_earcut as earcut

    flat_points: list[tuple[float, float]] = list(outer)
    ring_ends = [len(outer)]
    for hole in holes:
        flat_points.extend(hole)
        ring_ends.append(ring_ends[-1] + len(hole))
    points_array = np.array(flat_points, dtype=np.float64)
    indices = earcut.triangulate_float64(
        points_array, np.array(ring_ends, dtype=np.uint32)
    )
    return [
        (int(indices[i]), int(indices[i + 1]), int(indices[i + 2]))
        for i in range(0, len(indices), 3)
    ]


def _fan_cap(
    name: str,
    polygon: list[tuple[float, float]],
    z: float,
    facing_up: bool,
) -> TriangleMesh:
    """Fan-triangulate a convex polygon at constant z with the given facing normal."""
    centroid = _polygon_centroid(polygon)
    vertices: list[tuple[float, float, float]] = [(centroid[0], centroid[1], z)]
    for x, y in polygon:
        vertices.append((x, y, z))
    triangles: list[tuple[int, int, int]] = []
    n = len(polygon)
    for i in range(n):
        a = 0
        b = 1 + i
        c = 1 + ((i + 1) % n)
        if facing_up:
            triangles.append((a, b, c))
        else:
            triangles.append((a, c, b))
    return TriangleMesh(name, vertices, triangles)


def _holey_cap(
    name: str,
    outer_polygon: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
    z: float,
    facing_up: bool,
) -> TriangleMesh:
    """Triangulate an outer polygon (CCW) with one or more holes (CCW) at constant z.

    Holes are reversed to CW before being handed to earcut.  The returned mesh
    uses the same outer CCW coordinates and CW hole coordinates so that
    coordinate-based merging in tests lines up with adjacent walls/strips.
    """
    holes_cw = [list(reversed(hole)) for hole in holes]
    triangles_2d = _triangulate_polygon_with_holes(outer_polygon, holes_cw)
    flat: list[tuple[float, float]] = list(outer_polygon)
    for hole in holes_cw:
        flat.extend(hole)
    vertices: list[tuple[float, float, float]] = [(x, y, z) for x, y in flat]
    if facing_up:
        triangles = list(triangles_2d)
    else:
        triangles = [(c, b, a) for a, b, c in triangles_2d]
    return TriangleMesh(name, vertices, triangles)


def _extruded_wall(
    name: str,
    polygon: list[tuple[float, float]],
    z_bottom: float,
    z_top: float,
    outward: bool = True,
) -> TriangleMesh:
    """Vertical side walls for a CCW polygon extruded along z."""
    n = len(polygon)
    vertices: list[tuple[float, float, float]] = []
    for x, y in polygon:
        vertices.append((x, y, z_bottom))
    for x, y in polygon:
        vertices.append((x, y, z_top))
    triangles: list[tuple[int, int, int]] = []
    for i in range(n):
        j = (i + 1) % n
        if outward:
            triangles.append((i, j, j + n))
            triangles.append((i, j + n, i + n))
        else:
            triangles.append((i, j + n, j))
            triangles.append((i, i + n, j + n))
    return TriangleMesh(name, vertices, triangles)


def _annular_strip(
    name: str,
    outer_polygon: list[tuple[float, float]],
    inner_polygon: list[tuple[float, float]],
    z: float,
    facing_up: bool,
) -> TriangleMesh:
    """Triangle strip between two same-length polygons at a constant z."""
    if len(outer_polygon) != len(inner_polygon):
        raise ValueError("annular strip requires polygons of equal length")
    n = len(outer_polygon)
    vertices: list[tuple[float, float, float]] = []
    for x, y in outer_polygon:
        vertices.append((x, y, z))
    for x, y in inner_polygon:
        vertices.append((x, y, z))
    triangles: list[tuple[int, int, int]] = []
    for i in range(n):
        j = (i + 1) % n
        if facing_up:
            triangles.append((i, j, j + n))
            triangles.append((i, j + n, i + n))
        else:
            triangles.append((i, j + n, j))
            triangles.append((i, i + n, j + n))
    return TriangleMesh(name, vertices, triangles)


def _hollow_rounded_box(
    name: str,
    outer_w: float,
    outer_d: float,
    outer_h: float,
    wall_t: float,
    bottom_t: float,
    outer_radius: float,
    cy_offset: float = 0.0,
    segments: int = ROUNDED_CORNER_SEGMENTS,
) -> TriangleMesh:
    """Closed 2-manifold rounded-rectangle box with a hollow upper cavity (top is open)."""
    inner_radius = max(outer_radius - wall_t, max(wall_t * 0.5, 2.0))
    outer_pts = _rounded_rect_polygon(outer_w, outer_d, outer_radius, segments, cy=cy_offset)
    inner_pts = _rounded_rect_polygon(
        outer_w - 2.0 * wall_t,
        outer_d - 2.0 * wall_t,
        inner_radius,
        segments,
        cy=cy_offset,
    )
    mesh = TriangleMesh(name)
    # Bottom plane (closes the box from below; normal -z).
    mesh.extend_triangle_mesh(_fan_cap(name + "_bottom", outer_pts, 0.0, facing_up=False))
    # Outer side wall from z=0 up to the top edge.
    mesh.extend_triangle_mesh(
        _extruded_wall(name + "_outer_wall", outer_pts, 0.0, outer_h, outward=True)
    )
    # Annular top edge connecting outer and inner perimeters (closes off the wall thickness).
    mesh.extend_triangle_mesh(
        _annular_strip(name + "_top_edge", outer_pts, inner_pts, outer_h, facing_up=True)
    )
    # Inner wall going down from the top edge to the inner floor (faces into the cavity).
    mesh.extend_triangle_mesh(
        _extruded_wall(name + "_inner_wall", inner_pts, bottom_t, outer_h, outward=False)
    )
    # Inner floor (closes the cavity from below; normal +z).
    mesh.extend_triangle_mesh(_fan_cap(name + "_inner_floor", inner_pts, bottom_t, facing_up=True))
    return mesh


def _rounded_plate_with_hole(
    name: str,
    plate_w: float,
    plate_d: float,
    plate_thickness: float,
    outer_radius: float,
    hole_w: float,
    hole_d: float,
    hole_radius: float,
    cy_offset: float = 0.0,
    segments: int = ROUNDED_CORNER_SEGMENTS,
) -> TriangleMesh:
    """Flat rounded plate with a centered rounded-rectangle through-hole (centered at y=0)."""
    outer_pts = _rounded_rect_polygon(plate_w, plate_d, outer_radius, segments, cy=cy_offset)
    hole_pts = _rounded_rect_polygon(hole_w, hole_d, hole_radius, segments)
    mesh = TriangleMesh(name)
    # Bottom annulus (facing -z).
    mesh.extend_triangle_mesh(
        _annular_strip(name + "_bottom", outer_pts, hole_pts, 0.0, facing_up=False)
    )
    # Top annulus (facing +z).
    mesh.extend_triangle_mesh(
        _annular_strip(name + "_top", outer_pts, hole_pts, plate_thickness, facing_up=True)
    )
    # Outer perimeter wall.
    mesh.extend_triangle_mesh(
        _extruded_wall(name + "_outer", outer_pts, 0.0, plate_thickness, outward=True)
    )
    # Inner perimeter wall around the hole (faces into the hole).
    mesh.extend_triangle_mesh(
        _extruded_wall(name + "_hole", hole_pts, 0.0, plate_thickness, outward=False)
    )
    return mesh


def _lofted_wall(
    name: str,
    bottom_polygon: list[tuple[float, float]],
    z_bottom: float,
    top_polygon: list[tuple[float, float]],
    z_top: float,
    outward: bool = True,
) -> TriangleMesh:
    """Vertical-ish walls connecting two same-length CCW polygons at different z."""
    if len(bottom_polygon) != len(top_polygon):
        raise ValueError("lofted wall requires matching polygon lengths")
    n = len(bottom_polygon)
    vertices: list[tuple[float, float, float]] = []
    for x, y in bottom_polygon:
        vertices.append((x, y, z_bottom))
    for x, y in top_polygon:
        vertices.append((x, y, z_top))
    triangles: list[tuple[int, int, int]] = []
    for i in range(n):
        j = (i + 1) % n
        if outward:
            triangles.append((i, j, j + n))
            triangles.append((i, j + n, i + n))
        else:
            triangles.append((i, j + n, j))
            triangles.append((i, i + n, j + n))
    return TriangleMesh(name, vertices, triangles)


def _solid_cylinder_with_hole(
    name: str,
    cx: float,
    cy: float,
    z_bottom: float,
    height: float,
    outer_radius: float,
    inner_radius: float,
    segments: int = STANDOFF_SEGMENTS,
) -> TriangleMesh:
    """Alias for _cylinder_ring_mesh that lets the new builders read cleanly."""
    return _cylinder_ring_mesh(
        name,
        cx,
        cy,
        z_bottom=z_bottom,
        height=height,
        outer_radius=outer_radius,
        inner_radius=inner_radius,
        segments=segments,
    )


def _write_zip_entry(archive: zipfile.ZipFile, filename: str, text: str) -> None:
    info = zipfile.ZipInfo(filename=filename, date_time=FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, text.encode("utf-8"))


def _unit_to_mm_scale(unit: str | None) -> float:
    if unit == "meter":
        return 1000.0
    if unit in {None, "millimeter"}:
        return 1.0
    if unit == "centimeter":
        return 10.0
    raise ValueError(f"unsupported 3MF unit: {unit}")


def _load_3mf_mesh_mm(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    namespace = {"core": CORE_NAMESPACE}
    with zipfile.ZipFile(path) as archive:
        model_name = next(name for name in archive.namelist() if name.endswith(".model"))
        with archive.open(model_name) as model_file:
            model_root = ET.parse(model_file).getroot()

    scale = _unit_to_mm_scale(model_root.attrib.get("unit"))
    vertices = [
        (
            float(vertex.attrib["x"]) * scale,
            float(vertex.attrib["y"]) * scale,
            float(vertex.attrib["z"]) * scale,
        )
        for vertex in model_root.findall(".//core:vertex", namespace)
    ]
    triangles = [
        (
            int(triangle.attrib["v1"]),
            int(triangle.attrib["v2"]),
            int(triangle.attrib["v3"]),
        )
        for triangle in model_root.findall(".//core:triangle", namespace)
    ]
    if not vertices or not triangles:
        raise ValueError(f"no mesh data found in {path}")
    return vertices, triangles


def _scaled_original_print_mesh(
    name: str,
    source_filename: str,
    target_mm: tuple[float, float, float],
) -> TriangleMesh:
    source_vertices, source_triangles = _load_3mf_mesh_mm(ORIGINAL_PRINT_DIR / source_filename)
    xs = [x for x, _y, _z in source_vertices]
    ys = [y for _x, y, _z in source_vertices]
    zs = [z for _x, _y, z in source_vertices]
    min_z = min(zs)
    scale_x = target_mm[0] / (max(xs) - min(xs))
    scale_y = target_mm[1] / (max(ys) - min(ys))
    scale_z = target_mm[2] / (max(zs) - min(zs))

    # Scale X/Y around the lamp arm origin so the original base-to-arm relationship stays aligned.
    scaled_vertices = [
        (x * scale_x, y * scale_y, (z - min_z) * scale_z)
        for x, y, z in source_vertices
    ]
    return TriangleMesh(name, scaled_vertices, source_triangles)


def _base_plate(
    mesh: Mesh,
    outer_mm: tuple[float, float, float],
    thickness: float,
    center_y: float = 0.0,
) -> None:
    mesh.add_box(0.0, center_y, thickness / 2.0, outer_mm[0], outer_mm[1], thickness)


def _edge_rails(
    mesh: Mesh,
    outer_mm: tuple[float, float, float],
    rail_width: float,
    rail_height: float,
    z_bottom: float,
    center_y: float = 0.0,
) -> None:
    sx, sy, _ = outer_mm
    cz = z_bottom + rail_height / 2.0
    mesh.add_box(0.0, center_y + sy / 2.0 - rail_width / 2.0, cz, sx, rail_width, rail_height)
    mesh.add_box(0.0, center_y - sy / 2.0 + rail_width / 2.0, cz, sx, rail_width, rail_height)
    mesh.add_box(-sx / 2.0 + rail_width / 2.0, center_y, cz, rail_width, sy, rail_height)
    mesh.add_box(sx / 2.0 - rail_width / 2.0, center_y, cz, rail_width, sy, rail_height)


def _vent_slots(
    mesh: Mesh,
    x_values: tuple[float, ...],
    cy: float,
    z_center: float,
    sx: float,
    sy: float,
    sz: float,
) -> None:
    for x in x_values:
        mesh.subtract_box(x, cy, z_center, sx, sy, sz)


def _rounded_corner_cutouts(
    mesh: Mesh,
    outer_mm: tuple[float, float, float],
    radius_mm: float,
    z_center: float,
    z_size: float,
    center_y: float = 0.0,
    steps: int = SMOOTH_CORNER_STEPS,
) -> None:
    sx, sy, _sz = outer_mm
    half_x = sx / 2.0
    half_y = sy / 2.0
    strip = radius_mm / steps
    for step in range(steps):
        inward = (step + 0.5) * strip
        circle_dy = radius_mm - inward
        keep_from_center = max(radius_mm * radius_mm - circle_dy * circle_dy, 0.0) ** 0.5
        cut_width = radius_mm - keep_from_center
        if cut_width <= 0.05:
            continue
        for sign_x in (-1.0, 1.0):
            for sign_y in (-1.0, 1.0):
                cx = sign_x * (half_x - cut_width / 2.0)
                cy = center_y + sign_y * (half_y - inward)
                mesh.subtract_box(cx, cy, z_center, cut_width + 0.4, strip + 0.2, z_size)


def _cylinder_ring_mesh(
    name: str,
    cx: float,
    cy: float,
    z_bottom: float,
    height: float,
    outer_radius: float,
    inner_radius: float,
    segments: int = STANDOFF_SEGMENTS,
) -> TriangleMesh:
    if inner_radius <= 0.0 or inner_radius >= outer_radius:
        raise ValueError("inner_radius must be positive and smaller than outer_radius")
    vertices: list[tuple[float, float, float]] = []
    for z in (z_bottom, z_bottom + height):
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = 2.0 * 3.141592653589793 * index / segments
                vertices.append(
                    (
                        cx + radius * math.cos(angle),
                        cy + radius * math.sin(angle),
                        z,
                    )
                )

    outer_bottom = 0
    inner_bottom = segments
    outer_top = segments * 2
    inner_top = segments * 3
    triangles: list[tuple[int, int, int]] = []
    for index in range(segments):
        next_index = (index + 1) % segments

        ob0 = outer_bottom + index
        ob1 = outer_bottom + next_index
        ib0 = inner_bottom + index
        ib1 = inner_bottom + next_index
        ot0 = outer_top + index
        ot1 = outer_top + next_index
        it0 = inner_top + index
        it1 = inner_top + next_index

        # Outer wall.
        triangles.append((ob0, ob1, ot1))
        triangles.append((ob0, ot1, ot0))
        # Inner wall, reversed so normals face into the screw clearance hole.
        triangles.append((ib0, it0, it1))
        triangles.append((ib0, it1, ib1))
        # Bottom and top annular faces.
        triangles.append((ob0, ib1, ob1))
        triangles.append((ob0, ib0, ib1))
        triangles.append((ot0, ot1, it1))
        triangles.append((ot0, it1, it0))
    return TriangleMesh(name, vertices, triangles)


def _plate_with_square_cutouts(
    mesh: Mesh,
    outer_x: float,
    outer_y: float,
    thickness: float,
    cutouts: tuple[tuple[float, float, float, float], ...],
) -> None:
    x_edges = {-outer_x / 2.0, outer_x / 2.0}
    y_edges = {-outer_y / 2.0, outer_y / 2.0}
    for cx, cy, sx, sy in cutouts:
        x_edges.update((cx - sx / 2.0, cx + sx / 2.0))
        y_edges.update((cy - sy / 2.0, cy + sy / 2.0))

    sorted_x = sorted(x_edges)
    sorted_y = sorted(y_edges)
    for x0, x1 in zip(sorted_x, sorted_x[1:]):
        for y0, y1 in zip(sorted_y, sorted_y[1:]):
            if x1 <= x0 or y1 <= y0:
                continue
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            inside_cutout = any(
                abs(cx - cutout_x) < cutout_sx / 2.0
                and abs(cy - cutout_y) < cutout_sy / 2.0
                for cutout_x, cutout_y, cutout_sx, cutout_sy in cutouts
            )
            if not inside_cutout:
                mesh.add_box(cx, cy, thickness / 2.0, x1 - x0, y1 - y0, thickness)


_JETSON_STANDOFF_HEIGHT_MM = 8.0
_DRIVER_STANDOFF_HEIGHT_MM = 7.0
_PICO_STANDOFF_HEIGHT_MM = 7.0
_CASE_SCREW_BOSS_HEIGHT_MM = 32.0   # tall column from z=cavity floor up to top
_CASE_SCREW_BOSS_INNER_R_MM = 1.25  # phi 2.5 M2 self-tap for cover screws


def _integrated_base_internal_features() -> TriangleMesh:
    """v7.3-C internal layout: ALL cover/board mount posts (we now own them).

    With the smaller v7.3-C cradle insert (X ± 25 only), the original
    LampBase's Pi mounts, Waveshare mounts, and corner case-screw bosses are
    all discarded.  AILamp now provides:

      * 4 corner case-screw bosses at INTEGRATED_BASE_CASE_SCREW_POSITIONS_MM
        ((±67, -87/+117)) — phi 2.5 self-tap, ~32 mm tall (z=4..36) for
        proper cover-to-shell clamping at the actual shell corners.
      * 4 Jetson Nano standoffs (84 × 64 pattern) at (±42, +43/+107),
        phi 3.4 self-tap, 8 mm tall hanging from the closed top.
      * 4 Waveshare ST3215 driver standoffs (58 × 23 pattern) at
        (±29, -53.5/-76.5), phi 3.4 self-tap, 7 mm tall.
      * 4 Pico WH standoffs (11.4 × 47 rotated pattern) at (+45, 0)
        ± (5.7, 23.5), phi 2.1 M2 self-tap, 7 mm tall.
    """
    features = TriangleMesh("AILamp_LampBase_Electronics_Internal_Features")

    outer_h = INTEGRATED_BASE_OUTER_MM[2]
    top_floor_underside_z = outer_h - INTEGRATED_BASE_TOP_THICKNESS_MM

    # 4 corner case-screw bosses — phi 10 OD with phi 2.5 self-tap pilot, full
    # height columns from z=4 up to the top-floor underside (~32 mm tall).
    # Cover screws enter from below (z < 0), pass through cover (z = 0..6),
    # and self-tap into the boss starting at z = 4 — ~28 mm of engagement.
    case_screw_z_bottom = 4.0
    case_screw_height = top_floor_underside_z - case_screw_z_bottom
    for cx, cy in INTEGRATED_BASE_CASE_SCREW_POSITIONS_MM:
        features.extend_triangle_mesh(
            _cylinder_ring_mesh(
                "case_screw_boss",
                cx,
                cy,
                z_bottom=case_screw_z_bottom,
                height=case_screw_height,
                outer_radius=5.0,
                inner_radius=_CASE_SCREW_BOSS_INNER_R_MM,
            )
        )

    # Jetson Nano standoffs (84 × 64 mm pattern) — 8 mm tall, hanging from
    # the top floor underside.  Board mounts in front of the motor cradle.
    # v7.2.2: cradle is now at Y=0±25.6 (real 3D position, not the to_2D-shifted
    # Y=-25.7 I used before).  jetson_y moved from +50 to +75 so the Jetson
    # board's rear edge clears the cradle's front face by ≥ 9 mm.
    jetson_y = 75.0
    jetson_z_bottom = top_floor_underside_z - _JETSON_STANDOFF_HEIGHT_MM
    for x in (
        -JETSON_STANDOFF_SPACING_MM[0] / 2.0,
        JETSON_STANDOFF_SPACING_MM[0] / 2.0,
    ):
        for y in (
            jetson_y - JETSON_STANDOFF_SPACING_MM[1] / 2.0,
            jetson_y + JETSON_STANDOFF_SPACING_MM[1] / 2.0,
        ):
            features.extend_triangle_mesh(
                _cylinder_ring_mesh(
                    "jetson_standoff",
                    x,
                    y,
                    z_bottom=jetson_z_bottom,
                    height=_JETSON_STANDOFF_HEIGHT_MM,
                    outer_radius=4.0,
                    inner_radius=JETSON_STANDOFF_HOLE_MM / 2.0,
                )
            )

    # Waveshare ST3215 driver standoffs (58 × 23 mm hole pattern) — 7 mm
    # tall, hanging from the top floor.  v7.2.2: moved to BEHIND the cradle
    # (Y = -65) so it sits in the previously-empty rear zone (Y < -25.6) and
    # doesn't compete with the Jetson Nano up front.
    driver_center_x = 0.0
    driver_center_y = -65.0
    driver_z_bottom = top_floor_underside_z - _DRIVER_STANDOFF_HEIGHT_MM
    for x in (
        driver_center_x - SERVO_DRIVER_MOUNT_HOLE_MM[0] / 2.0,
        driver_center_x + SERVO_DRIVER_MOUNT_HOLE_MM[0] / 2.0,
    ):
        for y in (
            driver_center_y - SERVO_DRIVER_MOUNT_HOLE_MM[1] / 2.0,
            driver_center_y + SERVO_DRIVER_MOUNT_HOLE_MM[1] / 2.0,
        ):
            features.extend_triangle_mesh(
                _cylinder_ring_mesh(
                    "servo_driver_standoff",
                    x,
                    y,
                    z_bottom=driver_z_bottom,
                    height=_DRIVER_STANDOFF_HEIGHT_MM,
                    outer_radius=3.5,
                    inner_radius=1.7,
                )
            )

    # Pico WH standoffs (11.4 × 47 mm rotated pattern, M2 self-tap) — 7 mm
    # tall, hanging from the top floor.  Pico stands UP on the right side of
    # the cradle at (+45, 0).
    pico_cx, pico_cy = PICO_CENTER_XY_MM
    pico_hx, pico_hy = PICO_HOLE_PATTERN_MM
    pico_z_bottom = top_floor_underside_z - _PICO_STANDOFF_HEIGHT_MM
    for dx in (-pico_hx / 2.0, pico_hx / 2.0):
        for dy in (-pico_hy / 2.0, pico_hy / 2.0):
            features.extend_triangle_mesh(
                _cylinder_ring_mesh(
                    "pico_standoff",
                    pico_cx + dx,
                    pico_cy + dy,
                    z_bottom=pico_z_bottom,
                    height=_PICO_STANDOFF_HEIGHT_MM,
                    outer_radius=2.0,
                    inner_radius=PICO_STANDOFF_HOLE_MM / 2.0,
                )
            )

    return features


def _merge_duplicate_vertices(
    tm: TriangleMesh, tolerance: float = 1e-4
) -> TriangleMesh:
    """Collapse coincident vertices (rounded to ``tolerance``) into a single index.

    Required before feeding a multi-sub-mesh TriangleMesh into manifold3d, whose
    2-manifold validation requires topologically-shared vertices (same index)
    rather than just coordinate-shared vertices.
    """
    key_to_index: dict[tuple[int, int, int], int] = {}
    new_vertices: list[tuple[float, float, float]] = []
    remap: list[int] = []
    scale = 1.0 / tolerance
    for x, y, z in tm.vertices:
        key = (round(x * scale), round(y * scale), round(z * scale))
        if key not in key_to_index:
            key_to_index[key] = len(new_vertices)
            new_vertices.append((x, y, z))
        remap.append(key_to_index[key])
    new_triangles: list[tuple[int, int, int]] = []
    for a, b, c in tm.triangles:
        ra, rb, rc = remap[a], remap[b], remap[c]
        if ra != rb and rb != rc and rc != ra:
            new_triangles.append((ra, rb, rc))
    return TriangleMesh(tm.name, new_vertices, new_triangles)


def _trianglemesh_to_manifold(tm: TriangleMesh):
    """Convert a TriangleMesh to a manifold3d.Manifold for boolean ops."""
    import manifold3d as m3

    merged = _merge_duplicate_vertices(tm)
    verts = np.asarray(merged.vertices, dtype=np.float32)
    tris = np.asarray(merged.triangles, dtype=np.uint32)
    mesh_obj = m3.Mesh(vert_properties=verts, tri_verts=tris)
    return m3.Manifold(mesh_obj)


def _manifold_to_trianglemesh(name: str, manif) -> TriangleMesh:
    mesh_obj = manif.to_mesh()
    verts_array = np.asarray(mesh_obj.vert_properties)[:, :3]
    tris_array = np.asarray(mesh_obj.tri_verts)
    vertices = [tuple(float(c) for c in v) for v in verts_array]
    triangles = [tuple(int(c) for c in t) for t in tris_array]
    return TriangleMesh(name, vertices, triangles)


def _shell_vent_slot_cutters():
    """Two staggered rows of ventilation slots on every side wall.

    76 vertical slots total (long walls 11 × 2 rows × 2 sides, short walls
    8 × 2 rows × 2 sides), all clear of the 4 case-screw boss positions.
    Each slot is 4 × 13 mm, fully pierces the 2.5 mm wall, and prints with
    zero overhang on FDM because the long axis is vertical.
    """
    import manifold3d as m3

    slot_width = 4.0   # opening width along the wall
    slot_height = 13.0  # vertical (Z) opening height per row
    slot_punch = 8.0   # depth perpendicular to wall (must exceed wall thickness)
    z_centers = (11.5, 30.5)  # two stacked rows: below Jetson, above Jetson
    cy = INTEGRATED_BASE_Y_CENTER_MM             # 15.0 mm

    cutters = []
    half_w_outer = INTEGRATED_BASE_OUTER_MM[0] / 2.0   # 95
    half_d_outer = INTEGRATED_BASE_OUTER_MM[1] / 2.0   # 115

    # Long side walls (perpendicular to X, at x = ±77.5 for v7.3-C).
    # v7.3-C: shell shrunk from 230 → 225 mm Y; long Y wall has 225 mm minus
    # 2×18 corner radius = 189 mm straight section.  Keep 11 columns over
    # 175 mm span (slightly narrower than 180), giving 7 mm gap to corner.
    long_y_count = 11
    long_y_span = 175.0
    long_y_positions = [
        cy + (i - (long_y_count - 1) / 2.0) * (long_y_span / (long_y_count - 1))
        for i in range(long_y_count)
    ]
    for sign_x in (-1.0, 1.0):
        for y_pos in long_y_positions:
            for z_c in z_centers:
                box = m3.Manifold.cube([slot_punch, slot_width, slot_height], center=True)
                box = box.translate([sign_x * half_w_outer, y_pos, z_c])
                cutters.append(box)

    # Front wall (sign_y = +1) — keep both vent rows.
    # v7.3-C: shell shrunk 190 → 155 mm X; front wall straight section is
    # 155 − 2×18 = 119 mm.  Reduce 8 cols / 140 mm → 6 cols / 100 mm to fit.
    short_x_count = 6
    short_x_span = 100.0
    short_x_positions = [
        (i - (short_x_count - 1) / 2.0) * (short_x_span / (short_x_count - 1))
        for i in range(short_x_count)
    ]
    for x_pos in short_x_positions:
        for z_c in z_centers:
            box = m3.Manifold.cube([slot_width, slot_punch, slot_height], center=True)
            box = box.translate([x_pos, cy + half_d_outer, z_c])
            cutters.append(box)

    # Back wall (sign_y = -1) — large rectangular opening for the Jetson Nano
    # I/O panel (power barrel / USB-C, microSD edge, 4 × USB 3.0, HDMI,
    # DisplayPort, Gigabit Ethernet).  Replaces the vent slot column on this
    # wall; the opening itself contributes plenty of ventilation.
    io_window_width = 95.0   # spans X[-47.5, 47.5], clears case-screw bosses at x=±82
    io_window_height = 22.0  # spans Z[8, 30], covers PCB (z=11) up through tallest port (~z=27)
    io_window_z_center = 19.0
    io_box = m3.Manifold.cube([io_window_width, slot_punch, io_window_height], center=True)
    io_box = io_box.translate([0.0, cy - half_d_outer, io_window_z_center])
    cutters.append(io_box)

    # Back wall — 2 × Φ7 mm button holes for off-board Power and Reset buttons
    # mounted above the I/O window.  Z = 36 mm (≈6 mm above the I/O window top
    # at z = 30 mm, clear of the upper case-screw bosses at z = 32 mm).  X = ±25
    # mm keeps them away from the I/O window edges and centred between the back
    # wall midline and the case-screw bosses at x = ±82 mm.
    button_radius = 3.5    # Φ7 mm self-cut hole for 12 mm tactile switch nut + recess
    button_z = 36.0
    for sign_x in (-1.0, 1.0):
        btn = m3.Manifold.cylinder(slot_punch, button_radius, button_radius, 32, center=False)
        btn = btn.rotate([90.0, 0.0, 0.0])  # axis aligned with -Y (through back wall)
        btn = btn.translate([sign_x * 25.0, cy - half_d_outer + slot_punch / 2.0, button_z])
        cutters.append(btn)

    # Union all slots into a single Manifold for one boolean subtract.
    combined = cutters[0]
    for c in cutters[1:]:
        combined = combined + c
    return combined


def _v6_shell_top_cutters():
    """Top-face cutters for v6 shell: motor body pass-through + cable slit.

    Both cut all the way through the ``INTEGRATED_BASE_TOP_THICKNESS_MM`` slab
    at the closed top of the shell (z = outer_h − top_t  →  z = outer_h, plus
    0.5 mm overshoot on each end for clean booleans).
    """
    import manifold3d as m3

    outer_h = INTEGRATED_BASE_OUTER_MM[2]
    top_t = INTEGRATED_BASE_TOP_THICKNESS_MM
    z_bot = outer_h - top_t - 0.5
    cut_h = top_t + 1.0

    motor_w_x, motor_d_y = MOTOR_PASS_THROUGH_MM
    mx, my = MOTOR_CENTER_XY_MM
    motor_hole = m3.Manifold.cube([motor_w_x, motor_d_y, cut_h], center=False)
    motor_hole = motor_hole.translate(
        [mx - motor_w_x / 2.0, my - motor_d_y / 2.0, z_bot]
    )

    cable_w_x, cable_d_y = CABLE_SLIT_MM
    cx_pos, cy_pos = CABLE_SLIT_CENTER_XY_MM
    cable_hole = m3.Manifold.cube([cable_w_x, cable_d_y, cut_h], center=False)
    cable_hole = cable_hole.translate(
        [cx_pos - cable_w_x / 2.0, cy_pos - cable_d_y / 2.0, z_bot]
    )

    return motor_hole + cable_hole


def _v6_motor_cavity_walls():
    """STS3215 motor-body cradle hanging from the v6 shell's closed top, plus
    the bottom mounting floor with 2 flange platforms, 4× M2.5 screw bores,
    and the Φ21 mm daisy-chain wire pass-through.

    Replicates the full original LeLamp ``LampBase.3mf`` internal cradle
    topology (verified by slicing the upstream 3MF at z = 0, 2, 30, and 34):

      • Cradle walls — hollow box hanging from the closed top down to the
        floor level (z = MOTOR_FLOOR_BOTTOM_Z_MM + MOTOR_FLOOR_THICKNESS_MM).
      • Floor — two adjacent rectangular flanges at
        z = MOTOR_FLOOR_BOTTOM_Z_MM → +MOTOR_FLOOR_THICKNESS_MM:
          - rear flange (30.7 × 21 mm) co-located with the motor centre, with
            2× M2.5 self-tap screw pilots at the back end of the STS3215;
          - front flange (30.7 × 24.7 mm) 28.3 mm forward of the motor
            centre, with 2× M2.5 pilots at the front end of the STS3215 *and*
            a Φ21 mm pocket that accepts the STS3215's idle (axis-alignment)
            horn protruding from the bottom of the motor body.
      • Each screw bore is countersunk on the underside (Φ3.5 mm × 0.6 mm)
        so the M2.5 pan head sits flush — matches the original.
    """
    import manifold3d as m3

    outer_w, outer_d = MOTOR_CAVITY_OUTER_MM
    inner_w, inner_d = MOTOR_CAVITY_INNER_MM
    shell_h = INTEGRATED_BASE_OUTER_MM[2]
    top_t = INTEGRATED_BASE_TOP_THICKNESS_MM
    mx, my = MOTOR_CENTER_XY_MM

    floor_bottom_z = MOTOR_FLOOR_BOTTOM_Z_MM
    floor_top_z = floor_bottom_z + MOTOR_FLOOR_THICKNESS_MM
    cavity_top_z = shell_h - top_t
    walls_h = cavity_top_z - floor_top_z

    # --- Cradle walls ---
    outer = m3.Manifold.cube([outer_w, outer_d, walls_h], center=False)
    outer = outer.translate(
        [mx - outer_w / 2.0, my - outer_d / 2.0, floor_top_z]
    )
    inner = m3.Manifold.cube([inner_w, inner_d, walls_h + 1.0], center=False)
    inner = inner.translate(
        [mx - inner_w / 2.0, my - inner_d / 2.0, floor_top_z - 0.5]
    )
    walls = outer - inner

    # --- Floor flanges ---
    rear_w, rear_d = MOTOR_FLOOR_REAR_FLANGE_MM
    front_w, front_d = MOTOR_FLOOR_FRONT_FLANGE_MM
    rear_cy = my
    front_cy = my + MOTOR_FLOOR_FRONT_OFFSET_MM

    rear_flange = m3.Manifold.cube(
        [rear_w, rear_d, MOTOR_FLOOR_THICKNESS_MM], center=False
    )
    rear_flange = rear_flange.translate(
        [mx - rear_w / 2.0, rear_cy - rear_d / 2.0, floor_bottom_z]
    )
    front_flange = m3.Manifold.cube(
        [front_w, front_d, MOTOR_FLOOR_THICKNESS_MM], center=False
    )
    front_flange = front_flange.translate(
        [mx - front_w / 2.0, front_cy - front_d / 2.0, floor_bottom_z]
    )
    floor = rear_flange + front_flange

    # --- 4× M2.5 self-tap screw bores (Φ2.5 pilot through full floor thickness,
    # plus Φ3.5 countersink on the underside for the screw head) ---
    pilot_r = MOTOR_FLOOR_SCREW_PILOT_RADIUS_MM
    sink_r = MOTOR_FLOOR_SCREW_SINK_RADIUS_MM
    sink_h = MOTOR_FLOOR_SCREW_SINK_HEIGHT_MM
    screw_positions = [
        (mx - MOTOR_FLOOR_SCREW_X_OFFSET_MM, rear_cy + MOTOR_FLOOR_REAR_SCREW_Y_OFFSET_MM),
        (mx + MOTOR_FLOOR_SCREW_X_OFFSET_MM, rear_cy + MOTOR_FLOOR_REAR_SCREW_Y_OFFSET_MM),
        (mx - MOTOR_FLOOR_SCREW_X_OFFSET_MM, front_cy + MOTOR_FLOOR_FRONT_SCREW_Y_OFFSET_MM),
        (mx + MOTOR_FLOOR_SCREW_X_OFFSET_MM, front_cy + MOTOR_FLOOR_FRONT_SCREW_Y_OFFSET_MM),
    ]
    for hx, hy in screw_positions:
        pilot = m3.Manifold.cylinder(
            MOTOR_FLOOR_THICKNESS_MM + 1.0, pilot_r, pilot_r, 24, center=False
        )
        pilot = pilot.translate([hx, hy, floor_bottom_z - 0.5])
        floor = floor - pilot
        sink = m3.Manifold.cylinder(
            sink_h, sink_r, sink_r, 24, center=False
        )
        sink = sink.translate([hx, hy, floor_bottom_z - 0.1])
        floor = floor - sink

    # --- Φ21 idle-horn axis-alignment pocket in the front flange ---
    horn_r = MOTOR_FLOOR_IDLE_HORN_POCKET_RADIUS_MM
    horn_y = front_cy + MOTOR_FLOOR_IDLE_HORN_POCKET_Y_OFFSET_MM
    horn_pocket = m3.Manifold.cylinder(
        MOTOR_FLOOR_THICKNESS_MM + 1.0, horn_r, horn_r, 48, center=False
    )
    horn_pocket = horn_pocket.translate([mx, horn_y, floor_bottom_z - 0.5])
    floor = floor - horn_pocket

    # --- 4 corner alignment posts (Φ4 × 2 mm) on floor's top face ---
    # Located inside the cradle's inner cavity at the 4 corners, INSET so
    # they fit between the STS3215 body and the cradle walls.  The motor's
    # bottom face touches these posts on assembly, ensuring precise XY
    # alignment before the 4 M2.5 screws thread up from below.
    post_r = MOTOR_CRADLE_CORNER_POST_RADIUS_MM
    post_h = MOTOR_CRADLE_CORNER_POST_HEIGHT_MM
    inset = MOTOR_CRADLE_CORNER_POST_INSET_MM
    inner_w, inner_d = MOTOR_CAVITY_INNER_MM   # 24.7, 45.2
    half_w = inner_w / 2.0 - inset
    half_d = inner_d / 2.0 - inset
    for sign_x in (-1.0, 1.0):
        for sign_y in (-1.0, 1.0):
            post = m3.Manifold.cylinder(post_h, post_r, post_r, 24, center=False)
            post = post.translate([mx + sign_x * half_w, my + sign_y * half_d, floor_top_z])
            floor = floor + post

    # --- Rear-half ceiling shelf inside cradle interior ---
    # A horizontal slab covering the cradle's REAR HALF interior, at the top
    # of the cavity walls (just below the shell top).  This closes off the
    # rear of the cradle from above so that the shell-top 24.7×45.2 mm motor
    # pass-through only sees through the cradle's FRONT HALF (where the drive
    # horn protrudes); the rear half stays solid.
    shelf_inner_w, shelf_inner_d = MOTOR_CAVITY_INNER_MM    # 24.7, 45.2
    shelf_length = MOTOR_CRADLE_REAR_SHELF_LENGTH_MM        # 22.6 (half-Y)
    shelf_t = MOTOR_CRADLE_REAR_SHELF_THICKNESS_MM          # 2 mm
    shelf = m3.Manifold.cube([shelf_inner_w, shelf_length, shelf_t], center=False)
    # Place at the REAR half of the cradle interior (y < motor center).
    shelf = shelf.translate(
        [mx - shelf_inner_w / 2.0, my - shelf_inner_d / 2.0, cavity_top_z - shelf_t]
    )
    walls = walls + shelf

    return walls + floor


def _load_lelamp_cradle_insert():
    """Load the original LeLamp ``LampBase.3mf`` and crop to the cradle area.

    Returns a manifold3d.Manifold containing JUST the cradle structure
    (motor cavity walls, floor flanges with 4 M2.5 screw holes, Φ21 idle-horn
    pocket, top motor pass-through, top cable slit, any cradle interior
    detail features).  This is the v7 strategy: instead of trying to
    reconstruct the cradle programmatically (which kept "drifting" from the
    original geometry), we use the original .3mf directly — bit-identical
    cradle, guaranteed.

    The crop preserves only the central column of the LampBase
    (X ∈ [-25, +25], Y ∈ [-55, +20]); the Pi-mount bosses, motor-driver
    mount bosses, and outer shell walls of the original LeLamp are all
    discarded so we can replace them with Jetson-Nano-friendly equivalents.

    The result is in original LampBase coordinates (z = -4 → +36).  Callers
    apply ``CRADLE_INSERT_Z_OFFSET_MM`` (+4) to align z=0 with the new
    shell's open-bottom face.
    """
    import manifold3d as m3
    import trimesh

    path = ORIGINAL_PRINT_DIR / "LampBase.3mf"
    scene = trimesh.load(path, force="scene")
    sub_meshes: list[trimesh.Trimesh] = []
    for g in scene.geometry.values():
        h = g.copy()
        h.apply_scale(1000.0)
        sub_meshes.append(h)
    full = trimesh.util.concatenate(sub_meshes)

    verts = np.asarray(full.vertices, dtype=np.float32)
    tris = np.asarray(full.faces, dtype=np.uint32)
    mesh_obj = m3.Mesh(vert_properties=verts, tri_verts=tris)
    full_manif = m3.Manifold(mesh_obj)

    crop_w = 2.0 * CRADLE_INSERT_X_HALF_MM
    crop_d = CRADLE_INSERT_Y_MAX_MM - CRADLE_INSERT_Y_MIN_MM
    crop_h = 50.0
    crop_box = m3.Manifold.cube([crop_w, crop_d, crop_h], center=False)
    crop_box = crop_box.translate(
        [-CRADLE_INSERT_X_HALF_MM, CRADLE_INSERT_Y_MIN_MM, -5.0]
    )
    return m3.Manifold.batch_boolean(
        [full_manif, crop_box], m3.OpType.Intersect
    )


def build_integrated_lampbase_shell() -> TriangleMesh:
    """v7.2 LeLamp-faithful electronics shell — clean cradle handover.

    The cradle is the **original LeLamp ``LampBase.3mf``** inner-cavity
    geometry cropped wholesale (X ± 76 mm, Y -79..+104, Z full) and embedded
    as a fixed Manifold asset — bit-identical to the upstream design.

    v7.2 fixes the v7.0/7.1 mistakes:

      * v7.0/7.1 cut sharp-cornered rectangular cube cutters at MISMEASURED
        positions (the to_2D-shifted Y ≈ -25.7 and +4.9) into the new shell's
        top slab.  In raw 3D coords those openings actually live at Y = 0
        and Y = +30.6, and they're not sharp rectangles — the cable slit is a
        stadium/capsule shape (123 polyline points!).
      * v7.2 stops cutting cube openings entirely.  Instead the new shell's
        top slab gets a large rectangular hole spanning the cradle insert's
        XY footprint, and the cradle insert's own top slab (with its native
        rounded openings, Φ19.2 idle pocket on bottom, all the original
        details) fills that hole when unioned.  The two slabs are at the
        same z (38..40), giving a flush continuous top.

    Build steps:
      1. New outer hollow shell (190 × 230 × 40 mm with 2 mm top slab).
      2. Cut a large rectangular hole in the top slab matching the cradle
         insert's footprint so the cradle insert's natural openings can show
         through.
      3. Load the cradle insert, shift it up by ``CRADLE_INSERT_Z_OFFSET_MM``
         (+4) to align Z with the new shell.
      4. Union with cradle insert.
      5. Subtract side-wall vents + back I/O window + button holes.
      6. Add minimal SHORT internal standoffs (no full-height columns —
         original LeLamp's internal bosses are 6–8 mm tall and they come
         along with the cradle insert).
    """
    import manifold3d as m3

    outer_w, outer_d, outer_h = INTEGRATED_BASE_OUTER_MM
    cy_offset = INTEGRATED_BASE_Y_CENTER_MM
    top_t = INTEGRATED_BASE_TOP_THICKNESS_MM
    wall_t = INTEGRATED_BASE_WALL_MM
    radius = INTEGRATED_BASE_CORNER_RADIUS_MM

    # 1) Build new outer hollow shell, then mirror Z so the closed face is up.
    base_shell = _hollow_rounded_box(
        "AILamp_LampBase_Electronics_Shell",
        outer_w=outer_w,
        outer_d=outer_d,
        outer_h=outer_h,
        wall_t=wall_t,
        bottom_t=top_t,
        outer_radius=radius,
        cy_offset=cy_offset,
        segments=ROUNDED_CORNER_SEGMENTS,
    )
    shell = _trianglemesh_to_manifold(base_shell)
    shell = shell.scale([1.0, 1.0, -1.0]).translate([0.0, 0.0, outer_h])

    # 2) Cut a large rectangular hole through the top slab that exposes the
    #    entire cradle-insert XY footprint, so the insert's native top (with
    #    its rounded original openings) takes over in that region.
    crop_w = 2.0 * CRADLE_INSERT_X_HALF_MM
    crop_d = CRADLE_INSERT_Y_MAX_MM - CRADLE_INSERT_Y_MIN_MM
    top_hole = m3.Manifold.cube([crop_w, crop_d, top_t + 1.0], center=False)
    top_hole = top_hole.translate(
        [
            -CRADLE_INSERT_X_HALF_MM,
            CRADLE_INSERT_Y_MIN_MM,
            outer_h - top_t - 0.5,
        ]
    )
    shell = shell - top_hole

    # 3) Load original cradle insert and shift it into v7 coords.
    cradle_insert = _load_lelamp_cradle_insert()
    cradle_insert = cradle_insert.translate([0.0, 0.0, CRADLE_INSERT_Z_OFFSET_MM])

    # 4) Union new shell with the cradle insert — the cradle insert's native
    #    top slab fills the rectangular hole we cut, bringing its rounded
    #    openings exactly as they are in the original LampBase.3mf.
    shell = m3.Manifold.batch_boolean([shell, cradle_insert], m3.OpType.Add)

    # 5) Subtract side-wall vents + back I/O window + button holes.
    shell = shell - _shell_vent_slot_cutters()

    # 6) Convert and add minimal SHORT internal standoffs (Jetson + driver,
    #    8 mm and 7 mm tall respectively, hanging from the top floor — no
    #    full-height columns).  The cover-to-shell case-screws use the
    #    original LampBase's existing corner bosses (already in the insert).
    tm = _manifold_to_trianglemesh("AILamp_LampBase_Electronics_Shell", shell)
    tm.extend_triangle_mesh(_integrated_base_internal_features())
    return _merge_duplicate_vertices(tm)


def build_integrated_lampbase_cover() -> TriangleMesh:
    """v6 LeLamp-style cover plate: a 6 mm bottom panel that closes the shell.

    Two-layer shape, mirroring the original ``LampBase - Cover.3mf`` topology:

      * ``z = 0`` → ``z = COVER_FLANGE_THICKNESS_MM`` : the *flange* — full
        outer footprint, exposed at the bottom of the assembled lamp.
      * ``z = COVER_FLANGE_THICKNESS_MM`` → ``z = COVER_TOTAL_THICKNESS_MM`` :
        the *lip* — inset by ``COVER_LIP_INSET_MM`` from the shell's interior
        cavity so it slides into the shell's open bottom with a small
        registration gap.

    Four corner Ø-cleared bores pierce the full 6 mm thickness for the
    case-screws that thread up into the shell's internal bosses.  No
    central horn-anchor holes and no cable hole — the motor + horn interface
    lives entirely on the shell side in v6.
    """
    import manifold3d as m3

    outer_w = INTEGRATED_BASE_COVER_MM[0]
    outer_d = INTEGRATED_BASE_COVER_MM[1]
    flange_t = COVER_FLANGE_THICKNESS_MM
    lip_t = COVER_LIP_HEIGHT_MM
    cy_offset = INTEGRATED_BASE_Y_CENTER_MM
    plate_radius = INTEGRATED_BASE_COVER_CORNER_RADIUS_MM
    segments = ROUNDED_CORNER_SEGMENTS

    # Lip footprint = shell inner cavity − COVER_LIP_INSET on each side.
    cavity_w = INTEGRATED_BASE_OUTER_MM[0] - 2.0 * INTEGRATED_BASE_WALL_MM
    cavity_d = INTEGRATED_BASE_OUTER_MM[1] - 2.0 * INTEGRATED_BASE_WALL_MM
    lip_w = cavity_w - 2.0 * COVER_LIP_INSET_MM
    lip_d = cavity_d - 2.0 * COVER_LIP_INSET_MM
    lip_radius = max(plate_radius - INTEGRATED_BASE_WALL_MM - COVER_LIP_INSET_MM, 4.0)

    flange_pts = _rounded_rect_polygon(outer_w, outer_d, plate_radius, segments, cy=cy_offset)
    lip_pts = _rounded_rect_polygon(lip_w, lip_d, lip_radius, segments, cy=cy_offset)

    cover = TriangleMesh("AILamp_LampBase_Electronics_Cover")
    # Flange bottom face — full outer perimeter, no holes (corner-screw holes
    # are cut later via manifold3d for a clean watertight result).
    cover.extend_triangle_mesh(
        _holey_cap("cover_flange_bottom", flange_pts, [], z=0.0, facing_up=False)
    )
    # Flange outer wall (z = 0 → z = flange_t).
    cover.extend_triangle_mesh(
        _extruded_wall("cover_flange_outer", flange_pts, 0.0, flange_t, outward=True)
    )
    # Step top: annulus from flange perimeter inward to lip perimeter at z = flange_t.
    cover.extend_triangle_mesh(
        _annular_strip(
            "cover_step_top", flange_pts, lip_pts, flange_t, facing_up=True,
        )
    )
    # Lip outer wall (z = flange_t → z = flange_t + lip_t).
    cover.extend_triangle_mesh(
        _extruded_wall(
            "cover_lip_outer", lip_pts, flange_t, flange_t + lip_t, outward=True,
        )
    )
    # Lip top cap.
    cover.extend_triangle_mesh(
        _holey_cap(
            "cover_lip_top", lip_pts, [], z=flange_t + lip_t, facing_up=True,
        )
    )

    # Convert to manifold3d and punch the 4 corner case-screw bores.
    cover_manif = _trianglemesh_to_manifold(cover)
    total_h = flange_t + lip_t
    for cx, cy in INTEGRATED_BASE_CASE_SCREW_POSITIONS_MM:
        bore = m3.Manifold.cylinder(
            total_h + 1.0,
            COVER_CASE_SCREW_CLEARANCE_RADIUS_MM,
            COVER_CASE_SCREW_CLEARANCE_RADIUS_MM,
            32,
            center=False,
        )
        bore = bore.translate([cx, cy, -0.5])
        cover_manif = cover_manif - bore

    cover = _manifold_to_trianglemesh("AILamp_LampBase_Electronics_Cover", cover_manif)
    cover = _merge_duplicate_vertices(cover)
    return cover


def build_jetson_tray() -> Mesh:
    mesh = Mesh("AILamp_Jetson_Nano_Base_Tray")
    outer = (122.0, 102.0, 12.0)
    _base_plate(mesh, outer, 3.0)
    _edge_rails(mesh, outer, 4.0, 9.0, 3.0)
    mesh.subtract_box(0.0, -49.0, 7.5, 44.0, 10.0, 12.0)
    for x in (-42.0, 42.0):
        for y in (-32.0, 32.0):
            mesh.add_box(x, y, 5.0, 8.0, 8.0, 4.0)
            mesh.subtract_box(x, y, 5.0, 3.2, 3.2, 10.0)
    for y in (-42.0, 42.0):
        mesh.subtract_box(0.0, y, 1.5, ZIP_TIE_SLOT_MM[0], ZIP_TIE_SLOT_MM[1], 6.0)
    return mesh


def build_electronics_side_deck() -> Mesh:
    mesh = Mesh("AILamp_Electronics_Side_Deck")
    outer = (145.0, 48.0, 10.0)
    _base_plate(mesh, outer, 3.0)
    mesh.add_box(-36.5, 21.0, 6.5, 72.0, 4.0, 7.0)
    mesh.add_box(-36.5, -21.0, 6.5, 72.0, 4.0, 7.0)
    mesh.add_box(37.0, 21.0, 6.5, 62.0, 4.0, 7.0)
    mesh.add_box(37.0, -21.0, 6.5, 62.0, 4.0, 7.0)
    mesh.add_box(0.0, 0.0, 5.0, 5.0, 42.0, 4.0)
    for x in (-66.0, -7.0, 18.0, 64.0):
        mesh.add_box(x, 0.0, 5.0, 6.0, 8.0, 4.0)
    for x in (
        -36.5 - SERVO_DRIVER_MOUNT_HOLE_MM[0] / 2.0,
        -36.5 + SERVO_DRIVER_MOUNT_HOLE_MM[0] / 2.0,
    ):
        for y in (
            -SERVO_DRIVER_MOUNT_HOLE_MM[1] / 2.0,
            SERVO_DRIVER_MOUNT_HOLE_MM[1] / 2.0,
        ):
            mesh.subtract_box(x, y, 2.0, 3.4, 3.4, 8.0)
    mesh.subtract_box(68.0, -21.0, 6.5, PICO_USB_RELIEF_MM[0], 10.0, 10.0)
    mesh.subtract_box(37.0, 0.0, 1.5, 38.0, 4.0, 6.0)
    return mesh


def build_cable_clip(
    name: str, channel_width_mm: float, outer_mm: tuple[float, float, float]
) -> Mesh:
    mesh = Mesh(name)
    sx, sy, sz = outer_mm
    wall = max(3.0, (sx - channel_width_mm) / 2.0)
    _base_plate(mesh, outer_mm, 2.5)
    mesh.add_box(-sx / 2.0 + wall / 2.0, 0.0, sz / 2.0, wall, sy, sz - 2.5)
    mesh.add_box(sx / 2.0 - wall / 2.0, 0.0, sz / 2.0, wall, sy, sz - 2.5)
    mesh.add_box(0.0, -sy / 2.0 + 2.0, sz / 2.0, sx, 4.0, sz - 2.5)
    mesh.add_box(0.0, sy / 2.0 - 1.5, sz - 1.0, sx, 3.0, 2.0)
    mesh.subtract_box(0.0, 0.0, 1.25, sx - 8.0, 4.0, 5.0)
    return mesh


def generate_all(output_dir: Path | str = Path("3D/AILamp_Adapters")) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    builders = {
        "AILamp_LampBase_Electronics_Shell": build_integrated_lampbase_shell,
        "AILamp_LampBase_Electronics_Cover": build_integrated_lampbase_cover,
        "AILamp_Jetson_Nano_Base_Tray": build_jetson_tray,
        "AILamp_Electronics_Side_Deck": build_electronics_side_deck,
        "AILamp_Cable_Clip_6mm": lambda: build_cable_clip(
            "AILamp_Cable_Clip_6mm",
            _loose_cable_channel_width(6.0),
            (24.0, 18.0, 8.0),
        ),
        "AILamp_Cable_Clip_10mm": lambda: build_cable_clip(
            "AILamp_Cable_Clip_10mm",
            _loose_cable_channel_width(10.0),
            (30.0, 22.0, 10.0),
        ),
    }
    expected_files = {
        output / f"{name}{suffix}"
        for name in builders
        for suffix in (".3mf", ".stl")
    }
    for stale_path in output.glob("AILamp_*"):
        if stale_path.suffix in {".3mf", ".stl"} and stale_path not in expected_files:
            stale_path.unlink()

    written: list[Path] = []
    for spec in adapter_specs():
        mesh = builders[spec.name]()
        stl_path = output / f"{spec.name}.stl"
        model_path = output / f"{spec.name}.3mf"
        mesh.write_3mf(model_path)
        mesh.write_stl(stl_path)
        written.extend([model_path, stl_path])
    return written


if __name__ == "__main__":
    for generated_path in generate_all():
        print(generated_path)
