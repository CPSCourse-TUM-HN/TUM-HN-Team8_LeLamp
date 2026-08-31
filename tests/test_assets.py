from pathlib import Path
import struct

from ailamp.services.motor import RecordingStore


def test_required_assets_and_recordings_are_present():
    root = Path(__file__).resolve().parents[1]

    assert (root / "simulation/scene.xml").exists()
    assert (root / "simulation/ailamp_scene.xml").exists()
    assert (root / "simulation/robot.xml").exists()
    assert (root / "simulation/ailamp_robot.xml").exists()
    assert (root / "simulation/assets/lamp_head.stl").exists()
    assert (root / "3D/LampHead.3mf").exists()
    adapter_dir = root / "3D/AILamp_Adapters"
    simulation_adapter_dir = root / "simulation/assets/ailamp_adapters"
    assert (adapter_dir / "AILamp_LampBase_Electronics_Shell.3mf").exists()
    assert (adapter_dir / "AILamp_LampBase_Electronics_Cover.3mf").exists()
    assert (adapter_dir / "AILamp_Jetson_Nano_Base_Tray.3mf").exists()
    assert (adapter_dir / "AILamp_Electronics_Side_Deck.3mf").exists()
    assert (adapter_dir / "AILamp_Cable_Clip_6mm.3mf").exists()
    assert (adapter_dir / "AILamp_Cable_Clip_10mm.3mf").exists()
    for stl_file in adapter_dir.glob("*.stl"):
        simulation_stl = simulation_adapter_dir / stl_file.name
        assert simulation_stl.exists()
        data = simulation_stl.read_bytes()
        assert data[:28].startswith(b"AILamp MuJoCo binary STL")
        assert struct.unpack("<I", data[80:84])[0] > 0
        assert (len(data) - 84) % 50 == 0

    recordings = RecordingStore(root / "ailamp_runtime/ailamp/recordings")
    names = recordings.list_names()
    assert {"wake_up", "idle", "nod", "scanning", "shy"}.issubset(set(names))

    wake_up = recordings.load("wake_up")
    assert wake_up
    assert set(wake_up[0]) == {
        "base_yaw.pos",
        "base_pitch.pos",
        "elbow_pitch.pos",
        "wrist_roll.pos",
        "wrist_pitch.pos",
    }
