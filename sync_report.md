# Vibe Mouse 本地工程 vs GitHub 官网 对比报告

> 对比时间：2026-11-01
> 官网仓库：https://github.com/CSCB/vibe-mouse （main 分支，14 次提交，最近提交 `增加编程工具检测` 2026-07-23）
> 本地路径：`c:\Users\danhui\Desktop\vibe-mouse(1)\vibe-mouse\vibe-mouse`

## 结论摘要

本地工程是官网的**重度改造分支**：新增了语音识别链路（FunASR/Whisper）、悬浮桌宠「牛来」、BLE 继电器（多色灯光）、控制面板、核心控制中枢（三大标签 + 自然语言配置 + 大模型文生图）等大量功能；但**缺失了官网的部分文件**（README、requirements、skills、gui_client、system_tray）。

---

## 一、本地缺失，需从官网补回（需要更新）

| 文件 / 目录 | 官网大小 | 说明 | 优先级 |
|---|---|---|---|
| `README.md` | 38.9 KB | 根目录主文档（项目说明 / 安装 / 快捷键 / 技能系统 / 硬件说明） | 高 |
| `requirements.txt` | 778 B | Python 依赖清单（本地缺，`install.bat` 也因此无法按此安装） | 高 |
| `skills/quick-code.yaml` | 700 B | 技能定义：快速生成代码 | 中 |
| `skills/code-review.yaml` | 796 B | 技能定义：代码审查 | 中 |
| `skills/presentation.yaml` | 698 B | 技能定义：演示/讲解 | 中 |
| `core/gui_client.py` | 12.0 KB | 桌面 GUI 面板源码（本地只剩 `.pyc` 缓存，源码已删） | 中 |
| `core/system_tray.py` | 2.8 KB | 系统托盘源码（本地只剩 `.pyc` 缓存，源码已删） | 中 |

说明：
- `skills/` 目录整体缺失。本地保留了 `core/skill_engine.py`（技能引擎），但缺少 3 个 YAML 技能定义文件，技能系统实际上不完整。
- `gui_client.py` / `system_tray.py` 的源码被删除，本地改用 `panel_ui.py` / `pet_ui.py` 替代了 GUI 与托盘入口，需确认是否还有必要保留官网那两套。

---

## 二、本地新增，官网没有（若维护官网需同步）

| 文件 / 目录 | 说明 |
|---|---|
| `core/settings_ui.py` | 核心控制中枢设置对话框（三大标签：Vibe Coding 输入 / 输出反馈 / 三方伙伴 + 自然语言配置 + 大模型文生图） |
| `core/panel_ui.py` | 控制面板（设备映射速查、继电器实时控制） |
| `core/pet_ui.py` | 悬浮桌宠「牛来」（idle/working/done/action 动画 + 自定义待机图） |
| `core/ble_relay.py` / `core/ble_relay_ui.py` | BLE 继电器（多色灯光，鉴权/改名/改密/通道控制） |
| `core/funasr_worker.py` | 语音识别 worker（FunASR SenseVoiceSmall） |
| `core/completion_detector.py` | AI 生成完成检测（IO 判定） |
| `core/asset_generator.py` | 桌宠素材生成 |
| `core/__init__.py` | 包初始化 |
| `start.bat` | 唯一启动脚本（自动选 .venv / 系统 Python，透传参数） |
| `install.bat` / `install.ps1` | 一键安装脚本 |
| `list_hid.py` | HID 设备列表调试工具 |
| `assets/` | 桌宠素材（idle/working/done/action/accept GIF + 图标） |
| `music/` | 语音提示音频（牛来 / mama） |
| `config.json` | 运行时生成的配置 |

---

## 三、本地改动过的核心文件（同名但内容已不同）

| 文件 | 官网大小 | 本地主要改动 |
|---|---|---|
| `core/config.py` | 9.2 KB | 新增 `keyboard_mappings`、多设备映射；移除 `voice_settings`；默认映射改为「上侧键=语音、下侧键=发送」 |
| `core/executor.py` | 9.2 KB | 新增 `submit_chat` 动作、语音输入链路（ASR → 可选 LLM）、桌宠通知、继电器反馈联动 |
| `core/feedback.py` | 10.3 KB | 新增 `mascot` 桌宠联动开关、反馈类型细化 |
| `core/main.py` | 3.0 KB | 新增桌宠模式、IO 检测回调、`--gui` 参数、桌宠联动开关读取 |
| `core/token_plan.py` | 6.5 KB | 新增多模型预设 `MODEL_PRESETS`、文生图 `generate_image`（华为云 MaaS）、同步 `chat` |
| `core/voice_llm.py` | 15.6 KB | 语音桥接 + 本地关键词兜底 + refine 开关 |
| `core/listener.py` | 1.8 KB | 新增键盘映射 `keyboard_mappings`、多设备监听 |

---

## 四、一致的目录（本地与官网相同，无需更新）

- `actuator/`（README + mechanical / pcb / software）
- `docs/`（README + faq / api / software / hardware / quickstart）
- `example/`（README + integrated-demo / monitor-patrol / actuator-group / actuator-single / vibe-mouse-basic）
- `monitor/`（README + software / firmware / hardware）
- `core/adapters/`（10 个适配器：base / mouse / keyboard / gamepad / bluetooth / hid / ir / network / voice + `__init__.py`）
- `LICENSE`、`build.py`、`config-tool.html`、`config.example.json`

---

## 五、建议的更新行动清单

### A. 从官网补回本地缺失
1. 拉取 `README.md`、`requirements.txt` 到本地根目录。
2. 拉取 `skills/` 目录（3 个 YAML），恢复技能系统完整性。
3. 确认 `core/gui_client.py` / `core/system_tray.py` 是否需要恢复源码，还是明确用 `panel_ui.py` / `pet_ui.py` 替代（若替代，建议从官网删除或标注废弃）。

### B. 同步本地改动到官网（若需维护官网）
4. 提交本地新增模块（settings_ui / panel_ui / pet_ui / ble_relay / funasr_worker 等）。
5. 提交核心文件改造（config / executor / feedback / main / token_plan / voice_llm / listener）。
6. 提交启动与安装脚本（start.bat / install.bat / install.ps1 / list_hid.py）。
7. 更新 `README.md` 补充新功能说明（语音识别、桌宠、继电器、自然语言配置、多模型文生图、多 IDE 适配）。

### C. 建议但不强制
8. 清理本地根目录的运行时产物（`gui.log`、`gui.err`、`install.log`、`install.err`、`funasr_worker.err`）。
9. `.venv/`、`assets/`、`music/` 是否纳入版本控制需按需决定（`.venv` 一般应加入 `.gitignore`）。
