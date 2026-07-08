import sys
import os
import threading

# 确保在项目根目录可以正常 import core
# Ensure core can be imported normally from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config, VibeTool
from core.executor import ActionExecutor
from core.listener import MouseListener
from core.system_tray import SystemTray

def print_help():
    print("===============================")
    print("       Vibe Mouse Core         ")
    print("===============================")
    print("可用工具 / Available Tools:")
    for tool in VibeTool:
        print(f"  - {tool.value}")
    print("\n命令行用法 / Command line usage: python core/main.py [tool_name]")
    print("例如 / Example: python core/main.py trae")
    print("系统托盘模式 / System Tray Mode: 直接运行程序，将在右下角/顶部菜单栏显示图标")
    print("Run the program directly, an icon will appear in the bottom right corner / top menu bar")
    print("===============================\n")

def main():
    config = Config()
    
    # 允许通过命令行参数切换当前工具 (向后兼容)
    # Allow switching the current tool via command line arguments (backward compatible)
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
    listener = MouseListener(config, executor)
    
    def on_exit():
        print("Vibe Mouse 正在退出 / is exiting...")
        os._exit(0) # 强制退出所有线程 / Force exit all threads
    
    # 初始化系统托盘
    # Initialize system tray
    tray = SystemTray(config, executor, listener, on_exit)
    
    try:
        # 在非阻塞线程中启动鼠标监听
        # Start mouse listener in a non-blocking thread
        listener_thread = threading.Thread(target=listener.start, daemon=True)
        listener_thread.start()
        
        print(f"Vibe Mouse 运行中 / running... 映射工具为 / mapped tool: {config.current_tool}")
        print("请在系统托盘查看图标并进行控制 / Please check the system tray icon for controls.")
        
        # 启动系统托盘 (阻塞主线程，保持程序运行)
        # Start system tray (blocks main thread, keeps program running)
        tray.run()
        
    except KeyboardInterrupt:
        print("\n检测到退出信号 / Exit signal detected...")
        listener.stop()
        os._exit(0)

if __name__ == "__main__":
    main()