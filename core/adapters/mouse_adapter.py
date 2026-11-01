"""
鼠标适配器 / Mouse Adapter

兼容原有 vibe-mouse 鼠标监听逻辑，通过 pynput 监听鼠标按键。
Backward-compatible mouse listener using pynput.
"""

import time
import threading
from pynput import mouse
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class MouseAdapter(BaseAdapter):
    """
    鼠标适配器
    将 pynput 鼠标事件转换为统一 Event。

    特殊处理：middle 按键检测双击（300ms 内两次按下），
    其他按键仍为单击触发。
    """

    # pynput Button -> input_id 映射
    BUTTON_MAP = {
        mouse.Button.left: "left",
        mouse.Button.right: "right",
        mouse.Button.middle: "middle",
        mouse.Button.x1: "button8",
        mouse.Button.x2: "button9",
    }

    # 双击检测时间窗口（秒）
    DOUBLE_CLICK_WINDOW = 0.35

    def __init__(self, device_id: str, config: dict, on_event):
        super().__init__(device_id, config, on_event)
        self._last_middle_press = 0.0
        self._middle_click_count = 0
        self._double_click_timer = None

    def _run(self):
        """启动 pynput 鼠标监听"""
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()
        while self._running:
            self._listener.join(timeout=0.5)
        self._listener.stop()

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return

        # 中键：双击检测
        if button == mouse.Button.middle:
            now = time.time()
            self._middle_click_count += 1

            if self._middle_click_count == 1:
                self._last_middle_press = now
                # 启动超时定时器：如果 350ms 内没有第二次点击，丢弃
                self._double_click_timer = threading.Timer(
                    self.DOUBLE_CLICK_WINDOW, self._reset_middle_click
                )
                self._double_click_timer.daemon = True
                self._double_click_timer.start()
            elif self._middle_click_count == 2:
                # 检查时间窗口
                if now - self._last_middle_press <= self.DOUBLE_CLICK_WINDOW:
                    # 双击确认！取消超时定时器
                    if self._double_click_timer:
                        self._double_click_timer.cancel()
                        self._double_click_timer = None
                    self._middle_click_count = 0
                    self._emit_event(x, y, "middle_double", button)
                else:
                    # 超时，重置为第一次点击
                    self._middle_click_count = 1
                    self._last_middle_press = now
                    self._double_click_timer = threading.Timer(
                        self.DOUBLE_CLICK_WINDOW, self._reset_middle_click
                    )
                    self._double_click_timer.daemon = True
                    self._double_click_timer.start()
            return

        # 非中键：正常单击触发
        input_id = self.BUTTON_MAP.get(button, str(button))
        self._emit_event(x, y, input_id, button)

    def _reset_middle_click(self):
        """超时重置中键点击计数（单击不触发）"""
        self._middle_click_count = 0

    def _emit_event(self, x, y, input_id, button):
        event = Event(
            device_type=DeviceType.MOUSE,
            device_id=self.device_id,
            input_type=InputType.BUTTON,
            input_id=input_id,
            value=1,
            raw_data={"x": x, "y": y, "button": str(button), "pressed": True}
        )
        self._emit(event)
