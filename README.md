# vibe-mouse

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

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
- **Visual Config Tool**: Open `config-tool.html` in a browser to configure tools, devices, mappings, feedback, and Token Plan visually — no backend required.

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
- **可视化配置工具**: 用浏览器打开 `config-tool.html`，图形化配置工具、外设、映射、反馈和 Token Plan，无需后端。

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

### 使用方法

1. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```
2. （可选）按需安装适配器依赖（pygame、bleak、pyserial 等）
3. 通过 `config-tool.html` 或 `config.json` 配置
4. 启动:
   ```bash
   python core/main.py
   ```
   系统托盘出现蓝色 "V" 图标，右键切换工具或退出。

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