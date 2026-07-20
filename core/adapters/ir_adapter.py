"""
红外遥控器适配器 / IR Remote Adapter

支持电视遥控器、空调遥控器等红外设备。
Supports TV remotes, AC remotes, and other IR devices.

依赖方案：
A. USB 红外接收头 (如 TSOP4838 + CH340) -> 串口读取
   pip install pyserial
B. 树莓派等 GPIO + lirc
C. Broadlink RM 系列 (WiFi 红外转发器)
   pip install broadlink

架构：监听原始 NEC / RC5 / RC6 / 自定义协议 -> 解码为按键标识
"""

import time
import importlib
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class IRAdapter(BaseAdapter):
    """
    红外遥控器适配器
    支持串口红外接收头、Broadlink WiFi 红外、GPIO lirc 三种模式。
    """

    # 常见电视遥控器 NEC 协议码表（示例）
    TV_BUTTON_MAP = {
        0xFFA25D: "power",
        0xFF629D: "vol_up",
        0xFFA857: "vol_down",
        0xFF22DD: "prev",
        0xFF02FD: "next",
        0xFFC23D: "play_pause",
        0xFFE01F: "down",
        0xFF906F: "up",
        0xFF6897: "left",
        0xFF9867: "right",
        0xFFB04F: "ok",
        0xFF38C7: "menu",
        0xFF18E7: "back",
        0xFF10EF: "home",
        0xFF5AA5: "mute",
    }

    # 空调遥控器常见按键（由于空调码通常包含状态，这里用简化映射）
    AC_BUTTON_MAP = {
        0x01: "power",
        0x02: "mode_cool",
        0x03: "mode_heat",
        0x04: "temp_up",
        0x05: "temp_down",
        0x06: "fan_auto",
        0x07: "fan_low",
        0x08: "fan_high",
        0x09: "swing",
        0x0A: "timer",
    }

    def _run(self):
        """根据配置选择模式启动"""
        mode = self.config.get("mode", "serial")  # "serial" / "broadlink" / "lirc"

        if mode == "serial":
            self._run_serial()
        elif mode == "broadlink":
            self._run_broadlink()
        elif mode == "lirc":
            self._run_lirc()
        else:
            print(f"[IRAdapter] Unknown mode / 未知模式: {mode}")

    def _run_serial(self):
        """串口红外接收头模式"""
        try:
            serial = importlib.import_module("serial")
        except ImportError:
            print(f"[IRAdapter] pyserial not installed. Run: pip install pyserial")
            return

        port = self.config.get("port", "COM3")
        baudrate = self.config.get("baudrate", 9600)
        remote_type = self.config.get("remote_type", "tv")  # "tv" or "ac"
        button_map = self.TV_BUTTON_MAP if remote_type == "tv" else self.AC_BUTTON_MAP

        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            print(f"[IRAdapter] Serial IR listening / 串口红外监听中: {port}")
        except Exception as e:
            print(f"[IRAdapter] Serial open failed: {e}")
            return

        while self._running:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                # 假设串口输出格式: "IR:0xFFA25D" 或 "IR:01"
                if line.startswith("IR:"):
                    code_str = line[3:]
                    if code_str.startswith("0x"):
                        code = int(code_str, 16)
                    else:
                        code = int(code_str)

                    input_id = button_map.get(code, f"ir_{code:04x}")
                    self._emit(Event(
                        device_type=DeviceType.IR_REMOTE,
                        device_id=self.device_id,
                        input_type=InputType.BUTTON,
                        input_id=input_id,
                        value=1,
                        raw_data={"code": code, "protocol": remote_type}
                    ))
            except Exception as e:
                print(f"[IRAdapter] Serial parse error: {e}")

        ser.close()

    def _run_broadlink(self):
        """Broadlink WiFi 红外转发器模式"""
        try:
            broadlink = importlib.import_module("broadlink")
        except ImportError:
            print(f"[IRAdapter] broadlink not installed. Run: pip install broadlink")
            return

        ip = self.config.get("ip")
        mac = self.config.get("mac")

        if not ip:
            print(f"[IRAdapter] No Broadlink IP configured / 未配置 Broadlink IP")
            return

        try:
            device = broadlink.hello(ip)
            if not device:
                print(f"[IRAdapter] Broadlink device not found / 未找到设备")
                return
            device.auth()
            print(f"[IRAdapter] Broadlink connected / 已连接: {ip}")
        except Exception as e:
            print(f"[IRAdapter] Broadlink init error: {e}")
            return

        remote_type = self.config.get("remote_type", "tv")
        button_map = self.TV_BUTTON_MAP if remote_type == "tv" else self.AC_BUTTON_MAP

        while self._running:
            try:
                # Broadlink 不支持被动接收，这里是模拟学习模式的轮询
                # 实际使用时通常需要配合外部脚本推送事件到本地 socket
                time.sleep(0.5)
            except Exception as e:
                print(f"[IRAdapter] Broadlink error: {e}")

    def _run_lirc(self):
        """lirc 模式（Linux GPIO）"""
        try:
            lirc_client = importlib.import_module("lirc")
        except ImportError:
            print(f"[IRAdapter] lirc not installed. Install python-lirc")
            return

        # lirc 通常通过 socket 接收事件
        # 这里提供一个基础框架，实际实现需根据具体 lirc 配置调整
        print(f"[IRAdapter] lirc mode requires Linux + lircd / lirc 模式需要 Linux + lircd")
