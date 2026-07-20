"""
蓝牙设备适配器 / Bluetooth Device Adapter

支持蓝牙电话座机、蓝牙遥控器、蓝牙旋钮等 BLE/Classic 设备。
Supports Bluetooth phones, remotes, dials via BLE or Classic Bluetooth.

依赖：bleak (BLE) 或 pybluez (Classic)
  pip install bleak
  pip install pybluez  # Windows 可能需要预编译 wheel

架构：
- BLE 设备：扫描 -> 连接 -> 订阅特征值通知 -> 解析按键数据
- Classic：配对 -> 监听 RFCOMM 或 HID 报告
"""

import asyncio
import importlib
import time
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class BluetoothAdapter(BaseAdapter):
    """
    蓝牙设备适配器
    同时支持 BLE ( bleak ) 和 Classic Bluetooth ( pybluez ) 模式。
    """

    # 常见蓝牙电话座机按键映射
    PHONE_BUTTON_MAP = {
        0x01: "hook",      # 摘机/挂机
        0x02: "redial",    # 重拨
        0x03: "mute",      # 静音
        0x04: "vol_up",    # 音量+
        0x05: "vol_down",  # 音量-
        0x06: "hold",      # 保持
    }

    def __init__(self, device_id, config, on_event):
        super().__init__(device_id, config, on_event)
        self._bleak = None
        self._loop = None

    def _run(self):
        """启动蓝牙监听"""
        mode = self.config.get("mode", "ble")  # "ble" or "classic"

        if mode == "ble":
            self._run_ble()
        else:
            self._run_classic()

    def _run_ble(self):
        """BLE 模式：使用 bleak 库"""
        try:
            bleak = importlib.import_module("bleak")
        except ImportError:
            print(f"[BluetoothAdapter] bleak not installed. Run: pip install bleak")
            return

        target_address = self.config.get("mac_address")
        if not target_address:
            print(f"[BluetoothAdapter] No MAC address configured / 未配置 MAC 地址")
            return

        # 获取通知特征值 UUID
        notify_uuid = self.config.get("notify_uuid", "0000ffe1-0000-1000-8000-00805f9b34fb")

        def _on_notify(sender, data):
            """BLE 通知回调"""
            # 解析按键数据（具体协议取决于设备）
            key_code = data[0] if data else 0
            input_id = self.PHONE_BUTTON_MAP.get(key_code, f"key_{key_code:02x}")

            self._emit(Event(
                device_type=DeviceType.BLUETOOTH,
                device_id=self.device_id,
                input_type=InputType.BUTTON,
                input_id=input_id,
                value=1,
                raw_data=data
            ))

        async def _ble_loop():
            while self._running:
                try:
                    async with bleak.BleakClient(target_address) as client:
                        print(f"[BluetoothAdapter] BLE connected / 已连接: {target_address}")
                        await client.start_notify(notify_uuid, _on_notify)
                        while self._running and client.is_connected:
                            await asyncio.sleep(0.5)
                        await client.stop_notify(notify_uuid)
                except Exception as e:
                    print(f"[BluetoothAdapter] BLE error: {e}, retrying in 3s...")
                    await asyncio.sleep(3)

        try:
            asyncio.run(_ble_loop())
        except Exception as e:
            print(f"[BluetoothAdapter] BLE loop error: {e}")

    def _run_classic(self):
        """Classic Bluetooth 模式：使用 pybluez"""
        try:
            bluetooth = importlib.import_module("bluetooth")
        except ImportError:
            print(f"[BluetoothAdapter] pybluez not installed. Run: pip install pybluez")
            return

        target_address = self.config.get("mac_address")
        port = self.config.get("port", 1)

        if not target_address:
            print(f"[BluetoothAdapter] No MAC address configured / 未配置 MAC 地址")
            return

        while self._running:
            try:
                sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                sock.connect((target_address, port))
                print(f"[BluetoothAdapter] Classic connected / 已连接: {target_address}")

                while self._running:
                    data = sock.recv(1024)
                    if not data:
                        break
                    # 解析按键数据
                    key_code = data[0] if data else 0
                    input_id = self.PHONE_BUTTON_MAP.get(key_code, f"key_{key_code:02x}")
                    self._emit(Event(
                        device_type=DeviceType.BLUETOOTH,
                        device_id=self.device_id,
                        input_type=InputType.BUTTON,
                        input_id=input_id,
                        value=1,
                        raw_data=data
                    ))

                sock.close()
            except Exception as e:
                print(f"[BluetoothAdapter] Classic error: {e}, retrying in 3s...")
                time.sleep(3)
