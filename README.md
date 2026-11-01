# vibe-mouse

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

> **Beta / 预览版** — This project is under active development. Features, APIs, and configurations may change. Feedback and contributions are welcome.

Core open-source Vibecoding interactive mouse project, belonging to a self-developed open-source system including the nation's first open-source robot actuator and stepless mobile intelligent monitoring solution.

# Self-Developed Vibecoding Interactive Mouse 
A brand-new coding-based human-computer interaction paradigm that breaks the operational limitations of traditional mice, supporting refined and fully customizable interaction logic. 
 
# Nation's First Open-Source Robot Actuator 
An open-source robot motion driving architecture featuring reusability, secondary development compatibility, and mass deployment capability. 
 
# Limitless Mobile Intelligent Monitoring System 
End-to-end capabilities including full-area gradient-free mobile monitoring, equipment inspection, status perception, and abnormal early warning. 
 
# Fully Decoupled Three-Module Design 
The three projects are independently open-sourced, operable separately, and freely combinable for linkage. 
 
# Lightweight, Deployable & Open-Source Shared 
Applicable to individual development, laboratory projects, smart device retrofitting, and robotics scenario development. All derivative works must remain open-source in compliance with the specified license. 

---

### Features

- **Cross-Platform Key Adaptation**: Automatically identifies Mac (`Cmd`) or Windows/Linux (`Ctrl`), eliminating the need to manually modify shortcut configurations.
- **System Tray**: The program runs in the system tray. Right-click the icon to switch Vibe tools at any time.
- **One-Click Build**: Provides a `build.py` script to generate `.exe` or `.app` files with one click.
- **Multi-Device Input**: Pluggable adapter architecture supporting mouse, keyboard, gamepad, Bluetooth, IR remote, HID, and network/IoT devices.
- **Hardware Feedback**: Instant feedback when actions are triggered or completed — via system sound, screen overlay, tray notification, LED indicator, or vibration motor (hardware requires custom setup).
- **Voice-to-LLM Bridge**: Speech recognition results can be sent directly to Huawei Cloud Token Plan / MaaS (GLM / DeepSeek / Kimi). Just fill in your API Key and say "generate a quicksort function" — AI writes the code for you.
- **Prompt Refine (Optional)**: Converts colloquial speech into precise, structured prompts before sending to the LLM. Corrects homophones, accents, and technical terminology, while expanding vague requests into actionable instructions.
- **Skill System (Complete Config Unit) (Beta)**: A Skill = a complete work mode. Bind any button/key to a Skill (`"skill:<name>"`) or let voice keywords auto-match. Each Skill can override shortcuts, feedback config, device activation, and system prompt — all in one package. Supports YAML/JSON files and built-in templates (quick-code, code-review, presentation, explain-code).
- **Auto Window Detection (Beta)**: Automatically detects which AI IDE is currently in focus (Trae, Cursor, Windsurf, VS Code, DevEco, CodeArts) and switches shortcuts accordingly. No more manual switching.
- **Tool Switch History**: Every tool switch saves a full state snapshot (active Skill, shortcut overrides, feedback config). Switch back and your previous context is restored instantly.
- **GUI Client Mode**: Run `python core/main.py --gui` for a desktop panel showing current tool, active Skill, switch history, and auto-detection toggle.
- **Visual Config Tool**: Open `config-tool.html` in a browser to configure tools, devices, mappings, feedback, Token Plan, and Skills visually — no backend required.

### Core Architecture

```
Device Event → Adapter → Event (unified) → DeviceManager → Executor (keyboard shortcut)
```

| File | Description |
|---|---|
| `core/config.py` | Tool shortcuts & multi-device input mappings, with persistence |
| `core/executor.py` | Parses and executes shortcut combinations, with feedback triggers |
| `core/feedback.py` | Feedback manager: sound, overlay, notification, LED, vibration |
| `core/token_plan.py` | Huawei Cloud Token Plan / MaaS client — just fill in API Key |
| `core/voice_llm.py` | Voice-to-LLM bridge + Prompt Refine: speech → optimized prompt → LLM → action |
| `core/skill_engine.py` | Skill parsing and matching engine — trigger words → system_prompt injection |
| `core/window_detector.py` | Cross-platform foreground window detection — auto-identifies AI IDE |
| `core/tool_switcher.py` | Tool switch history with full state snapshots (Skill, shortcuts, feedback) |
| `core/gui_client.py` | Desktop GUI panel (tkinter) — status, history, auto-detect toggle |
| `core/device_manager.py` | Manages all adapters and routes events to the executor |
| `core/event.py` | Unified event abstraction layer (`DeviceType`, `InputType`, `Event`) |
| `core/adapters/base.py` | Abstract base class for all adapters |
| `core/adapters/mouse_adapter.py` | Mouse (pynput) |
| `core/adapters/keyboard_adapter.py` | Keyboard / multimedia keys |
| `core/adapters/gamepad_adapter.py` | Gamepad — Xbox, PS, Switch (pygame) |
| `core/adapters/bluetooth_adapter.py` | BLE / Classic Bluetooth (bleak / pybluez) |
| `core/adapters/ir_adapter.py` | IR remote — TV, AC (pyserial / broadlink / lirc) |
| `core/adapters/hid_adapter.py` | Generic HID — Stream Deck, scanner (hidapi / pywinusb) |
| `core/adapters/network_adapter.py` | IoT — MQTT / WebSocket / HTTP |
| `core/adapters/voice_adapter.py` | Voice — wake words & voice commands |
| `core/system_tray.py` | System tray menu |
| `core/main.py` | Entry point |

### Full Project Structure

```
vibe-mouse/
├── core/                          # Vibe Mouse core
│   ├── config.py                  # Config & shortcuts
│   ├── executor.py                # Shortcut executor
│   ├── device_manager.py          # Multi-device manager & event router
│   ├── event.py                   # Unified event abstraction
│   ├── adapters/                  # Pluggable device adapters
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mouse_adapter.py
│   │   ├── keyboard_adapter.py
│   │   ├── gamepad_adapter.py
│   │   ├── bluetooth_adapter.py
│   │   ├── ir_adapter.py
│   │   ├── hid_adapter.py
│   │   ├── network_adapter.py
│   │   └── voice_adapter.py
│   ├── skill_engine.py            # Skill parsing and matching engine
│   ├── main.py                    # Entry point
│   └── system_tray.py             # System tray
├── actuator/                      # Open-source robot actuator module
│   ├── mechanical/                # Mechanical design (Zhao Wang Motor)
│   ├── pcb/                       # Circuit board design
│   └── software/                  # Firmware & control software
├── monitor/                       # Stepless mobile monitoring system
│   ├── hardware/                  # Hardware design
│   ├── firmware/                  # Embedded firmware
│   └── software/                  # Host software & algorithms
├── example/                       # Example projects
│   ├── vibe-mouse-basic/
│   ├── actuator-single/
│   ├── actuator-group/
│   ├── monitor-patrol/
│   └── integrated-demo/
├── docs/                          # Documentation
│   ├── quickstart/
│   ├── hardware/
│   ├── software/
│   ├── api/
│   └── faq/
├── skills/                        # Skill files (YAML/JSON)
│   ├── quick-code.yaml
│   └── code-review.yaml
├── config-tool.html               # Visual config tool (browser-based, no backend)
├── config.example.json            # Example multi-device config
├── build.py                       # Build script
└── requirements.txt               # Dependencies
```

### Default Mouse Mapping

| Button | Action |
|---|---|
| Middle button | Accept AI code (Accept Diff) |
| Side button 1 (button8) | Invoke inline code generation (Inline Edit) |
| Side button 2 (button9) | Toggle AI chat panel (Toggle Chat) |

*Customize in `config-tool.html` or `config.json`.*

### Supported Tools

| Tool | Inline Edit | Toggle Chat | Accept | Reject | Voice Input |
|---|---|---|---|---|---|
| `trae` | Ctrl+U | Ctrl+I | Ctrl+Enter | Esc | Alt+V |
| `cursor` | Ctrl+K | Ctrl+L | Ctrl+Y | Esc | - |
| `windsurf` | Ctrl+Shift+I | Ctrl+L | Ctrl+Enter | Esc | Alt+A |
| `copilot` | Ctrl+I | Ctrl+Alt+I | Ctrl+Enter | Esc | Alt+A |
| `deveco_studio` | Alt+I | Alt+U | Alt+Enter | Esc | Alt+V |
| `deveco_code` | Tab | Esc | Tab | Esc | - |
| `codearts` | Alt+C | Alt+X | Tab | Esc | Alt+A |

### Supported Devices

| Type | Adapter | Dependencies | Examples |
|---|---|---|---|
| Mouse | `mouse_adapter.py` | pynput | Any mouse with side buttons |
| Keyboard | `keyboard_adapter.py` | pynput | Multimedia keys, foot pedals, PTT |
| Gamepad | `gamepad_adapter.py` | pygame | Xbox, PS, Switch controllers |
| Bluetooth | `bluetooth_adapter.py` | bleak / pybluez | Bluetooth desk phone, BLE remote, dial |
| IR Remote | `ir_adapter.py` | pyserial / broadlink | TV remote, AC remote, learning remote |
| HID Generic | `hid_adapter.py` | hidapi / pywinusb | Stream Deck, barcode scanner, presenter |
| Network/IoT | `network_adapter.py` | paho-mqtt / websockets | Smart buttons, phone virtual controller |
| Voice | `voice_adapter.py` | SpeechRecognition / pvporcupine / pyaudio | Voice commands, wake words |

### Configuration

**Option 1: Visual Config Tool (Recommended)**

Open `config-tool.html` in any browser. Add devices, edit mappings, switch tools, then click "Save Config" to download `config.json`.

**Option 2: Manual JSON Editing**

Copy `config.example.json` to `config.json` and edit:

```json
{
    "current_tool": "trae",
    "devices": [
        {"id": "mouse_default", "type": "mouse", "config": {}, "enabled": true},
        {"id": "xbox", "type": "gamepad", "config": {"joystick_index": 0}, "enabled": true}
    ],
    "device_mappings": {
        "mouse_default": {"button8": "inline_edit", "button9": "toggle_chat", "middle": "accept_diff"},
        "xbox": {"a": "accept_diff", "b": "reject_diff", "x": "inline_edit", "y": "toggle_chat"}
    }
}
```

**Token Plan (Huawei Cloud LLM)**

Fill in your Huawei Cloud API Key in `config.json` to enable voice-to-LLM:

```json
{
    "token_plan": {
        "enabled": true,
        "api_key": "YOUR_HW_CLOUD_API_KEY",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
        "model": "glm-4.7",
        "max_tokens": 2048,
        "temperature": 0.7,
        "refine_voice_text": true
    }
}
```

- `refine_voice_text` — Optional. When enabled, speech recognition results are first sent to the LLM for **Prompt Refine**: correcting homophones, accents, and technical terminology, while expanding vague requests (e.g., "write a sort" → "Implement quicksort in Python with input validation and detailed comments"). Falls back to raw text if refinement fails.

Then configure your voice device with `"use_llm": true`:

```json
{
    "id": "voice_mic",
    "type": "voice",
    "config": {
        "mode": "command",
        "language": "zh-CN",
        "use_llm": true
    },
    "enabled": true
}
```

**Skill System**

A Skill is a **complete configuration unit** — not just a prompt, but an entire work mode. When activated, a Skill can:

- **Execute actions** (press shortcuts, switch tools, set processing mode)
- **Override shortcuts** (change key bindings per tool for this mode)
- **Override feedback** (change sound/LED/overlay/vibration behavior)
- **Activate devices** (enable specific input devices like voice mic)
- **Inject system prompt** (set the LLM persona for voice input)

**Trigger methods:**

1. **Device binding** (`"skill:<name>"` in mappings) — any button/key directly triggers a Skill, applying all its config overrides.
2. **Voice matching** (trigger words/regex) — when voice input matches a Skill's keywords, the Skill's `system_prompt` is injected into the LLM call.

When a Skill is deactivated (by activating another Skill or manually exiting), all overrides are removed and default config is restored.

*Skill File Format (YAML or JSON)*

```yaml
name: code-review
version: "1.0"
description: "Code review mode — opens chat panel, LED on, review prompt"
triggers:
  words: ["review", "check code", "refactor"]
  priority: 10
system_prompt: |
  You are a senior code reviewer. Analyze for bugs, performance, security, and style.
actions:
  - type: execute_action      # Press toggle_chat shortcut
    value: toggle_chat
  - type: set_mode            # Voice response mode: paste/chat/action/auto
    value: chat
shortcuts:                    # Override shortcuts for this mode (optional)
  trae:
    inline_edit: ["ctrl", "u"]
    toggle_chat: ["ctrl", "i"]
feedback:                     # Override feedback config (optional)
  on_received: ["sound", "led"]
  on_success: ["overlay"]
  on_error: ["sound", "notification", "led"]
  hardware:
    led_enabled: true
devices:                      # Auto-enable devices (optional)
  - id: voice_mic
    enabled: true
metadata:                     # Author, tags, etc. (optional)
  author: "vibemouse"
  tags: ["code", "review"]
enabled: true
```

| Field | Description |
|---|---|
| `name` | Unique skill identifier (e.g., `quick-code`) |
| `version` | Semantic version string (e.g., `"1.0"`, `"1.2.3"`) |
| `description` | Human-readable description shown in the config tool |
| `triggers.words` | List of trigger keywords; if any word is contained in the voice text, the skill matches |
| `triggers.regex` | Optional regex pattern for advanced matching |
| `triggers.priority` | Integer; higher priority wins when multiple skills match |
| `system_prompt` | The system prompt injected when this skill is matched |
| `actions` | Actions executed on activation: `set_mode` (auto/paste/chat/action), `execute_action` (press a native shortcut), `set_tool` (switch Vibe tool), `inject_text` (prepend text to voice message). |
| `shortcuts` | **(Optional)** Override key bindings per tool for this Skill mode. Format: `{tool: {action: [keys]}}` |
| `feedback` | **(Optional)** Override feedback config (sound/LED/overlay/vibration) for this Skill mode |
| `devices` | **(Optional)** Auto-enable input devices when Skill is activated |
| `metadata` | **(Optional)** Author, tags, and other metadata |
| `enabled` | Whether this skill is active |

*Configuration in `config.json`*

```json
{
    "skills": {
        "enabled": true,
        "fallback_action": "inline_edit",
        "skill_files": [
            "skills/quick-code.yaml",
            "skills/code-review.yaml"
        ],
        "inline_skills": [
            {
                "name": "explain-code",
                "version": "1.0",
                "description": "Explain code logic",
                "triggers": {"words": ["explain", "what does this do"], "priority": 8},
                "system_prompt": "You are a programming tutor. Explain code in simple terms.",
                "actions": [{"type": "set_mode", "value": "chat"}],
                "enabled": true
            }
        ]
    }
}
```

- `skill_files` — Load skills from external YAML/JSON files (recommended for sharing and versioning)
- `inline_skills` — Define skills directly inside `config.json` (recommended for quick customization via the config tool)

*Binding a Skill to a device button*

In `device_mappings`, use the `"skill:<name>"` format as the action value:
```json
{"mouse_default": {"button9": "skill:code-review"}}
```
This maps the mouse side button to the `code-review` Skill — pressing it activates the Skill's system prompt and executes its defined actions.

*Built-in Skills*

| Skill | Triggers | Mode | Description |
|---|---|---|---|
| `quick-code` | "generate code", "write", "code" | `paste` | Directly outputs code without explanation |
| `code-review` | "review", "check code", "refactor" | `chat` | Reviews code for bugs, performance, and security |
| `doc-writer` | "write docs", "comments", "documentation" | `paste` | Generates function docs and comments |
| `explain-code` | "explain", "how", "meaning" | `chat` | Explains code logic in beginner-friendly terms |
| `presentation` | "demo", "present", "展示" | `chat` | Silent feedback (LED only), simplified shortcuts |
| `debug-helper` | "debug", "bug", "error", "fix" | `chat` | Helps locate and fix bugs |

*How it works*

1. Voice input is recognized
2. (Optional) Prompt Refine optimizes the text
3. **Skill Engine** matches the text against all enabled skills (by trigger words → regex → priority)
4. If a skill matches, its `system_prompt` replaces the default prompt; its `actions` set the mode (paste/chat/action)
5. The optimized text + skill system prompt are sent to the LLM
6. The response is handled according to the skill's mode

### Window Auto-Detection

Enable automatic window focus detection in GUI mode:

```bash
python core/main.py --gui
```

In the GUI panel, check "Enable window focus auto-detection". VibeMouse will poll the foreground window every second and automatically switch to the matching tool config when you switch between IDEs.

Detection is based on window title keywords and process name matching. Supported tools: Trae, Cursor, Windsurf, VS Code (Copilot), DevEco Studio, DevEco Code, CodeArts.

### GUI Client Mode

```bash
python core/main.py --gui
```

The GUI panel shows:
- **Current Tool**: The active AI IDE (auto-detected or manually selected)
- **Current Skill**: The active Skill mode and its version
- **Auto-Detection Toggle**: Enable/disable window focus monitoring
- **Tool Buttons**: Manually switch to any tool
- **Quick Actions**: Quick switch back, refresh detection, open config, exit Skill
- **Switch History**: Recent tool switches with timestamps and Skill info

### Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional) Install adapter-specific dependencies as needed (pygame, bleak, pyserial, etc.)
3. Configure via `config-tool.html` or `config.json`
4. Start:
   ```bash
   python core/main.py
   ```
   A blue "V" icon appears in the system tray. Right-click to switch tools or exit.

### Package as Executable

```bash
pip install pyinstaller
python build.py
```
Find `VibeMouse.exe` (Windows) or `VibeMouse.app` (Mac) in `dist/`.

---

## Technical Features
1. Modular, pluggable adapter architecture — add new devices without touching core logic
2. Fully open-source, no closed-source dependencies; AGPL-3.0 strong copyleft
3. Supports standalone deployment, dual-module linkage, and full three-module integration
4. Compatible with secondary development, academic research, and open-source innovation

---

## License
**AGPL-3.0** — All derivative works must remain open-source. Cloud deployments must provide source code to users. No closed-source commercial use permitted.

---

## Star / Fork / Pull Request Welcome
Contributors are welcome to co-build China's first open-source robot actuator ecosystem and the innovative Vibecoding intelligent interaction framework. All contributed code is automatically released under AGPL-3.0.

---

<a name="中文"></a>
## 中文

> **Beta / 预览版** — 本项目处于活跃开发阶段，功能、API 和配置可能变动。欢迎反馈和贡献。

核心开源 Vibecoding 交互鼠标项目，属于包含全国首个开源机器人执行器及无级移动智能监控解决方案的自研开源系统的一部分。

# 自研 Vibecoding 交互鼠标
打破传统鼠标操作限制的全新基于代码的人机交互范式，支持精细化和完全可定制的交互逻辑。

# 全国首个开源机器人执行器
具备高复用性、支持二次开发及规模化部署能力的开源机器人运动驱动架构。

# 无级移动智能监控系统
端到端能力，涵盖全域无死角移动监控、设备巡检、状态感知及异常预警。

# 全解耦三模块设计
三大项目独立开源，可单独运行，亦可自由组合联动。

# 轻量化、易部署与开源共享
适用于个人开发、实验室项目、智能设备改造及机器人场景开发。所有衍生作品必须遵循指定的开源协议保持开源。

---

### 功能特性

- **跨平台按键自适应**: 自动识别 Mac (`Cmd`) 或 Windows/Linux (`Ctrl`)，无需手动修改快捷键配置。
- **系统托盘**: 程序运行后隐藏在系统托盘，右键图标随时切换 Vibe 工具。
- **一键打包**: 提供 `build.py` 脚本，一键生成 `.exe` 或 `.app`。
- **多外设输入**: 可插拔适配器架构，支持鼠标、键盘、手柄、蓝牙、红外遥控、HID、网络/IoT 设备。
- **硬件反馈**: 操作触发或完成时即时反馈 —— 系统声音、屏幕浮窗、托盘通知、LED 指示灯、震动马达（硬件需外接）。
- **语音接入大模型**: 语音识别结果可直接发送给华为云 Token Plan / MaaS（GLM / DeepSeek / Kimi），填入 API Key 后说"生成一个快排函数"，AI 自动帮你写代码。
- **提示词优化（可选）**: 将口语化的语音输入转化为精准、结构化的高质量 Prompt。纠正同音字/口音/编程术语误识别，同时将模糊描述扩展为明确指令（如"写个排序"→"用Python实现快速排序，包含输入验证和注释"）。
- **Skill 技能系统（完整配置单元）（Beta）**: 一个 Skill = 一套完整工作模式。任意按键可绑定 Skill（`"skill:<name>"`），也可语音关键词自动匹配。每个 Skill 可覆盖快捷键、反馈配置、设备激活和系统提示词——全部打包在一起。支持 YAML/JSON 文件和内置模板（quick-code、code-review、presentation、explain-code）。
- **窗口焦点自动检测（Beta）**: 自动检测当前焦点窗口属于哪个 AI IDE（Trae、Cursor、Windsurf、VS Code、DevEco、CodeArts），自动切换对应快捷键配置，无需手动切换。
- **工具切换历史记录**: 每次切换工具自动保存完整状态快照（激活的 Skill、快捷键覆盖、反馈配置）。切回工具时自动恢复之前的上下文。
- **GUI 客户端模式**: 运行 `python core/main.py --gui` 启动桌面面板，显示当前工具、激活的 Skill、切换历史和自动检测开关。
- **可视化配置工具**: 用浏览器打开 `config-tool.html`，图形化配置工具、外设、映射、反馈、Token Plan 和 Skills，无需后端。

### 核心架构

```
外设事件 → 适配器 → 统一事件 → 外设管理器 → 执行器（键盘快捷键）
```

| 文件 | 说明 |
|---|---|
| `core/config.py` | 工具快捷键 & 多外设输入映射，支持持久化 |
| `core/executor.py` | 解析并执行快捷键组合，集成反馈触发 |
| `core/feedback.py` | 反馈管理器：声音、浮窗、通知、LED、震动 |
| `core/token_plan.py` | 华为云 Token Plan / MaaS 客户端，填入 API Key 即可 |
| `core/voice_llm.py` | 语音-大模型桥接器 + 提示词优化：语音 → 优化 Prompt → LLM → 动作 |
| `core/skill_engine.py` | Skill 解析与匹配引擎 — 触发词 → system_prompt 注入 |
| `core/window_detector.py` | 跨平台前台窗口检测器 — 自动识别当前 AI IDE |
| `core/tool_switcher.py` | 工具切换历史记录 — 完整状态快照（Skill、快捷键、反馈） |
| `core/gui_client.py` | 桌面 GUI 面板（tkinter）— 状态、历史、自动检测开关 |
| `core/device_manager.py` | 管理所有适配器，将事件路由到执行器 |
| `core/event.py` | 统一事件抽象层 (`DeviceType`, `InputType`, `Event`) |
| `core/adapters/base.py` | 适配器抽象基类 |
| `core/adapters/mouse_adapter.py` | 鼠标 (pynput) |
| `core/adapters/keyboard_adapter.py` | 键盘 / 多媒体键 |
| `core/adapters/gamepad_adapter.py` | 游戏手柄 — Xbox、PS、Switch (pygame) |
| `core/adapters/bluetooth_adapter.py` | BLE / 经典蓝牙 (bleak / pybluez) |
| `core/adapters/ir_adapter.py` | 红外遥控 — 电视、空调 (pyserial / broadlink / lirc) |
| `core/adapters/hid_adapter.py` | 通用 HID — Stream Deck、扫描枪 (hidapi / pywinusb) |
| `core/adapters/network_adapter.py` | IoT — MQTT / WebSocket / HTTP |
| `core/adapters/voice_adapter.py` | 语音 — 唤醒词 & 语音命令 |
| `core/system_tray.py` | 系统托盘菜单 |
| `core/main.py` | 入口 |

### 完整项目结构

```
vibe-mouse/
├── core/                          # Vibe Mouse 核心
│   ├── config.py                  # 配置与快捷键
│   ├── executor.py                # 快捷键执行器
│   ├── device_manager.py          # 多外设管理器 & 事件路由
│   ├── event.py                   # 统一事件抽象
│   ├── adapters/                  # 可插拔外设适配器
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mouse_adapter.py
│   │   ├── keyboard_adapter.py
│   │   ├── gamepad_adapter.py
│   │   ├── bluetooth_adapter.py
│   │   ├── ir_adapter.py
│   │   ├── hid_adapter.py
│   │   ├── network_adapter.py
│   │   └── voice_adapter.py
│   ├── skill_engine.py            # Skill 解析与匹配引擎
│   ├── main.py                    # 入口
│   └── system_tray.py             # 系统托盘
├── actuator/                      # 开源机器人执行器模块
│   ├── mechanical/                # 机械结构（赵王开源电机）
│   ├── pcb/                       # 线路板设计
│   └── software/                  # 固件与控制软件
├── monitor/                       # 无级移动智能监控系统
│   ├── hardware/                  # 硬件设计
│   ├── firmware/                  # 嵌入式固件
│   └── software/                  # 上位机与算法
├── example/                       # 示例工程
│   ├── vibe-mouse-basic/
│   ├── actuator-single/
│   ├── actuator-group/
│   ├── monitor-patrol/
│   └── integrated-demo/
├── docs/                          # 文档
│   ├── quickstart/
│   ├── hardware/
│   ├── software/
│   ├── api/
│   └── faq/
├── skills/                        # Skill 文件（YAML/JSON）
│   ├── quick-code.yaml
│   └── code-review.yaml
├── config-tool.html               # 可视化配置工具（浏览器打开，无需后端）
├── config.example.json            # 多外设配置示例
├── build.py                       # 打包脚本
└── requirements.txt               # 依赖清单
```

### 默认鼠标映射

| 按键 | 动作 |
|---|---|
| 中键 | 接受 AI 代码 (Accept Diff) |
| 侧键 1 (button8) | 唤起内联代码生成 (Inline Edit) |
| 侧键 2 (button9) | 唤起 AI 聊天面板 (Toggle Chat) |

*可在 `config-tool.html` 或 `config.json` 中自定义。*

### 支持工具

| 工具 | 内联编辑 | 切换面板 | 接受 | 拒绝 | 语音输入 |
|---|---|---|---|---|---|
| `trae` | Ctrl+U | Ctrl+I | Ctrl+Enter | Esc | Alt+V |
| `cursor` | Ctrl+K | Ctrl+L | Ctrl+Y | Esc | - |
| `windsurf` | Ctrl+Shift+I | Ctrl+L | Ctrl+Enter | Esc | Alt+A |
| `copilot` | Ctrl+I | Ctrl+Alt+I | Ctrl+Enter | Esc | Alt+A |
| `deveco_studio` | Alt+I | Alt+U | Alt+Enter | Esc | Alt+V |
| `deveco_code` | Tab | Esc | Tab | Esc | - |
| `codearts` | Alt+C | Alt+X | Tab | Esc | Alt+A |

### 支持外设

| 类型 | 适配器 | 依赖库 | 示例设备 |
|---|---|---|---|
| 鼠标 | `mouse_adapter.py` | pynput | 任意带侧键鼠标 |
| 键盘 | `keyboard_adapter.py` | pynput | 多媒体键、脚踏开关、PTT |
| 游戏手柄 | `gamepad_adapter.py` | pygame | Xbox、PS、Switch 手柄 |
| 蓝牙设备 | `bluetooth_adapter.py` | bleak / pybluez | 蓝牙电话座机、BLE 遥控器、旋钮 |
| 红外遥控 | `ir_adapter.py` | pyserial / broadlink | 电视遥控器、空调遥控器、学习型遥控器 |
| HID 通用 | `hid_adapter.py` | hidapi / pywinusb | Stream Deck、条码扫描枪、翻页笔 |
| 网络/IoT | `network_adapter.py` | paho-mqtt / websockets | 智能家居按键、手机虚拟手柄 |
| 语音输入 | `voice_adapter.py` | SpeechRecognition / pvporcupine / pyaudio | 语音命令、唤醒词 |

### 配置方式

**方式一：可视化配置工具（推荐）**

浏览器打开 `config-tool.html`，添加外设、编辑映射、切换工具、配置反馈和 Token Plan，点击"Save Config"下载 `config.json` 放到项目目录即可。

**方式二：手动编辑 JSON**

复制 `config.example.json` 为 `config.json` 并编辑：

```json
{
    "current_tool": "trae",
    "devices": [
        {"id": "mouse_default", "type": "mouse", "config": {}, "enabled": true},
        {"id": "xbox", "type": "gamepad", "config": {"joystick_index": 0}, "enabled": true}
    ],
    "device_mappings": {
        "mouse_default": {"button8": "inline_edit", "button9": "toggle_chat", "middle": "accept_diff"},
        "xbox": {"a": "accept_diff", "b": "reject_diff", "x": "inline_edit", "y": "toggle_chat"}
    }
}
```

**Token Plan（华为云大模型接入）**

在 `config.json` 中填入华为云 API Key，即可启用语音接入大模型：

```json
{
    "token_plan": {
        "enabled": true,
        "api_key": "YOUR_HW_CLOUD_API_KEY",
        "endpoint": "https://maas-api.cn-north-4.myhuaweicloud.com",
        "model": "glm-4.7",
        "max_tokens": 2048,
        "temperature": 0.7,
        "refine_voice_text": true
    }
}
```

- `refine_voice_text` — 可选。开启后，语音识别结果会先经大模型进行**提示词优化**：纠错（同音字/口音/术语误识别）+ 提示词工程（口语→精准指令，如"写个排序"→"用Python实现快速排序，包含输入验证和注释"）。优化失败时自动回退到原始文本。

然后为语音设备配置 `"use_llm": true`：

```json
{
    "id": "voice_mic",
    "type": "voice",
    "config": {
        "mode": "command",
        "language": "zh-CN",
        "use_llm": true
    },
    "enabled": true
}
```

**反馈配置**

```json
{
    "feedback": {
        "on_received": ["sound", "overlay"],
        "on_success": ["sound"],
        "on_error": ["sound", "notification", "overlay"],
        "hardware": {
            "led_enabled": false,
            "vibration_enabled": false,
            "serial_port": null,
            "serial_baudrate": 9600
        }
    }
}
```

**Skill 技能系统**

Skill 是**完整的配置单元**——不只是一个提示词，而是一整套工作模式。激活后，Skill 可以：

- **执行动作**（按快捷键、切换工具、设置处理模式）
- **覆盖快捷键**（为当前模式修改各工具的按键绑定）
- **覆盖反馈**（修改声音/LED/浮窗/震动行为）
- **激活设备**（启用指定输入设备，如麦克风）
- **注入系统提示词**（设置语音输入的 LLM 人设）

**触发方式：**

1. **外设绑定**（映射中使用 `"skill:<name>"`）— 任意按键直接触发 Skill，应用其所有配置覆盖
2. **语音匹配**（触发词/正则）— 语音输入匹配到 Skill 关键词时，注入对应的 `system_prompt`

退出 Skill 时（激活另一个 Skill 或手动退出），所有覆盖配置自动移除，恢复默认配置。

*Skill 文件格式（YAML 或 JSON）*

```yaml
name: code-review
version: "1.0"
description: "代码审查模式 — 激活后打开聊天面板，LED 变蓝，语音用审查 prompt"
triggers:
  words: ["审查", "review", "检查代码", "优化"]
  priority: 10
system_prompt: |
  你是一个资深代码审查专家。请审查用户提供的代码，指出：
  1. 潜在Bug  2. 性能瓶颈  3. 安全风险  4. 代码规范问题
actions:
  - type: execute_action      # 按下 toggle_chat 快捷键
    value: toggle_chat
  - type: set_mode            # 语音回复模式：paste/chat/action/auto
    value: chat
shortcuts:                    # 覆盖此模式下的快捷键（可选）
  trae:
    inline_edit: ["ctrl", "u"]
    toggle_chat: ["ctrl", "i"]
feedback:                     # 覆盖此模式下的反馈配置（可选）
  on_received: ["sound", "led"]
  on_success: ["overlay"]
  on_error: ["sound", "notification", "led"]
  hardware:
    led_enabled: true
devices:                      # 自动启用的设备（可选）
  - id: voice_mic
    enabled: true
metadata:                     # 作者、标签等（可选）
  author: "vibemouse"
  tags: ["code", "review"]
enabled: true
```

| 字段 | 说明 |
|---|---|
| `name` | Skill 唯一标识（如 `quick-code`） |
| `version` | 语义化版本号（如 `"1.0"`、`"1.2.3"`） |
| `description` | 人类可读的描述，显示在配置工具中 |
| `triggers.words` | 触发关键词列表；语音文本包含任一关键词即匹配 |
| `triggers.regex` | 可选正则表达式，用于高级匹配 |
| `triggers.priority` | 整数，多个 Skill 同时匹配时优先级高的生效 |
| `system_prompt` | 匹配成功后注入的系统提示词 |
| `actions` | 激活时执行的动作：`set_mode`（auto/paste/chat/action）、`execute_action`（按下原生快捷键）、`set_tool`（切换 Vibe 工具）、`inject_text`（在语音消息前注入文本） |
| `shortcuts` | **（可选）** 覆盖此 Skill 模式下各工具的快捷键。格式：`{tool: {action: [keys]}}` |
| `feedback` | **（可选）** 覆盖此 Skill 模式下的反馈配置（声音/LED/浮窗/震动） |
| `devices` | **（可选）** Skill 激活时自动启用的输入设备 |
| `metadata` | **（可选）** 作者、标签等元信息 |
| `enabled` | 是否启用该 Skill |

*在 `config.json` 中配置*

```json
{
    "skills": {
        "enabled": true,
        "fallback_action": "inline_edit",
        "skill_files": [
            "skills/quick-code.yaml",
            "skills/code-review.yaml"
        ],
        "inline_skills": [
            {
                "name": "explain-code",
                "version": "1.0",
                "description": "解释代码逻辑和原理",
                "triggers": {"words": ["解释", "什么意思", "原理"], "priority": 8},
                "system_prompt": "你是一个编程导师。请用简洁的中文解释代码的逻辑和关键知识点。",
                "actions": [{"type": "set_mode", "value": "chat"}],
                "enabled": true
            }
        ]
    }
}
```

- `skill_files` — 从外部 YAML/JSON 文件加载 Skill（推荐用于共享和版本管理）
- `inline_skills` — 直接在 `config.json` 中定义 Skill（推荐通过配置工具快速自定义）

*将 Skill 绑定到外设按键*

在 `device_mappings` 中使用 `"skill:<name>"` 格式作为动作值：
```json
{"mouse_default": {"button9": "skill:code-review"}}
```
这样鼠标侧键就绑定到了 `code-review` Skill — 按下后激活该 Skill 的 system_prompt 并执行其定义的动作。

*内置 Skill 模板*

| Skill | 触发词 | 模式 | 说明 |
|---|---|---|---|
| `quick-code` | "生成代码"、"写个"、"code" | `paste` | 直接输出代码，不加解释 |
| `code-review` | "审查"、"检查代码"、"优化" | `chat` | 审查代码的 Bug、性能和安全问题 |
| `doc-writer` | "写文档"、"注释"、"documentation" | `paste` | 生成函数文档和注释 |
| `explain-code` | "解释"、"什么意思"、"原理" | `chat` | 用通俗易懂的方式解释代码逻辑 |
| `presentation` | "演示"、"展示"、"demo" | `chat` | 静音反馈（仅 LED），简化快捷键 |
| `debug-helper` | "调试"、"bug"、"报错"、"fix" | `chat` | 帮助定位和修复代码 Bug |

*工作流程*

1. 语音输入被识别
2. （可选）提示词优化处理语音文本
3. **Skill 引擎**将文本与所有启用的 Skill 进行匹配（触发词 → 正则 → 优先级）
4. 若匹配成功，使用该 Skill 的 `system_prompt` 替换默认提示词；其 `actions` 设置处理模式（paste/chat/action）
5. 优化后的文本 + Skill 系统提示词发送给大模型
6. 按照 Skill 设定的模式处理模型回复

### 窗口焦点自动检测

在 GUI 客户端模式下启用自动检测：

```bash
python core/main.py --gui
```

在 GUI 面板中勾选「启用窗口焦点自动检测」。VibeMouse 每秒轮询一次前台窗口，当你在多个 IDE 间切换时自动切换到对应的工具配置。

检测基于窗口标题关键词和进程名匹配。支持工具：Trae、Cursor、Windsurf、VS Code（Copilot）、DevEco Studio、DevEco Code、CodeArts。

### GUI 客户端模式

```bash
python core/main.py --gui
```

GUI 面板显示：
- **当前工具**: 当前激活的 AI IDE（自动检测或手动选择）
- **当前 Skill**: 当前激活的 Skill 模式及版本
- **自动检测开关**: 启用/禁用窗口焦点监控
- **工具按钮**: 手动切换到任意工具
- **快捷操作**: 快速回切、刷新检测、打开配置、退出 Skill
- **切换历史**: 最近工具切换记录，含时间戳和 Skill 信息

### 使用方法

1. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```
2. （可选）按需安装适配器依赖（pygame、bleak、pyserial 等）
3. 通过 `config-tool.html` 或 `config.json` 配置
4. 启动（托盘模式/默认）:
   ```bash
   python core/main.py
   ```
   系统托盘出现蓝色 "V" 图标，右键切换工具或退出。

   或启动 GUI 客户端模式:
   ```bash
   python core/main.py --gui
   ```
   打开桌面面板，支持自动检测、切换历史和 Skill 管理。

### 打包成可执行文件

```bash
pip install pyinstaller
python build.py
```
去 `dist/` 目录找到 `VibeMouse.exe` (Windows) 或 `VibeMouse.app` (Mac)。

---

## 技术特性
1. 模块化可插拔适配器架构 — 新增外设无需改动核心逻辑
2. 完全开源，无闭源依赖；AGPL-3.0 强 Copyleft
3. 支持独立部署、双模块联动及全三模块集成
4. 兼容二次开发、学术研究及开源项目创新

---

## 开源许可
**AGPL-3.0** — 所有衍生作品必须保持开源。云端部署须向用户提供源代码。禁止闭源商业使用。

---

## 欢迎 Star / Fork / Pull Request
欢迎开发者共同建设中国首个开源机器人执行器生态和创新的 Vibecoding 智能交互框架。所有贡献的代码将自动在 AGPL-3.0 许可下发布。