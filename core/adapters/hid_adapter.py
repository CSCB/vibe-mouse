"""
通用 HID 适配器 / Generic HID Adapter

支持 USB 脚踏开关、Stream Deck、条码扫描枪、无线演示器等
通过 USB HID 报告描述符通信的设备。

依赖：hidapi (cross-platform) 或 pywinusb (Windows)
  pip install hidapi
  # Windows: pip install hid

也可使用 pynput 监听 HID 键盘模拟设备（如条码枪）。
"""

import importlib
import time
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class HIDAdapter(BaseAdapter):
    """
    通用 HID 适配器
    通过 hidapi 或 pywinusb 读取 HID 报告。
    """

    def _run(self):
        """启动 HID 监听"""
        backend = self.config.get("backend", "hidapi")  # "hidapi" / "pywinusb"

        if backend == "hidapi":
            self._run_hidapi()
        elif backend == "pywinusb":
            self._run_pywinusb()
        else:
            print(f"[HIDAdapter] Unknown backend / 未知后端: {backend}")

    def _run_hidapi(self):
        """使用 hidapi 库"""
        try:
            hid = importlib.import_module("hid")
        except ImportError:
            print(f"[HIDAdapter] hidapi not installed. Run: pip install hidapi")
            return

        vendor_id = self.config.get("vendor_id")
        product_id = self.config.get("product_id")

        if vendor_id is None or product_id is None:
            print(f"[HIDAdapter] vendor_id and product_id required / 需要配置 vendor_id 和 product_id")
            return

        try:
            device = hid.device()
            device.open(vendor_id, product_id)
            device.set_nonblocking(1)
            print(f"[HIDAdapter] HID opened / 已打开: VID={vendor_id:04x} PID={product_id:04x}")
        except Exception as e:
            print(f"[HIDAdapter] HID open failed: {e}")
            return

        report_size = self.config.get("report_size", 64)

        while self._running:
            try:
                data = device.read(report_size)
                if not data:
                    time.sleep(0.01)
                    continue

                # 解析 HID 报告
                input_id = self._parse_hid_report(data)
                if input_id:
                    self._emit(Event(
                        device_type=DeviceType.HID_GENERIC,
                        device_id=self.device_id,
                        input_type=InputType.BUTTON,
                        input_id=input_id,
                        value=1,
                        raw_data=bytes(data)
                    ))
            except Exception as e:
                print(f"[HIDAdapter] HID read error: {e}")
                time.sleep(0.5)

        device.close()

    def _run_pywinusb(self):
        """使用 pywinusb 库（Windows）"""
        try:
            pywinusb = importlib.import_module("pywinusb.hid")
        except ImportError:
            print(f"[HIDAdapter] pywinusb not installed. Run: pip install pywinusb")
            return

        vendor_id = self.config.get("vendor_id")
        product_id = self.config.get("product_id")

        filter = pywinusb.hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id)
        devices = filter.get_devices()

        if not devices:
            print(f"[HIDAdapter] No HID device found / 未找到 HID 设备")
            return

        hid_device = devices[0]
        hid_device.open()

        def _on_data(data):
            input_id = self._parse_hid_report(data)
            if input_id:
                self._emit(Event(
                    device_type=DeviceType.HID_GENERIC,
                    device_id=self.device_id,
                    input_type=InputType.BUTTON,
                    input_id=input_id,
                    value=1,
                    raw_data=bytes(data)
                ))

        hid_device.set_raw_data_handler(_on_data)
        print(f"[HIDAdapter] pywinusb listening / 监听中: {hid_device}")

        while self._running:
            time.sleep(0.5)

        hid_device.close()

    def _parse_hid_report(self, data):
        """解析 HID 报告数据为 input_id"""
        # 默认：报告的第一个非零字节作为按键码
        # 子类或配置可覆盖此逻辑
        custom_parser = self.config.get("report_parser")
        if custom_parser:
            # 自定义解析函数（高级用法）
            return custom_parser(data)

        if not data:
            return None

        # 基础解析：查找第一个非零字节
        for i, byte in enumerate(data):
            if byte != 0:
                return f"report_byte{i}_{byte:02x}"

        return None
