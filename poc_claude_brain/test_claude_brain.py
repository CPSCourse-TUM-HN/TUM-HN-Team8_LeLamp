"""Claude 大脑 PoC 单元测试 — 不需要网络、API key 或 mujoco。

运行: PYTHONPATH=ailamp_runtime python3 -m pytest poc_claude_brain/ -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from claude_brain import (  # noqa: E402
    MAX_DELTA_PER_TICK_DEG,
    ClaudeBrain,
    DryRunOutputs,
    FakeCamera,
    MockAnthropic,
    SafetyGate,
    brain_tools,
)
from ailamp.services.behavior import BehaviorService  # noqa: E402


RECORDINGS = ["idle", "nod", "wake_up", "shy"]


def make_brain(client=None) -> tuple[ClaudeBrain, DryRunOutputs]:
    outputs = DryRunOutputs()
    brain = ClaudeBrain(
        model="test-model",
        client=client or MockAnthropic(),
        gate=SafetyGate(RECORDINGS),
        outputs=outputs,
        behavior=BehaviorService(),
        tools=brain_tools(RECORDINGS),
    )
    return brain, outputs


# ---------------------------------------------------------------- SafetyGate

def test_gate_clamps_oversized_delta_and_drops_unknown_joint():
    gate = SafetyGate(RECORDINGS)
    deltas = gate.clamp_deltas({"base_yaw": -30.0, "unknown_joint": 5.0, "wrist_pitch": "junk"})
    assert deltas == {"base_yaw": -MAX_DELTA_PER_TICK_DEG}


def test_gate_rejects_unknown_recording():
    gate = SafetyGate(RECORDINGS)
    assert gate.valid_recording("nod")
    assert not gate.valid_recording("rm -rf /")


def test_gate_clamps_rgb():
    assert SafetyGate.clamp_rgb(300, -5, "80") == (255, 0, 80)
    assert SafetyGate.clamp_rgb(None, 10, 10) == (0, 10, 10)


# ---------------------------------------------------------------- tick 执行

def test_mock_script_runs_full_pipeline_with_safety():
    brain, outputs = make_brain()
    camera = FakeCamera()

    r1 = brain.tick(camera.jpeg())            # wake_up + light
    r2 = brain.tick(camera.jpeg())            # 越界 base_yaw -30 → 钳到 -8, unknown joint 丢弃
    r3 = brain.tick(camera.jpeg())            # 正常小步
    r4 = brain.tick(camera.jpeg())            # do_nothing

    assert not r1.degraded and r1.actions == ["play wake_up", "light (255, 235, 190)"]
    assert outputs.log[0] == "play wake_up"
    assert f"move {{'base_yaw': -{MAX_DELTA_PER_TICK_DEG}}}" == outputs.log[2]
    assert r2.actions == [f"move base_yaw:-{MAX_DELTA_PER_TICK_DEG:.1f}"]
    assert r3.actions == ["move base_yaw:+4.0,wrist_pitch:+2.0"]
    assert r4.actions and r4.actions[0].startswith("idle")
    assert brain.frame_index == 4
    assert len(brain.history) == 4


def test_at_most_two_tool_calls_executed():
    class ThreeToolClient(MockAnthropic):
        _SCRIPT = [[
            ("set_light", {"red": 1, "green": 2, "blue": 3}),
            ("play_recording", {"name": "nod"}),
            ("play_recording", {"name": "shy"}),   # 第 3 个应被忽略
        ]]

    brain, outputs = make_brain(ThreeToolClient())
    result = brain.tick(FakeCamera().jpeg())
    assert result.actions == ["light (1, 2, 3)", "play nod"]
    assert "play shy" not in outputs.log


def test_api_failure_falls_back_to_local_behavior_and_keeps_loop_alive():
    class ExplodingClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise ConnectionError("network down")

    brain, outputs = make_brain(ExplodingClient())
    result = brain.tick(FakeCamera().jpeg())

    assert result.degraded
    assert result.actions and result.actions[0].startswith("local_fallback")
    assert outputs.log == ["light (30, 30, 80)"]   # 本地 no_person 兜底色
    assert brain.frame_index == 1                  # 循环继续，不抛异常


def test_unknown_tool_is_dropped():
    class WeirdClient(MockAnthropic):
        _SCRIPT = [[("format_disk", {"target": "/"}), ("play_recording", {"name": "nod"})]]

    brain, outputs = make_brain(WeirdClient())
    result = brain.tick(FakeCamera().jpeg())
    assert result.actions == ["play nod"]
    assert outputs.log == ["play nod"]


def test_tools_schema_covers_all_joints_and_recordings():
    tools = brain_tools(RECORDINGS)
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name) == {"move_joints", "play_recording", "set_light", "do_nothing"}
    joint_props = by_name["move_joints"]["input_schema"]["properties"]
    assert set(joint_props) == {"base_yaw", "base_pitch", "elbow_pitch", "wrist_roll", "wrist_pitch"}
    assert "nod" in by_name["play_recording"]["description"]


def test_fake_camera_produces_decodable_jpeg():
    from PIL import Image
    import io

    data = FakeCamera().jpeg()
    image = Image.open(io.BytesIO(data))
    assert image.size == (512, 384)
