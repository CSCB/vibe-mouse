"""
鼠标适配器 / Mouse Adapter

兼容原有 vibe-mouse 鼠标监听逻辑，通过 pynput 监听鼠标按键。
Backward-compatible mouse listener using pynput.
"""

from pynput import mouse
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class MouseAdapter(BaseAdapter):
    """
    鼠标适配器
    将 pynput 鼠标事件转换为统一 Event。
    """

    # pynput Button -> input_id 映射
    BUTTON_MAP = {
        mouse.Button.left: "left",
        mouse.Button.right: "right",
        mouse.Button.middle: "middle",
        mouse.Button.x1: "button8",
        mouse.Button.x2: "button9",
    }

    def _run(self):
        """启动 pynput 鼠标监听"""
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()
        # 保持线程存活
        while self._running:
            self._listener.join(timeout=0.5)
        self._listener.stop()

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return
        input_id = self.BUTTON_MAP.get(button, str(button))
        event = Event(
            device_type=DeviceType.MOUSE,
            device_id=self.device_id,
            input_type=InputType.BUTTON,
            input_id=input_id,
            value=1,
            raw_data={"x": x, "y": y, "button": button, "pressed": pressed}
        )
        self._emit(event)
