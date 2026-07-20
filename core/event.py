"""
统一事件抽象层 / Unified Event Abstraction Layer

所有外设输入都转换为标准 Event 对象，由外设管理器统一路由。
All device inputs are converted to standard Event objects and routed by the Device Manager.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import time


class DeviceType(Enum):
    """外设类型 / Device type"""
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    GAMEPAD = "gamepad"
    BLUETOOTH = "bluetooth"
    IR_REMOTE = "ir_remote"
    HID_GENERIC = "hid_generic"
    NETWORK = "network"


class InputType(Enum):
    """输入类型 / Input type"""
    BUTTON = "button"          # 按键按下/释放
    AXIS = "axis"              # 模拟轴（摇杆、扳机等）
    HAT = "hat"                # 方向键/十字键
    DIAL = "dial"              # 旋转拨轮/旋钮
    TOUCH = "touch"            # 触控手势
    GESTURE = "gesture"        # 空中手势
    VOICE = "voice"            # 语音触发
    SCAN = "scan"              # 条码/二维码扫描
    RAW = "raw"                # 原始数据（特殊外设）


@dataclass
class Event:
    """
    统一输入事件
    Unified input event

    Attributes:
        device_type: 外设类型 (DeviceType)
        device_id: 设备唯一标识（如 "mouse_0", "gamepad_xbox_1"）
        input_type: 输入类型 (InputType)
        input_id: 输入标识（如 "button_a", "axis_lx", "power"）
        value: 输入值（button: 1/0, axis: -1.0~1.0, dial: 旋转步数）
        raw_data: 原始数据（适配器保留的原始事件，可选）
        timestamp: 事件时间戳
    """
    device_type: DeviceType
    device_id: str
    input_type: InputType
    input_id: str
    value: Any = 1
    raw_data: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)

    def __repr__(self):
        return (f"Event({self.device_type.value}/{self.device_id} "
                f"{self.input_type.value}:{self.input_id}={self.value})")
