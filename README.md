# vibe-mouse 🖱️

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

Core open-source Vibecoding interactive mouse project, belonging to a self-developed open-source system including the nation's first open-source robot actuator and stepless mobile intelligent monitoring solution.

# Self-Developed Vibecoding Interactive Mouse 
A brand-new coding-based human-computer interaction paradigm that breaks the operational limitations of traditional mice, supporting refined and fully customizable interaction logic. 
 
# Nation’s First Open-Source Robot Actuator 
An open-source robot motion driving architecture featuring reusability, secondary development compatibility, and mass deployment capability. 
 
# Limitless Mobile Intelligent Monitoring System 
End-to-end capabilities including full-area gradient-free mobile monitoring, equipment inspection, status perception, and abnormal early warning. 
 
# Fully Decoupled Three-Module Design 
The three projects are independently open-sourced, operable separately, and freely combinable for linkage. 
 
# Lightweight, Deployable & Open-Source Shared 
Applicable to individual development, laboratory projects, smart device retrofitting, and robotics scenario development. All derivative works must remain open-source in compliance with the specified license. 

---

### New Features (Optimized Version)

- **Cross-Platform Key Adaptation**: Automatically identifies Mac (`Cmd`) or Windows/Linux (`Ctrl`), eliminating the need to manually modify shortcut configurations.
- **System Tray**: Say goodbye to the dark command line! Once the program runs, it hides in the system tray (bottom right corner or top menu bar), and you can **right-click the icon to switch Vibe tools at any time**.
- **One-Click Build**: Provides a `build.py` script to generate `.exe` or `.app` files with one click, making it easy for non-technical users to double-click and use directly.

### Core Architecture

- `core/config.py`: Defines the mapping configuration between platform shortcuts and mouse buttons, supporting persistence.
- `core/executor.py`: Parses and executes corresponding shortcut combinations to achieve seamless interaction with major IDEs.
- `core/listener.py`: Globally listens to mouse button events, intercepts corresponding buttons, and sends commands to the executor.
- `core/main.py`: Project entry point.

### Default Mouse Mapping

- **Mouse Middle Button** (middle) -> Accept AI Code (Accept Diff)
- **Mouse Side Button 1** (button8) -> Invoke Inline Code Generation (Inline Edit / Builder)
- **Mouse Side Button 2** (button9) -> Invoke AI Chat Panel (Toggle Chat)

*You can modify these later in the generated `config.json`.*

### Default Supported Tools

- `trae`: Default adaptation for Trae shortcuts (Ctrl+U, Ctrl+I, etc.)
- `cursor`: Adaptation for Cursor (Ctrl+K, Ctrl+L, etc.)
- `windsurf`: Adaptation for Windsurf (Ctrl+Shift+I, etc.)
- `copilot`: Adaptation for GitHub Copilot (Ctrl+I, etc.)
- `deveco_studio`: Adaptation for DevEco Studio CodeGenie (Alt+I Inline Chat, Alt+U Panel, Alt+Enter Accept)
- `deveco_code`: Adaptation for DevEco Code CLI Agent (Tab Accept, Esc Dismiss)

### Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the program:
   ```bash
   python core/main.py
   ```
   *After starting, a blue "V" icon will appear in the system tray. You can right-click it to switch IDEs (e.g., Trae, Cursor) or exit the program.*

### Package as an Executable (No Python Environment Required)

If you want to send the tool to someone else to double-click and use:

1. Ensure build dependencies are installed (`pyinstaller`)
2. Run the build script:
   ```bash
   python build.py
   ```
3. Find `VibeMouse.exe` (Windows) or `VibeMouse.app` (Mac) in the `dist/` directory and send it to your friends!

## ⚙️ Technical Features (Revised) 
1. Modular architecture with low coupling and high scalability 
2. Fully open-source with no closed-source dependencies; all derivative projects must stay open-source under the license terms 
3. Supports standalone deployment, dual-module linkage, and full three-module integration 
4. Compatible with secondary development, academic research, and open-source project innovation 

--- 

## 📄 Open-Source License 
This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** to sustain the perpetual openness of this self-developed open-source technology stack, ensuring all derivative works give back to the open-source community. 

### Core Permissions 
- Free access to, study, and research all source code of this project 
- Free redistribution of unmodified original source code 
- Permission for secondary development, technical modification, and academic research based on this project 

### Core Mandatory Restrictions (Strong Copyleft Provisions) 
1. **Derivative works must remain open-source**: All modified, integrated, or secondarily developed works derived from this project must adopt the AGPL-3.0 license and release their complete corresponding source code. 
2. **Cloud deployments require open-sourcing**: If the project is deployed as an online service accessible via network (without distributing installation packages), full runnable source code must be provided to all service end-users. 
3. **Closed-source commercial use prohibited**: The original project and all its derivatives shall not be sold, privately licensed, or operated as closed-source commercial products. 

### License Selection Rationale 
AGPL-3.0 is chosen to protect core self-developed assets including the Nation’s First Open-Source Robot Actuator from unauthorized closed-source commercial exploitation. It guarantees all iterative improvements across the entire interaction-actuation-monitoring tech stack stay publicly accessible, fostering a fully transparent, freely shared open-source robotics ecosystem. 

--- 

## 🤝 Star / Fork / Pull Request Welcome 
This suite is a personal self-developed open-source system under continuous iteration. Developers are welcome to co-build China’s first open-source robot actuator ecosystem and the innovative Vibecoding intelligent interaction framework. All contributed code is automatically released under the AGPL-3.0 license.

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

### 新特性 (优化版)

- **跨平台按键自适应**: 自动识别 Mac (`Cmd`) 或 Windows/Linux (`Ctrl`)，无需手动修改快捷键配置。
- **系统托盘**: 告别黑乎乎的命令行！程序运行后会隐藏在系统托盘（右下角或顶部菜单栏），你可以**右键点击图标随时切换 Vibe 工具**。
- **一键打包**: 提供 `build.py` 脚本，可一键生成 `.exe` 或 `.app`，方便非技术人员直接双击使用。

### 核心架构

- `core/config.py`: 定义各平台快捷键与鼠标按键的映射配置，并支持持久化。
- `core/executor.py`: 解析并执行对应快捷键组合，实现与各大 IDE 的无缝交互。
- `core/listener.py`: 全局监听鼠标按键事件，拦截对应按键后下发指令给执行器。
- `core/main.py`: 项目入口。

### 默认鼠标映射

- **鼠标中键** (middle) -> 接受 AI 代码 (Accept Diff)
- **鼠标侧键 1** (button8) -> 唤起内联代码生成 (Inline Edit / Builder)
- **鼠标侧键 2** (button9) -> 唤起 AI 聊天面板 (Toggle Chat)

*后续可在生成的 `config.json` 中自行修改。*

### 默认支持工具

- `trae`: 默认适配 Trae 快捷键 (Ctrl+U, Ctrl+I 等)
- `cursor`: 适配 Cursor (Ctrl+K, Ctrl+L 等)
- `windsurf`: 适配 Windsurf (Ctrl+Shift+I 等)
- `copilot`: 适配 GitHub Copilot (Ctrl+I 等)
- `deveco_studio`: 适配 DevEco Studio CodeGenie (Alt+I 内联对话, Alt+U 面板, Alt+Enter 接受)
- `deveco_code`: 适配 DevEco Code 终端 AI Agent (Tab 接受, Esc 关闭)

### 使用方法

1. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

2. 启动程序:
   ```bash
   python core/main.py
   ```
   *程序启动后，会在系统托盘显示一个蓝色的 "V" 图标，你可以右键点击它来切换 IDE (如 Trae, Cursor 等) 或退出程序。*

### 打包成可执行文件 (无需 Python 环境)

如果你想把工具发给别人直接双击使用：

1. 确保安装了打包依赖 (`pyinstaller`)
2. 运行打包脚本:
   ```bash
   python build.py
   ```
3. 去 `dist/` 目录下找到 `VibeMouse.exe` (Windows) 或 `VibeMouse.app` (Mac)，发给你的朋友即可！

## ⚙️ 技术特性 (修订版)
1. 模块化架构，低耦合，高可扩展性
2. 完全开源，无闭源依赖；所有衍生项目必须在许可条款下保持开源
3. 支持独立部署、双模块联动及全三模块集成
4. 兼容二次开发、学术研究及开源项目创新

---

## 📄 开源许可
本项目基于 **GNU Affero General Public License v3.0 (AGPL-3.0)** 许可，以维持这一自研开源技术栈的永久开放性，确保所有衍生作品反哺开源社区。

### 核心权限
- 自由获取、学习和研究本项目的所有源代码
- 自由重新分发未修改的原始源代码
- 允许基于本项目进行二次开发、技术修改和学术研究

### 核心强制限制 (强 Copyleft 条款)
1. **衍生作品必须保持开源**：所有基于本项目的修改、集成或二次开发的衍生作品，必须采用 AGPL-3.0 许可，并发布其完整的对应源代码。
2. **云端部署要求开源**：如果项目作为通过网络访问的在线服务部署（不分发安装包），必须向所有服务端最终用户提供完整的可运行源代码。
3. **禁止闭源商业使用**：原项目及其所有衍生作品不得作为闭源商业产品出售、私下授权或运营。

### 许可选择的理由
选择 AGPL-3.0 是为了保护包括全国首个开源机器人执行器在内的核心自研资产免受未经授权的闭源商业剥削。它保证了整个交互-驱动-监控技术栈的所有迭代改进保持公开可访问，培育一个完全透明、自由共享的开源机器人生态系统。

---

## 🤝 欢迎 Star / Fork / Pull Request
本套件是一个持续迭代中的个人自研开源系统。欢迎开发者共同建设中国首个开源机器人执行器生态和创新的 Vibecoding 智能交互框架。所有贡献的代码将自动在 AGPL-3.0 许可下发布。