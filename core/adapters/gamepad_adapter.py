"""
游戏手柄适配器 / Gamepad Adapter

支持 Xbox/PS/Switch 等游戏手柄，监听按键、摇杆轴、扳机、方向键。
Supports Xbox/PS/Switch gamepads: buttons, joysticks, triggers, D-pad.

依赖：pygame (pip install pygame)
也可替换为 inputs 库或 xinput 以获得更低延迟。
"""

import time
import importlib
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class GamepadAdapter(BaseAdapter):
    """
    游戏手柄适配器
    使用 pygame.joystick 监听手柄事件。
    """

    # 常见手柄按键标准化映射
    BUTTON_NAMES = [
        "a", "b", "x", "y",
        "lb", "rb",
        "back", "start",
        "guide",
        "l3", "r3"
    ]

    AXIS_NAMES = [
        "lx", "ly",        # 左摇杆 X/Y
        "rx", "ry",        # 右摇杆 X/Y
        "lt", "rt",        # 左/右扳机
    ]

    def _run(self):
        """初始化 pygame 并轮询手柄状态"""
        try:
            pg = importlib.import_module("pygame")
        except ImportError:
            print(f"[GamepadAdapter] pygame not installed. Run: pip install pygame")
            return

        pg.init()
        pg.joystick.init()

        joystick_index = self.config.get("joystick_index", 0)
        deadzone = self.config.get("deadzone", 0.15)

        if pg.joystick.get_count() == 0:
            print(f"[GamepadAdapter] No gamepad detected / 未检测到手柄")
            pg.quit()
            return

        try:
            joystick = pg.joystick.Joystick(joystick_index)
            joystick.init()
            print(f"[GamepadAdapter] Connected / 已连接: {joystick.get_name()}")
        except Exception as e:
            print(f"[GamepadAdapter] Failed to init joystick: {e}")
            pg.quit()
            return

        # 记录上一帧状态，用于检测变化
        prev_buttons = [False] * joystick.get_numbuttons()
        prev_axes = [0.0] * joystick.get_numaxes()
        prev_hats = [(0, 0)] * joystick.get_numhats()

        clock = pg.time.Clock()

        while self._running:
            pg.event.pump()

            # 检测按键变化
            for i in range(joystick.get_numbuttons()):
                state = joystick.get_button(i)
                if state and not prev_buttons[i]:
                    name = self.BUTTON_NAMES[i] if i < len(self.BUTTON_NAMES) else f"btn_{i}"
                    self._emit(Event(
                        device_type=DeviceType.GAMEPAD,
                        device_id=self.device_id,
                        input_type=InputType.BUTTON,
                        input_id=name,
                        value=1
                    ))
                prev_buttons[i] = state

            # 检测轴变化（带死区）
            for i in range(joystick.get_numaxes()):
                val = joystick.get_axis(i)
                if abs(val) > deadzone and abs(val - prev_axes[i]) > 0.1:
                    name = self.AXIS_NAMES[i] if i < len(self.AXIS_NAMES) else f"axis_{i}"
                    # 报告方向：正/负
                    direction = "+" if val > 0 else "-"
                    self._emit(Event(
                        device_type=DeviceType.GAMEPAD,
                        device_id=self.device_id,
                        input_type=InputType.AXIS,
                        input_id=f"{name}{direction}",
                        value=round(val, 3)
                    ))
                prev_axes[i] = val

            # 检测方向键 (hat)
            for i in range(joystick.get_numhats()):
                hx, hy = joystick.get_hat(i)
                if (hx, hy) != prev_hats[i] and (hx, hy) != (0, 0):
                    direction_map = {
                        (0, 1): "up", (0, -1): "down",
                        (1, 0): "right", (-1, 0): "left",
                        (1, 1): "up_right", (-1, 1): "up_left",
                        (1, -1): "down_right", (-1, -1): "down_left"
                    }
                    self._emit(Event(
                        device_type=DeviceType.GAMEPAD,
                        device_id=self.device_id,
                        input_type=InputType.HAT,
                        input_id=direction_map.get((hx, hy), f"hat_{hx}_{hy}"),
                        value=1
                    ))
                prev_hats[i] = (hx, hy)

            clock.tick(60)  # 60 FPS 轮询

        joystick.quit()
        pg.quit()
