"""
键盘/多媒体键适配器 / Keyboard & Multimedia Key Adapter

监听键盘按键和多媒体键（播放、音量、搜索等）。
Listen to keyboard keys and multimedia keys (play, volume, search, etc.).

依赖：pynput
"""

from pynput import keyboard
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class KeyboardAdapter(BaseAdapter):
    """
    键盘适配器
    监听配置中指定的按键（支持全局热键）。
    """

    def _run(self):
        """启动 pynput 键盘监听"""
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()
        while self._running:
            self._listener.join(timeout=0.5)
        self._listener.stop()

    def _on_press(self, key):
        """按键回调"""
        # 将 key 转为字符串标识
        if isinstance(key, keyboard.Key):
            key_id = key.name.lower()
        elif isinstance(key, keyboard.KeyCode):
            key_id = key.char.lower() if key.char else str(key.vk)
        else:
            key_id = str(key)

        # 只处理配置中白名单的按键
        watched_keys = self.config.get("watched_keys", [])
        if watched_keys and key_id not in watched_keys:
            return

        event = Event(
            device_type=DeviceType.KEYBOARD,
            device_id=self.device_id,
            input_type=InputType.BUTTON,
            input_id=key_id,
            value=1,
            raw_data={"key": key}
        )
        self._emit(event)
