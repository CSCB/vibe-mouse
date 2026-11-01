"""
Vibe Mouse 入口 / Main Entry Point

两种运行模式，统一使用 PyQt5 技术栈：
1. 桌宠模式（默认）：PyQt5 桌面宠物 + 完成检测 + 系统托盘
2. GUI 模式（--gui）：桌宠 + 控制面板（工具切换/窗口检测/Skill/历史）

启动方式：
  python core/main.py              # 桌宠模式
  python core/main.py --gui        # GUI 控制面板模式
"""

import sys
import os

# 解决 CTranslate2 (Whisper) 与 PyQt5 的 OpenMP 库冲突
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import threading

# 确保在项目根目录可以正常 import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config, VibeTool
from core.executor import ActionExecutor
from core.feedback import FeedbackTiming
from core.tool_switcher import ToolSwitcher
from core.ble_relay import get_relay_controller


def run_pet_mode(config, show_panel=False):
    """
    桌宠模式（默认）：PyQt5 桌面宠物 + 完成检测 + 系统托盘。
    show_panel=True 时额外显示控制面板（即 --gui 模式）。
    """
    from PyQt5.QtWidgets import QApplication
    from core.pet_ui import DesktopPet
    from core.completion_detector import CompletionDetector
    from core.window_detector import WindowDetector
    from core.listener import MouseListener, KeyListener

    executor = ActionExecutor(config)

    # 注入 ToolSwitcher（统一工具切换：状态快照 + 历史）
    executor.tool_switcher = ToolSwitcher(config, executor)

    # BLE 继电器（config.ble_relay.enabled=False 时为 None）
    relay = get_relay_controller(config)
    if relay is not None:
        # 硬件反馈：AI 完成/出错时继电器反馈（feedback 配置 on_success/on_error 列表加 "relay" 启用）
        # action: "pulse"=脉冲 duration_ms | "on"/"off"=常亮模式开关（接灯场景）
        def _relay_feedback(channel, duration_ms, action="pulse"):
            if not relay.is_connected:
                return
            try:
                if action == "on":
                    relay.set_channel(channel, True)
                elif action == "off":
                    relay.set_channel(channel, False)
                elif action == "off_pulse":
                    relay.drop_channel(channel, duration_ms)
                else:
                    relay.pulse_channel(channel, duration_ms)
            except Exception as e:
                print(f"[Relay] 反馈动作失败: {e}")

        executor.feedback.register_hardware_handler("relay", _relay_feedback)
        # 自动连接上次设备
        if config.ble_relay.get("auto_connect") and config.ble_relay.get("last_address"):
            print(f"[Relay] 自动连接上次设备: {config.ble_relay.get('last_name') or config.ble_relay['last_address']}")
            relay.connect(config.ble_relay["last_address"])

    listener = MouseListener(config, executor)

    # 全局键盘监听：激光笔/翻页笔等模拟标准键盘的设备。
    # log_keys=True 打印所有按键（调试用），确定键值后在 config 配置 keyboard_mappings。
    key_listener = KeyListener(config, executor, log_keys=True)

    # 多外设支持：从 config.json 加载非鼠标设备（手柄/蓝牙/HID 等）。
    # 鼠标已由 MouseListener 全局监听，跳过以避免重复触发。
    from core.device_manager import DeviceManager
    device_manager = DeviceManager(config, executor)
    for _dev in config.get_devices():
        if _dev.get("type") == "mouse":
            continue
        device_manager.register_device(
            device_type=_dev["type"],
            device_id=_dev["id"],
            device_config=_dev.get("config", {})
        )
    device_manager.start_all()

    # 启动 PyQt5 应用
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 初始化桌宠 UI
    pet_ui = DesktopPet(config, executor, listener)

    # 注册 feedback 的 QApplication 引用（overlay 浮窗用）
    executor.feedback.set_qt_app(app)

    # 桌宠联动开关（feedback.mascot.enabled）
    def _mascot_on():
        return bool((config.feedback.get("mascot") or {}).get("enabled", True))

    # 注入 Trae 完成回调：触发桌宠 done 动画 + 蜂鸣
    executor._trae_done_callback = (lambda: pet_ui.signals.state_changed.emit("done")) if _mascot_on() else None

    # 非 Trae 工具（Cursor/CodeArts/Windsurf 等无 SessionControl 日志）：
    # 用 IO 检测器的 done 回调兜底（IO 巨量尖峰后连续 3 秒低 IO = 完成）。
    # Trae 仍走日志精确检测，避免双重通知。
    def _on_io_detect_done():
        if (config.current_tool or "trae") != "trae":
            print(f"[Detector] {config.current_tool} AI 生成完成（IO 判定）")
            executor._notify_trae_done()

    def _on_io_detect_start():
        # AI 开始工作（IO 判定）：仅触发桌宠 working 动画。
        # 灯的"灭"改由用户提交动作（submit_chat）驱动，见 executor.execute_action —— IO 推断开始
        # 存在后台噪声误判/漏判，不适合驱动状态灯
        if _mascot_on():
            pet_ui.signals.state_changed.emit("working")

    # 初始化完成检测器（working 动画提示 + 非 Trae 工具完成通知）
    detector = CompletionDetector(
        config=config,
        on_start_callback=_on_io_detect_start,
        on_done_callback=_on_io_detect_done
    )
    detector.start_detecting()
    pet_ui.detector = detector  # 注入到 UI，切换工具时可重置状态

    # 窗口焦点自动检测（如果配置启用）
    window_detector = None
    if config.auto_detect_ide:
        window_detector = WindowDetector(poll_interval=1.0)

        def _on_tool_changed(new_tool, old_tool):
            if old_tool:
                print(f"[AutoDetect] {old_tool} -> {new_tool}")
            pet_ui.switch_tool(new_tool)

        window_detector.set_on_tool_changed(_on_tool_changed)
        window_detector.start_monitoring()
        print("[AutoDetect] 窗口焦点自动检测已启动")

    # listener 回调 → 触发桌宠动画（submit_chat 不触发动画，避免发送时误显示完成动画）
    def on_action(action_name):
        if action_name in ("submit_chat", "voice_input"):
            return  # 提交和语音输入不触发桌宠动画
        if _mascot_on():
            pet_ui.signals.action_triggered.emit(action_name)

    listener.set_action_callback(on_action)
    # 手柄等多外设动作同样触发桌宠动画
    device_manager.on_action = on_action
    key_listener.set_action_callback(on_action)

    # 启动设备监听线程
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()
    key_listener.start()

    # 可选：显示控制面板（--gui 模式）
    panel = None
    if show_panel:
        from core.panel_ui import ControlPanel
        panel = ControlPanel(config, executor, window_detector, relay_controller=relay)

        # 工具切换信号 → 走 ToolSwitcher（带状态快照）+ 重置检测器
        def _on_switch(tool_name):
            executor.tool_switcher.switch(tool_name)
            detector.reset_state()
            pet_ui.switch_tool(tool_name)
            panel.refresh()

        panel.tool_switch_requested.connect(_on_switch)
        panel.skill_exit_requested.connect(executor.deactivate_skill)
        panel.show()
        print("[Panel] 控制面板已显示 / Control panel shown")

    print(f"Vibe Mouse 运行中 / running... 映射工具为 / mapped tool: {config.current_tool}")
    print("像素桌宠已启动，可以拖动它，双击打开设置 / Pixel pet started")

    # 进入 PyQt5 事件循环
    ret = app.exec_()

    # 清理
    detector.stop_detecting()
    if window_detector:
        window_detector.stop_monitoring()
    listener.stop()
    key_listener.stop()
    device_manager.stop_all()
    if relay is not None:
        relay.shutdown()
    sys.exit(ret)


def main():
    parser = argparse.ArgumentParser(description="Vibe Mouse Core")
    parser.add_argument("--tool", type=str, help="Specify the default Vibe tool")
    parser.add_argument("--gui", action="store_true", help="Launch with control panel (PyQt5)")
    parser.add_argument("--tray", action="store_true", help="Launch pet/tray mode (PyQt5, default)")
    args = parser.parse_args()

    config = Config()
    if args.tool:
        config.current_tool = args.tool.lower()
        config.save_config()

    run_pet_mode(config, show_panel=args.gui)


if __name__ == "__main__":
    main()
