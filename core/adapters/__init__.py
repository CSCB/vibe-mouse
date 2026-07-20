"""
外设适配器包 / Device Adapters Package

每个外设类型对应一个适配器，负责：
1. 监听原生输入事件
2. 将原生事件转换为统一的 Event 对象
3. 通过回调函数将 Event 上报给外设管理器

Each device type has an adapter responsible for:
1. Listening to native input events
2. Converting native events to unified Event objects
3. Reporting Events to the Device Manager via callbacks
"""

from .base import BaseAdapter
from .mouse_adapter import MouseAdapter
from .keyboard_adapter import KeyboardAdapter
from .gamepad_adapter import GamepadAdapter
from .bluetooth_adapter import BluetoothAdapter
from .ir_adapter import IRAdapter
from .hid_adapter import HIDAdapter
from .network_adapter import NetworkAdapter
from .voice_adapter import VoiceAdapter

__all__ = [
    "BaseAdapter",
    "MouseAdapter",
    "KeyboardAdapter",
    "GamepadAdapter",
    "BluetoothAdapter",
    "IRAdapter",
    "HIDAdapter",
    "NetworkAdapter",
    "VoiceAdapter",
]

# 适配器注册表：device_type -> AdapterClass
ADAPTER_REGISTRY = {
    "mouse": MouseAdapter,
    "keyboard": KeyboardAdapter,
    "gamepad": GamepadAdapter,
    "bluetooth": BluetoothAdapter,
    "ir_remote": IRAdapter,
    "hid_generic": HIDAdapter,
    "network": NetworkAdapter,
    "voice": VoiceAdapter,
}


def get_adapter_class(device_type: str):
    """根据外设类型获取适配器类 / Get adapter class by device type"""
    return ADAPTER_REGISTRY.get(device_type)


def list_supported_devices():
    """列出所有支持的外设类型 / List all supported device types"""
    return list(ADAPTER_REGISTRY.keys())
