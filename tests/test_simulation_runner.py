import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from ailamp.simulation.mujoco_runner import (
    CSV_TO_ACTUATOR,
    FREEJOINT_QPOS,
    FREEJOINT_QVEL,
    RecordingControlMapper,
)
from ailamp.simulation.sim_vision import classify_virtual_target_from_joints
from ailamp.models import VisionEventType


def test_recording_control_mapper_converts_degrees_to_radians_and_clamps():
    mapper = RecordingControlMapper()
    row = {
        "base_pitch.pos": -60.0,
        "base_yaw.pos": 45.0,
        "elbow_pitch.pos": 120.0,
        "wrist_roll.pos": -30.0,
        "wrist_pitch.pos": 25.0,
    }

    controls = mapper.row_to_controls(row)

    assert set(controls) == set(CSV_TO_ACTUATOR.values())
    assert controls["1"] == pytest.approx(math.radians(45.0))
    assert controls["2"] == pytest.approx(math.radians(-60.0))
    assert controls["3"] <= 0.3215685722854582


def test_freejoint_constants_lock_base_pose():
    assert FREEJOINT_QPOS == (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    assert FREEJOINT_QVEL == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_virtual_vision_can_use_target_slide_joints():
    assert classify_virtual_target_from_joints(None).event_type == VisionEventType.NO_PERSON
    assert classify_virtual_target_from_joints({"target_slide_x": -0.6, "target_slide_y": -1.5}).event_type == VisionEventType.PERSON_LEFT
    assert classify_virtual_target_from_joints({"target_slide_x": 0.6, "target_slide_y": -1.5}).event_type == VisionEventType.PERSON_RIGHT
    assert classify_virtual_target_from_joints({"target_slide_x": 0.0, "target_slide_y": -0.45}).event_type == VisionEventType.PERSON_CLOSE
    assert classify_virtual_target_from_joints({"target_slide_x": 0.0, "target_slide_y": -3.8}).event_type == VisionEventType.PERSON_FAR


def test_ailamp_adapter_visuals_are_present_in_scene():
    root = Path(__file__).resolve().parents[1]
    scene = ET.parse(root / "simulation/ailamp_scene.xml").getroot()
    assert scene.find("include").attrib["file"] == "ailamp_robot.xml"
    derived_robot = ET.parse(root / "simulation/ailamp_robot.xml").getroot()
    derived_base_geoms = [
        geom
        for geom in derived_robot.findall(".//geom")
        if geom.attrib.get("mesh") in {"lamp_base", "lamp_base_cover"}
    ]
    assert derived_base_geoms == []

    geoms = {
        geom.attrib["name"]: geom.attrib
        for geom in scene.findall(".//geom")
        if "name" in geom.attrib
    }
    meshes = {
        mesh.attrib["name"]: mesh.attrib
        for mesh in scene.findall(".//mesh")
        if "name" in mesh.attrib
    }
    cameras = {
        camera.attrib["name"]: camera.attrib
        for camera in scene.findall(".//camera")
        if "name" in camera.attrib
    }
    welds = {
        weld.attrib["name"]: weld.attrib
        for weld in scene.findall(".//weld")
        if "name" in weld.attrib
    }

    for name in [
        "ailamp_integrated_base_shell_visual",
        "ailamp_integrated_base_cover_visual",
        "ailamp_cable_clip_6mm_visual",
        "ailamp_cable_clip_10mm_visual",
    ]:
        assert geoms[name]["type"] == "mesh"
        assert geoms[name]["mesh"] in meshes
        assert geoms[name]["contype"] == "0"
        assert geoms[name]["conaffinity"] == "0"

    base_layout = scene.find(".//body[@name='ailamp_base_layout_visuals']")
    assert base_layout is not None
    base_names = {geom.attrib["name"] for geom in base_layout.findall("geom") if "name" in geom.attrib}
    assert {
        "ailamp_integrated_base_shell_visual",
        "ailamp_integrated_base_cover_visual",
        "ailamp_cable_clip_6mm_visual",
        "ailamp_cable_clip_10mm_visual",
    }.issubset(base_names)
    assert scene.find(".//body[@name='ailamp_head_adapter_visuals']") is None
    assert "ailamp_camera_mount_visual" not in geoms
    assert "ailamp_neomatrix_visual" not in geoms

    for mesh in meshes.values():
        if mesh["name"].startswith("ailamp_"):
            assert mesh["file"].startswith("ailamp_adapters/")
            assert mesh["scale"] == "0.001 0.001 0.001"

    assert "ailamp_overview_camera" in cameras
    assert "ailamp_sim_camera" in cameras

    target_joint = scene.find(".//joint[@name='target_slide_y']")
    assert target_joint is not None
    assert target_joint.attrib["ref"] == "-1.5"

    assert welds["ailamp_lock_base_to_world"]["body1"] == "world"
    assert welds["ailamp_lock_base_to_world"]["body2"] == "lamparm__base_elbow"
