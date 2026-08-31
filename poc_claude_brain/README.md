# Claude 大脑 PoC

用 Claude API（tool use + 视觉）替代规则决策层，直接驱动 AILamp 的 5 个关节、动作录制和灯板。
详细分析见 `AILamp_Claude大脑可行性报告_2026-07-24.md`。

## 一句话架构

```
摄像头帧 (JPEG ≤512px)
   └─► Claude（每 tick 一次调用：看图 + 状态 → 至多 2 个工具调用）
          move_joints / play_recording / set_light / do_nothing
             └─► SafetyGate（关节绝对限位 + 单步 ±8° 限幅 + 动作名白名单 + RGB 钳位）
                    └─► MotorBackend（dry / MuJoCo / 真机 ST3215）+ Pico LED
API 挂了？ └─► 本地 BehaviorService 规则兜底，循环永不死
```

## 快速开始（都在仓库根目录执行）

```bash
# 0. 依赖（在已有环境上只多一个包）
pip install anthropic

# 1. 无 API key 自检：脚本化假 Claude 跑通全链路（含安全钳位演示）
PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode dry --mock --frames 4

# 2. 真·Claude 干跑（Mac 上即可，假摄像头合成画面，不碰硬件）
export ANTHROPIC_API_KEY=sk-ant-...
PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode dry --frames 5

# 3. MuJoCo 仿真闭环（Claude 看仿真渲染画面，动作写回仿真）
MUJOCO_GL=egl PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode sim --frames 5

# 4. 给 Claude 下语音指令
PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode dry --frames 3 --say "跟着我，灯调成粉色"

# 5. Jetson 真机（需 lelamp_runtime 已装、串口在位）
PYTHONPATH=ailamp_runtime python3 poc_claude_brain/claude_brain.py --mode real --frames 20 --interval 3
```

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--mode` | `dry` | `dry` 假摄像头+打印 / `sim` MuJoCo 闭环 / `real` 真机 |
| `--model` | `claude-haiku-4-5-20251001` | 最快最便宜；可换 `claude-sonnet-5` |
| `--frames` | 5 | tick 数 |
| `--interval` | 3.0 | tick 间隔（秒），真机模式生效 |
| `--say` | – | 注入一条用户语音指令 |
| `--mock` | – | 脚本化假 Claude（无需 key） |
| `--max-calls` | 200 | 单次运行 API 调用上限（成本保险丝） |

## 测试

```bash
PYTHONPATH=ailamp_runtime python3 -m pytest poc_claude_brain/ -q   # 9 项，无需网络/key/mujoco
```

覆盖：越界增量钳位、未知关节/工具/动作名丢弃、RGB 钳位、每 tick 至多 2 个动作、
API 失败回退本地规则且循环存活、工具 schema 完整性、假摄像头 JPEG 可解码。

## 安全边界（写死在本地，Claude 无法绕过）

1. 关节绝对限位 = runtime 的 `JointSafetyLimiter`（与 MuJoCo 模型一致）。
2. 单 tick 单关节最大 ±8°（`MAX_DELTA_PER_TICK_DEG`）。
3. 动作名白名单 = recordings 目录实际存在的 CSV。
4. 每 tick 至多执行 2 个工具调用；`--max-calls` 限制单次运行总调用数。
5. API 异常/超时 → 本地 `BehaviorService`（已接 TOML behavior_map）兜底。
6. 硬件层还有 BOM 里的 12V 急停开关作最后一道保险。
