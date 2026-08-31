"""Claude 大脑 PoC — 用 Claude API (tool use) 直接驱动 AILamp。

架构（分层控制）：
    摄像头/仿真帧 ──► Claude (每 tick 一次 API 调用, 视觉+状态 → 工具调用)
                          │  move_joints / play_recording / set_light / do_nothing
                          ▼
                     SafetyGate（关节限位 + 单步限幅 + 动作名白名单 + 频率限制）
                          ▼
                     MotorBackend（DryRun / MuJoCo 仿真 / 真机 LeLamp ST3215）+ LED

安全设计：Claude 永远不直接碰硬件 —— 它只能提出意图，所有输出都经过本地
SafetyGate 钳位；API 失败/超时时自动回退到本地 BehaviorService 规则，循环不死。

运行方式（在仓库根目录）：
    # 1. 干跑（无硬件无 mujoco，假摄像头，需要 ANTHROPIC_API_KEY）
    PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode dry --frames 5

    # 2. MuJoCo 仿真闭环（Claude 看的是仿真渲染画面，动作写回仿真）
    MUJOCO_GL=egl PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode sim --frames 5

    # 3. 无 API key 的管线自检（脚本化假 Claude，验证全链路）
    PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode sim --mock --frames 4

    # 4. Jetson 真机（需 lelamp_runtime + 串口）
    PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode real --frames 20
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ailamp.config import load_hardware_config
from ailamp.models import VisionEvent, VisionEventType
from ailamp.paths import resolve_project_path
from ailamp.services.behavior import BehaviorService
from ailamp.services.motor import DEFAULT_JOINT_LIMITS_DEG, JointSafetyLimiter, RecordingStore


logger = logging.getLogger("claude_brain")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"   # 最快、最便宜、带视觉；可用 --model 换 claude-sonnet-5
MAX_DELTA_PER_TICK_DEG = 8.0                  # 单个 tick 单关节最大转角（叠加在绝对限位之上）
MAX_HISTORY_TICKS = 8                         # 滚动上下文里保留的历史 tick 摘要条数
API_TIMEOUT_S = 20.0

JOINTS = list(DEFAULT_JOINT_LIMITS_DEG)


# --------------------------------------------------------------------------- tools

def brain_tools(recording_names: list[str]) -> list[dict]:
    """Anthropic tool use 的工具定义。每个 tick Claude 从这里选 1~2 个动作。"""
    joint_props = {
        joint: {
            "type": "number",
            "description": f"{joint} 增量角度(度)，正负均可，绝对限位 {DEFAULT_JOINT_LIMITS_DEG[joint]}，单步会被钳到 ±{MAX_DELTA_PER_TICK_DEG}°",
        }
        for joint in JOINTS
    }
    return [
        {
            "name": "move_joints",
            "description": "微调一个或多个关节角度（相对增量，度）。用于跟踪人、调整头部朝向。小步慢动，保持台灯动作优雅。",
            "input_schema": {"type": "object", "properties": joint_props, "additionalProperties": False},
        },
        {
            "name": "play_recording",
            "description": f"播放一段预录制的整体动作。可选：{', '.join(recording_names)}",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "录制动作名"}},
                "required": ["name"],
            },
        },
        {
            "name": "set_light",
            "description": "设置 8x8 NeoPixel 灯板的纯色 (0-255)。配合动作表达情绪。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "red": {"type": "integer", "minimum": 0, "maximum": 255},
                    "green": {"type": "integer", "minimum": 0, "maximum": 255},
                    "blue": {"type": "integer", "minimum": 0, "maximum": 255},
                },
                "required": ["red", "green", "blue"],
            },
        },
        {
            "name": "do_nothing",
            "description": "画面没有值得反应的变化时保持不动（这是很好的选择，不要坐立不安）。",
            "input_schema": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    ]


SYSTEM_PROMPT = """你是 AILamp——一盏有性格的桌面机器人台灯（5 自由度机械臂 + 8x8 RGB 灯板 + 摄像头）。
你通过摄像头帧观察书桌前的人，每个 tick 用工具做出至多 2 个物理反应。

性格：好奇、温柔、克制。像宠物而不是监控器。

行为准则：
1. 有人进入/离开/明显移动、做手势、表情变化时才反应；画面几乎没变就 do_nothing。
2. 跟踪人用 move_joints 小步转动（base_yaw 朝人的方向；人近了 wrist_pitch 后仰，人远了前倾）。
3. 表达情绪用 play_recording（nod=点头, shy=害羞, happy_wiggle=开心摇摆, curious=好奇, headshake=摇头, scanning=张望, idle=待机, wake_up=唤醒, excited=兴奋, sad=难过, shock=惊讶）。
4. 灯光低调：暖光工作 (255,235,190)，情绪时短暂换色，无人时暗蓝 (30,30,80)。
5. 用户的语音指令优先级最高。
6. 安全：动作幅度小、频率低。你每次输出都会被本地安全层钳位，超限指令会被截断。
只输出工具调用，不要输出多余文字。"""


# --------------------------------------------------------------------------- actions & safety

@dataclass
class TickResult:
    frame_index: int
    actions: list[str] = field(default_factory=list)
    degraded: bool = False
    latency_s: float = 0.0

    def format(self) -> str:
        status = "degraded→local_fallback" if self.degraded else "claude"
        acts = "; ".join(self.actions) or "none"
        return f"tick={self.frame_index} src={status} latency={self.latency_s:.2f}s actions=[{acts}]"


class SafetyGate:
    """所有 Claude 指令的强制关卡：白名单 + 限幅 + 限位。"""

    def __init__(self, recording_names: list[str]):
        self.limiter = JointSafetyLimiter()
        self.recording_names = set(recording_names)

    def clamp_deltas(self, raw: dict[str, Any]) -> dict[str, float]:
        deltas: dict[str, float] = {}
        for joint, value in raw.items():
            if joint not in DEFAULT_JOINT_LIMITS_DEG:
                logger.warning("SafetyGate: 丢弃未知关节 %r", joint)
                continue
            try:
                step = float(value)
            except (TypeError, ValueError):
                logger.warning("SafetyGate: 丢弃非数值增量 %r=%r", joint, value)
                continue
            deltas[joint] = max(-MAX_DELTA_PER_TICK_DEG, min(MAX_DELTA_PER_TICK_DEG, step))
        return deltas

    def valid_recording(self, name: str) -> bool:
        return name in self.recording_names

    @staticmethod
    def clamp_rgb(red: Any, green: Any, blue: Any) -> tuple[int, int, int]:
        def _c(v: Any) -> int:
            try:
                return max(0, min(255, int(v)))
            except (TypeError, ValueError):
                return 0
        return (_c(red), _c(green), _c(blue))


# --------------------------------------------------------------------------- cameras

class FakeCamera:
    """无硬件时的合成画面：一个在桌前左右移动的人形色块，足够让 Claude 理解场景。"""

    def __init__(self, width: int = 512, height: int = 384):
        self.width, self.height, self._t = width, height, 0

    def jpeg(self) -> bytes:
        from PIL import Image, ImageDraw

        self._t += 1
        img = Image.new("RGB", (self.width, self.height), (40, 42, 54))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, self.height - 60, self.width, self.height], fill=(90, 70, 50))  # 桌面
        cx = int(self.width * (0.5 + 0.35 * ((self._t % 8) - 4) / 4.0))                    # 左右走动
        draw.ellipse([cx - 28, 90, cx + 28, 146], fill=(224, 190, 160))                    # 头
        draw.rectangle([cx - 45, 146, cx + 45, self.height - 60], fill=(70, 110, 170))     # 身体
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()


class SimCamera:
    """MuJoCo 渲染画面作为 Claude 的眼睛（需要 MUJOCO_GL=egl/osmesa）。"""

    def __init__(self, runner, out_dir: Path):
        self.runner = runner
        self.out_dir = out_dir
        self._i = 0

    def jpeg(self) -> bytes:
        from PIL import Image

        self._i += 1
        png = self.out_dir / f"brain_sim_frame_{self._i:03d}.png"
        self.runner.render(png, width=640, height=480, camera_name="ailamp_overview_camera")
        buf = io.BytesIO()
        Image.open(png).convert("RGB").save(buf, format="JPEG", quality=80)
        return buf.getvalue()


class RealCamera:
    def __init__(self, config):
        from ailamp.services.camera import CameraService

        self.service = CameraService(
            config.camera.device_path, config.camera.width, config.camera.height,
            config.camera.fps, config.camera.pixel_format,
        )
        self.service.open()
        self.max_px = config.vision.api_image_max_px

    def jpeg(self) -> bytes:
        from ailamp.services.api_vision import _encode_frame_as_jpeg

        frame = self.service.read()
        if frame is None:
            raise OSError("camera returned no frame")
        return _encode_frame_as_jpeg(frame, self.max_px)


# --------------------------------------------------------------------------- output backends

class DryRunOutputs:
    def __init__(self):
        self.log: list[str] = []

    def move(self, deltas: dict[str, float]) -> None:
        self.log.append(f"move {deltas}")
        print(f"    [dry-run] 关节增量: {deltas}")

    def play(self, name: str) -> None:
        self.log.append(f"play {name}")
        print(f"    [dry-run] 播放动作: {name}")

    def light(self, rgb: tuple[int, int, int]) -> None:
        self.log.append(f"light {rgb}")
        print(f"    [dry-run] 灯光: {rgb}")

    def close(self) -> None:
        pass


class SimOutputs:
    """写入 MuJoCo 仿真（复用 runtime 的 MujocoMotorBackend）。"""

    def __init__(self, runner, recordings_dir: Path):
        from ailamp.services.motor_backend import MujocoMotorBackend

        self.backend = MujocoMotorBackend(runner, recordings_dir)
        self.backend.connect()

    def move(self, deltas: dict[str, float]) -> None:
        from ailamp.services.motor import JointDeltaCommand

        commands = [JointDeltaCommand(j, d) for j, d in deltas.items()]
        state = self.backend.apply_joint_deltas(commands)
        print(f"    [sim] 关节目标: { {k: round(v, 1) for k, v in state.items()} }")

    def play(self, name: str) -> None:
        self.backend.play(name)
        print(f"    [sim] 播放动作: {name}")

    def light(self, rgb: tuple[int, int, int]) -> None:
        print(f"    [sim] 灯光: {rgb}")

    def close(self) -> None:
        self.backend.close()


class RealOutputs:
    """真机：LeLamp ST3215 总线 + Pico LED 串口。"""

    def __init__(self, config):
        from ailamp.services.led_serial import LEDSerialService
        from ailamp.services.motor_backend import LeLampMotorBackend

        self.backend = LeLampMotorBackend(
            port=config.motors.port,
            lamp_id=config.system.project_name.lower(),
            recordings_dir=resolve_project_path(config.simulation.recordings_dir),
        )
        self.led = LEDSerialService(config.led.port, config.led.count, config.led.baudrate)
        self.backend.connect()
        self.led.connect()

    def move(self, deltas: dict[str, float]) -> None:
        from ailamp.services.motor import JointDeltaCommand

        self.backend.apply_joint_deltas([JointDeltaCommand(j, d) for j, d in deltas.items()])

    def play(self, name: str) -> None:
        self.backend.play(name)

    def light(self, rgb: tuple[int, int, int]) -> None:
        self.led.solid(*rgb)

    def close(self) -> None:
        self.backend.close()
        self.led.close()


# --------------------------------------------------------------------------- mock client

class MockAnthropic:
    """无 API key 时验证全链路的脚本化假 Claude（含一条越界指令测试 SafetyGate）。"""

    class _Block:
        def __init__(self, name, input):
            self.type, self.name, self.input = "tool_use", name, input

    class _Msg:
        def __init__(self, blocks):
            self.content = blocks

    _SCRIPT = [
        [("play_recording", {"name": "wake_up"}), ("set_light", {"red": 255, "green": 235, "blue": 190})],
        [("move_joints", {"base_yaw": -30.0, "unknown_joint": 5})],   # 越界+未知关节 → 应被钳位/丢弃
        [("move_joints", {"base_yaw": 4.0, "wrist_pitch": 2.0})],
        [("do_nothing", {"reason": "scene unchanged"})],
    ]

    def __init__(self):
        self._i = 0
        self.messages = self

    def create(self, **kwargs):
        script = self._SCRIPT[self._i % len(self._SCRIPT)]
        self._i += 1
        return self._Msg([self._Block(name, dict(input)) for name, input in script])


# --------------------------------------------------------------------------- brain

class ClaudeBrain:
    def __init__(self, *, model: str, client, gate: SafetyGate, outputs, behavior: BehaviorService, tools: list[dict]):
        self.model = model
        self.client = client
        self.gate = gate
        self.outputs = outputs
        self.behavior = behavior
        self.tools = tools
        self.history: list[str] = []
        self.frame_index = 0

    def tick(self, frame_jpeg: bytes, user_text: str | None = None) -> TickResult:
        result = TickResult(frame_index=self.frame_index)
        started = time.monotonic()
        try:
            blocks = self._ask_claude(frame_jpeg, user_text)
            result.actions = self._execute(blocks)
        except Exception as exc:  # API/网络/解析失败 → 本地规则兜底，循环不死
            logger.warning("Claude tick failed, falling back to local behavior: %s", exc)
            result.degraded = True
            action = self.behavior.decide(VisionEvent(VisionEventType.NO_PERSON, semantic_reason=f"brain_error:{exc}"))
            self.outputs.light(action.rgb)
            result.actions = [f"local_fallback light={action.rgb}"]
        result.latency_s = time.monotonic() - started
        self.history.append(f"tick {self.frame_index}: " + ("; ".join(result.actions) or "none"))
        self.history = self.history[-MAX_HISTORY_TICKS:]
        self.frame_index += 1
        return result

    def _ask_claude(self, frame_jpeg: bytes, user_text: str | None):
        state_lines = ["最近动作历史:"] + [f"  {line}" for line in self.history[-MAX_HISTORY_TICKS:]]
        if user_text:
            state_lines.append(f"用户语音指令（最高优先级）: {user_text}")
        state_lines.append("这是当前摄像头画面，请决定这个 tick 的反应（至多 2 个工具调用）。")
        message = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            tools=self.tools,
            tool_choice={"type": "auto"},
            timeout=API_TIMEOUT_S,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(frame_jpeg).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": "\n".join(state_lines)},
                    ],
                }
            ],
        )
        return [block for block in message.content if getattr(block, "type", None) == "tool_use"]

    def _execute(self, blocks) -> list[str]:
        actions: list[str] = []
        for block in blocks[:2]:  # 每 tick 至多执行 2 个动作
            name, args = block.name, dict(block.input or {})
            if name == "move_joints":
                deltas = self.gate.clamp_deltas(args)
                if deltas:
                    self.outputs.move(deltas)
                    actions.append("move " + ",".join(f"{j}:{d:+.1f}" for j, d in deltas.items()))
            elif name == "play_recording":
                rec = str(args.get("name", ""))
                if self.gate.valid_recording(rec):
                    self.outputs.play(rec)
                    actions.append(f"play {rec}")
                else:
                    logger.warning("SafetyGate: 丢弃未知动作名 %r", rec)
            elif name == "set_light":
                rgb = self.gate.clamp_rgb(args.get("red"), args.get("green"), args.get("blue"))
                self.outputs.light(rgb)
                actions.append(f"light {rgb}")
            elif name == "do_nothing":
                actions.append(f"idle ({args.get('reason', '')})")
            else:
                logger.warning("SafetyGate: 丢弃未知工具 %r", name)
        return actions


# --------------------------------------------------------------------------- main

def build(args) -> tuple[ClaudeBrain, Any, Any]:
    config = load_hardware_config(args.config)
    recordings_dir = resolve_project_path(config.simulation.recordings_dir)
    recording_names = RecordingStore(recordings_dir).list_names()
    gate = SafetyGate(recording_names)
    behavior = BehaviorService.from_config(config)

    runner = None
    if args.mode == "sim":
        from ailamp.simulation.mujoco_runner import MujocoRunner

        runner = MujocoRunner(config.simulation.model_path, lock_freejoint=config.simulation.lock_freejoint)
        runner.load()
        out_dir = resolve_project_path("outputs/claude_brain")
        out_dir.mkdir(parents=True, exist_ok=True)
        camera, outputs = SimCamera(runner, out_dir), SimOutputs(runner, recordings_dir)
    elif args.mode == "real":
        camera, outputs = RealCamera(config), RealOutputs(config)
    else:
        camera, outputs = FakeCamera(), DryRunOutputs()

    if args.mock:
        client = MockAnthropic()
    else:
        import anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("需要 ANTHROPIC_API_KEY 环境变量（或加 --mock 跑脚本化演示）")
        client = anthropic.Anthropic()

    brain = ClaudeBrain(
        model=args.model, client=client, gate=gate, outputs=outputs,
        behavior=behavior, tools=brain_tools(recording_names),
    )
    return brain, camera, outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="AILamp Claude 大脑 PoC")
    parser.add_argument("--config", default="config/hardware.toml")
    parser.add_argument("--mode", choices=["dry", "sim", "real"], default="dry")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--frames", type=int, default=5, help="tick 数")
    parser.add_argument("--interval", type=float, default=3.0, help="tick 间隔秒")
    parser.add_argument("--say", default=None, help="注入一条用户语音指令（作用于第一个 tick）")
    parser.add_argument("--mock", action="store_true", help="用脚本化假 Claude 验证管线（无需 API key）")
    parser.add_argument("--max-calls", type=int, default=200, help="本次运行 API 调用上限（成本保险丝）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    brain, camera, outputs = build(args)
    transcript: list[dict] = []
    print(f"Claude 大脑启动: mode={args.mode} model={args.model if not args.mock else 'MOCK'} ticks={args.frames}")
    try:
        for i in range(min(args.frames, args.max_calls)):
            user_text = args.say if i == 0 else None
            result = brain.tick(camera.jpeg(), user_text=user_text)
            print(result.format())
            transcript.append({"tick": result.frame_index, "actions": result.actions,
                               "degraded": result.degraded, "latency_s": round(result.latency_s, 2)})
            if i + 1 < args.frames:
                time.sleep(args.interval if args.mode == "real" else min(args.interval, 0.5))
    finally:
        outputs.close()
        out = resolve_project_path("outputs/claude_brain")
        out.mkdir(parents=True, exist_ok=True)
        (out / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
        print(f"transcript → {out / 'transcript.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
