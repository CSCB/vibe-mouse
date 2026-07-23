"""
窗口焦点检测器 / Window Focus Detector

跨平台检测当前前台窗口，判断其属于哪个 AI 开发工具，
实现自动工具切换。

支持平台：Windows（优先）、macOS、Linux
"""

import platform
import time
import threading
from typing import Optional, Callable, Dict, List
from enum import Enum


class DetectionMethod(Enum):
    """检测方法"""
    TITLE = "title"           # 窗口标题匹配
    PROCESS = "process"       # 进程名匹配
    BOTH = "both"             # 标题+进程双重匹配


# AI 工具窗口特征库
# 每个工具定义窗口标题关键词和进程名关键词
TOOL_WINDOW_SIGNATURES = {
    "trae": {
        "titles": ["Trae", "Trae IDE"],
        "processes": ["Trae", "Trae.exe", "trae"],
        "description": "Trae IDE"
    },
    "cursor": {
        "titles": ["Cursor", "Cursor IDE"],
        "processes": ["Cursor", "Cursor.exe", "cursor"],
        "description": "Cursor IDE"
    },
    "windsurf": {
        "titles": ["Windsurf", "Windsurf IDE", "Surf"],
        "processes": ["Windsurf", "Windsurf.exe", "windsurf"],
        "description": "Windsurf IDE"
    },
    "copilot": {
        "titles": ["Visual Studio Code", "VS Code", "Code - ", "Code:"],
        "processes": ["Code", "Code.exe", "code", "Visual Studio Code"],
        "description": "VS Code + Copilot"
    },
    "deveco_studio": {
        "titles": ["DevEco Studio", "DevEco"],
        "processes": ["devecostudio", "devecostudio.exe", "DevEcoStudio"],
        "description": "DevEco Studio"
    },
    "deveco_code": {
        "titles": ["DevEco Code"],
        "processes": ["devecocode", "devecocode.exe", "DevEcoCode"],
        "description": "DevEco Code"
    },
    "codearts": {
        "titles": ["CodeArts", "CodeArts IDE"],
        "processes": ["CodeArts", "CodeArts.exe", "codearts"],
        "description": "CodeArts IDE"
    }
}


class WindowDetector:
    """
    窗口焦点检测器

    持续监控前台窗口，当检测到 AI 工具窗口时触发回调。
    支持手动检测（单次）和自动监控（后台线程）。
    """

    def __init__(self, poll_interval: float = 1.0):
        """
        Args:
            poll_interval: 自动检测轮询间隔（秒）
        """
        self.poll_interval = poll_interval
        self._platform = platform.system()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_tool: Optional[str] = None
        self._on_tool_changed: Optional[Callable[[str, str], None]] = None
        self._lock = threading.Lock()

        # 平台特定的检测函数
        self._detector = self._init_detector()

    def _init_detector(self):
        """根据平台初始化检测器"""
        if self._platform == "Windows":
            return self._detect_windows
        elif self._platform == "Darwin":
            return self._detect_macos
        else:
            return self._detect_linux

    # ------------------------------------------------------------------
    # Windows 检测
    # ------------------------------------------------------------------
    def _detect_windows(self) -> Optional[str]:
        """Windows 平台：使用 win32gui + psutil"""
        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd)

            # 获取进程名
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = ""

            return self._match_tool(title, process_name)

        except ImportError:
            # 回退到 ctypes 方案（不依赖 pywin32）
            return self._detect_windows_ctypes()
        except Exception as e:
            print(f"[WindowDetector] Windows detection error: {e}")
            return None

    def _detect_windows_ctypes(self) -> Optional[str]:
        """Windows 回退：仅使用 ctypes 获取窗口标题"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return None

            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            return self._match_tool(title, "")

        except Exception as e:
            print(f"[WindowDetector] ctypes detection error: {e}")
            return None

    # ------------------------------------------------------------------
    # macOS 检测
    # ------------------------------------------------------------------
    def _detect_macos(self) -> Optional[str]:
        """macOS 平台：使用 AppleScript 获取前台应用"""
        try:
            import subprocess
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                app_name = result.stdout.strip()
                return self._match_tool("", app_name)
        except Exception as e:
            print(f"[WindowDetector] macOS detection error: {e}")
        return None

    # ------------------------------------------------------------------
    # Linux 检测
    # ------------------------------------------------------------------
    def _detect_linux(self) -> Optional[str]:
        """Linux 平台：使用 xdotool 或 wmctrl"""
        try:
            import subprocess
            # 尝试 xdotool
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                title = result.stdout.strip()
                return self._match_tool(title, "")

            # 尝试 wmctrl
            result = subprocess.run(
                ["wmctrl", "-l", "-p"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                # 解析获取活动窗口标题（简化处理）
                lines = result.stdout.strip().split("\n")
                if lines:
                    # 取最后一行作为前台窗口
                    parts = lines[-1].split(None, 4)
                    if len(parts) >= 5:
                        title = parts[4]
                        return self._match_tool(title, "")
        except Exception as e:
            print(f"[WindowDetector] Linux detection error: {e}")
        return None

    # ------------------------------------------------------------------
    # 工具匹配
    # ------------------------------------------------------------------
    def _match_tool(self, title: str, process_name: str, method: DetectionMethod = DetectionMethod.BOTH) -> Optional[str]:
        """
        根据窗口标题和进程名匹配工具

        Args:
            title: 窗口标题
            process_name: 进程名
            method: 匹配方法

        Returns:
            匹配到的工具名，未匹配返回 None
        """
        title_lower = title.lower()
        process_lower = process_name.lower()

        for tool_name, signature in TOOL_WINDOW_SIGNATURES.items():
            title_match = False
            process_match = False

            # 标题匹配
            if method in (DetectionMethod.TITLE, DetectionMethod.BOTH):
                for keyword in signature["titles"]:
                    if keyword.lower() in title_lower:
                        title_match = True
                        break

            # 进程名匹配
            if method in (DetectionMethod.PROCESS, DetectionMethod.BOTH):
                for keyword in signature["processes"]:
                    if keyword.lower() in process_lower:
                        process_match = True
                        break

            # 根据匹配方法判断是否命中
            if method == DetectionMethod.BOTH and (title_match or process_match):
                return tool_name
            elif method == DetectionMethod.TITLE and title_match:
                return tool_name
            elif method == DetectionMethod.PROCESS and process_match:
                return tool_name

        return None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def detect_now(self) -> Optional[str]:
        """立即检测一次当前前台窗口"""
        return self._detector()

    def get_window_info(self) -> Dict[str, str]:
        """获取当前窗口详细信息"""
        tool = self.detect_now()
        info = {"tool": tool or "unknown", "title": "", "process": ""}

        if self._platform == "Windows":
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                info["title"] = win32gui.GetWindowText(hwnd)
                import win32process
                import psutil
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                info["process"] = psutil.Process(pid).name()
            except:
                pass

        return info

    def set_on_tool_changed(self, callback: Callable[[str, str], None]):
        """
        设置工具切换回调

        Args:
            callback: 回调函数 (new_tool_name, old_tool_name) -> None
        """
        self._on_tool_changed = callback

    def start_monitoring(self):
        """启动后台自动监控线程"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"[WindowDetector] 窗口监控已启动（轮询间隔: {self.poll_interval}s）")

    def stop_monitoring(self):
        """停止后台监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[WindowDetector] 窗口监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                detected = self.detect_now()

                with self._lock:
                    if detected and detected != self._last_tool:
                        old_tool = self._last_tool
                        self._last_tool = detected

                        if self._on_tool_changed:
                            try:
                                self._on_tool_changed(detected, old_tool)
                            except Exception as e:
                                print(f"[WindowDetector] Callback error: {e}")

            except Exception as e:
                print(f"[WindowDetector] Monitor error: {e}")

            time.sleep(self.poll_interval)

    @property
    def last_detected_tool(self) -> Optional[str]:
        """最后一次检测到的工具"""
        with self._lock:
            return self._last_tool

    @property
    def is_monitoring(self) -> bool:
        """是否正在监控"""
        return self._running


# 便捷函数：单次检测
def detect_current_tool() -> Optional[str]:
    """立即检测当前前台窗口所属的工具"""
    detector = WindowDetector()
    return detector.detect_now()
