"""
Vibe Mouse 入口 / Main Entry Point

支持两种运行模式：
1. 系统托盘模式（默认）：后台运行，右键托盘切换工具
2. GUI 客户端模式：桌面面板，支持窗口焦点自动检测 + 工具切换历史

启动方式：
  python core/main.py              # 系统托盘模式
  python core/main.py --gui        # GUI 客户端模式
  python core/main.py --tray       # 显式指定托盘模式
"""

import sys
import argparse
import threading

from core.config import Config
from core.executor import ActionExecutor
from core.device_manager import DeviceManager
from core.system_tray import SystemTray


def run_tray_mode(config, executor, device_manager):
    """运行系统托盘模式"""
    def on_exit():
        print("Vibe Mouse stopped / Vibe Mouse 已停止")
        device_manager.stop_all()
        sys.exit(0)

    tray = SystemTray(config, executor, device_manager, on_exit_callback=on_exit)

    # 在单独线程中启动设备监听
    device_thread = threading.Thread(target=device_manager.start_listening, daemon=True)
    device_thread.start()

    print("Vibe Mouse started in tray mode / Vibe Mouse 系统托盘模式已启动")
    print(f"Current tool / 当前工具: {config.current_tool}")
    print("Right-click the tray icon to switch tools / 右键托盘图标切换工具")

    tray.run()


def run_gui_mode(config, executor, device_manager):
    """运行 GUI 客户端模式"""
    from core.gui_client import VibeMouseGUI

    # 在单独线程中启动设备监听
    device_thread = threading.Thread(target=device_manager.start_listening, daemon=True)
    device_thread.start()

    gui = VibeMouseGUI(config, executor, device_manager)

    print("Vibe Mouse started in GUI mode / Vibe Mouse GUI 客户端模式已启动")
    print("Features: auto window detection, tool switch history, skill management")
    print("功能：窗口焦点自动检测、工具切换历史、Skill 管理")

    gui.run()

    # GUI 关闭后清理
    device_manager.stop_all()


def main():
    parser = argparse.ArgumentParser(description="Vibe Mouse - Vibecoding Interactive Mouse")
    parser.add_argument("--gui", action="store_true", help="启动 GUI 客户端模式")
    parser.add_argument("--tray", action="store_true", help="启动系统托盘模式（默认）")
    parser.add_argument("--auto-detect", action="store_true",
                        help="GUI 模式下默认启用窗口焦点自动检测")
    args = parser.parse_args()

    # 初始化配置
    config = Config()

    # 初始化执行器
    executor = ActionExecutor(config)

    # 初始化设备管理器
    device_manager = DeviceManager(config, executor)

    # 注册设备
    for device in config.get_devices():
        device_manager.register_device(device)

    # 决定运行模式
    if args.gui:
        run_gui_mode(config, executor, device_manager)
    else:
        run_tray_mode(config, executor, device_manager)


if __name__ == "__main__":
    main()
