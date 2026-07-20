import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config, VibeTool
from core.executor import ActionExecutor
from core.device_manager import DeviceManager
from core.system_tray import SystemTray


def print_help():
    print("=" * 40)
    print("       Vibe Mouse / Vibe 鼠标        ")
    print("=" * 40)
    print("可用工具 / Available Tools:")
    for tool in VibeTool:
        print(f"  - {tool.value}")
    print("\n命令行用法 / Usage: python core/main.py [tool_name]")
    print("例如 / Example: python core/main.py trae")
    print("系统托盘模式 / Tray mode: 直接运行即可")
    print("=" * 40 + "\n")


def main():
    config = Config()

    # 命令行参数切换工具（向后兼容）
    if len(sys.argv) > 1:
        tool_name = sys.argv[1].lower()
        if tool_name in ["--help", "-h"]:
            print_help()
            return
        valid_tools = [t.value for t in VibeTool]
        if tool_name in valid_tools:
            config.current_tool = tool_name
            config.save_config()
        else:
            print(f"未知工具 / Unknown tool: {tool_name}")
            print_help()
            return

    executor = ActionExecutor(config)
    device_manager = DeviceManager(config, executor)

    # 从配置加载并注册所有外设
    device_manager.load_from_config()

    def on_exit():
        print("Vibe Mouse 正在退出 / is exiting...")
        device_manager.stop_all()
        os._exit(0)

    # 系统托盘
    tray = SystemTray(config, executor, device_manager, on_exit)

    try:
        # 启动所有外设
        device_manager.start_all()

        active_devices = [d["id"] for d in config.get_devices()]
        print(f"Vibe Mouse 运行中 / running...")
        print(f"当前工具 / Current tool: {config.current_tool}")
        print(f"已注册外设 / Active devices: {', '.join(active_devices)}")
        print("请在系统托盘查看图标并进行控制 / Check system tray for controls.")

        # 启动系统托盘（阻塞主线程）
        tray.run()

    except KeyboardInterrupt:
        print("\n检测到退出信号 / Exit signal detected...")
        device_manager.stop_all()
        os._exit(0)


if __name__ == "__main__":
    main()
