"""
VibeMouse GUI 客户端 / GUI Client

轻量桌面面板，提供：
- 实时显示当前检测到的 AI 工具
- 显示当前激活的 Skill
- 手动切换工具
- 工具切换历史记录
- 启用/禁用自动检测
- 快捷操作按钮

依赖：tkinter（Python 标准库）
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from typing import Optional

from .config import VibeTool, Config
from .window_detector import WindowDetector
from .tool_switcher import ToolSwitcher, SwitchReason


class VibeMouseGUI:
    """
    VibeMouse 图形界面客户端

    功能：
    1. 状态面板：当前工具、当前 Skill、检测状态
    2. 工具切换：手动选择 + 自动检测开关
    3. 历史记录：最近切换记录列表
    4. 快捷操作：打开配置工具、刷新检测、快速回切
    """

    def __init__(self, config: Config, executor, device_manager):
        self.config = config
        self.executor = executor
        self.device_manager = device_manager

        # 窗口检测器
        self.detector = WindowDetector(poll_interval=1.0)
        self.detector.set_on_tool_changed(self._on_tool_auto_switched)

        # 工具切换器
        self.switcher = ToolSwitcher(config, executor)

        # Tkinter 根窗口
        self.root = tk.Tk()
        self.root.title("Vibe Mouse Client")
        self.root.geometry("420x580")
        self.root.configure(bg="#1a1d27")
        self.root.resizable(False, False)

        # 防止关闭窗口时退出程序（隐藏到托盘）
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # UI 更新锁
        self._ui_lock = threading.Lock()
        self._running = True

        self._build_ui()
        self._start_refresh_loop()

    def _build_ui(self):
        """构建 UI"""
        # 配色
        bg = "#1a1d27"
        surface = "#242736"
        text = "#e4e6f0"
        text2 = "#8b8fa3"
        accent = "#3b82f6"
        green = "#22c55e"
        red = "#ef4444"

        self.root.configure(bg=bg)

        # ===== 标题栏 =====
        header = tk.Frame(self.root, bg=bg, height=50)
        header.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(header, text="Vibe Mouse", font=("Segoe UI", 18, "bold"),
                 fg=accent, bg=bg).pack(side="left")
        tk.Label(header, text="Client", font=("Segoe UI", 12),
                 fg=text2, bg=bg).pack(side="left", padx=(6, 0), pady=(4, 0))

        # Beta 标签
        tk.Label(header, text="BETA", font=("Segoe UI", 8, "bold"),
                 fg=bg, bg="#eab308", padx=6, pady=1).pack(side="right", pady=(6, 0))

        # ===== 状态卡片 =====
        status_card = tk.Frame(self.root, bg=surface, bd=0,
                               highlightbackground="#2e3142", highlightthickness=1)
        status_card.pack(fill="x", padx=16, pady=8)

        # 当前工具
        tool_row = tk.Frame(status_card, bg=surface)
        tool_row.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(tool_row, text="当前工具", font=("Segoe UI", 10),
                 fg=text2, bg=surface).pack(side="left")
        self.lbl_tool = tk.Label(tool_row, text="检测中...", font=("Segoe UI", 14, "bold"),
                                  fg=text, bg=surface)
        self.lbl_tool.pack(side="right")

        # 当前 Skill
        skill_row = tk.Frame(status_card, bg=surface)
        skill_row.pack(fill="x", padx=12, pady=(4, 4))
        tk.Label(skill_row, text="当前 Skill", font=("Segoe UI", 10),
                 fg=text2, bg=surface).pack(side="left")
        self.lbl_skill = tk.Label(skill_row, text="无", font=("Segoe UI", 11),
                                   fg=text2, bg=surface)
        self.lbl_skill.pack(side="right")

        # 检测状态
        detect_row = tk.Frame(status_card, bg=surface)
        detect_row.pack(fill="x", padx=12, pady=(4, 12))
        tk.Label(detect_row, text="自动检测", font=("Segoe UI", 10),
                 fg=text2, bg=surface).pack(side="left")
        self.lbl_detect = tk.Label(detect_row, text="已关闭", font=("Segoe UI", 10),
                                    fg=red, bg=surface)
        self.lbl_detect.pack(side="right")

        # ===== 工具切换区 =====
        switch_frame = tk.LabelFrame(self.root, text=" 切换工具 ", font=("Segoe UI", 10),
                                      fg=text2, bg=bg, bd=0, highlightbackground="#2e3142",
                                      highlightthickness=1)
        switch_frame.pack(fill="x", padx=16, pady=8)

        btn_frame = tk.Frame(switch_frame, bg=bg)
        btn_frame.pack(padx=8, pady=8)

        self.tool_buttons = {}
        for i, tool in enumerate(VibeTool):
            name = tool.value
            btn = tk.Button(btn_frame, text=name.capitalize(), font=("Segoe UI", 9),
                            bg=surface, fg=text, activebackground=accent, activeforeground="white",
                            bd=0, padx=10, pady=4, cursor="hand2",
                            command=lambda t=name: self._manual_switch(t))
            btn.grid(row=i // 4, column=i % 4, padx=3, pady=3)
            self.tool_buttons[name] = btn

        # 自动检测开关
        auto_frame = tk.Frame(switch_frame, bg=bg)
        auto_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.var_auto = tk.BooleanVar(value=False)
        chk_auto = tk.Checkbutton(auto_frame, text="启用窗口焦点自动检测",
                                   variable=self.var_auto, font=("Segoe UI", 9),
                                   fg=text, bg=bg, selectcolor=surface,
                                   activebackground=bg, activeforeground=text,
                                   command=self._toggle_auto_detect)
        chk_auto.pack(side="left")

        # ===== 快捷操作 =====
        quick_frame = tk.LabelFrame(self.root, text=" 快捷操作 ", font=("Segoe UI", 10),
                                     fg=text2, bg=bg, bd=0, highlightbackground="#2e3142",
                                     highlightthickness=1)
        quick_frame.pack(fill="x", padx=16, pady=8)

        quick_btns = tk.Frame(quick_frame, bg=bg)
        quick_btns.pack(padx=8, pady=8)

        tk.Button(quick_btns, text="快速回切", font=("Segoe UI", 9),
                  bg=surface, fg=text, bd=0, padx=12, pady=5,
                  command=self._quick_switch).pack(side="left", padx=3)

        tk.Button(quick_btns, text="刷新检测", font=("Segoe UI", 9),
                  bg=surface, fg=text, bd=0, padx=12, pady=5,
                  command=self._refresh_detect).pack(side="left", padx=3)

        tk.Button(quick_btns, text="打开配置", font=("Segoe UI", 9),
                  bg=surface, fg=text, bd=0, padx=12, pady=5,
                  command=self._open_config).pack(side="left", padx=3)

        tk.Button(quick_btns, text="退出 Skill", font=("Segoe UI", 9),
                  bg="#3d1f1f", fg=red, bd=0, padx=12, pady=5,
                  command=self._deactivate_skill).pack(side="left", padx=3)

        # ===== 历史记录 =====
        hist_frame = tk.LabelFrame(self.root, text=" 切换历史 ", font=("Segoe UI", 10),
                                    fg=text2, bg=bg, bd=0, highlightbackground="#2e3142",
                                    highlightthickness=1)
        hist_frame.pack(fill="both", expand=True, padx=16, pady=8)

        self.hist_text = tk.Text(hist_frame, font=("Cascadia Mono", 9),
                                  fg=text, bg=surface, bd=0, height=8,
                                  state="disabled", wrap="none")
        self.hist_text.pack(fill="both", expand=True, padx=8, pady=8)

        # 底部信息
        footer = tk.Frame(self.root, bg=bg)
        footer.pack(fill="x", padx=16, pady=(4, 12))

        self.lbl_footer = tk.Label(footer, text="就绪", font=("Segoe UI", 9),
                                    fg=text2, bg=bg)
        self.lbl_footer.pack(side="left")

    def _on_tool_auto_switched(self, new_tool: str, old_tool: Optional[str]):
        """窗口自动检测到工具切换时的回调"""
        print(f"[GUI] 自动切换: {old_tool} -> {new_tool}")
        self.switcher.switch(new_tool, SwitchReason.AUTO_DETECT)
        self._update_ui()

    def _manual_switch(self, tool_name: str):
        """手动切换工具"""
        self.switcher.switch(tool_name, SwitchReason.MANUAL)
        self._update_ui()

    def _quick_switch(self):
        """快速回切到上一个工具"""
        self.switcher.quick_switch()
        self._update_ui()

    def _refresh_detect(self):
        """手动刷新窗口检测"""
        detected = self.detector.detect_now()
        if detected:
            info = self.detector.get_window_info()
            self.lbl_footer.config(text=f"检测到: {info.get('title', 'unknown')[:40]}")
            if detected != self.config.current_tool:
                self._manual_switch(detected)
        else:
            self.lbl_footer.config(text="未检测到已知的 AI 工具窗口")

    def _open_config(self):
        """打开配置工具（浏览器）"""
        import webbrowser
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config-tool.html")
        webbrowser.open(f"file:///{config_path}")

    def _deactivate_skill(self):
        """退出当前 Skill"""
        if self.executor.active_skill:
            self.executor.deactivate_skill()
            self._update_ui()

    def _toggle_auto_detect(self):
        """切换自动检测开关"""
        if self.var_auto.get():
            self.detector.start_monitoring()
            self.lbl_detect.config(text="运行中", fg="green")
        else:
            self.detector.stop_monitoring()
            self.lbl_detect.config(text="已关闭", fg="red")

    def _update_ui(self):
        """更新 UI 状态"""
        with self._ui_lock:
            # 当前工具
            current = self.config.current_tool
            self.lbl_tool.config(text=current.upper())

            # 高亮当前工具按钮
            for name, btn in self.tool_buttons.items():
                if name == current:
                    btn.config(bg="#3b82f6", fg="white")
                else:
                    btn.config(bg="#242736", fg="#e4e6f0")

            # 当前 Skill
            if self.executor.active_skill:
                skill = self.executor.active_skill
                self.lbl_skill.config(text=f"{skill.name} v{skill.version}", fg="#eab308")
            else:
                self.lbl_skill.config(text="无", fg="#8b8fa3")

            # 历史记录
            history = self.switcher.get_history_summary()
            self.hist_text.config(state="normal")
            self.hist_text.delete("1.0", "end")
            if history:
                for h in reversed(history[-10:]):
                    skill_tag = f" [{h['skill']}]" if h['skill'] else ""
                    line = f"{h['time']}  {h['from']:>10} -> {h['to']:<10} ({h['reason']}){skill_tag}\n"
                    self.hist_text.insert("end", line)
            else:
                self.hist_text.insert("end", "暂无切换记录\n")
            self.hist_text.config(state="disabled")

    def _start_refresh_loop(self):
        """启动 UI 刷新循环"""
        def refresh():
            if self._running:
                self._update_ui()
                self.root.after(1000, refresh)

        self.root.after(1000, refresh)

    def _on_close(self):
        """关闭窗口时隐藏到托盘而非退出"""
        self.root.withdraw()
        # 可以在这里添加托盘图标逻辑
        print("[GUI] 窗口已隐藏（按托盘图标可恢复）")

    def show(self):
        """显示窗口"""
        self.root.deiconify()

    def run(self):
        """运行 GUI 主循环"""
        print("[GUI] VibeMouse Client 已启动")
        self._update_ui()
        self.root.mainloop()
        self._running = False
        self.detector.stop_monitoring()
